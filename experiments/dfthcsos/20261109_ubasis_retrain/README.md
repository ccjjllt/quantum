# 换U基 + 换训练范式：R5/R4 500步探针（2026-11-09）

分支 `codex/dfthcsos-research`，工作区 `.worktree/dfthcsos/`。
起点 `b9eced3e`（λeff `46.891275349493`，T/Q=`14966/427`）。
本轮不重复 W-only / LSB / 预算 / R5短训复现 / angles实测
（见 `20261109_joint_budget/README.md` 与 `20261109_angles_r5/README.md`：
新电路-0.41%，短训182mHa）；
只做两件事：① 换U基（不用 cluster_chol/OMP），② 换训练范式（分阶段训）。

结论先行（全部 null，但数字完整保留）：

1. **换U基无收益。** R5/B135/C70 上随机球面帧 500 步到 **372.99 mHa**，
   实傅里叶帧到 **593.17 mHa**，均差于 cluster_chol 基线的 182.00 mHa；
   R4/B131/C83 上另一 Lera 初始化（eig leaves + roundrobin + OMP，
   非 cluster_chol）500 步到 **180.11 mHa**，与基线 stall 在同一位置。
2. **换训练范式无收益。** 同一起点/同预算下，
   U-only 250 步 + 联合 250 步到 **297.65 mHa**，
   比全程联合 182.00 mHa 差 **+115.65 mHa**。U-only 阶段本身停在 ~496 mHa，
   说明 W 不协同时 U 几乎不动；切开训等于浪费一半预算。
3. **切空间 refit 未触发。** 触发条件是任一变体连续 e2 ≤ 20 mHa；
   最优变体为 R4 eig/rr 的 180.11 mHa，距门 **160.11 mHa**。
   指数尾外推四条曲线的渐近线分别为 135/169/216/156 mHa（全 > 100），
   按当前尾律跑无限步也到不了 20 mHa；无 NPZ 候选，无 refit，无 shot 验证。

## 1. 换U基：方法

保留 Lera `compact_seed` 的 copies 构造（加权目标的 pivoted-Cholesky leaves
+ 平衡 k-means 分组，`balanced_kmeans` 按 V7 源码逐行复刻），但**替换共享基选择**：

- `rand`：每组 U 为 iid 高斯行归一化随机帧（B=135 > N=76，故为超完备随机帧，
  非严格正交；这是 B>N 下"随机正交"唯一诚实实现）。
  不调用 OMP、不读 leaves 本征向量。
- `dft`：每组 U 为实傅里叶帧（前 76 行为 cos/sin 对，
  频率 1..38；后 59 行为同频率固定伪随机相移 `rng.uniform(0,2π)` 扩展，
  行归一；每组固定置换区分）。与 chol-局域基相反的离域基。
- `R4 eig/rr`（另一 Lera 初始化）：用 `seed_numpy.py`
  `--leaves eig --assign roundrobin --select omp` 生成 R4/B131/C83 seed，
  即本征 leaves + 轮询分组 + OMP（非 cluster、非 chol）。

W 均为该固定 U 下的逐 copy 最小二乘最优解
（`W[r,:,c] = lstsq(Pi.T, leaf*mult)`，与 compact_seed 相同的 W-solve），
以隔离 U 基效应。脚本：
`experiments/dfthcsos/20261109_ubasis_retrain/make_alt_seed.py`。

| seed | 形状 | U 基 | 起点 e2 |
|---|---|---|---:|
| `seed_5x135x70_cluster_chol.npz`（既有基线） | 5/135/70 | chol leaves + cluster + OMP | 793.56 mHa |
| `seed_r5_rand.npz`（本轮新） | 5/135/70 | 随机球面帧 + W-lstsq | 11393.05 mHa |
| `seed_r5_dft.npz`（本轮新） | 5/135/70 | 实傅里叶帧 + W-lstsq | 10125.25 mHa |
| `seed_r4_eigrr.npz`（本轮新） | 4/131/83 | eig leaves + roundrobin + OMP | 2281.35 mHa |

注：随机/DFT 起点差 ~10 Ha 是预期的——W-lstsq 只能在给定坏 U 下最优，
不能弥补共享基与 copies 的失配；比较点是 500 步后的终点与尾律，不是起点。

## 2. 换U基：500 步 joint L-BFGS 曲线（`fit_probe.py`，float64，全程 U/W 联合）

| iter | R5 基线 cluster_chol | R5 rand（本轮） | R5 dft（本轮） | R4 eig/rr（本轮） |
|---:|---:|---:|---:|---:|
| 0 | 793.56 | 11393.05 | 10125.25 | 2281.35 |
| 100 | 411.29 | 1324.83 | 2850.05 | 443.96 |
| 200 | 314.32 | 740.04 | 1273.48 | 294.50 |
| 300 | 248.56 | 567.92 | 825.59 | 234.88 |
| 400 | 208.05 | 454.25 | 695.49 | 199.58 |
| 500 | **182.00** | **372.99** | **593.17** | **180.11** |
| 距 20 mHa 门 | +162.00 | +352.99 | +573.17 | **+160.11（最小）** |

- rand 起点差 10.6 Ha，500 步追到 373 mHa，前 100 步下降最快
 （−10068 mHa），但尾部仍在 373，差门 353 mHa。
- dft 全程最差（593 mHa），离域傅里叶基与局域 leaves 失配最严重。
- R4 eig/rr 从 2281 出发，第 100 步即到 444，第 500 步 180.11，
  与 R5 基线（182.00）会合在同一 stall 点：**换形状、换 leaves、换分组后
  仍是同一个 ~180 mHa 盆地**，不是种子运气问题。

指数尾拟合（末三点 `e = a + b·q^k`，k 单位 100 it）：

| 曲线 | q /100it | 渐近 a | 含义 |
|---|---|---:|---|
| R5 基线 | 0.643 | 135.1 mHa | 永不到 20（与 joint_budget 的 ~139 一致） |
| R5 rand | 0.715 | 169.3 mHa | 更差 |
| R5 dft | 0.786 | 216.3 mHa | 最差，且减速最慢 |
| R4 eig/rr | 0.552 | 156.2 mHa | 名义 q 最小但 a 仍 156，尾部比已升至 0.90/100it，减速中 |

四条渐近线全 > 130 mHa：**按当前尾律外推无限步也过不了门**；
幂律外推需数万步且跨量级不可靠（见 joint_budget §3），此处不采信。

## 3. 换训练范式：分阶段训（`staged_fit.py`，总额 500 iters）

同一起点（R5 cluster_chol，793.56 mHa），同一 float64 L-BFGS 内核，
`--chunk 50`，每阶段 fresh optax 状态：

| iter | 阶段 | e2 (mHa) |
|---:|---|---:|
| 0 | — | 793.56 |
| 50 | U-only（W 冻结） | 546.80 |
| 100 | U-only | 516.64 |
| 150 | U-only | 505.72 |
| 200 | U-only | 499.89 |
| 250 | U-only | 495.60 |
| 300 | joint | 409.38 |
| 350 | joint | 374.07 |
| 400 | joint | 342.96 |
| 450 | joint | 317.72 |
| 500 | joint | **297.65** |

对比（同 500 步预算）：

| 范式 | 500 步最优 e2 | vs 全程联合 |
|---|---:|---:|
| 全程 U/W 联合（基线 `fit_probe.py`） | 182.00 mHa | — |
| U-only 250 + 联合 250（本轮新） | 297.65 mHa | **+115.65 mHa（更差）** |

解读：U-only 阶段 200 步只从 547 走到 496（W 不动则 U 几乎无梯度可走）；
转入 joint 后从 496 出发，250 步只追到 298，远不及从起点全程联合的 182。
**分阶段等于把一半预算花在 W 冻结的贫瘠子空间**；L-BFGS 联合曲率才是
当前唯一有效的下降通道（虽然它也在 180 附近 stall）。
加权 loss（e1/e2/Egap 联合）未跑：连续探针尚无 e1 定义（需量化字），
且 e2 本身离门 160 mHa，调权重不能替代 8 倍误差下降；留给有 GPU 长训时。

## 4. 切空间 refit（未触发）+ 精确数声明

触发条件（任务 §3）：任一变体连续 e1/e2 ≤ 20 mHa。
实际最优 180.11 mHa（R4 eig/rr），距门 **160.11 mHa**（8 倍）；
次优 182.00 mHa（基线），距门 162.00 mHa。
**未触发，不执行 `nullspace_refit.py`；无 `evaluate_words` 精确数可报告。**
此处所有 e2 数均为 `fastfit.error2`（packed-pair 加权范数，
与验证器 `Compute_H2_residual_after_symmetry_shift` 同一定義）在最优 U/W 处的值，
float64 L-BFGS 训练探针产物，**不是**候选字（未量化、无 e1/Egap 门内数）。

## 5. 验证范围声明

- **无官方 78,080-shot PASS。** 本轮无候选（最优连续字离门 160 mHa），
  没有运行任何 78k-shot 验证，没有 `manual_verify.py` 调用。
- **无 `evaluate_words` 精确门数。** 连续探针 NPZ 只有 U/W（`fastfit.error2`
  曲线值），未经 signed 8-bit 编码 + 固定树 + one-body 成形，
  不能作为 `evaluate_words` 输入；先前实测表明未收敛 U 的量化字 e1/e2 在
  Ha 量级（见 angles_r5 §2），此处不再重复编码。
- 未提交 Kaggle，未推送，未改官方验证器、官方数据与共享环境。

## 6. 证据与复现

产物（`artifacts/20261109_ubasis_retrain/`，均为训练探针，非候选）：

- `seed_r5_rand.npz` / `train_r5_rand_500.npz`（起点 11393.05 → 500 步 372.99 mHa）
- `seed_r5_dft.npz` / `train_r5_dft_500.npz`（起点 10125.25 → 500 步 593.17 mHa）
- `seed_r4_eigrr.npz` / `train_r4_eigrr_500.npz`（起点 2281.35 → 500 步 180.11 mHa）
- `train_r5_staged_U250_joint250.npz`（U250+joint250，297.65 mHa）

```bash
# 新基生成（R5 rand/dft；R4 用 seed_numpy eig/rr）
uv run --no-project --with jax --with optax --with numpy --with scipy --with h5py \
  python experiments/dfthcsos/20261109_ubasis_retrain/make_alt_seed.py \
  artifacts/20261109_ubasis_retrain/seed_r5_rand.npz 5 135 70 --mode rand --seed 0
uv run --no-project --with jax --with optax --with numpy --with scipy --with h5py \
  python experiments/dfthcsos/20261109_ubasis_retrain/make_alt_seed.py \
  artifacts/20261109_ubasis_retrain/seed_r5_dft.npz 5 135 70 --mode dft --seed 0
.venv/bin/python experiments/dfthcsos/20261106_train_r5/seed_numpy.py \
  artifacts/20261109_ubasis_retrain/seed_r4_eigrr.npz 4 131 83 \
  --assign roundrobin --leaves eig --select omp --seed 0
# 500 步 joint 探针（任选一种子）
uv run --no-project --with jax --with optax --with numpy --with scipy --with h5py \
  python experiments/dfthcsos/20261106_train_r5/fit_probe.py \
  artifacts/20261109_ubasis_retrain/seed_r5_rand.npz \
  artifacts/20261109_ubasis_retrain/train_r5_rand_500.npz --iters 500 --chunk 100
# 分阶段范式（U250 + joint250）
uv run --no-project --with jax --with optax --with numpy --with scipy --with h5py \
  python experiments/dfthcsos/20261109_ubasis_retrain/staged_fit.py \
  artifacts/20261106_high_yield/train_r5/seed_5x135x70_cluster_chol.npz \
  artifacts/20261109_ubasis_retrain/train_r5_staged_U250_joint250.npz \
  --iters-u 250 --iters-joint 250 --stage2 joint --chunk 50
# 仅在有候选时才手动运行（本轮无）：
# .venv/bin/python scripts/manual_verify.py dfthcsos <family_dir> --salt <local-salt>
```

引用：Lera V7 `compact_seed.py` / `df_init.py`（`artifacts/20261106_high_yield/lera_data/dfthc_refit/`），
`fastfit.error2/lbfgs` 同目录；基线数字见 `20261109_joint_budget/README.md` §3
与 `20261109_angles_r5/README.md` §2。
