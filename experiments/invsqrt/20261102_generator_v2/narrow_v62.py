"""narrow_v62.py：窄 V 容器生成器（结构性重设计第一步，新文件）.

Why a new file（同 refit_variant62.py 的 single-line 论证）：
  1. width_opt62.py SHA 0075e006 是官方 PASS 基线（HMR 版，Q=149，
     verify_hmr_seed20261031.log score 2290413.64）。覆盖它会摧毁 fallback
     电路；本任务动的是 V 容器维度（与 A/R 拟合宽度正交），故新文件。
  2. 变体线 refit_variant62.py（BOTH/A18）动的是 A/R 系数位宽+行移位；
     本文件动的是主线 HMR 版的 V 容器（55→30）+ 行低位省略 + S6 重映射，
     故基于 width_opt62.py（主线 HMR 内核）派生，并在 narrow_v.md 说明两线关系。
  3. 系表用 BOTH 系 int_tables_R10_A20_quant.json（只读，不改拟合表，
     不读旧 KMB/tray/嵌入指令串）。BOTH 的 sA=2/sR=2 行移位写法参考
     refit_variant62.py（build_a1_q/build_r1_q），A1 两级内核直接复用
     refit_variant62._qa1_*（HMR init_and/del_and 原样保留）。

窄 V 设计（详见 narrow_v.md §1 重映射表）：
  Vn[0:30) 存逻辑 V[16:46)（Vn[k]=V[k+16]；V<2^45 故 Vn[29]=V[45]恒零 guard）。
  关键结构（相对初稿的修正：S6 曾用 transient 46 位扩展 + 30 位拷贝，
  实测 Q=201——双容器常驻；现改别名设计）：vd[0:46) 一次分配常驻
  （具名 22+5+33+46=106），Vn=vd[16:46) 为视图（view），行/QROM 全进 Vn 视图；
  vd[0:16) 自分配至 S6 保持为零（行片全在 Vn 内，square 不碰 vd），S6 直接
  right_rotate(vd,t)（旋转量与主线同为 t，无重映射偏移），舍入控制 vd[45]。
  - B 直装：V[16:45)=B[4:33)（29 位）→ Vn[0:29)；Vn[29] 不碰（恒零）。
  - A1 行 j=0..12（offset o=j+1+sA=j+3≤15<16）：减 Ahi>>(16-o) 进 Vn[0:)；
    MSB 行（o=14+sA=16）：加全 Ahi 进 Vn[0:)；低 drop=16-o 位不算。
  - R1 行 j=0..9（offset o=j+sR=j+2≤11<16）：加 S>>(16-o) 进 Vn[0:)；
    S 取 coef 高位（coef[16+drop:33)）；低 drop 位不算。
  - 行目标一律 Vn[0:30) 全片（进位向上传播到顶；真 Vn<2^29 无回绕，
    全域整数合同已验，见 prescreen_narrow_v.py --contract-full）。
  - S6：vd[0:46) 即 Vd[0:46)（低 16 真零，由常驻零区提供，无拷贝），barrel 同 t，
    舍入控制 vd[45]（=旧 Vd[t-1]；t≤16 时落在零区→舍入自然无操作，
    与整数模型 (Vd+2^(t-1))>>t 一致），+1 进 vd[0:36)，36×z_pow 不变；
    t+36>45 的高商位 wrap 进 vd[0:16) 零区（恒零）= 按零处理，
    正确性：wrap 目标恒零且真值恒零（V<2^45），同主线 t+36≤55 论证。
  - 逆向：数据严格镜像（S6 只逆 inc/barrel/t，不动 z_pow（D4 不变）；
    vd[0:16) 经 inc 逆 + barrel 逆回到全零，Vn 经 A1/R1/B 逆回到全零）。

断言重写：assert_tables_nv（BOTH 形状 wA=20/wR=10 + B 下界不变 +
  行 offset 上界静态断言 o<16/MSB o==16 + B 位偏移断言）；
  Q_CAP 收紧到实测峰值（初值 160，实测后收紧，见 narrow_v.md）。
"""

from __future__ import annotations

import hashlib
import json
import sys
from fractions import Fraction
from pathlib import Path

import kickmix as km

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import width_opt62 as W  # noqa: E402
import refit_variant62 as Q  # noqa: E402

ROOT = HERE.parents[2]
ART = ROOT / "artifacts/20261102_generator_v2/invsqrt"

CAND = "BOTH"
CFG = Q.CANDS[CAND]
W_A, W_R, N_R, S_A, S_R = CFG["wA"], CFG["wR"], CFG["nR"], CFG["sA"], CFG["sR"]


def set_cand(name: str) -> None:
    """Rebind module globals to another CANDS entry (call before building).

    All builders resolve W_A/W_R/N_R/S_A/S_R/CAND at call time from module
    globals, so rebinding is exact. nv_model_phase resolves None defaults
    at call time for the same reason (no def-time capture)."""
    global CAND, CFG, W_A, W_R, N_R, S_A, S_R
    if name not in Q.CANDS:
        raise KeyError(f"unknown cand {name}")
    CAND = name
    CFG = Q.CANDS[name]
    W_A, W_R, N_R, S_A, S_R = CFG["wA"], CFG["wR"], CFG["nR"], CFG["sA"], CFG["sR"]

W_X, W_LZ, W_B = W.W_X, W.W_LZ, W.W_B
W_D, W_U, W_S, S_OFF = W.W_D, W.W_U, W.W_S, W.S_OFF
W_P = W.W_P

V_LO = 16
W_VN = 30
V_TOP = V_LO + W_VN  # 46（逻辑顶；V<2^45 故 Vn[29]=V[45]恒零）
B_LO = 4  # B 直装位偏移（V[16:45)=B[4:33)，29 位进 Vn[0:29)）
# TH 收窄（2026-11-02，th_narrow.md）：行低 20 位全算（Vn[0:20)=V[16:36)），
# 高 Vn[20:30) 每行不碰；每行终进位 c3（0/1，减为 borrow 量）进 2 位有符号
# CARRY（two's complement，整数证据全域 C∈{-1,0,1}，前缀亦然）；最后一次
# 合并 High+=CARRY_unsigned，sign 时 High-=4（符号扩展）。删的是 36..44
# 全加器链，carry 本身不可删（th_carry_proof.py 小例 PASS 后进生成器）。
K_SPLIT = 20
W_CARRY = 2
CARRY_CORR = 4  # 1<<W_CARRY（High 长 10，4%1024≠0，修正激活）
Q_CAP = 132  # 实测峰值（TH 收窄后，double-build 确认；窄 V 初值 134）

TABLES_PATH = ART / "int_tables_R10_A20_quant.json"
OUT_KMB = ART / "narrow_v62.kmb"
OUT_STATS = ART / "narrow_v62_stats.json"

# Placement/shape consistency is enforced per-cand by assert_tables_nv below
# (BOTH: sA=2/sR=2/wA=20/wR=10/nR=10; A20R8: sA=2/sR=4/wA=20/wR=8/nR=8).


def assert_tables_nv(tables: W.CoefTables) -> None:
    """S0 重写：BOTH 形状 + V 非负下界（逻辑值不变）+ 窄 V 行放置静态断言."""
    assert len(tables.B) == len(tables.A) == len(tables.R) == 256
    assert all(0 <= v < 2**W_B for v in tables.B)
    assert all(0 <= v < 2**W_A for v in tables.A), "Ahi width"
    assert all(0 <= v < 2**W_R for v in tables.R), "Rhi width"
    assert min(tables.B) > (2**37 + 2**29) >> 12, "B 下界不足以保证 V 非负"
    # 行放置静态断言（窄 V 规则）：A 行 offset j+1+sA<16，MSB 行 ==16；
    # R 行 offset j+sR<16；B 直装 B[4:33) 恰 29 位进 Vn[0:29)。
    assert max(j + 1 + S_A for j in range(13)) < V_LO, "A1 行须全截短"
    assert W_D + S_A == V_LO, "A1 MSB 行须恰对齐容器底"
    assert max(j + S_R for j in range(N_R)) < V_LO, "R1 行须全截短"
    assert W_B - B_LO == W_VN - 1, "B 直装须恰为 Vn[0:29)"


def load_tables():
    return Q.load_qtables(CAND)


def nv_model_phase(x: int, B, Ah, Rh, sA=None, sR=None, wA=None, nR=None):
    if sA is None:
        sA = S_A
    if sR is None:
        sR = S_R
    if wA is None:
        wA = W_A
    if nR is None:
        nR = N_R
    """窄 V 整数 oracle：逐行低位省略的截短累加（与电路逐行对应）.

    Vn 单位（=逻辑>>16）：B 取 B>>4；A 行减 Ahi>>(16-o)；MSB 加全 Ahi；
    R 行加 S>>(16-o)。P 由 Vd=Vn<<16 经 (Vd+2^(t-1))>>t 求出（含 t≤16
    舍入自然无操作语义）。供 prescreen C / DUMP-V 用。
    """
    lz = 22 - x.bit_length()
    m = x << lz
    p = lz & 1
    a = (p << 7) | ((m >> 14) & 127)
    delta = m & 16383
    D = delta - 8192
    U = (delta >> 5) - 256
    S = U * U
    Vn = B[a] >> B_LO
    D14 = D & 0x3FFF
    for j in range(13):
        if (D14 >> j) & 1:
            o = j + 1 + sA
            assert o < V_LO
            Vn -= Ah[a] >> (V_LO - o)
    if (D14 >> 13) & 1:
        assert W_D + sA == V_LO
        Vn += Ah[a]
    for j in range(nR):
        if (Rh[a] >> j) & 1:
            o = j + sR
            assert o < V_LO
            Vn += S >> (V_LO - o)
    Vd = Vn << V_LO
    e = (lz >> 1) + p - 11
    t = 8 - e
    P = ((Vd + 2 ** (t - 1)) >> t) & (2**36 - 1)
    return Vn, Vd, t, P


# ---------------------------------------------------------------- B 直装（位偏移 QROM）
def qrom_sweep_off(b, it, table, lo: int, width: int, target) -> None:
    """单扫位偏移版：装 table[v][lo:lo+width) 进 target（CX 自逆，同 pattern 重放即卸载）."""
    for v in range(256):
        it.move_to(v)
        m = it.match_qubit
        tv = table[v]
        for j in range(width):
            if (tv >> (lo + j)) & 1:
                b.cx(m, target[j])


def mini_pass_off(b, x, lz, table, lo: int, width: int, target) -> None:
    addr = b.alloc_qubits(W.W_ADDR)
    W.build_addr(b, x, lz, addr)
    with b.unary_iteration(addr, range(256)) as it:
        qrom_sweep_off(b, it, table, lo, width, target)
    W.build_addr(b, x, lz, addr)
    b.free(addr)


# ---------------------------------------------------------------- B+A 联合解码（joint_decode.md）
# 配对：正向 F_B（Vn零初态直装）+ F_A_LOAD（coef零初态装载）共享一次
# unary decode；逆向 R_A_UNLOAD（coef回零）+ R_B（Vn回零）共享一次。
# 前提（任一不成立即否决该配对）：
#   J1 零初态（正向）：联合点前 coef 全零（S1/S2/D 皆不碰 coef）且
#      Vn 全零（vd 新分配，行尚未作用）。XOR 即整数加仅在零初态成立
#      （小例 nonzero-init 反例：init=31, tab=8 时 XOR=23≠ADDmod=7）。
#   J2 目标独立：Vn=vd[16:46) 与 coef 分属不同寄存器，无交叠；
#      同 match 下两组 CX 可任意序（均为对合且目标不交）。
#   J3 逆向自洽：联合点前 coef 恰为 A 表值（R_A_LOAD 后 A1_rev 只读 coef，
#      不写），Vn 恰为 B>>4（A1_rev 精确撤销 A1 贡献）；回放即双归零。
#      x/lz 自洽：D 恢复在联合之后，S2_rev/S1_rev 亦在后，故 addr 重算值
#      与正向同（A1/square/R1/S6 皆只读 x/lz，不写）。
# 否决记录：F_A_UNLOAD 不参与（A1 在中间，vn 已脏）；R_R 对不参与
#   （square-2 在中间，coef 已脏）。只做 B+A 这一对。
# 先证后建：/tmp joint_proof.py（4位地址16项穷举）JOINT-PROOF PASS：
#   joint==seq==table 32/32，roundtrip归零 ok，seq 28toff→joint 14toff。
def qrom_sweep_joint_ba(b, it, b_table, a_table, vn_tgt, coef_tgt) -> None:
    """单 decode 下双 pattern：B[lo:lo+29)→vn_tgt，A[0:20)→coef_tgt.

    同 match_qubit，两目标独立（J2），CX 均自逆；重放即联合卸载（J3）。
    """
    assert len(vn_tgt) == W_VN - 1 and len(coef_tgt) == W_A
    assert B_LO + (W_VN - 1) == W_B, "B 切片须恰为 B[4:33)"
    for v in range(256):
        it.move_to(v)
        m = it.match_qubit
        bv = b_table[v]
        for j in range(W_VN - 1):
            if (bv >> (B_LO + j)) & 1:
                b.cx(m, vn_tgt[j])
        av = a_table[v]
        for j in range(W_A):
            if (av >> j) & 1:
                b.cx(m, coef_tgt[j])


def joint_pass_ba(b, x, lz, b_table, a_table, vn_tgt, coef_tgt) -> None:
    """B+A 联合 mini-pass（装载与卸载同体，CX 自逆，重跑即另一向）."""
    addr = b.alloc_qubits(W.W_ADDR)
    W.build_addr(b, x, lz, addr)
    with b.unary_iteration(addr, range(256)) as it:
        qrom_sweep_joint_ba(b, it, b_table, a_table, vn_tgt, coef_tgt)
    W.build_addr(b, x, lz, addr)
    b.free(addr)


# ---------------------------------------------------------------- S1 二分 lz（温度计→二分，bs_lz.md）
# 动机：温度计 F_S1 42 flip / R_S1 82 flip（共 124×21CCX=2684），逆向贵一倍
# 纯属实现 artifact（rev 逐 i 重算+解散双阈值，正向滑动复用）；遗留估计
# “二分 31 比较+修正 vs 温度计 84”中 84 还是错的（实 124）。探针实锤：
# flip_if_less_than(x22, 2^k) 恒 21 CCX（无 2 幂优化，故全宽二分否决）；
# 切片 flip_if_equal(x[a:b],0) 耗 w CCX（1 位免费）。故 5 层切片谓词 +
# MUX 修正 + 折叠解码直达 lz：F-first 字典序叶序（内层选择变化最快），
# L5 不建 MUX 树（10 哑叶剪枝后直接并入解码：16 路 AND4 + 对位叶重算）。
# 先证后建：numpy 4M 全域 + narrow_proof.py 缩比穷举 + /tmp 全宽定向 PASS。
_BS_L2 = [((17, 22),), ((5, 11),)]                                  # F T
_BS_L3 = [((20, 22),), ((14, 17),), ((8, 11),), ((2, 5),)]          # FF FT TF TT
_BS_L4 = [((21, 22),), ((18, 20),), ((15, 17),), ((12, 14),),
          ((9, 11),), ((6, 8),), ((3, 5),), ((1, 2),)]
_BS_TH3 = {(True, True): 2, (True, False): 8, (False, True): 14, (False, False): 20}
_BS_TH4 = {(True, True, True): 1, (True, True, False): 3, (True, False, True): 6,
           (True, False, False): 9, (False, True, True): 12, (False, True, False): 15,
           (False, False, True): 18, (False, False, False): 21}


def _bs_decode_entries():
    """构建时整数推导：e=0..21 代表元走阈值树，得 path4→单叶 e / 对位 (eT,eF).

    纯确定性整数循环（无随机、无 KMB、无拟合表）；对位叶谓词恒为
    (x[eT+1]==0)（阈值位，1 位重算免费）。numpy 全域已交叉验证。"""
    groups = {}
    for e in range(22):
        x = 1 << e
        d1 = x < 2**11
        d2 = (x < 2**5) if d1 else (x < 2**17)
        d3 = x < 2**_BS_TH3[(d1, d2)]
        d4 = x < 2**_BS_TH4[(d1, d2, d3)]
        groups.setdefault((d1, d2, d3, d4), []).append(e)
    assert len(groups) == 16
    dec = {}
    for path, es in groups.items():
        assert len(es) in (1, 2) and (len(es) == 1 or es[1] - es[0] == 1)
        if len(es) == 1:
            dec[path] = ("s", 21 - es[0])
        else:
            dec[path] = ("p", 21 - es[0], 21 - es[1], es[0])
    return dec


_BS_DEC = _bs_decode_entries()


def _bs_mux2(b, s, aT, aF, o) -> None:
    """2:1 MUX（o ^= s?a:b，s 保持；对合，复跑即撤销）。"""
    b.ccx(s, aT, o)
    b.x(s)
    b.ccx(s, aF, o)
    b.x(s)


def _bs_pred_c(b, x, spec, t) -> None:
    """切片零谓词 t ^= (x[a:b]==0)；1 位时退化为 X+CX（0 toff）。"""
    a, bb = spec
    if bb - a == 1:
        b.x(t)
        b.cx(x[a], t)
    else:
        b.flip_if_equal(x[a:bb], 0, target=t)


def _bs_pred_u(b, x, spec, t) -> None:
    a, bb = spec
    if bb - a == 1:
        b.cx(x[a], t)
        b.x(t)
    else:
        b.flip_if_equal(x[a:bb], 0, target=t)


def _bs_tree_mux(b, x, sels, specs, out) -> None:
    """keep-all MUX 树：叶谓词全算→逐层 MUX→CX 入 out→严格逆序清零。

    叶序为 F-first 字典序（内层选择变化最快），故相邻配对恒为 [F,T]，
    复用同一 mux2(s, T=cur[i+1], F=cur[i])。自逆块，rev 复用同一函数。"""
    leaves = []
    for (spec,) in specs:
        t = b.alloc_qubits(1)
        _bs_pred_c(b, x, spec, t[0])
        leaves.append(t)
    layers = [leaves]
    cur = leaves
    si = len(sels) - 1
    while len(cur) > 1:
        s = sels[si]
        si -= 1
        nxt = []
        for i in range(0, len(cur), 2):
            m = b.alloc_qubits(1)
            _bs_mux2(b, s, cur[i + 1][0], cur[i][0], m[0])
            nxt.append(m)
        layers.append(nxt)
        cur = nxt
    assert len(cur) == 1
    b.cx(cur[0][0], out)
    for li in range(len(layers) - 1, 0, -1):
        s = sels[len(sels) - li]
        up, lo = layers[li], layers[li - 1]
        for k in range(len(up)):
            _bs_mux2(b, s, lo[2 * k + 1][0], lo[2 * k][0], up[k][0])
        for m in up:
            b.free(m)
    for (spec,), t in zip(reversed(specs), reversed(leaves)):
        _bs_pred_u(b, x, spec, t[0])
        b.free(t)


def _bs_and4_c(b, dd, path, ts, m) -> None:
    fx = [k for k in range(4) if not path[k]]
    for k in fx:
        b.x(dd[k])
    b.init_and(dd[0], dd[1], ts[0])
    b.init_and(dd[2], dd[3], ts[1])
    b.init_and(ts[0], ts[1], m[0])


def _bs_and4_u(b, dd, path, ts, m) -> None:
    fx = [k for k in range(4) if not path[k]]
    b.del_and(ts[0], ts[1], m[0])
    b.del_and(dd[2], dd[3], ts[1])
    b.del_and(dd[0], dd[1], ts[0])
    for k in fx:
        b.x(dd[k])


def _bs_decode_fwd(b, dd, lz, x) -> None:
    """折叠解码（L5 层）：16 路 path4→AND4 匹配；单叶直接 CX，对位叶重算
    1 位阈值并按 (bT,bF) 混合写入。自逆，rev 复用同一函数清 lz。"""
    for path, info in _BS_DEC.items():
        m = b.alloc_qubits(1)
        ts = b.alloc_qubits(2)
        _bs_and4_c(b, dd, path, ts, m)
        if info[0] == "s":
            for k in range(W.W_LZ):
                if (info[1] >> k) & 1:
                    b.cx(m[0], lz[k])
        else:
            _, lzT, lzF, eT = info
            t = b.alloc_qubits(1)
            b.x(t[0])
            b.cx(x[eT + 1], t[0])
            for k in range(W.W_LZ):
                bT = (lzT >> k) & 1
                bF = (lzF >> k) & 1
                if bT and bF:
                    b.cx(m[0], lz[k])
                elif (not bT) and bF:
                    b.cx(m[0], lz[k])
                    b.ccx(m[0], t[0], lz[k])
                elif bT and (not bF):
                    b.ccx(m[0], t[0], lz[k])
            b.cx(x[eT + 1], t[0])
            b.x(t[0])
            b.free(t)
        _bs_and4_u(b, dd, path, ts, m)
        b.free(ts)
        b.free(m)


def _bs_levels_fwd(b, x, dd) -> None:
    """d1..d4 由 x 重算（正逆共用；逆向先重算再解码清 lz）。"""
    _bs_pred_c(b, x, (11, 22), dd[0])
    _bs_tree_mux(b, x, [dd[0]], _BS_L2, dd[1])
    _bs_tree_mux(b, x, [dd[0], dd[1]], _BS_L3, dd[2])
    _bs_tree_mux(b, x, [dd[0], dd[1], dd[2]], _BS_L4, dd[3])


def _bs_levels_rev(b, x, dd) -> None:
    """d4..d1 倒序清零（严格镜像）。"""
    _bs_tree_mux(b, x, [dd[0], dd[1], dd[2]], _BS_L4, dd[3])
    _bs_tree_mux(b, x, [dd[0], dd[1]], _BS_L3, dd[2])
    _bs_tree_mux(b, x, [dd[0]], _BS_L2, dd[1])
    _bs_pred_u(b, x, (11, 22), dd[0])


def build_bs_fwd(b, x, lz, d) -> None:
    """S1 二分正向：x≥1 → lz=22-bit_length(x)。d 纯暂存（进零出零，Bennett
    compute-copy-uncompute；F/R 间 d 不存活，rev 由 x 重算，对称等价）。"""
    dd = [d[i] for i in range(5)]
    _bs_levels_fwd(b, x, dd)
    _bs_decode_fwd(b, dd[:4], lz, x)
    _bs_levels_rev(b, x, dd)


def build_bs_rev(b, x, lz, d) -> None:
    """S1 二分逆向：与正向同序列（levels 自逆、解码自逆；正向已清 d，
    此处重算 d→解码清 lz→再清 d）。与温度计 rev 重算阈值同模式。"""
    dd = [d[i] for i in range(5)]
    _bs_levels_fwd(b, x, dd)
    _bs_decode_fwd(b, dd[:4], lz, x)
    _bs_levels_rev(b, x, dd)


# ---------------------------------------------------------------- A1/R1 窄行（低位省略）
# TH 收窄行内核：Q._qa1_* 的 TH 部分替换（其余逐行照抄，HMR 结构不动）。
# 加行：Trem+=c2 后 c3=c2&(Trem_new==0)，CARRY+=c3；减行：c3=c2&(Trem_old==0)
# 先算，CARRY-=c3，再 Trem-=c2。rem 空（MSB，n0+n1==20）时 c3=c2 直进 CARRY。
# 正确性：th_carry_proof.py（整数 + 量子小例 + 修正激活 + roundtrip）PASS。
def _tha1_add_fwd(b, S, Tslice, ctl, n0, n1, carry) -> None:
    S0 = S[0:n0]; S1 = S[n0:n0 + n1]
    T0 = Tslice[0:n0]; T1 = Tslice[n0:n0 + n1]
    Trem = Tslice[n0 + n1:K_SPLIT]
    Cp0 = b.alloc_qubits(n0); ca0 = b.alloc_qubits(1); c1 = b.alloc_qubits(1)
    for i in range(n0):
        b.init_and(ctl, S0[i], Cp0[i])
    for i in range(n0):
        W._narrow_maj(b, Cp0[i], T0[i], ca0[0])
    b.cx(ca0[0], c1[0])
    for i in reversed(range(n0)):
        W._narrow_uma(b, Cp0[i], T0[i], ca0[0])
    for i in reversed(range(n0)):
        b.del_and(ctl, S0[i], Cp0[i])
    b.free(Cp0); b.free(ca0)
    Cp1 = b.alloc_qubits(n1)
    for i in range(n1):
        b.init_and(ctl, S1[i], Cp1[i])
    b.iadd(Cp1, target=T1)
    for i in reversed(range(n1)):
        b.del_and(ctl, S1[i], Cp1[i])
    b.free(Cp1)
    b.iadd(c1, target=T1)
    CpB = b.alloc_qubits(n1)
    for i in range(n1):
        b.init_and(ctl, S1[i], CpB[i])
    lt = b.alloc_qubits(1); eq = b.alloc_qubits(1)
    b.flip_if_less_than(T1, CpB, target=lt[0])
    b.flip_if_equal(T1, CpB, target=eq[0])
    s = b.alloc_qubits(1); c2 = b.alloc_qubits(1)
    b.init_and(c1[0], eq[0], s[0])
    b.cx(lt[0], c2[0]); b.cx(s[0], c2[0])
    for i in reversed(range(n1)):
        b.del_and(ctl, S1[i], CpB[i])
    b.free(CpB)
    # TH 收窄替换（原 b.iadd(c2→TH)，TH=Tslice[n0+n1:] 全长）：
    if len(Trem) == 0:
        b.iadd(c2, target=carry)
    else:
        b.iadd(c2, target=Trem)
        tmp = b.alloc_qubits(1)
        b.flip_if_less_than(Trem, 1, target=tmp[0])
        c3 = b.alloc_qubits(1)
        b.init_and(c2[0], tmp[0], c3[0])
        b.iadd(c3, target=carry)
        b.del_and(c2[0], tmp[0], c3[0]); b.free(c3)
        b.flip_if_less_than(Trem, 1, target=tmp[0]); b.free(tmp)
    b.cx(s[0], c2[0]); b.cx(lt[0], c2[0]); b.free(c2)
    b.del_and(c1[0], eq[0], s[0]); b.free(s)
    CpC = b.alloc_qubits(n1)
    for i in range(n1):
        b.init_and(ctl, S1[i], CpC[i])
    b.flip_if_equal(T1, CpC, target=eq[0])
    for i in reversed(range(n1)):
        b.del_and(ctl, S1[i], CpC[i])
    b.free(CpC); b.free(eq)
    CpD = b.alloc_qubits(n1)
    for i in range(n1):
        b.init_and(ctl, S1[i], CpD[i])
    b.flip_if_less_than(T1, CpD, target=lt[0])
    for i in reversed(range(n1)):
        b.del_and(ctl, S1[i], CpD[i])
    b.free(CpD); b.free(lt)
    Cp0B = b.alloc_qubits(n0)
    for i in range(n0):
        b.init_and(ctl, S0[i], Cp0B[i])
    b.flip_if_less_than(T0, Cp0B, target=c1[0])
    for i in reversed(range(n0)):
        b.del_and(ctl, S0[i], Cp0B[i])
    b.free(Cp0B); b.free(c1)


def _tha1_sub_fwd(b, S, Tslice, ctl, n0, n1, carry) -> None:
    S0 = S[0:n0]; S1 = S[n0:n0 + n1]
    T0 = Tslice[0:n0]; T1 = Tslice[n0:n0 + n1]
    Trem = Tslice[n0 + n1:K_SPLIT]
    c1 = b.alloc_qubits(1)
    Cp0a = b.alloc_qubits(n0)
    for i in range(n0):
        b.init_and(ctl, S0[i], Cp0a[i])
    b.flip_if_less_than(T0, Cp0a, target=c1[0])
    for i in reversed(range(n0)):
        b.del_and(ctl, S0[i], Cp0a[i])
    b.free(Cp0a)
    lt = b.alloc_qubits(1)
    Cp1a = b.alloc_qubits(n1)
    for i in range(n1):
        b.init_and(ctl, S1[i], Cp1a[i])
    b.flip_if_less_than(T1, Cp1a, target=lt[0])
    for i in reversed(range(n1)):
        b.del_and(ctl, S1[i], Cp1a[i])
    b.free(Cp1a)
    eq = b.alloc_qubits(1)
    Cp1b = b.alloc_qubits(n1)
    for i in range(n1):
        b.init_and(ctl, S1[i], Cp1b[i])
    b.flip_if_equal(T1, Cp1b, target=eq[0])
    for i in reversed(range(n1)):
        b.del_and(ctl, S1[i], Cp1b[i])
    b.free(Cp1b)
    s = b.alloc_qubits(1); c2 = b.alloc_qubits(1)
    b.init_and(c1[0], eq[0], s[0])
    b.cx(lt[0], c2[0]); b.cx(s[0], c2[0])
    # TH 收窄替换（原 b.isub(c2→TH）)：
    if len(Trem) == 0:
        b.isub(c2, target=carry)
    else:
        tmp = b.alloc_qubits(1)
        b.flip_if_less_than(Trem, 1, target=tmp[0])
        c3 = b.alloc_qubits(1)
        b.init_and(c2[0], tmp[0], c3[0])
        b.isub(c3, target=carry)
        b.del_and(c2[0], tmp[0], c3[0]); b.free(c3)
        b.flip_if_less_than(Trem, 1, target=tmp[0]); b.free(tmp)
        b.isub(c2, target=Trem)
    b.cx(s[0], c2[0]); b.cx(lt[0], c2[0]); b.free(c2)
    b.del_and(c1[0], eq[0], s[0]); b.free(s)
    Cp1c = b.alloc_qubits(n1)
    for i in range(n1):
        b.init_and(ctl, S1[i], Cp1c[i])
    b.flip_if_equal(T1, Cp1c, target=eq[0])
    for i in reversed(range(n1)):
        b.del_and(ctl, S1[i], Cp1c[i])
    b.free(Cp1c); b.free(eq)
    Cp1d = b.alloc_qubits(n1)
    for i in range(n1):
        b.init_and(ctl, S1[i], Cp1d[i])
    b.flip_if_less_than(T1, Cp1d, target=lt[0])
    for i in reversed(range(n1)):
        b.del_and(ctl, S1[i], Cp1d[i])
    b.free(Cp1d); b.free(lt)
    b.isub(c1, target=T1)
    Cp1e = b.alloc_qubits(n1)
    for i in range(n1):
        b.init_and(ctl, S1[i], Cp1e[i])
    b.isub(Cp1e, target=T1)
    for i in reversed(range(n1)):
        b.del_and(ctl, S1[i], Cp1e[i])
    b.free(Cp1e)
    Cp0b = b.alloc_qubits(n0); ca0 = b.alloc_qubits(1)
    for i in range(n0):
        b.init_and(ctl, S0[i], Cp0b[i])
    for i in range(n0):
        W._narrow_uma_inv(b, Cp0b[i], T0[i], ca0[0])
    b.cx(ca0[0], c1[0])
    for i in reversed(range(n0)):
        W._narrow_maj_inv(b, Cp0b[i], T0[i], ca0[0])
    for i in reversed(range(n0)):
        b.del_and(ctl, S0[i], Cp0b[i])
    b.free(Cp0b); b.free(ca0); b.free(c1)


def build_a1_nv(b, x, coef, vn, carry) -> None:
    """A1 窄 V + TH 收窄版：行 j 减 Ahi 高位进 Vn[0:20)；终进位 c3 进 CARRY.

    两级内核为 _tha1_*（Q._qa1_* 的 TH 收窄版，n0'/n1' 按截短后位宽取半；
    HMR init_and/del_and 在内核内部原样保留；高 Vn[20:30) 本阶段不碰，
    最后一次合并进 High）。
    """
    for j in range(13):
        o = j + 1 + S_A
        assert o < V_LO
        drop = V_LO - o
        wp = W_A - drop
        n0, n1 = wp // 2, wp - wp // 2
        b.info_tag(f"STAGE:A1_J{j}_ENTER")
        _tha1_sub_fwd(b, coef[drop:drop + wp], vn[0:W_VN], x[j], n0, n1, carry)
        b.info_tag(f"STAGE:A1_J{j}_EXIT")
    b.info_tag("STAGE:A1_J13_ENTER")
    n0, n1 = W_A // 2, W_A - W_A // 2
    _tha1_add_fwd(b, coef[0:W_A], vn[0:W_VN], x[13], n0, n1, carry)
    b.info_tag("STAGE:A1_J13_EXIT")


def build_a1_nv_rev(b, x, coef, vn, carry) -> None:
    b.info_tag("STAGE:A1R_J13_ENTER")
    n0, n1 = W_A // 2, W_A - W_A // 2
    _tha1_sub_fwd(b, coef[0:W_A], vn[0:W_VN], x[13], n0, n1, carry)
    b.info_tag("STAGE:A1R_J13_EXIT")
    for j in reversed(range(13)):
        o = j + 1 + S_A
        assert o < V_LO
        drop = V_LO - o
        wp = W_A - drop
        n0, n1 = wp // 2, wp - wp // 2
        b.info_tag(f"STAGE:A1R_J{j}_ENTER")
        _tha1_add_fwd(b, coef[drop:drop + wp], vn[0:W_VN], x[j], n0, n1, carry)
        b.info_tag(f"STAGE:A1R_J{j}_EXIT")


def _nvr1_row_fwd(b, S, Tslice, ctl, nS: int, carry) -> None:
    """单行窄加通用化 + TH 收窄（W._narrow_r1_row_fwd 的 nS 参数版 + TH 收窄）.

    低 nS 位 Cuccaro（HMR init_and/del_and 原样）；余 Trem=Tslice[nS:20)
    单比特传播；终进位 c3=cout&(Trem_new==0) 进 CARRY；高 Tslice[20:] 不碰。
    """
    Tlow = Tslice[0:nS]
    Trem = Tslice[nS:K_SPLIT]
    Cp = b.alloc_qubits(nS)
    carry0 = b.alloc_qubits(1)
    cout = b.alloc_qubits(1)
    for i in range(nS):
        b.init_and(ctl, S[i], Cp[i])
    for i in range(nS):
        W._narrow_maj(b, Cp[i], Tlow[i], carry0[0])
    b.cx(carry0[0], cout[0])
    for i in reversed(range(nS)):
        W._narrow_uma(b, Cp[i], Tlow[i], carry0[0])
    for i in reversed(range(nS)):
        b.del_and(ctl, S[i], Cp[i])
    b.free(Cp)
    b.free(carry0)
    b.iadd(cout, target=Trem)
    tmp = b.alloc_qubits(1)
    b.flip_if_less_than(Trem, 1, target=tmp[0])
    c3 = b.alloc_qubits(1)
    b.init_and(cout[0], tmp[0], c3[0])
    b.iadd(c3, target=carry)
    b.del_and(cout[0], tmp[0], c3[0]); b.free(c3)
    b.flip_if_less_than(Trem, 1, target=tmp[0]); b.free(tmp)
    Cp2 = b.alloc_qubits(nS)
    for i in range(nS):
        b.init_and(ctl, S[i], Cp2[i])
    b.flip_if_less_than(Tlow, Cp2, target=cout[0])
    for i in reversed(range(nS)):
        b.del_and(ctl, S[i], Cp2[i])
    b.free(Cp2)
    b.free(cout)


def _nvr1_row_rev(b, S, Tslice, ctl, nS: int, carry) -> None:
    """单行窄减（正向 TH 收窄版的严格逆；copy 对同 HMR）。"""
    Tlow = Tslice[0:nS]
    Trem = Tslice[nS:K_SPLIT]
    cout = b.alloc_qubits(1)
    Cp = b.alloc_qubits(nS)
    for i in range(nS):
        b.init_and(ctl, S[i], Cp[i])
    b.flip_if_less_than(Tlow, Cp, target=cout[0])
    for i in reversed(range(nS)):
        b.del_and(ctl, S[i], Cp[i])
    b.free(Cp)
    tmp = b.alloc_qubits(1)
    b.flip_if_less_than(Trem, 1, target=tmp[0])
    c3 = b.alloc_qubits(1)
    b.init_and(cout[0], tmp[0], c3[0])
    b.isub(c3, target=carry)
    b.del_and(cout[0], tmp[0], c3[0]); b.free(c3)
    b.flip_if_less_than(Trem, 1, target=tmp[0]); b.free(tmp)
    b.isub(cout, target=Trem)
    Cp2 = b.alloc_qubits(nS)
    carry0 = b.alloc_qubits(1)
    for i in range(nS):
        b.init_and(ctl, S[i], Cp2[i])
    for i in range(nS):
        W._narrow_uma_inv(b, Cp2[i], Tlow[i], carry0[0])
    b.cx(carry0[0], cout[0])
    for i in reversed(range(nS)):
        W._narrow_maj_inv(b, Cp2[i], Tlow[i], carry0[0])
    for i in reversed(range(nS)):
        b.del_and(ctl, S[i], Cp2[i])
    b.free(Cp2)
    b.free(carry0)
    b.free(cout)


def build_r1_nv(b, coef, vn, carry) -> None:
    """R1 窄 V + TH 收窄版：行 j 加 S 高位进 Vn[0:20)；终进位进 CARRY."""
    for j in range(N_R):
        o = j + S_R
        assert o < V_LO
        drop = V_LO - o
        wp = W_S - drop
        b.info_tag(f"STAGE:R1_J{j}_ENTER")
        _nvr1_row_fwd(b, coef[S_OFF + drop:S_OFF + W_S], vn[0:W_VN], coef[j], wp, carry)
        b.info_tag(f"STAGE:R1_J{j}_EXIT")


def build_r1_nv_rev(b, coef, vn, carry) -> None:
    for j in reversed(range(N_R)):
        o = j + S_R
        assert o < V_LO
        drop = V_LO - o
        wp = W_S - drop
        b.info_tag(f"STAGE:R1R_J{j}_ENTER")
        _nvr1_row_rev(b, coef[S_OFF + drop:S_OFF + W_S], vn[0:W_VN], coef[j], wp, carry)
        b.info_tag(f"STAGE:R1R_J{j}_EXIT")


# ---------------------------------------------------------------- TH 合并（一次）
def merge_carry_fwd(b, vn, carry) -> None:
    """合并：High(Vn[20:30)) += CARRY_unsigned；sign 时 High -= 4."""
    High = vn[K_SPLIT:W_VN]
    b.iadd(carry, target=High)
    b.isub(CARRY_CORR, target=High, control=carry[1])


def merge_carry_rev(b, vn, carry) -> None:
    """合并之逆（严格逆序）：sign 时 High += 4；High -= CARRY_unsigned."""
    High = vn[K_SPLIT:W_VN]
    b.iadd(CARRY_CORR, target=High, control=carry[1])
    b.isub(carry, target=High)


# ---------------------------------------------------------------- S6（别名 barrel）
def build_s6_nv(b, lz, vd, coef) -> None:
    """S6 窄 V 版：vd[0:46) 即 Vd[0:46)（vd[0:16) 为常驻零区，Vn=vd[16:46)）.

    t 计算与主线同（t∈8…19）；barrel 旋转量同为 t（vd 位序 = Vd 位序，
    无重映射偏移——别名设计的核心简化）；舍入控制 vd[45]（=旧 Vd[t-1]；
    t≤16 落零区→无操作，与模型 (Vd+2^(t-1))>>t 一致）；商 vd[0:36)
    （=Vd[t:t+36)，t+36>45 的高位 wrap 进 vd[0:16) 零区 = 按零处理；
    wrap 正确性：目标恒零且真值恒零（V<2^45），同主线 t+36≤55 论证）；
    常数增量复用 W._narrow_s6_inc_fwd（18/18+flip，峰值 19）。
    """
    t = coef[0:5]
    b.iadd(11, target=t)
    b.isub(lz[1:W_LZ], target=t)
    b.isub(lz[0:1], target=t)
    b.iadd(8, target=t)
    b.right_rotate(vd, t)
    W._narrow_s6_inc_fwd(b, vd[0:W_P], vd[V_TOP - 1])
    for k in range(W_P):
        b.z_pow(vd[k], Fraction(2**k, 2**35))


def build_s6_nv_rev(b, lz, vd, coef) -> None:
    """S6 逆：只逆数据（舍入撤销→barrel 逆→t 清零），不动 z_pow（D4 不变）.

    逆后 vd[0:16) 回到全零（inc 逆 + 旋转逆精确恢复），vd[16:46)=Vn 脏值
    留给后续 A1/R1/B 逆继续 uncompute。
    """
    t = coef[0:5]
    W._narrow_s6_inc_rev(b, vd[0:W_P], vd[V_TOP - 1])
    b.left_rotate(vd, t)
    b.isub(8, target=t)
    b.iadd(lz[0:1], target=t)
    b.iadd(lz[1:W_LZ], target=t)
    b.isub(11, target=t)


# ---------------------------------------------------------------- S7/S8 调度
def create_regs_nv(b):
    x = b.create_quantum_register(W_X, name="x")
    lz = b.alloc_qubits(W_LZ)
    coef = b.alloc_qubits(W_B)
    vd = b.alloc_qubits(V_TOP)
    carry = b.alloc_qubits(W_CARRY)
    regs = {"x": x, "lz": lz, "coef": coef, "vd": vd, "carry": carry}
    regs["vn"] = vd[V_LO:V_TOP]
    return regs


def build_forward_nv(b, tables, regs) -> None:
    assert_tables_nv(tables)
    x, lz, coef, vd = (regs[k] for k in ("x", "lz", "coef", "vd"))
    vn = regs["vn"]
    carry = regs["carry"]
    b.info_tag("STAGE:F_S1_ENTER")
    d5 = b.alloc_qubits(5)
    build_bs_fwd(b, x, lz, d5)
    b.free(d5)
    b.info_tag("STAGE:F_S1_EXIT")
    b.info_tag("STAGE:F_S2_ENTER")
    W.build_normalize(b, x, lz)
    b.info_tag("STAGE:F_S2_EXIT")
    b.info_tag("STAGE:F_D_ENTER")
    b.isub(8192, target=x[0:W.W_DELTA])
    b.info_tag("STAGE:F_D_EXIT")
    b.info_tag("STAGE:F_BA_JOINT_ENTER")
    joint_pass_ba(b, x, lz, tables.B, tables.A, vn[0:W_VN - 1], coef[0:W_A])
    b.info_tag("STAGE:F_BA_JOINT_EXIT")
    b.info_tag("STAGE:F_A1_ENTER")
    build_a1_nv(b, x, coef, vn, carry)
    b.info_tag("STAGE:F_A1_EXIT")
    b.info_tag("STAGE:F_A_UNLOAD_ENTER")
    W.mini_pass(b, x, lz, tables.A, W_A, coef[0:W_A])
    b.info_tag("STAGE:F_A_UNLOAD_EXIT")
    b.info_tag("STAGE:F_S3P_ENTER")
    W.build_square2(b, x, coef)
    b.info_tag("STAGE:F_S3P_EXIT")
    b.info_tag("STAGE:F_R_LOAD_ENTER")
    W.mini_pass(b, x, lz, tables.R, W_R, coef[0:W_R])
    b.info_tag("STAGE:F_R_LOAD_EXIT")
    b.info_tag("STAGE:F_R1_ENTER")
    build_r1_nv(b, coef, vn, carry)
    b.info_tag("STAGE:F_R1_EXIT")
    b.info_tag("STAGE:F_R_UNLOAD_ENTER")
    W.mini_pass(b, x, lz, tables.R, W_R, coef[0:W_R])
    b.info_tag("STAGE:F_R_UNLOAD_EXIT")
    b.info_tag("STAGE:F_TH_MERGE_ENTER")
    merge_carry_fwd(b, vn, carry)
    b.info_tag("STAGE:F_TH_MERGE_EXIT")
    b.info_tag("STAGE:F_S6_ENTER")
    build_s6_nv(b, lz, vd, coef)
    b.info_tag("STAGE:F_S6_EXIT")


def build_reverse_nv(b, tables, regs) -> None:
    x, lz, coef, vd = (regs[k] for k in ("x", "lz", "coef", "vd"))
    vn = regs["vn"]
    carry = regs["carry"]
    b.info_tag("STAGE:R_S6_ENTER")
    build_s6_nv_rev(b, lz, vd, coef)
    b.info_tag("STAGE:R_S6_EXIT")
    b.info_tag("STAGE:R_TH_MERGE_ENTER")
    merge_carry_rev(b, vn, carry)
    b.info_tag("STAGE:R_TH_MERGE_EXIT")
    b.info_tag("STAGE:R_R_LOAD_ENTER")
    W.mini_pass(b, x, lz, tables.R, W_R, coef[0:W_R])
    b.info_tag("STAGE:R_R_LOAD_EXIT")
    b.info_tag("STAGE:R_R1_ENTER")
    build_r1_nv_rev(b, coef, vn, carry)
    b.info_tag("STAGE:R_R1_EXIT")
    b.info_tag("STAGE:R_R_UNLOAD_ENTER")
    W.mini_pass(b, x, lz, tables.R, W_R, coef[0:W_R])
    b.info_tag("STAGE:R_R_UNLOAD_EXIT")
    b.info_tag("STAGE:R_S3P_ENTER")
    W.build_square2_rev(b, x, coef)
    b.info_tag("STAGE:R_S3P_EXIT")
    b.info_tag("STAGE:R_A_LOAD_ENTER")
    W.mini_pass(b, x, lz, tables.A, W_A, coef[0:W_A])
    b.info_tag("STAGE:R_A_LOAD_EXIT")
    b.info_tag("STAGE:R_A1_ENTER")
    build_a1_nv_rev(b, x, coef, vn, carry)
    b.info_tag("STAGE:R_A1_EXIT")
    b.info_tag("STAGE:R_AB_JOINT_ENTER")
    joint_pass_ba(b, x, lz, tables.B, tables.A, vn[0:W_VN - 1], coef[0:W_A])
    b.info_tag("STAGE:R_AB_JOINT_EXIT")
    b.info_tag("STAGE:R_D_ENTER")
    b.iadd(8192, target=x[0:W.W_DELTA])
    b.info_tag("STAGE:R_D_EXIT")
    b.info_tag("STAGE:R_S2_ENTER")
    W.build_normalize_rev(b, x, lz)
    b.info_tag("STAGE:R_S2_EXIT")
    b.info_tag("STAGE:R_S1_ENTER")
    d5 = b.alloc_qubits(5)
    build_bs_rev(b, x, lz, d5)
    b.free(d5)
    b.info_tag("STAGE:R_S1_EXIT")


def build_circuit_nv(tables=None):
    tables = load_tables() if tables is None else tables
    b = km.CircuitBuilder()
    regs = create_regs_nv(b)
    build_forward_nv(b, tables, regs)
    build_reverse_nv(b, tables, regs)
    circuit = b.finish_circuit()
    assert circuit.num_qubits <= Q_CAP, f"qubits {circuit.num_qubits} > cap {Q_CAP}"
    return circuit


def circuit_sha_nv(circuit) -> str:
    return hashlib.sha256(str(circuit).encode()).hexdigest()


def main(cand: str = "BOTH") -> None:
    set_cand(cand)
    tables = load_tables()
    assert_tables_nv(tables)
    c1 = build_circuit_nv(tables)
    c2 = build_circuit_nv(tables)
    assert str(c1) == str(c2), "两次构建逐指令不一致"
    sha = circuit_sha_nv(c1)
    print("sha256:", sha, "qubits:", c1.num_qubits)
    out_kmb = ART / f"narrow_v62_{cand.lower()}.kmb"
    out_stats = ART / f"narrow_v62_{cand.lower()}_stats.json"
    out_kmb.parent.mkdir(parents=True, exist_ok=True)
    c1.to_file(out_kmb, format="kmb")
    stats = W.resource_stats(c1)
    stats["int_tables_sha256"] = hashlib.sha256(
        json.dumps(
            {"B": list(tables.B), "A": list(tables.A), "R": list(tables.R)},
            sort_keys=True,
        ).encode()
    ).hexdigest()
    stats["cand"] = CAND
    out_stats.write_text(json.dumps(stats, indent=2, sort_keys=True) + "\n")
    print("wrote", out_kmb, "and", out_stats)
    print(json.dumps(stats, indent=2, sort_keys=True)[:2000])


if __name__ == "__main__":
    import argparse

    _ap = argparse.ArgumentParser()
    _ap.add_argument("--cand", default="BOTH")
    main(cand=_ap.parse_args().cand)
