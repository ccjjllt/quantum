# 联合 W+angle 小步优化、误差预算再分配、R5 短训探针（2026-11-09）

分支 `codex/dfthcsos-research`，工作区 `.worktree/dfthcsos/`。
起点 `b9eced3e`（`artifacts/20261108_public_frontier/dfthcsos_refit/submission.npz`，
λeff `46.891275349493`，T/Q=`14966/427`，`T×Q=6390482`）。固定 tree，brot=8。

结论先行（三项全是 null，但数字完整保留）：

1. **联合 W+1 LSB Newton 回缩无收益。** `r76c74+1` 翻转后三门全破
  （e1 +3.96uHa、e2 +0.23uHa、E_gap −9.57uHa，均超裕度），表观 −369 分不可行；
   W Newton 回缩收敛到残差 2e-15，但 λeff 代价 +169uHa（+1080 分相对翻转点），
   净 +711 分（+111uHa），远超 100uHa 容忍线。对照 `r1219c74+1` 同样净 +321 分。
   W 能吸收（收敛），但价格数倍于收益。
2. **预算再分配：e2 方向每 1uHa 值约 2200 分，但剩余裕度仅 0.025nHa（值约 0.05 分），
   无可再分配之预算。** KKT 在 b9eced3e 处复算
   `dλeff/de2=−344.81`（与任务给出的 −344.8 一致）、`dλeff/de1=−0.248`、
   `dλeff/dEgap=+5.592`。e1 方向的交换比是 e2 的 1/1390，可忽略。
   E_gap ±1uHa 值 ±35.7 分；1uHa E_gap ≈ 16.2nHa e2。
   任务原文"放宽到 19.99999mHa"存在小数误读（该值小于基线，实为收紧），正文已纠正并给出双向数字。
3. **R5/B135/C70 的 500 步短训：182mHa，未过门；外推不支持 20mHa 可达。**
   起点 793.6mHa → 500 步 182.0mHa；每 100 步下降 382/97/66/41/26，
   尾部比稳定 ~0.63，指数外推渐近 ~139mHa（到不了 20）；
   幂律外推需 ~39k 步且不可靠。结合已完成的 17k–50k 步长轨迹
   （停在 25–37mHa），判断为优化器/盆地问题叠加形状 PSD 充分性不足，
   不是单纯"步数不够"。

## 1. 联合 W+angle 小步优化（精确算术，官方内核数）

方法：`joint_newton.py`。翻转 1 个 angle LSB（U 重算），固定 W 先得官方
`evaluate_words` 精确数；再以解析 Jacobian（Hellmann-Feynman，同
`20261108_frontier_refit/nullspace_refit.py` 推导）在翻转后角度处对
40549+349 平滑 W 坐标做 Newton 回缩（pinv，容差 1e-14），两种变体：
(a) 守四门（e1/e2/E_gap/λ58，保 kink）；(b) 只守三真门（kink 自由）。
所有上报行均为官方内核在（新 W，新角度）处的精确数（`load_inputs` 接受
内存映射，不写候选文件、无 shots）。

修正说明：初版用自建 `signs[58]=+1` 模型报 λeff，与官方 `sum|λ|`
在翻转点差 ~1.7uHa；终表全部以官方内核为准，已消除该差异。
基线/回缩点的 ev58≈0 处两者一致（<1e-9）。

| 情形 | e1 (mHa) | e2 (mHa) | E_gap (Ha) | Lambda | λeff | Δscore |
|---|---|---|---|---|---:|---:|
| 基线 b9eced3e | 19.999999975 | 19.999999975 | 3.914898000028 | 282.781075042 | 46.891275349 | 0 |
| r76c74+1 翻转（W 不动）OFFICIAL | 20.003959411 | 20.000229192 | 3.914888428520（低于下界 9.57uHa） | 282.781065470 | 46.891217628 | −368.9（不可行） |
| +W Newton 四门 OFFICIAL | 19.999999975 | 19.999999975 | 3.914898000028 | 282.782408303 | 46.891386662 | **+711.3** |
| +W Newton 三门 OFFICIAL | 守住 | 守住 | 守住 | 282.782497719 | 46.891394127 | **+759.0** |
| r1219c74+1 翻转 OFFICIAL | 20.009746020 | 20.000157123 | 3.914855079445（低于下界 42.9uHa） | 282.781032121 | 46.891016513 | −1654.1（不可行） |
| +W Newton 四门 OFFICIAL | 守住 | 守住 | 守住 | 282.781676331 | 46.891325550 | **+320.8** |
| +W Newton 三门 OFFICIAL | 守住 | 守住 | 守住 | 282.781737155 | 46.891330629 | **+353.3** |

Newton 收敛：r76 四门 9 步到残差 2.0e-15，`||ΔW||_F=2.37e-5`，
`max|ΔW|=2.57e-6`；三门 8 步到 3.1e-15。r1219 四门 6 步到 1.4e-15。
W 移动量级微小（1e-5），说明"吸收"本身不难——难的是 λeff 价格：
r76 回缩代价 = 711.3+368.9 = 1080.2 分 = 169uHa λeff；
r1219 回缩代价 = 320.8+1654.1 = 1974.9 分 = 309uHa。
三门变体反而略差，说明 kink 约束不是代价来源。

新增发现：`multikink_probe.json` 的 LSB 表只记了 de1/de2/dle，
漏了 E_gap 列；本轮补上——单 LSB 翻转同时把 E_gap 拉低 9.6/42.9uHa，
而 E_gap 裕度仅 0.028uHa（2.8e-11Ha）。即 LSB 是三门齐破，
不是单门超限；W 回缩必须同时补 e1、e2、E_gap 三个洞，
这就是价格高昂的直接原因。

证据：`artifacts/20261109_joint_budget/joint_newton.json`
（脚本 `experiments/dfthcsos/20261109_joint_budget/joint_newton.py`）。

## 2. 误差预算再分配（解析 Jacobian + 一次精确 Newton 核验）

KKT 在 b9eced3e 处复算（40549+349 平滑坐标）：
`∇λeff ≈ −0.2482·∇e1 −344.81·∇e2 +5.592·∇Egap +0.1612·∇λ58`，
切空间投影范数 0.148。`dλeff/de2=−344.81` 与任务给出的 −344.8 一致。

小数纠正：基线 e2 = 19.999999975mHa；19.99999mHa（=19.999990000）
比基线小 9.975e-6mHa，是收紧而非放宽。以下同时给出该收紧点的精确数
与"放宽"方向的单位换算率：

| 交换 | Δ约束 | Δλeff（线性） | Δscore（线性） | 精确核验 |
|---|---|---:|---:|---|
| (a) e2 → 19.99999mHa（收紧 9.975e-9Ha） | −9.975e-9 Ha | +3.44e-6 | +22.0 | Newton 5 步收敛，精确 +3.52e-6 / **+22.5 分**（线性误差 2%） |
| 反向：e2 放宽 +1uHa（会破门，仅作汇率） | +1e-6 Ha | −3.448e-4 | **−2203** | — |
| (b) e1 → 19.99999mHa（同区间） | −9.975e-9 Ha | +2.48e-9 | +0.016 | e2 的 1/1390，可忽略 |
| (c) E_gap 收紧 +1uHa | +1e-6 Ha | +5.59e-6 | **+35.7** | — |
| (c) E_gap 放宽 −1uHa | −1e-6 Ha | −5.59e-6 | −35.7 | — |
| 交叉：1uHa E_gap ≡ 16.2nHa e2（=0.0162uHa） | — | — | — | `|5.592/344.81|` |

政策含义：e1 方向无价值（汇率差 1390 倍）；e2 方向汇率虽陡，
但剩余裕度仅 2.5e-11Ha = 0.025nHa，全部兑现也只值约 0.05 分——
门内已无预算可调。任何 uHa 级的"放宽"都直接破门（见 §1 三门齐破）。

证据：`artifacts/20261109_joint_budget/budget_exchange.json`
（脚本 `experiments/dfthcsos/20261109_joint_budget/budget_exchange.py`）。

## 3. R5/B135/C70 的 500 步短训探针

复用 `20261106_train_r5/fit_probe.py`（连续 packed-pair L-BFGS，同时优化
U/W，float64）与种子
`artifacts/20261106_high_yield/train_r5/seed_5x135x70_cluster_chol.npz`，
CPU 上约 8 it/s、62 秒完成 500 步。只训连续 error_2（8-bit 量化与
error_1/one-body 尚未计入，故 20mHa 本就是必要非充分线）。

| iter | e2 (mHa) | 当段下降 |
|---:|---:|---:|
| 0 | 793.56 | — |
| 100 | 411.29 | −382.3 |
| 200 | 314.32 | −97.0 |
| 300 | 248.56 | −65.8 |
| 400 | 208.05 | −40.5 |
| 500 | 182.00 | −26.0 |

斜率：末段 −0.26mHa/步；每 100 步下降比 0.68/0.62/0.64（稳定 ~0.63）。
外推：指数尾拟合渐近 ≈139mHa（永不到 20）；幂律拟合（p≈0.51）
需 ~39k 步（~80 分钟 CPU），但跨两个量级外推不可靠。
决定性参照是已完成的长轨迹（见 `20261106_train_r5/README.md` §7–§12）：
compact seed 20k 步停 34.1mHa、grow-then-50k 步停 25.8mHa，
shrink 即反弹到 28–37mHa——100 倍步数仍离门 5–17mHa。
因此判断：**优化器/盆地（指数尾、早停滞）为主，形状 PSD 充分性亦未证**
（7.55mHa 只是必要界；共享 U 基+L1+SOS gap+量化才是卡住的部分），
不是"再跑久一点就能过门"。

证据：`artifacts/20261109_joint_budget/train_r5_500.npz`（500 步最优 U/W，
连续探针产物，非候选）+ 本节曲线数字。

## 4. 验证范围声明

- **78,080-shot 官方本地 PASS**：仅既有的 `c1321df2` 与 `b9eced3e`
 （salt `local-frontier-refit-20261108`），见
  `artifacts/20261108_public_frontier/dfthcsos_refit/verify*.log`。
  本轮**没有**新候选，**没有**新的 shot 运行。
- **精确算术评估**：本轮三份 JSON（`joint_newton.json`、
  `budget_exchange.json`、`train_r5_500.npz` 曲线）均为官方内核
  （`verify.evaluate_words` / `dfthc_math` / `fastfit.error2`）精确计算，
  不是 verifier PASS，不计入排行榜。
- 未提交 Kaggle，未推送，未改官方验证器与共享环境。

## 5. 复现

```bash
.venv/bin/python experiments/dfthcsos/20261109_joint_budget/joint_newton.py
.venv/bin/python experiments/dfthcsos/20261109_joint_budget/budget_exchange.py
uv run --no-project --with jax --with optax --with numpy --with scipy --with h5py \
  python experiments/dfthcsos/20261106_train_r5/fit_probe.py \
  artifacts/20261106_high_yield/train_r5/seed_5x135x70_cluster_chol.npz \
  artifacts/20261109_joint_budget/train_r5_500.npz --iters 500 --chunk 100
# 仅在有新候选时才手动运行（本轮无）：
# .venv/bin/python scripts/manual_verify.py dfthcsos <family_dir> --salt <local-salt>
```

引用：Lera V7 `dfthc_refit`（`artifacts/20261106_high_yield/lera_data/dfthc_refit`，
VERSION 文件见该目录）、官方 starter kit V4（同目录 `starter_kit/`）、
KKT/Newton 方法见 `20261108_frontier_refit/nullspace_refit.py` 及其 README。
