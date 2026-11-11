# invsqrt `6c6a734d`：均执行 Toffoli 普查 + splice 泛化（无收益，关闭）

日期：2026-11-11；分支 `codex/invsqrt-research`；工作区 `.worktree/invsqrt/`。
基线：`artifacts/20261111_grimoire33/candidate/invsqrt.kmb`，
SHA `6c6a734dbcb693bb18950a4e4ab84e630854df90dbe6558ed3cef3ecc89b0666`，
本地官方全量 **PASS，93,863.29319626842**（62Q，mean toffoli 1218.833259921885，
static 1380，41 rotations，eps 2.43404148e-13，worst 0.99932377@161，200,540,928 shots）。
本实验**未找到更便宜电路**；没有构建可提交候选，没有跑候选全量验证，无 Kaggle 提交。

## 0. 结论与验证范围（先读）

| 方向 | 判 | 依据 |
|---|---|---|
| 均执行 Toffoli 条件化（把无条件门移到 mostly-false flag 后） | 关，上限 ≈3 mean gates（−186 分） | §1；池子 6 门，低于 30 门立项线 |
| 通用 splice（gengsr/ozer 之外再找切点） | 关，现有 S0 切点已最优 | §2；S2 合并块栈不兼容，S2 后缀切点实测 FAIL |
| 公开 invsqrt < 93,863 检索 | 无 | §3；73 个公开 invsqrt 清单，最好即 6c6a734d |
| 62Q→61Q | 静态否证（仅可行性注记） | §4；峰点 62 线全活，非重标号可解 |
| HMR 清理 uncompute | 一行关闭 | §5；X 基 HMR 随机，无 Z 基测量 |

验证范围：**基线全量 PASS 沿用 grimoire33 日志**（未重跑）；本实验只跑了两个
候选的**小 domain 官方验证器**（均 FAIL，见 §2.2、§5），没有跑 200M 全量；
没有构建任何"应通过"的候选，因此没有可全量验证的对象。普查数字全部为
`census_mean_tof.py` 的蒙特卡洛结果（模型对基线全量实测吻合到 0.00025 门）。

复现命令：

```bash
# kmb -> kmx（只读分析文本；REGISTER 头需手工写 x=q0..q21，kickmix 的 kmx dump 会把 62 线全塞进 r0）
.worktree/invsqrt/.venv/bin/python - <<'PY'
import kickmix as km
c = km.Circuit.from_file('artifacts/20261111_grimoire33/candidate/invsqrt.kmb', format='kmb')
c.to_file('/tmp/hybrid.kmx', format='kmx')
PY
# 去掉 APPEND 行后（保留 REGISTER）跑普查
.worktree/invsqrt/.venv/bin/python \
  .worktree/invsqrt/experiments/invsqrt/20261111_hybrid_census/census_mean_tof.py /tmp/hybrid.kmx 400000
# 候选小 domain 验证
.worktree/invsqrt/.venv/bin/python data/competition/verifiers/invsqrt/verify_submission_invsqrt.py \
  .worktree/invsqrt/artifacts/20261111_hybrid_census/candS2_s2suffix.kmb --max-x 4096 --shots-per-x 64
```

## 1. 均执行 Toffoli 普查（`census_mean_tof.py`，N=400k）

关键事实：invsqrt 电路的所有门要么是计算基置换（X/CX/CCX/SWAP/CSWAP），
要么是对角相位（CZ/CCZ/Z/Z_POW/NEG），要么是 X 基测量复位（HMR）。态始终是
计算基态 + 全局相位，所以**每个 HMR 结果都是独立公平硬币，与 x 无关**；
条件位的触发率是固定的 2^-k，均执行门数是一个与 x 无关的常数。
模型与官方全量实测完全吻合：

| 量 | 模型（400k MC） | 官方全量 |
|---|---:|---:|
| mean executed Toffoli-like | **1218.832412** | **1218.833259921885** |

分布（静态 1380，N=400k，seed 7；`artifacts/20261111_hybrid_census/census_hybrid.txt`）：

| 触发概率 | 门数 | 均成本 |
|---|---:|---:|
| P∈[0.999,1] | **1131** | **1131.000** |
| P∈[0.9,0.99) | 8 | 7.719 |
| P∈[0.7,0.9) | 2 | 1.625 |
| P∈[0.45,0.55) | 138 | 68.991 |
| P∈[0.1,0.3) | 39 | 8.378 |
| P∈[0.001,0.1) | 43 | 1.116 |
| P<0.001 | 19 | 0.003 |
| 合计 | 1380 | 1218.832 |

条件化池（数据流：对每个无条件 CCX/CSWAP/CX 目标，找目标的下一次"使用"——
控制位、对角门参数、或 XOR/swap 目标；X/HMR 视为覆盖而非使用）：

- 无条件目标门 1127；目标之后**从未再被使用**：0（普查脚本把 X/HMR 当覆盖，
  报出的 5 个"dead"全是假阳性：X 的新值依赖旧值，HMR 的相位 m·b 也依赖旧值，
  后续 CZ/HMR 仍读它）。
- 下一次使用的最大触发概率：1116 门 ≈1；6 门 ∈[0.45,0.55]；其余无。
- **全部后续使用都条件化（P≤0.55）的门：6 个，最大可省 3.00 mean gates
  ≈ 186 分**。低于用户设定的 30 门（≈1,860 分）立项线，故不构建。

结论：电路的条件化结构已饱和——1130/1380 的付费门是算法本体（S0 前导零
计数、S1 累加、S2 乘积/相位），其目标马上被无条件使用；能移到 flag 后的
只剩 6 门。HMR 作为相位 gadget（`HMR; CZ if bit`）是合法的，本普查模型即
建立在此语义上；"HMR 清理值 ancilla"不在本方向内（见 §5）。

## 2. Splice 泛化（gengsr `26ebf39d` ↔ a15b0d73）

### 2.1 逐 hunk 均成本账（`hunkmean.py`）

- 全电路均值：gengsr **1229.709**，a15b0d73 **1219.829**（Δ +9.880；静态 1392 vs 1381）。
- 现有 hybrid = gengsr 前 474 ops + 两个 Clifford Z_POW + a15b0d73 从 op 330；
  S0 头这一刀恰好 **−1.000 mean gate**（−62.06 分，实测 93,925.35→93,863.29）。
- 对每个 diff hunk 计算"gengsr 后缀 − ozer 后缀"的均成本差（负 = gengsr 更便宜）：
  最佳后缀切点是 **−0.75**（S1 尾部 g[8896]/o[8804] 附近），其余 −0.75…+53。
  **没有任何切点优于现有 S0 切点的 −1.00**；即单切点 hybrid 已最优。

### 2.2 两个候选（均 FAIL，未全量）

**(a) S2 合并块回退（−1.0 mean ≈ −62 分）——栈不兼容，构造即失败。**
gengsr 的 163 行嵌套相位窗（g[18207:18370]）在 `depth=1` 进入、`depth=0` 退出，
它消耗一个更早打开的 PUSH；a15b0d73 的 33 行合并块（o[18294:18327]）在 `depth=0`
进入/退出。hybrid 的上下文是 depth 0，直接替换会让条件栈欠 1，无法组装。
这不是"再证明一次"的问题，是结构性不可拼。

**(b) S2 后缀切点（g[16928]/o[17015]，后缀差 −0.75）——实测 FAIL。**
构造 `candS2_s2suffix.kmb`（hybrid 保留 o[0:17015] 后接 gengsr 后缀），
均值 1218.695740（比基线低 0.137 mean gate），62Q、36919 ops、静态 1381。
小 domain 官方验证器（`--max-x 4096 --shots-per-x 64`）：

```
FAIL  x=5: phase error 5.000e-01 turns exceeds tolerance 2.666e-08
```

逐 x 诊断（x=1..32，seed 12345）：相位误差是 **0 或 ±0.5 turns** 的交替图案
（x=4,5,6,9,11,12 为 0.5），不是常数偏移，无法用单个 Clifford Z_POW 修正；
说明两个后缀在切点处不是同一状态（S1/S2 的 HMR 条件结构不同）。
判：**关，不构建候选，不跑全量**。

产物（gitignored，SHA 见 `artifacts/20261111_hybrid_census/SHA256SUMS.txt`）：
- `candS2_s2suffix.kmb` SHA `641790312ab77cfd9362c41e07d761c39da4be209ee02f5ba90f090fddaf6b1a`
- `candH_hmr14.kmb` SHA `2a859e31ba6847bffb0c73d4bac2b39ee8972ad08bc42524ef63dff0f341abb9`（§5）

## 3. 公开 invsqrt 检索（截至 2026-11-11 20:00 本地）

数据源：`manwithacat/vqcc-apache-public-circuits` **v115**（2026-11-11 11:18 UTC）
的 `manifest.csv`（每行含 `local_task_score`，官方本地验证器、默认 salt）。

- **73 个公开 invsqrt 电路**，按本地分排序：
  1. `6c6a734d` **93,863.36**（manwithacat HW-25，即本基线）
  2. `a15b0d73` 93,925.35
  3. `26ebf39d` 94,537.59
  4. `c6519219` 94,599.61
  5. `46743f7f` 95,345.51
  … 无任何电路 < 93,863.36。
- 最新数据集交叉核对：`ozertuu/quantum-sim-linalg-cache` v22（11:44）
  `invsqrt.kmb` = `6c6a734d`；`matousakura/best-of-public-portfolio`（11-11 05:46）
  `invsqrt.kmb` = `6c6a734d`；`busyaprime/33-qcc-v8-members` v13（10:42）= `6c6a734d`。
- 11:18 之后的新 notebook：`infnitycoder2009/invsqrt-edit-search`（11:19，运行失败，
  日志为 `kaggle: error: unrecognized arguments: --include`）；`attabeezy/gq-invsqrt-precision-retune`
  （11:38，输出是 259Q、7533 Toffoli 的 Newton-Raphson 参考电路，非竞争候选）；
  `ozertuu/25-33133`、`busyaprime/lb-25-33133`、`junmiaotiao/qcc-portfolio-assembly`
  均为组合/展示，invsqrt 成员仍是 `6c6a734d`。
- `malachiwmoody/vqcc-lb-24-7928-public-circuits`（LB 24.79，11-11 07:36）的
  invsqrt 是 `0104d1b4`（97,921.68，作者两处精确编辑 −0.75 toffoli），
  低 LB 来自 chemistry，不是 invsqrt。

判：**公开前沿仍是 93,863.36 量级，没有可捡的更便宜 invsqrt。**

## 4. 62Q→61Q：静态可行性注记（不做）

逆向存活分析（X/HMR 目标 kill；CX/CCX 目标是 XOR，旧值被使用，不 kill；
对角门/SWAP/CSWAP 只读）：

- hybrid、a15b0d73、gengsr 三者的高水位均为 **62**，峰点在 tail-A3
  （hybrid op ≈25210，`HMR q47 b0` 附近），且峰点 62 线全部被后续门读取。
- 若把 CX/CCX 目标也当 kill（错误模型）会得到 54，但那是把"XOR 读旧值"
  当成了覆盖，不能用于重标号。
- 结论：**纯重标号/复用不可能降到 61Q**；只有"重算代替存值"的值级改写才可能，
  属独立方向，本轮不做、不报价。

## 5. HMR uncompute 清理：一行关闭

kickmix `HMR` 是 X 基测量+复位，对计算基态结果随机、且相位为 m·b；没有 Z 基
测量，无法确定性地读/清一个值 ancilla。用"目标在 uncompute 时等于 a&b"的
样本判据筛出 14 个 CCX 做 `HMR + CZ(a,b) if bit` 候选（`candH_hmr14.kmb`，
均值 1216.105 vs 1218.833），小 domain 验证器 **FAIL x=3，0.5 turn**——样本
判据把"稀有乘积 no-op"误判为可转。**方向关闭，不做全量。**

## 6. 下一步（均未立项）

1. 若还要动 invsqrt，只剩"换算法"：S1 重算链的 shift-select 降级（复盘方向二）
   或 61Q 的值级重算证明；两者都是大工程，且旧 family 的失败模式（支撑集/
   守卫不稳）会重现。
2. S2 合并块的回退需要连同其外层 PUSH 上下文一起回退（即更大窗口的
   gengsr 版本），窗口成本差 +1.25，负收益，不建议。
3. 公开侧继续盯 `manwithacat/vqcc-apache-public-circuits` 的 manifest 版本；
   目前 v115 已含 11-11 全部公开 invsqrt。
