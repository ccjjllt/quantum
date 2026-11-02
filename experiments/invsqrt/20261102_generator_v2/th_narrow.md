# th_narrow.md：两级行 TH 收窄（Vn[20:29) 进位合并）—— 正确但只省 2Q，5~8Q 预期否决

分支 `invsqrt-generator-rebuild`。对象：BOTH 系表（sA=sR=2，只读，未改拟合表；
不读旧 KMB/tray）。本轮止于预筛 + 全域整数合同（A/B/C+DUMP-V 16 样本 +
`--contract-full`），**未跑官方 200M-shot 验证**（门禁）。产物只在
`experiments/invsqrt/20261102_generator_v2/`（`narrow_v62.py` 单线续改、
`prescreen_narrow_v.py` 同步、`th_carry_proof.py`、`th_tail.md` 既有、本文件）与
`artifacts/20261102_generator_v2/invsqrt/`（`narrow_v62.kmb`、`narrow_v62_stats.json`、
`th_carry_proof.log`、`th_carry_integer.log`、`th_narrow_prescreen.log`、
`th_narrow_contract.log`）。

## 0. 为什么延续 `narrow_v62.py` 单线（理由）

- 本任务与窄 V 是同一容器、同一系表、同一调度上的增量行优化（只动行 TH 高位
  处理 + 一次合并，不动 V 容器维度 `vd46/Vn30`、不动 A/R 拟合位宽与移位、
  不动 B 直装位偏移、不动 S6）。另起文件会为同一电路分叉 double-build 谱与
  REC_SHA，且 DUMP-V/合同基址（`V_BASE=76`）完全不变；单线可直接用新旧 SHA
  对比证明“只变了行高位”。
- 参照 `refit_variant62.py` 头注的 single-line 论证之反面：上次新文件是因为
  V 容器维度与拟合宽度正交；这次正交轴未变，故**不建新文件**，直接改
  `narrow_v62.py`（`_tha1_*`、`_nvr1_row_*`、`merge_carry_*`、`create_regs_nv`
  加 `carry2`），`prescreen_narrow_v.py` 只改 `dump_v` 传参 + 合并 + REC_SHA。
- 旧 SHA `c1116ede…`（窄 V，Q=134，官方 PASS 1609096.90）对其对应电路继续有效、
  不被取代；作废含义仅为“旧值不适用于本电路”（本线 double-build 从不产生旧值，
  A 门用新值比对）。Q_CAP 由 134 收紧到 **132**（本任务实测，见 §3）。

## 1. carry 合并恒等式（先证后建）

整数模型（Vn 单位，k=20 低，`Vn=B'+Σr_i`，`r_i<2^20` 已由 `th_tail.md` 证：
A1/R1 行加数恒 `<2^36` 即 Vn `<2^20`，唯一触高的是 B）：

- 设 `B'=B_lo+B_hi·2^20`，`S=B_lo+Σr_i=L+C·2^20`（`L∈[0,2^20)`，`C` 为净进位，
  减行为负 borrow）。则 `Vn=L+(B_hi+C)·2^20`。逐行顺序加的 High 更新
  `H_{i+1}=H_i+c_i`（`c_i∈{0,1}` 加 / `{0,-1}` 减，`c_i` 只依赖低 20 位演化，
  而低演化与 High 无关），累加得 `H_n=H_0+Σc_i`，故 `Σc_i=C`，defer（低全算、
  High 不碰、累 `C`、最后一次 `High+=C`）与逐行全宽精确等价。对减行同理
  （borrow）。carry 本身不可删，删的是 36..44 全加器链。

全域整数证据（BOTH 表，3,133,452 输入逐行顺序仿真，
`th_carry_integer.log`，EXIT=0）：

```
after-Asub Cmin -1 Cmax 0
after-AMSB Cmin -1 Cmax 1
final Cmin -1 Cmax 1
Cdist {-1: 283571, 0: 2556681, 1: 293200}
Bhi range 181 361 Blo range 8475 1046576
```

即净 `C∈{-1,0,1}` 恒成立，前缀亦然（Asub 段 `[-1,0]`）。故 2 位 two's complement
CARRY（范围 `-2..1`）永不溢出（余量 1 档；`-2` 本身合并亦正确，见下），
`B_hi+C` 仍在 `[0,2^9)` 内（`Vn<2^29`，合同已验）。

合并符号扩展：CARRY 无符号值 `U∈0..3`，有符号值 `=U-4·sign`（`sign=CARRY[1]`）。
正向合并 `High+=U` 后若 `sign` 则 `High-=4`；逆向严格逆序（先 `+=4` 再 `-=U`）。
2 位全值域（`00=0,01=+1,11=-1,10=-2`）均正确；实际只出现前三种。

量子小例穷举（`th_carry_proof.py`，与生成器同原语：`iadd/isub` 单比特进余区、
`flip_if_less_than(.,1)` 零检测、`init_and/del_and` 求 `c3`、`iadd/isub(c3→CARRY)`、
终合并 `iadd + controlled-isub` 修正；低 Cuccaro 等价性已由 `narrow_proof.py` 证，
此处低用整数等价的通用写法以隔离合并逻辑；`th_carry_proof.log`，EXIT=0）：

```
int-single: 128/128 ok nets=[-1, 0, 1]
int-multi(sub,add,add): 1024/1024 ok nets=[-1, 0, 1]
int-multi(sub,sub,add): 1024/1024 ok nets=[-1, 0, 1]
int-net coverage -1/0/+1: ok [-1, 0, 1]
quantum-multi(sub,add,add) fwd+merge: 1024/1024 ok nets=[-1, 0, 1]
quantum-multi(sub,sub,add) fwd+merge: 1024/1024 ok
quantum-correction-active K2/H3 (corr=4): 512/512 ok nets=[-1, 0, 1]
roundtrip fwd+merge+unmerge+rev: 144/144 ok
TH-CARRY-PROOF PASS
```

其中 `correction-active`（K=2/H=3，`corr=4%8=4`）专证符号修正路径
（净 `-1` 经 `+3` 再 `-4`），覆盖 H=2 小例中 `corr=0` 的修正空洞；
roundtrip 证正向（行+合并）与逆向（解合并+行逆）严格互逆、CARRY 归零。
**先证后建**：以上 PASS 后才进 `narrow_v62.py`。

## 2. diff（vs 窄 V `c1116ede…`）

- `K_SPLIT=20`、`W_CARRY=2`、`CARRY_CORR=4`（`narrow_v62.py` 头部）。
- A1：新增 `_tha1_add_fwd/_tha1_sub_fwd`（`Q._qa1_*` 逐行照抄，HMR 不动；
  仅把 `iadd/isub(c2→TH)`（`TH=Tslice[n0+n1:]` 全长 11..23）换成：
  `Trem=Tslice[n0+n1:20)`（余区 0..13，MSB 空时 `c3=c2` 直进）；
  加行 `Trem+=c2` 后 `c3=c2&(Trem_new==0)` 进 `CARRY+=c3`；
  减行先 `c3=c2&(Trem_old==0)`、`CARRY-=c3`、清 `c3/tmp` 再 `Trem-=c2`；
  其余 `c2/s/eq/lt/c1` 清理原样）。`build_a1_nv[_rev]` 加 `carry` 参，
  高 `Vn[20:30)` 本阶段不碰（B 高位静态直装保留）。
- R1：`_nvr1_row_fwd` 同式替换（`Trem=Tslice[nS:20)`，余区 8..17；
  `c3=cout&(new==0)`，`CARRY+=c3`）；`_nvr1_row_rev` 为其严格逆
  （先重算 `cout`，再由 `Trem_new` 重算 `c3`、`CARRY-=c3`、清、`Trem-=cout`、
  再低逆 `UMAinv/cx/MAJinv` 清 `cout`，与旧逆序镜像）。
- 合并：`merge_carry_fwd`（`High(Vn[20:30))+=CARRY`；`sign` 时 `-=4`）、
  `merge_carry_rev`（严格逆序）。正向置 R 卸载后、S6 前；逆向置 S6 逆后、
  R1 逆前。CARRY（2 线）在 `create_regs_nv` 分配、经 S6 常驻、逆向归零
  （B 门检查含其归零）。
- `prescreen_narrow_v.py`：`dump_v` 同传参 + `merge_carry_fwd` 后再读 Vn
  （否则高 10 位仍是 `B_hi`，与模型终值对不上）；`REC_SHA→e036965d…`。
- 整数 oracle `nv_model_phase` **未动**（数学终值不变，故合同 maxrel 不变）。

## 3. 成本对比（实测）与否决记录

| 口径 | 窄 V（`c1116ede…`） | TH 收窄（本任务，`e036965d…`） | 变化 |
|---|---|---|---|
| Q（num_qubits） | 134 | **132** | −2（−1.5%） |
| num_instructions | 105708 | 109642 | +3934（+3.7%） |
| toffoli_like | 11776 | 11752 | −24（−0.2%） |
| Q×toff（静态） | 1577984 | 1551264 | **−1.7%** |
| 文本 SHA | c1116ede… | e036965d… | 新 REC_SHA（A PASS，double-build `str(c1)==str(c2)`） |
| maxrel 全域 | 0.8712321494 | **0.8712321494**（同模型，同值） | 仍 <1 PASS，最坏 x=1796095 不变 |
| min_margin 全域 | 105643461 | 105643461（同） | 仍 >0 |
| 16 样本 C 余量 | 全 >0（最小 524594562 @2097151） | 全 >0（同电路值一致，见预筛） | 全 >0 |
| 官方验证 | PASS 1609096.90（窄 V） | **未跑**（门禁） | — |

具名：106（22+5+33+46）→ **108**（+carry2）；行暂存 28→~24（余区 iadd/flip
17 位仍主导，CARRY 加 2 位常驻抵消一半）。

**否决记录（诚实记）**：5~8Q 预期（`th_tail.md`“峰值 `iadd(c2→TH)` 暂存 ~23 主导，
降 ~5~8Q”）**否决**。实测仅 −2Q，门数基本持平、指令数反涨 3.7%。
原因：删掉的只是余区之上 10 位高链（23→17），余区本身（R J0 17 位、
A J0 13 位）的 `iadd + flip_if_less_than + c3` 三件套仍要 ~17 暂存，
外加 CARRY 2 位穿越 S6 常驻；门数上 24 次大高加换成 24 次余区小加 +
24 次零检测 + 24 次 CARRY 小加 + 1 次合并，toff 微降但指令膨胀。
结论：carry 合并恒等式成立、电路正确（§4），但**本设计不值得为 −1.7%
Q×toff  churn 基线之外的任何 claim**；保留为新单线状态仅因无回归
（B/C/DUMP-V/合同全 PASS，Q/toff 非负），预期部分的“省 5~8Q”作废。

## 4. 预筛证据（命令 + 输出要点，全 PASS）

```
uv run python experiments/invsqrt/20261102_generator_v2/th_carry_proof.py
  ...（见 §1） TH-CARRY-PROOF PASS  # th_carry_proof.log，EXIT=0
uv run python .../prescreen_narrow_v.py --a --b --c --dump-v
  sha1=sha2=recorded=e036965d… → PRESCREEN-A PASS（Q_CAP=132）
  checked 16 samples x 132 qubits: x-recovery ok, scratch all zero: True → PASS
  16/16 dphase=0，余量全>0 → PRESCREEN-C PASS
  16/16 Vn 精确一致 → DUMP-V PASS   # th_narrow_prescreen.log，EXIT=0
uv run python .../prescreen_narrow_v.py --contract-full
  checked=3133452 fails=0 maxrel=0.8712321494 worst=(1796095, 3.87e-11)
  min_margin_units=105643461.0
  Vn_range=(189812578,379625054) out_of_[0,2^29)=0 max|Vn-(Vtrue>>16)|=10
  CONTRACT-FULL PASS   # th_narrow_contract.log，EXIT=0；maxrel<1 满足门禁
```

16 样本同各线：`1,2,3,8,31,32,63,128,161,888,2047,2048,2097151,2097152,2506015,3133452`。
REC_SHA 同步：`prescreen_narrow_v.py` REC_SHA=`e036965d…`。

## 5. 下一步

1. 余区才是新主导（R J0 余 17 位 `iadd+flip`）。若还要压行宽度，需把余区
   17 位一分二（S6 式 8/9 + flip 进位，暂存 ~9），或改单比特加法为 1-temp
   纹波手写（替代通用 `iadd`），而非再动 High（High 已只剩一次 10 位合并，
   峰值占比消失）。本任务未做（需新小例，禁令遵守）。
2. CARRY 2 位穿越 S6 是固定 +2。若改“合并提前、S6 后重算”可省常驻，
   但逆向需由终态重算 CARRY（终态 High 已合，需先剥离），复杂度换 2Q 不值；
   否决（同 narrow_v.md §6 零区教训：复杂度换小 Q 否决）。
3. 送完整官方验证（门禁外）前需掂量：本任务 Q×toff 仅 −1.7%、指令 +3.7%，
   score 未必跟进；若送验，预期 ~158w（−2%）量级，需主线程确认是否值得花
   200M-shot。
4. 远目标仍远（相对 BOTH −26% 左右，非量级解），如实记。
