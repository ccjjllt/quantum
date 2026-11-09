# 紧凑秩形状精确成本 + 多折点钉扎/LSB 探针（2026-11-09）

分支 `codex/dfthcsos-research`，工作区 `.worktree/dfthcsos/`。
固定基线：Public Frontier `c1321df2` 化学产物（只读链接
`artifacts/20261108_public_frontier/release/dfthcsos/`，15 个 `angle_k_*.kmb` +
`U(8,143,76)` + `tree` + `angle_words(1220,75)` + `H1/Hsym` 与 Syed V9 逐字节一致，
`Q=427`，`T=14966`）与切空间 refit 候选 `b9eced3e`
（`artifacts/20261108_public_frontier/dfthcsos_refit/submission.npz`，
λeff `46.891275349493`，成本 `299657851.0780`，78080-shot PASS）。
固定 `(8,143,44)` 连续 refit 已近极限（见 `20261108_frontier_refit/`）。

## 0. 结论先行（无收益，记 closed，留数字）

1. **紧凑形状 R5/B135/C70（首选）与 R4/B131/C83：无新候选。**
   `SpinFreeData_V1` 精确启发式成本与 PSD 必要下界已算出（下表），
   但 8-bit 公开训练路线在本机 CPU 预算内到不了 20 mHa（`20261106_train_r5/`
   四条路线 25.8–37.4 mHa，收益区与门限区无交集），本轮未启动新的
   GPU/长时训练，也就没有满足 `error_1/error_2≤20mHa、Lambda>49、E_gap`
   约束的 `(λeff, score)` 可报告。`T/Q` 预算中 5–8% 的大头来自
   ANGLES 共享 planner（需新电路），不是已测量的精确值，已如实区分。
2. **多折点钉扎 + angle_words ±1 LSB：在固定 W 约束下无收益。**
   第 2 小 `|λj|`（`j59=+2.5721 mHa`，正）理想钉扎收益仅 `-1372` 分，
   且 KKT 四约束切空间上的真实步进（Newton 回缩）在 `step=4e-7` 反而
   `+0.17` 分、`4e-6` 时 `+18.4` 分（曲率主导，线性估计 `-20.9` 已被淹没）。
   第 3 小（`j57=-3.2933 mHa`，负）理想 `-252k` 分是假象：
   它把 `E_gap` 拉到 `3.90831 Ha`，直接违反严格下界 `E_gap>3.914898 Ha`；
   约束切空间线性估计为 `+8.9` 分（变差）。
   单 LSB 翻转（精确算术）全部冲破 20 mHa 门或裕度（最小 `+3.96/-1.50 uHa`，
   而剩余裕度仅 `0.025 uHa`），且无 planner 证据表明 195 products 能保持。
   本轮不产生新 `submission.npz`。

## 1. 紧凑形状：精确成本（SpinFreeData_V1）+ PSD 必要界 + 打平线

`KEEP_BITS=10`，`beta=brot=8`，`N=76`。`heur_T` 与 qubit 为
`costs_prepare.SpinFreeData_V1` 精确值；`ANGLES=8304` 为当前 195-products
实测值（`dfthcsos_refit/verify.log`）。新形状若不发新电路，`T_cons`
只能按“angles 不变”保守计算；`T_budget_README` 是旧预算（需新 planner
电路），**不是本轮测量**。

| 形状 | A/地址位 | RC | PSD 下界 | heur_T | Q_cons | T_cons（angles不变） | T×Q_cons vs 当前 | 打平 λeff_cons | T_budget | T×Q_budget vs 当前 | 打平 λeff_budget |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 8/143/44 当前 | 1220/11 | 352 | 7.361 mHa | 6662 | 427 | 14966 | — | 46.8913 | — | — | — |
| **R5/B135/C70** | 751/10 | 350 | 7.552 mHa | 6627 | 427 | 14931 | −0.23% | 47.0012（+0.23%） | 14177 | −5.27% | 49.5009（+5.57%） |
| R5/B135/C69 | 751/10 | 345 | 8.062 mHa | 6579 | 427 | 14883 | −0.55% | 47.1528 | — | — | — |
| **R4/B131/C83** | 600/10 | 332 | 9.687 mHa | 6442 | 426 | 14746 | −1.70% | 47.7026（+1.73%） | 13722 | −8.53% | 51.2624（+9.32%） |
| R4/B131/C82 | 600/10 | 328 | 10.267 mHa | 6403 | 426 | 14707 | −1.96% | 47.8291 | 13683 | −8.79% | 51.4085 |
| R6/B143/C59 | 934/10 | 354 | 7.2 mHa | 6682 | 427 | 14986 | +0.13%（更差） | 46.8287 | 14592 | −2.50% | 48.0931 |

- PSD 为必要不充分界（`shifted_target_eigenvalues.npy`，2926 维）：
  `RC=350→7.552`、`332→9.687`、`328→10.267 mHa`，确实都在 20 mHa 内，
  不能证伪 R5/R4；但充分性（共享 U 基、L1、SOS gap、one-body、8-bit 量化、
  电路综合）才是训练卡住的地方。
- 保守列（精确）：R5 只省 `35 T`（heuristic），`T×Q −0.23%`；
  R4 省 `220 T + Q−1`，`−1.70%`。大预算（−5.27%/−8.53%）的差额
  `~754/1000 T` 必须来自 ANGLES 新电路，本轮没有新电路，故不能计入候选。
- 在约束下可报告的 `(λeff, score)`：**无**。训练证据见
  `experiments/dfthcsos/20261106_train_r5/README.md` §7–§12
 （R6 合法形状 33.30/37.41/34.14 mHa，grow 到 6x180x90 50k 步 25.80 mHa
  仍无收益且 shrink 即反弹；收益区 `B≤144、C≤65` 与 20 mHa 门限无交集）。
  本轮未重复长时 CPU 训练（同一路线，预期不变），未产生新 NPZ。

证据：`artifacts/20261109_compact_multikink/compact_costs.json`
（本目录 `compact_costs.py` 生成，精确算术，无 shots）。

## 2. 多折点钉扎：谱、理想收益与约束真相

基线 `b9eced3e` 的 `h1'` 最小 `|λ|`（精确算术，`dfthc_math`）：

| rank | j | λ (mHa) | 符号 | 钉到 0 的理想 Δscore | E_gap 新值 | 能否过 `E_gap>3.914898` |
|---:|---:|---:|:--:|---:|---:|:--:|
| 0 | 58 | −0.0000 | 已钉 | — | — | —（当前 `E_gap=3.914898000028`） |
| 1 | 59 | +2.5721 | 正 | −1372.3 | 3.914898000028（不变） | 通过（但需保误差） |
| 2 | 57 | −3.2933 | 负 | −252181.7（假象） | 3.908311486350 | **违反**（差 −6.59 mHa） |
| 3 | 56 | −3.9811 | 负 | −304882.4（假象） | 3.906935742695 | **违反** |
| 4 | 60 | +4.2817 | 正 | −2284.4 | 不变 | 通过（但需保误差） |

- 负特征值钉扎看似大收益，实为 `E_SOS` 上升→`E_gap` 下降的记账效应；
  当前 `E_gap` 裕度仅 `2.82e-11 Ha`（`2.82e-8 mHa`），任何 mHa 级下降
  都直接 FAIL。KKT 乘子 `dλeff/dE_gap=+5.59`（`20261108_frontier_refit`）
  意味着用 W 补偿 `E_gap` 的代价远超 `Lambda` 节省。
- 正特征值（`j59/j60`）`E_gap` 不变，理想收益 `-1372/−2284` 分，
  但这是“其余全固定”的上界，不含误差约束代价。

## 3. 约束切空间真实步进（W-only，Newton 回缩，精确算术）

KKT（`b9eced3e` 处复算，与 `20261108_frontier_refit` 一致）：
`∇λeff ≈ −0.248·∇e1 −344.8·∇e2 +5.592·∇Egap +0.161·∇λ58`，
`‖Proj_kerJ(∇λeff)‖=0.148`。把 `∇λ59` 投影到
`ker(e1,e2,Egap,λ58)`（`|gn|=7.417`，`dle/ds=+0.00942`），
沿 `-gn`（推 `λ59→0`）+ 8 步 Newton 回缩（`A_pinv`，目标守住基线四约束）：

| step | λ59 (mHa) | e1 (mHa) | e2 (mHa) | E_gap (Ha) | λeff | Δscore（精确算术） |
|---:|---:|---:|---:|---:|---:|---:|
| 4e-7 | 2.5692 | 19.999999975 | 19.999999975 | 3.914898000028 | 46.891275376 | **+0.171（变差）** |
| 4e-6 | 2.5449 | 守住 | 守住 | 守住 | 46.891278227 | **+18.39（变差）** |
| ≥4e-5 | 发散（`|res|~1e33`，Newton 失效） | — | — | — | — | — |

线性估计全程钉扎（`s=3.47e-4`）为 `−20.9` 分，但二阶曲率在 `4e-7`
已反超；`ev57` 约束方向线性估计即 `+8.9` 分（变差），`ev60` 为 `+90.4`。
结论：**W-only 第二折点无收益**，与固定 `(8,143,44)` 已近 KKT 极限一致。

## 4. angle_words ±1 LSB 离散坐标搜索（精确算术，无 shots）

`evaluate_words`（官方内核）单比特翻转，基线误差裕度仅
`e1/e2 ~2.5e-11 Ha = 0.025 nHa = 0.000025 uHa`：

| 翻转 | Δe1 | Δe2 | Δλeff | 20 mHa |
|---|---:|---:|---:|:--:|
| r76c0 ±1（两体首地址） | +24567/+25649 uHa | +4570/+4553 uHa | +38490/+98269 uHa | FAIL |
| r76c74 +1/−1 | +3.96/−1.50 uHa | +0.23/+0.08 uHa | −57.7/+54.4 uHa | FAIL/FAIL（e2 超门或 e1 超门） |
| r500c37 +1 | +12.33 uHa | +0.90 uHa | +239.3 uHa | FAIL |
| r1219c74 +1/−1 | +9.75/−1.70 uHa | +0.16/+0.10 uHa | −258.8/+266.3 uHa | FAIL/FAIL |
| r0c0 ±1（一体） | +13883/+13940 uHa | 0 | 0 | FAIL |

最小扰动（`3.96 uHa`）已是裕度的 `~1.6e5` 倍；`r1219c74+1` 的
`−258 uHa`（约 `−1650` 分上界）同样被 `+9.75 uHa` 误差淹没，
需 W 联合回缩 `~uHa` 量级，而 §3 表明 W 回缩在 `1e-8 uHa` 精度外
即被曲率主导。且 195-products 是否保持需共享 planner 重跑，
本工作区 planner 快照已随 2026-11-07 清理删除（见 `CLOSED_RESEARCH.md`），
**无证据不断言自由位**。故本轮无 LSB 候选。

证据：`artifacts/20261109_compact_multikink/multikink_probe.json`
（本目录 `multikink_probe.py` 生成，精确算术，无 shots）。

## 5. 约束裕度（b9eced3e，精确算术）

- `error_1`：`19.999999974995 mHa`，余 `2.5005e-11 Ha`（`2.50e-8 mHa`）。
- `error_2`：`19.999999975000 mHa`，余 `2.5000e-11 Ha`。
- `E_gap`：`3.914898000028 Ha`，余 `2.82e-11 Ha`（严格 `>`，等号拒绝）。
- `Lambda`：`282.781075042`，余 `233.781`（`>49` 非绑定）。
- `T/Q`：`14966/427`，`T×Q=6390482`，`score=λeff·T·Q`。

## 6. 验证范围声明（ crunch 区分）

- **78,080-shot 官方本地 PASS**：仅 `c1321df2`（`verify_baseline.log`）
  与 `b9eced3e`（`verify.log`，`salt=local-frontier-refit-20261108`，
  `score=299657851.0780`，`SHA submission 8f04b9ab…`），见
  `artifacts/20261108_public_frontier/dfthcsos_refit/`。
  本轮**没有**新候选，故**没有**新的 78,080-shot 运行。
- **精确算术评估**：本轮两份 JSON（`compact_costs.json`、
  `multikink_probe.json`）与正文表格均为官方内核精确计算，
  **不是** verifier PASS，不计入排行榜。
- 未提交 Kaggle，未推送，未改官方验证器与共享环境。

## 7. 复现

```bash
.venv/bin/python experiments/dfthcsos/20261109_compact_multikink/compact_costs.py
.venv/bin/python experiments/dfthcsos/20261109_compact_multikink/multikink_probe.py
# 仅在有新候选时才手动运行（本轮无）：
# .venv/bin/python scripts/manual_verify.py dfthcsos <family_dir> --salt <local-salt>
```
