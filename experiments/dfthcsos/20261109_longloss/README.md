# R5/B135/C70 新loss + 2000步长训（2026-11-09）

分支 `codex/dfthcsos-research`，工作区 `.worktree/dfthcsos/`。
起点 `b9eced3e`（λeff `46.891275349493`，T/Q=`14966/427`）。
不重复短训500步/换基/分阶段/angles实测（见 `20261109_ubasis_retrain/README.md` 最优180mHa距门160mHa，
`20261109_angles_r5/README.md` -0.41%）；本轮只做：① 新loss 500步对比，② 最优者分段续训到总量2000步。

结论先行（新loss与长训都是 null，但数字完整）：

1. **GPU 检查：无。** `nvidia-smi` 缺失，JAX 后端 `cpu`（Apple M5 本机），`torch` 未安装故无 MPS。
   按任务走无 GPU 分支：新 loss 500 步对比，不做 GPU ≥2000 步单段 `fit_probe`；
   2000 步总量用 CPU 分段续训实现（fresh L-BFGS state/段，见 §4 局限）。
2. **新 loss 500 步无收益。** 同起点 793.56 mHa、同 L-BFGS 内核：
   Huber（δ=2e-4）500 步 **440.80 mHa**（+258.8 vs 基线 182.00）；
   joint（e2+α·eL1，α=1.25e-4）500 步 **183.51 mHa**（+1.51，紧贴基线）。
   Huber 下权重大的残差被线性化后早期下降慢一半以上，尾渐近 392.6 mHa；
   joint 全程与纯 L2 重合（100–500 步差值仅 +1.6/+4.7/+3.0/+4.2/+1.5 mHa）。
3. **2000 步长训仍不过门。** L2 分段 500→2000 到 **85.31 mHa**（距门 +65.31）；
   joint 分段 500→2000 到 **86.01 mHa**（距门 +66.01，比特 L2 差 0.7 mHa）。
   L2 尾部 q≈0.909/100 步，指数渐近 **≈63.3 mHa**（距门 +43.3）；
   joint 尾部 q≈0.855，渐近 **≈74.3 mHa**（距门 +54.3）。按当前尾律无限步也到不了 20。
4. **切空间 refit/量化未触发。** 触发条件是任一跑进连续 e2≤20 mHa；最优 85.31，
   距门 65.31。**未执行** signed 8-bit 量化、`evaluate_words` 精确数与
   `nullspace_refit.py`。此处 e2 均为 `fastfit.error2`（与验证器同定义的 packed-pair
   加权范数）在最优 U/W 处的值，float64 L-BFGS 探针产物，**不是候选字**。
5. **外推与换形建议。** 末段斜率仅 −0.022/步且 ratio→0.975（持续减速）；
   线性外推需再 ~3000 步，但指数模型下 20 mHa 在渐近线之下、不可达。
   两 loss 在 2000 步会合到同一 ~85 盆地（joint 与 L2 全程差 <2 mHa），
   加上 R4 eig/rr 在 500 步同样 stall 在 180（见 ubasis_retrain），判断为
   形状/盆地限制而非 loss 选择问题。**建议换形状**（如 R6/B143/C59：
   rows=76+858=934 vs 当前 751，表达力更大；但 T/Q 会涨，需实测 heuristic+angles，
   不能只看 e2）。备选：不同 basin 的 seed（非 cluster_chol 已试过仍同盆地，
   意义不大）、或换优化器（L-BFGS 之外的二阶/自然梯度），留给有 GPU 时。

## 1. 方法：新 loss 定义与量级纠正

复用 `20261106_train_r5/fit_probe.py` 的 problem（`fastfit.problem`，frozen Hsym/H1_I）
与 `fastfit.lbfgs`（optax L-BFGS，zoom line search）。新脚本
`experiments/dfthcsos/20261109_longloss/newloss_probe.py` 只换目标函数，
报告与存档都按**真 e2**（门指标），不按 surrogate 选优。

- `huber (δ=2e-4)`：`L=sqrt(sum M·ρ(H))`，`ρ=x² (|x|≤δ)` 否则 `2δ|x|−δ²`。
  δ→∞ 时退化为 e2；有限 δ 下大残差线性化（C1）。δ 按 seed 处残差分布选：
  |Hw| 中位 4.5e-06、90% 6.3e-05、99% 7.9e-04、max 0.064，故 δ=2e-4 时
  ~92% 在二次区、顶部 8% 被线性化。seed 处 huber=363.48 mHa vs e2 793.56。
- `joint (α=1.25e-4)`：`L=e2+α·eL1`，`eL1=Compute_H2_norm_1(H)`（同一 packed
  残差的全指标 L1，与 starter kit `error_h2_ord=1` 同定义）。
  **量级纠正**：seed 处 eL1=636 Ha、e2=0.79 Ha（比 801）。字面 α=0.1 会得
  64.4 Ha、纯 L1 主导，无意义；取 α=1.25e-4 使 `α·eL1=0.1·e2`（e2 单位下 10%
  权重）。seed 处 surrogate=0.873 Ha。
- `l2`：纯 `fastfit.error2`，作长训对照（500 步 182.00 与 joint_budget 逐位一致）。

## 2. 500 步对比（真 e2，mHa）

| iter | L2 基线 | Huber δ=2e-4（本轮） | Joint α=1.25e-4（本轮） |
|---:|---:|---:|---:|
| 0 | 793.56 | 793.56 | 793.56 |
| 100 | 411.29 | 547.01 | 412.90 (+1.61) |
| 200 | 314.32 | 502.77 | 319.00 (+4.68) |
| 300 | 248.56 | 478.22 | 251.59 (+3.03) |
| 400 | 208.05 | 456.84 | 212.29 (+4.24) |
| 500 | **182.00** | **440.80 (+258.80)** | **183.51 (+1.51)** |
| 距门 | +162.00 | +420.80 | +163.51 |

- Huber：前 100 步只降 246（基线降 382）；100–500 每段仅 −44/−24/−21/−16。
  末三点指数尾 q≈0.750，渐近 ≈392.6 mHa（距门 +372.6）。下权重大残差等于
  自废早期最有效的下降通道。
- Joint：全程与 L2 重合（最大偏离 4.7 mHa，末点仅 +1.5）。L1 项在平衡权重下
  几乎不改变轨迹：同一盆地、同一 stall，只是慢 ~1%。

## 3. 分段续训到总量 2000 步（真 e2，mHa）

从 500 步最优点接续（fresh L-BFGS state，`--chunk 100`），CPU 约 20 s/100 步（L2）
与 30 s/100 步（joint，L1 额外开销）：

| 总量 | L2（基线 500 + 续 1500） | Joint（500 + 续 1500） | 差值 |
|---:|---:|---:|---:|
| 500 | 182.00 | 183.51 | +1.51 |
| 600 | 169.91 | 172.19 | +2.28 |
| 700 | 153.31 | 156.76 | +3.45 |
| 800 | 140.73 | 142.51 | +1.78 |
| 900 | 130.56 | 131.85 | +1.29 |
| 1000 | 122.19 | 123.33 | +1.14 |
| 1100 | 115.39 | 116.27 | +0.88 |
| 1200 | 109.99 | 110.53 | +0.54 |
| 1300 | 105.57 | 106.00 | +0.43 |
| 1400 | 101.76 | 102.19 | +0.43 |
| 1500 | 98.33 | 98.79 | +0.46 |
| 1600 | 95.21 | 95.64 | +0.43 |
| 1700 | 92.47 | 92.80 | +0.33 |
| 1800 | 89.93 | 90.30 | +0.37 |
| 1900 | 87.51 | 87.99 | +0.48 |
| 2000 | **85.31** | **86.01** | +0.70 |

- 最优 **85.31 mHa（L2）**，距门 **+65.31**；joint 86.01，距门 +66.01。
- 尾部（末三点 `e=a+b·q^k`，k 单位 100 it）：
  L2 q=0.9090，a=63.33（+43.33）；joint q=0.8553，a=74.31（+54.31）。
- 末段每 100 步下降 2.7→2.5→2.4→2.2（ratio 0.971→0.975），持续减速；
  按 −0.022/步线性外推需再 ~3000 步，但指数模型下 20 在渐近线之下，
  外推步数无意义（到不了）。
- 500 步尾曾外推渐近 135–139（见 joint_budget/ubasis_retrain）；2000 步把它
  修到 63–74，但门仍在渐近线之下 43–54 mHa。长训把 stall 从 180 推到 85，
  没换盆地。

## 4. 切空间 refit（未触发）+ 精确数声明

触发条件（任务 §2）：任一跑进连续 e2≤20 mHa。实际最优 85.31（L2 2000 步），
距门 65.31；次优 86.01（joint 2000 步）。**未触发，不执行**
`signed 8-bit 量化 + evaluate_words + nullspace_refit.py`；无 λeff/score 精确数。
此处全部 e2 数为 `fastfit.error2` 在最优 U/W 处的值（float64 探针），
NPZ 只有 U/W（`H2_I=W.sum(1)` 附带），**不是候选字**（未经 8-bit 编码+固定树+
one-body 成形；先前实测未收敛 U 的量化字 e1/e2 在 Ha 量级，见 angles_r5 §2，
此处不再重复编码）。

局限：分段续训每段 fresh optax L-BFGS state（与 staged_fit.py 同做法）；
单段 ≥2000 步在 CPU 上约 7–10 分钟且与 500 步尾律一致，未做单段 2000 复核。
JAX CPU 与 GPU 的 L-BFGS 轨迹可能差 high-precision 尾数，但 65 mHa 差距下
不影响门判断。

## 5. 验证范围声明

- **无官方 78,080-shot PASS。** 本轮无候选（最优连续字离门 65 mHa），
  没有运行任何 78k-shot 验证，没有 `manual_verify.py` 调用。
- **无 `evaluate_words` 精确门数。** 连续探针 NPZ 未经 signed 8-bit 编码，
  不能作为 `evaluate_words` 输入。
- 未提交 Kaggle，未推送，未改官方验证器、官方数据与共享环境。

## 6. 证据与复现

产物（`artifacts/20261109_longloss/`，均为训练探针，非候选）：
`train_r5_huber_d2e-4_500.npz`（440.80）、`train_r5_joint_a1p25e-4_500.npz`（183.51）、
`train_r5_l2_500to2000.npz`（85.31，总量 2000）、`train_r5_joint_2000.npz`（86.01，总量 2000），
各配 `.log`（逐 100 步 e2/surrogate/seconds）。

```bash
# 新 loss 500 步（任选其一；基线 L2 见 20261109_joint_budget §5）
uv run --no-project --with jax --with optax --with numpy --with scipy --with h5py \
  python experiments/dfthcsos/20261109_longloss/newloss_probe.py \
  artifacts/20261106_high_yield/train_r5/seed_5x135x70_cluster_chol.npz \
  artifacts/20261109_longloss/train_r5_huber_d2e-4_500.npz \
  --loss huber --delta 2e-4 --iters 500 --chunk 100
uv run --no-project --with jax --with optax --with numpy --with scipy --with h5py \
  python experiments/dfthcsos/20261109_longloss/newloss_probe.py \
  artifacts/20261106_high_yield/train_r5/seed_5x135x70_cluster_chol.npz \
  artifacts/20261109_longloss/train_r5_joint_a1p25e-4_500.npz \
  --loss joint --alpha 1.25e-4 --iters 500 --chunk 100
# 分段续训到总量 2000（fresh L-BFGS state/段）
uv run --no-project --with jax --with optax --with numpy --with scipy --with h5py \
  python experiments/dfthcsos/20261109_longloss/newloss_probe.py \
  artifacts/20261109_joint_budget/train_r5_500.npz \
  artifacts/20261109_longloss/train_r5_l2_500to2000.npz --loss l2 --iters 1500 --chunk 100
uv run --no-project --with jax --with optax --with numpy --with scipy --with h5py \
  python experiments/dfthcsos/20261109_longloss/newloss_probe.py \
  artifacts/20261109_longloss/train_r5_joint_a1p25e-4_500.npz \
  artifacts/20261109_longloss/train_r5_joint_2000.npz \
  --loss joint --alpha 1.25e-4 --iters 1500 --chunk 100
# 仅在有候选时才手动运行（本轮无）：
# .venv/bin/python scripts/manual_verify.py dfthcsos <family_dir> --salt <local-salt>
```

引用：Lera V7 `compact_seed.py`/`fastfit.error2/lbfgs`（`artifacts/20261106_high_yield/lera_data/dfthc_refit/`），
基线 500 步数见 `20261109_joint_budget/README.md` §3，换基/分阶段 null 见
`20261109_ubasis_retrain/README.md`，新电路 -0.41% 见 `20261109_angles_r5/README.md`。
