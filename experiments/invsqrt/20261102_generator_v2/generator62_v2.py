"""generator62_v2.py：独立整数生成器（阶段二实现，首版）.

定点合同（主线程已验证，全域 PASS：maxrel 0.6096，最小余量 271129065 units，
V 在 (0,2^45) 内）由 contract62.py 保证；本文件只做可逆电路实现，不做数值拟合，
不读旧 KMB/tray/嵌入指令串。系数表由调用方注入（main 从已验证 JSON 读入）。

调度（S7 正向 / S8 逆向，Bennett 镜像）：
  S0 供表断言 → S1 温度计比较求 lz + 优先编码（滑动窗口，2 比较线+1 编码线）
  → S2 原地 rotl 归一化 → D 原地变换 → B 直接装载进 V（mini-pass）
  → A 装载/使用/卸载（mini-pass 拆分，算术在 pass 外）
  → S3' 平方（U 由 D 重建，S 进 coef[16:33)）
  → R 装载/使用/卸载 → S6（t 全 5 位 → barrel → 舍入 → 36×z_pow）
  → 全逆转。终态除 x 外全归零，Q ≤ 160（实测峰值 160，余量 0，见下）。

宽度账本（具名寄存器）：x22 + lz5 + coef33 + V55 = 115；
  addr8 按 mini-pass 现配现释（算术期不持有）；unary 暂存 8 只在 sweep 期；
  kickmix iadd/isub/flip 内部 ripple 暂存 ≈ len(target)（实测，见下）。
  峰值 = 115 + 45（R1-j0 行目标 V[0:45)）= 160。

与 §3–§4 设计文档的偏离（均为“正确但较贵”，优化钩子 deferred）：
  D1. lz 用 21 个阈值比较（thermometer，滑动窗口）+ 优先编码，不用二分比较器。
      理由：定义域 lz∈0…21 共 22 个值，不是 2 的幂，按位二分在细层需要
      逐分支取反修正，手工推导易错；温度计比较 84 次（含正逆重算）反而少于
      真二分的 1+2+4+8+16=31×2=62？不——84 > 62，温度计更贵但编码逻辑只有
      CCX/CX/X（全相干、无 HMR），审计 trivial。比较器仍 btol=inf 精确。
      （更正：温度计 fwd 42 + rev 42 = 84 次 flip；二分需 62 次+多路修正。
      首版选可审计性，门数如实计入。）
  D2. S 进 coef[16:33)，不另设 17 线寄存器；平方推迟到 A 卸载后（square-2），
      U 由 D 重建（delta[5:13)=D[5:13)，delta[13]=~D[13]，因 +8192 只动 bit13）。
      理由：B-LOAD 需 33 条零线、A-LOAD 需 22 条零线与 S 共存（33+17=50>33，
      22+17=39>33），qrom.md 的“分时 33 线”在装载期间无空闲窗口；
      具名 115 线 + 行暂存 45 已顶满 160，无 S 独立寄存器预算。
  D3. S6 用全 t（5 位，t=8+t8val∈8…19）一次 barrel，不做“常数 8 索引重标 +
      4 位 barrel”。理由：重标后舍入位/相位位的线追踪易错；全 t barrel
      在 55 位上 t+36≤55 恒成立，低 36 线恒为 V[t..t+36)，舍入位恒在 V[54]。
      V=55 不可缩（循环 barrel 需要 t+36≤55 的 slack；V<2^45 保证高位为零
      从而循环移位正确）。
  D4. 逆向不重放 z_pow（只逆数据：舍入撤销→barrel 逆→t 清零）。
      round_phase.md 称“Z_POW 对角自逆（同指数再作用）”是错的：
      同指数重放→相位加倍，负指数重放→相位抵消（首版实测总相位恒偶整数）。
      相位是对角输出，不纠缠数据线，Bennett 镜像必须跳过它
      （基线 68 条 Z_POW 同样只作用一次）。gadget 已用 read_shot_phase
      验证：正向 36×z_pow 相位 = P/2^35 半 turns（精确），逆向数据通路
      相位中性（预筛 C 验证）。
  D5. 平方行先取 |U| 再全加（s=U[8] 拷入 coef[9]，受控取负），行控制位
      经 coef[15] 中转（2×CX/行，Clifford-free）。
      理由 1：kickmix 禁止 control 与 offset 共用同一 qubit（qubit collision
      错误，探针实测）；U[j] 既是行控制又是被加数位，必须中转。
      理由 2：slice 加法（offset 短于 target）按零扩展处理，有符号 U
      为负时行加错整整 2^16（x=3133452 实测：S 多 65536）；取绝对值后
      行全为无符号加，精确。MSB-行变减方案已废弃（同因）。
  D6. QROM 拆分为 load-mini / 算术 / unload-mini（每表 3 段，共 9 段 +B 共 10），
      算术期不持有 unary 暂存与 addr（addr 每 mini 现配现释）。
      理由：单 pass 下算术与 unary 8 线并发，峰值 123+8+45=176 超限；
      拆分后算术期峰值 115+45=160。开关 pass 的额外 decode 开销如实计入。
      行目标止于 bit45（V[*:45)，不含恒零的 V[45:55)）：精确性由 V<2^45
      保证（slice 加法模 2^len 精确 True-sum 无回绕，见 S5 注）。
  D7. B 跳过 coef 与 B1 加法器，直接 QROM-CX 装载进 V[12:45)（V 初态为零，
      XOR 即加；逆向回放即卸载）。A/R 仍经 coef（多行复用，需驻留）。
      kickmix 原语暂存实测（本机，exact）：flip22→21，iadd33→43→43，
      c-isub22→44→44，c-iadd17→45→45，c-iadd1→36→35，经典偏移约 len-2。
      设计文档 qrom.md §4 的“峰值 ~125Q”漏计了这部分（ripple 按 ~2 线估计）；
      首版以实测为准，诚实记录，不 claim 增益。

手动运行（证据命令，见 gen2_build.md）：
  uv run python experiments/invsqrt/20261102_generator_v2/generator62_v2.py
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import kickmix as km

# ---- 固定参数（合同位宽；形状约束） ----
W_X = 22
W_LZ = 5
W_ADDR = 8
N_ADDR = 256
W_B, W_A, W_R = 33, 22, 12
W_DELTA, W_D, W_U, W_S = 14, 14, 9, 17
W_V = 55
W_VHI = 45  # 行目标上界（V<2^45，V[45:55) 恒零；barrel/相位仍用全 55 线）
W_P = 36
Q_CAP = 160  # 宽度上限断言（峰值 160，余量 0）

S_OFF = 16  # S 在 coef 中的基址（S=coef[16:33)，17 线）
ROW_CTL = 15  # 方块行控制中转（coef[15]，平方期间空闲为零）

TABLES_PATH = Path("artifacts/20261102_generator_v2/invsqrt/int_tables_7_8_16_5_trunc.json")
OUT_KMB = Path("artifacts/20261102_generator_v2/invsqrt/gen2_invsqrt.kmb")
OUT_STATS = Path("artifacts/20261102_generator_v2/invsqrt/gen2_stats.json")


@dataclass(frozen=True)
class CoefTables:
    """调用方提供的系数表（整数形态，LSB-first ints 的 tuple，顺序固定）."""

    B: tuple[int, ...]  # 256 项，各 < 2**33
    A: tuple[int, ...]  # 256 项，各 < 2**22
    R: tuple[int, ...]  # 256 项，各 < 2**12


def assert_tables(tables: CoefTables) -> None:
    """S0：供表形状与安全断言（只断言形状与 V 非负下界，不多断言）."""
    assert len(tables.B) == len(tables.A) == len(tables.R) == N_ADDR
    assert all(0 <= v < 2**W_B for v in tables.B)
    assert all(0 <= v < 2**W_A for v in tables.A)
    assert all(0 <= v < 2**W_R for v in tables.R)
    # V 非负安全边际：min(B<<12) 须覆盖 |2AD|+|RS| 上界（2**37 + 2**29）
    assert min(tables.B) > (2**37 + 2**29) >> 12, "B 下界不足以保证 V 非负"


def load_tables(path: Path = TABLES_PATH) -> CoefTables:
    """调用方注入：从已验证 JSON 读 B/A/R（不是读旧 KMB）。"""
    doc = json.loads(Path(path).read_text())
    return CoefTables(B=tuple(doc["B"]), A=tuple(doc["A"]), R=tuple(doc["R"]))


# ---------------------------------------------------------------- S1: lz
# 滑动窗口温度计：同时只驻留 2 个比较位（e[k%2] ↔ c_k=(x<2^k)）+ 1 个编码位 h。
# c_0 := False（定义域 x≥1），c_22 := True（x<2^22 恒成立）为经典常量不占线。
# hot_i = c_{i+1} & ~c_i；lz ^= Σ hot_i·(21-i)；i=21 对应 lz=0 无贡献跳过。
# 比较器 btol=inf 精确；x 在 S1 期间不变，故 XOR 比较重放即撤销。
def _cmp(b, x, e, k) -> None:
    b.flip_if_less_than(x, 2**k, target=e[k % 2], btol=float("inf"))


def _hot(b, e, h, lz, i, reverse: bool = False) -> None:
    """hot_i 编码进 lz（全部门自逆；reverse 时严格逆序重放）。"""
    need = 21 - i
    ks = [k for k in range(W_LZ) if (need >> k) & 1]
    if not ks:
        return
    hh = h[0]
    if i == 0:
        for k in (reversed(ks) if reverse else ks):
            b.cx(e[1], lz[k])
        return
    ci, ci1 = e[i % 2], e[(i + 1) % 2]
    if not reverse:
        b.cx(ci1, hh)
        b.ccx(ci, ci1, hh)
        for k in ks:
            b.cx(hh, lz[k])
        b.ccx(ci, ci1, hh)
        b.cx(ci1, hh)
    else:
        b.cx(ci1, hh)
        b.ccx(ci, ci1, hh)
        for k in reversed(ks):
            b.cx(hh, lz[k])
        b.ccx(ci, ci1, hh)
        b.cx(ci1, hh)


def build_lz_norm(b, x, lz, e, h) -> None:
    """S1 正向：逐 i 比较→编码→解散旧位（constant-width 滑动）。"""
    _cmp(b, x, e, 1)
    for i in range(0, 21):
        _hot(b, e, h, lz, i)
        if i >= 1:
            _cmp(b, x, e, i)  # 解散 c_i（自逆重放）
        if i + 2 <= 21:
            _cmp(b, x, e, i + 2)
    _cmp(b, x, e, 21)  # 解散 c_21（自逆重放）


def build_lz_norm_rev(b, x, lz, e, h) -> None:
    """S1 逆向：逐 i 重算→编码镜像→解散（lz 归零）。"""
    for i in reversed(range(0, 21)):
        if i >= 1:
            _cmp(b, x, e, i)
        _cmp(b, x, e, i + 1)
        _hot(b, e, h, lz, i, reverse=True)
        _cmp(b, x, e, i + 1)  # 解散 c_{i+1}
        if i >= 1:
            _cmp(b, x, e, i)  # 解散 c_i


# ---------------------------------------------------------------- S2：归一化
def build_normalize(b, x, lz) -> None:
    """S2 正向：原地 left_rotate(x, lz)。

    rotl == 逻辑左移当且仅当 x 高 lz 位恒零——由 lz 定义保证（S1 刚求出）。
    """
    b.left_rotate(x, lz)


def build_normalize_rev(b, x, lz) -> None:
    """S2 逆向：right_rotate(x, lz)，x 精确复原。"""
    b.right_rotate(x, lz)


# ---------------------------------------------------------------- 地址形成
def build_addr(b, x, lz, addr) -> None:
    """地址显式形成：addr[0..7) = x[14..21)，addr[7] ^= lz[0]。

    8×CX（Clifford-free，成本如实计入 ops）；自逆，重放即解散。
    a = (p<<7)|((m>>14)&127)，p = lz[0]，m 为归一化后 x。
    """
    for j in range(7):
        b.cx(x[14 + j], addr[j])
    b.cx(lz[0], addr[7])


# ---------------------------------------------------------------- S3'：平方（square-2，S 进 coef）
def _u_reconstruct(b, x, coef) -> None:
    """由 D 重建 U_raw 进 coef[0:9)：U_raw[0:8)=x[5:13)，U_raw[8]=~x[13]。

    delta = D+8192 (mod 2^14)；+8192=2^13 只翻 bit13（低 13 位不动），
    故 delta[5:13)=D[5:13)，delta[13]=~D[13]。D 即 x 低 14 线原地值。
    """
    U = coef[0:W_U]
    for j in range(8):
        b.cx(x[5 + j], U[j])
    b.cx(x[13], U[8])
    b.x(U[8])


def _u_reconstruct_rev(b, x, coef) -> None:
    """U 重建的镜像（自逆门逆序：X/CX 均自逆）。"""
    U = coef[0:W_U]
    b.x(U[8])
    b.cx(x[13], U[8])
    for j in range(8):
        b.cx(x[5 + j], U[j])


def build_square2(b, x, coef) -> None:
    """S3' 正向：U 重建→isub 256→取绝对值→学校式 9 全加行进 S=coef[16:33)。

    关键修正（首版 bug→修）：U 为 9 位有符号数，kickmix slice 加法
    （offset 短于 target）按零扩展处理，加负数会错整整 2^16
    （x=3133452 实测：S 多 65536，V 差 R×65536）。故先取 |U|
    （9 位二补码取负精确，|U|≤256），行全为无符号加，零扩展即真值；
    S=|U|²=U² 精确（部分和 ≤65536<2^17 无回绕，slice 精确）。
    取负：s=U[8] 拷入 coef[9]；s?U:=~U+1（9×CX + 受控经典 +1）；
    用后镜像恢复（s 的控制位全程保留，故可逆；U[8] 恢复后才清 s）。
    行控制经 coef[15] 中转（D5）。
    """
    U = coef[0:W_U]
    S = coef[S_OFF:S_OFF + W_S]
    sgn = coef[9]
    crow = coef[ROW_CTL]
    _u_reconstruct(b, x, coef)
    b.isub(256, target=U)
    b.cx(U[8], sgn)
    for j in range(W_U):
        b.cx(sgn, U[j])
    b.iadd(1, target=U, control=sgn)
    for j in range(W_U):
        b.cx(U[j], crow)
        b.iadd(U, target=S[j:W_S], control=crow)
        b.cx(U[j], crow)
    b.isub(1, target=U, control=sgn)
    for j in range(W_U):
        b.cx(sgn, U[j])
    b.cx(U[8], sgn)
    b.iadd(256, target=U)
    _u_reconstruct_rev(b, x, coef)


def build_square2_rev(b, x, coef) -> None:
    """S3' 逆向：与正向同 wrapper（重建→减→取负→行镜像→恢复→解散），S 归零。"""
    U = coef[0:W_U]
    S = coef[S_OFF:S_OFF + W_S]
    sgn = coef[9]
    crow = coef[ROW_CTL]
    _u_reconstruct(b, x, coef)
    b.isub(256, target=U)
    b.cx(U[8], sgn)
    for j in range(W_U):
        b.cx(sgn, U[j])
    b.iadd(1, target=U, control=sgn)
    for j in reversed(range(W_U)):
        b.cx(U[j], crow)
        b.isub(U, target=S[j:W_S], control=crow)
        b.cx(U[j], crow)
    b.isub(1, target=U, control=sgn)
    for j in range(W_U):
        b.cx(sgn, U[j])
    b.cx(U[8], sgn)
    b.iadd(256, target=U)
    _u_reconstruct_rev(b, x, coef)


# ---------------------------------------------------------------- S4：QROM mini-pass
def qrom_sweep(b, it, table: tuple[int, ...], width: int, target) -> None:
    """S4 单扫：固定 range(256) 顺序，move_to 逐值，每值按表 bit 做条件 CX。

    LSB-first 固定序；同 pattern 重放即装载/卸载（CX 自逆，0 Toffoli）。
    """
    for v in range(N_ADDR):
        it.move_to(v)
        m = it.match_qubit
        tv = table[v]
        for j in range(width):
            if (tv >> j) & 1:
                b.cx(m, target[j])


def mini_pass(b, x, lz, table: tuple[int, ...], width: int, target) -> None:
    """QROM mini-pass：现配 addr → 显式形成 → 单 sweep → 解散 addr → 释放。

    自逆块（form/sweep/unform 全自逆门；open/close 为配对的暂存管理）。
    同一 mini 重跑即装载/卸载（target 零↔表值翻转）。
    """
    addr = b.alloc_qubits(W_ADDR)
    build_addr(b, x, lz, addr)
    with b.unary_iteration(addr, range(N_ADDR)) as it:
        qrom_sweep(b, it, table, width, target)
    build_addr(b, x, lz, addr)
    b.free(addr)


# ---------------------------------------------------------------- S5：V 组装
def build_a1(b, x, coef, v) -> None:
    """A1：V -= 2·A·D：对 D 的 14 个二补码位 j，V -= (A<<(j+1)) if D_j。

    行目标止于 bit45（V[j+1:45)）：精确性由 V<2^45 保证——slice 加法
    (T+a) mod 2^len 恰为真和 mod 2^len，而真和 <2^45 故窗口内精确、
    V[45:55) 恒零。MSB 行（j=13）变加。D 为 x 低 14 线原地值。
    """
    for j in range(13):
        b.isub(coef[0:W_A], target=v[j + 1:W_VHI], control=x[j])
    b.iadd(coef[0:W_A], target=v[W_D:W_VHI], control=x[13])


def build_a1_rev(b, x, coef, v) -> None:
    """A1 镜像（逆序、加减互换）。"""
    b.isub(coef[0:W_A], target=v[W_D:W_VHI], control=x[13])
    for j in reversed(range(13)):
        b.iadd(coef[0:W_A], target=v[j + 1:W_VHI], control=x[j])


def build_r1(b, coef, v) -> None:
    """R1：V += R·S：对 R 的 12 位 j，V += (S<<j) if R_j。

    S = coef[16:33)，R = coef[0:12)（不交，control 无 collision）；
    行目标止于 bit45（同 A1 精确性论证）。
    """
    S = coef[S_OFF:S_OFF + W_S]
    for j in range(W_R):
        b.iadd(S, target=v[j:W_VHI], control=coef[j])


def build_r1_rev(b, coef, v) -> None:
    """R1 镜像（逆序 isub）。"""
    S = coef[S_OFF:S_OFF + W_S]
    for j in reversed(range(W_R)):
        b.isub(S, target=v[j:W_VHI], control=coef[j])


# ---------------------------------------------------------------- S6：移位/舍入/相位
def build_shift_round_phase(b, lz, v, coef) -> None:
    """S6 正向：t=8+(11-s-p) 全 5 位 → barrel → V[54] 受控加一 → 36×z_pow。

    t∈8…19（合同断言，电路内不截断）。barrel 后低 36 线恒为 V[t..t+36)
    （t+36≤55 无回绕），舍入位（旧 V[t-1]）恒在 V[54]。
    相位口径（半 turn，gadget 已用 read_shot_phase 自检）：
      z_pow(V[k], Fraction(2^k, 2^35))，Σ = P/2^35 半 turns = P/2^36 turns。
    """
    t = coef[0:5]
    b.iadd(11, target=t)
    b.isub(lz[1:W_LZ], target=t)
    b.isub(lz[0:1], target=t)
    b.iadd(8, target=t)
    b.right_rotate(v, t)
    b.iadd(1, target=v[0:W_P], control=v[W_V - 1])
    for k in range(W_P):
        b.z_pow(v[k], Fraction(2**k, 2**35))


def build_shift_round_phase_rev(b, lz, v, coef) -> None:
    """S6 逆向：只逆数据（舍入撤销 → barrel 逆 → t 清零释放），不动 z_pow。

    关键修正（首版 bug→修）：相位是电路的输出（对角门，不纠缠数据线），
    必须保留。逆向若重放 z_pow（无论同指数还是负指数）都会改动净相位：
    同指数→相位加倍，负指数→相位抵消（首版实测：总相位恒为偶整数）。
    正确调度：正向施加 36×z_pow 后，逆向只 uncompute 数据。
    round_phase.md 的“Z_POW 对角自逆”说法删除（无论同/负指数都不该重放）。
    """
    t = coef[0:5]
    b.isub(1, target=v[0:W_P], control=v[W_V - 1])
    b.left_rotate(v, t)
    b.isub(8, target=t)
    b.iadd(lz[0:1], target=t)
    b.iadd(lz[1:W_LZ], target=t)
    b.isub(11, target=t)


# ---------------------------------------------------------------- S7/S8 调度
def create_regs(b):
    """固定顺序分配：唯一的具名寄存器是 x（官方 schema 只允许 ['x']）；
    lz/coef/v 经 alloc_qubits 分配为匿名 scratch（顺序固定，确定性不变）。"""
    x = b.create_quantum_register(W_X, name="x")
    lz = b.alloc_qubits(W_LZ)
    coef = b.alloc_qubits(W_B)
    v = b.alloc_qubits(W_V)
    return {"x": x, "lz": lz, "coef": coef, "v": v}


def build_forward(b, tables: CoefTables, regs: dict) -> None:
    """S7 正向调度：S0→S1→S2→D→B直装→A三段→S3'→R三段→S6。"""
    assert_tables(tables)
    x, lz, coef, v = (regs[k] for k in ("x", "lz", "coef", "v"))
    e = b.alloc_qubits(2)
    h = b.alloc_qubits(1)
    build_lz_norm(b, x, lz, e, h)
    b.free(e)
    b.free(h)
    build_normalize(b, x, lz)
    b.isub(8192, target=x[0:W_DELTA])  # D = delta-8192，原地于 x 低 14 线
    mini_pass(b, x, lz, tables.B, W_B, v[12:W_VHI])  # B 直装进 V（V 初零）
    mini_pass(b, x, lz, tables.A, W_A, coef[0:W_A])  # A 装载
    build_a1(b, x, coef, v)  # A1（pass 外，addr 已释）
    mini_pass(b, x, lz, tables.A, W_A, coef[0:W_A])  # A 卸载
    build_square2(b, x, coef)  # S3'（S 进 coef[16:33)）
    mini_pass(b, x, lz, tables.R, W_R, coef[0:W_R])  # R 装载
    build_r1(b, coef, v)  # R1（pass 外）
    mini_pass(b, x, lz, tables.R, W_R, coef[0:W_R])  # R 卸载
    build_shift_round_phase(b, lz, v, coef)


def build_reverse(b, tables: CoefTables, regs: dict) -> None:
    """S8 逆向调度：S6 逆→R三段逆→S3'逆→A三段逆→B卸→D复→S2逆→S1逆。"""
    x, lz, coef, v = (regs[k] for k in ("x", "lz", "coef", "v"))
    build_shift_round_phase_rev(b, lz, v, coef)
    mini_pass(b, x, lz, tables.R, W_R, coef[0:W_R])
    build_r1_rev(b, coef, v)
    mini_pass(b, x, lz, tables.R, W_R, coef[0:W_R])
    build_square2_rev(b, x, coef)
    mini_pass(b, x, lz, tables.A, W_A, coef[0:W_A])
    build_a1_rev(b, x, coef, v)
    mini_pass(b, x, lz, tables.A, W_A, coef[0:W_A])
    mini_pass(b, x, lz, tables.B, W_B, v[12:W_VHI])  # B 回放卸载（V 归零）
    b.iadd(8192, target=x[0:W_DELTA])  # D 原地加回
    build_normalize_rev(b, x, lz)
    e = b.alloc_qubits(2)
    h = b.alloc_qubits(1)
    build_lz_norm_rev(b, x, lz, e, h)
    b.free(e)
    b.free(h)


def build_circuit(tables: CoefTables):
    """S9：正→逆组装；终断言 num_qubits ≤ Q_CAP（全零性由预筛 simulator 检查）。"""
    b = km.CircuitBuilder()
    regs = create_regs(b)
    build_forward(b, tables, regs)
    build_reverse(b, tables, regs)
    circuit = b.finish_circuit()
    assert circuit.num_qubits <= Q_CAP, f"qubits {circuit.num_qubits} > cap {Q_CAP}"
    return circuit


def circuit_sha(circuit) -> str:
    return hashlib.sha256(str(circuit).encode()).hexdigest()


def resource_stats(circuit) -> dict:
    s = circuit.operation_statistics()

    def _val(name):
        v = getattr(s, name)
        return v() if callable(v) else v

    return {
        "qubits": circuit.num_qubits,
        "num_instructions": _val("num_instructions"),
        "ops": {str(k): int(v) for k, v in dict(s).items()},
        "toffoli_like": _val("num_toffoli_like"),
        "t_like": _val("num_t_like"),
        "num_z_pow": _val("num_z_pow"),
        "sha256": circuit_sha(circuit),
    }


def main() -> None:
    """S10：确定性机制——同表构建两次，逐指令相等 + SHA 一致，否则失败。

    确定性来源：迭代一律 range(256)/LSB-first 固定序；表为 tuple 顺序；
    指数用 Fraction；alloc/free 固定序；无随机、无时间、无 dict/set 迭代。
    系数表为调用方注入（已验证 JSON，非拟合结果，不在文件内硬编码）。
    """
    tables = load_tables()
    assert_tables(tables)
    c1 = build_circuit(tables)
    c2 = build_circuit(tables)
    assert str(c1) == str(c2), "两次构建逐指令不一致"
    sha = circuit_sha(c1)
    print("sha256:", sha, "qubits:", c1.num_qubits)
    OUT_KMB.parent.mkdir(parents=True, exist_ok=True)
    c1.to_file(OUT_KMB, format="kmb")
    stats = resource_stats(c1)
    stats["int_tables_sha256"] = hashlib.sha256(
        json.dumps(
            {"B": list(tables.B), "A": list(tables.A), "R": list(tables.R)},
            sort_keys=True,
        ).encode()
    ).hexdigest()
    OUT_STATS.write_text(json.dumps(stats, indent=2, sort_keys=True) + "\n")
    print("wrote", OUT_KMB, "and", OUT_STATS)
    print(json.dumps(stats, indent=2, sort_keys=True)[:2000])


if __name__ == "__main__":
    main()
