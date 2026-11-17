# 2026-11-17 深度并行轮：工作台与进行中的证据

本目录是这一轮（2026-11-17 起）的共享工作台。目标、收益换算和硬规则见
[PLAN.md](PLAN.md)。四条研究线并行，全部在本机只做静态分析与算术、所有电路仿真与
官方验证只在 **Kaggle CPU kernel**。

## 基线与目标

| 项 | 值 |
|---|---|
| 本账号最佳 public | **28.15083**（ref `58454232`，COMPLETE；GM 28.15082863） |
| 三件 | invsqrt `0af21cb8` 44Q / 74,797.36535717871；DQI `61c8348d` 890Q / clean 346,413,579,540.50；chem `a73b25d2` 427Q T=14,706 / 294,643,137.73 |
| gold | 28.71339（rank 16）→ 单腿需再便宜 **5.77%** |
| silver | 28.14702（rank 161），本件仅高 0.00381 |
| 榜首 | 31.01379 |

`scripts/gm.py` 用官方参考常数复算 GM（纯算术）：`python3 scripts/gm.py --current` →
`GM 28.15082863`，与榜上一致。

## 共享工具（本机）

| 工具 | 用途 |
|---|---|
| `scripts/kgpu.py` | 建/推/查/取 Kaggle **CPU-only** kernel（`enable_gpu=false` 写死） |
| `scripts/gm.py` | 三腿官方 cost → GM，并反算金线所需单腿成本 |
| `integration/` | 通用三腿集成 kernel：按 18 成员 SHA-256 定位/嵌入 → 未修改官方 verifier full shots → GM → `submission.zip` + `receipt.json` |

`integration/make_main.py` 从 `pipeline/members_2815083.json`（当前 18 成员清单）与
invsqrt 的 zlib/base64 生成自包含脚本；新候选只需换 manifest。

## 本轮的结构性发现（写入各线任务的依据）

1. **化学 heuristic 成本是形状的纯函数**：`SpinFreeData_V1`（`optimize_qubits=True`）
   给出 `T_h`、`Q_h`；`(8,143,44,8)` 恰好落在 `inner_temp=303` 的口袋（k2=5 时 606 超过
   阈值 `brot·(N−1)=600` 而退到 k2=4）。B=128 会退到 575（Q 658，更差）。
2. **化学 `angles` 成本随行数 `rows = 76 + R·B` 增长**（当前 1220 行 → 8,044 T，占 T 的 55%），
   而误差地板由 `K = R·C` 决定。`rows = K·(B/C)`，所以「减小 B/C」是同时压低 T 与保持精度的
   唯一方向；队伍历史只测过 (5,143,75)=53.65 mHa 这类大 B 形状，未给 B/C 方向的分数前沿。
3. **DQI 宽度换汇**：盈亏平衡 826–900 T/qubit，实测最便宜机制 925 T/qubit（q864，1 CCX/episode），
   只超 7.4%；金线在 Q865 只容忍 6.6 T/qubit。Q 890→880 = +0.216 GM，→870 = +0.433。
4. **invsqrt**：`C = Toffoli + T/4`，44Q 的 Toffoli 面已刮净；Q44→42 需 C ≤ 1781.06（+4.78%），
   Q44→40 需 C ≤ 1869.93（+10.0%）。33 个非 Clifford 旋转的 ε 被 `worst/tol=0.99956` 锁死。

## 收益换算（其余两腿不变）

`GM ∝ cost^(-1/3)`：单腿每降 1% → GM +0.336%。本基线上 1% 单腿 ≈ +0.094 GM。

| 改动 | 新 GM | 增量 |
|---|---:|---:|
| DQI T −1%（3,671 T） | 28.245 | +0.094 |
| DQI Q 890→880（T 不变） | 28.307 | +0.216 |
| DQI Q→870 / Q→860 / Q→840 | 28.524 / 28.745 / 29.257 | +0.43 / +0.65 / +1.11 |
| invsqrt Q 44→43 / 42 / 40 | 28.311 / 28.534 / 29.002 | +0.16 / +0.38 / +0.85 |
| invsqrt C −5.5% | 28.69 | +0.54 |
| chem T 14,706→14,000 / →13,500 | 28.59 / 28.94 | +0.44 / +0.79 |
| chem Q 427→400 / →380 | 28.60 / 28.85 | +0.45 / +0.70 |
| chem λ_eff 46.92→40 / →35 | 28.99 / 29.78 | +0.84 / +1.63 |

金线 28.71339 需要单腿 **−5.77%**（invsqrt ≤ 70,486.58；DQI ≤ 326,448,778,537；chem ≤ 277,662,014.70）。

## 本轮最重要的杠杆：已算术性关闭

曾以为是最大杠杆的 chemistry `|W|` 集中（`lam_h2` 的 52% 是 cross 项），被两个精确恒等式关死：
`E_gap` 钉住 `2·Nneg + 0.5·ΣW² = 540.0`，`Nneg ≥ 0 ⇒ ΣW² ≤ 1080`，而出厂点 `ΣW² = 1079.846`
已是上限的 **99.99%**；同时 `lam_h2 ≥ 270.066`（Cauchy–Schwarz 地板），出厂 270.115。
所以 `Λ ≥ 283.095` vs 283.144，**全部余量 0.049 Λ = GM +0.0003**。
关键修正：verifier 的偏移是 `W = H2_I − Σ_b w`，`lam_h2` 看 `H2_I`、`H1p`/`E_SOS` 看 `W`。
详见 [chem/RESULT3.md](chem/RESULT3.md) §6。

## 进行中的 kernel

| kernel | 用途 | 状态 |
|---|---|---|
| `qingyu1232/qcc-deep-integrator-re-verify-28-15083` v3 | 端到端复验当前 28.15083 三件 + 打包 | **COMPLETE**：三腿官方 verifier 全 PASS，18/18 成员按 SHA-256 定位；默认盐 DQI 抽到 dirty draw → 本次 GM 28.10786705（公开榜 58454232 为 clean draw 28.15083）。见 [integration/RESULT.md](integration/RESULT.md) |
| `qingyu1232/qcc-scout-verify-dqi-575b043f` v2 | 侦察到的新 DQI 字节复核 | COMPLETE：`575b043f` cost 346,409,762,292.72（3 salts 3/3 PASS），组合 GM 28.15093204（**+0.00010**，不值一个提交名额，且有已知 weight-35 见证错误） |
| `qingyu1232/qcc-scout-dfthc-baselines` v2 | dfthc-sos starter kit 8 个基线 | COMPLETE：只有 FeMoCo 一个可提交，Λ=308.45 / λ_eff=49.25，**全面劣于我们**；不存在公开低 Λ 分解 |
