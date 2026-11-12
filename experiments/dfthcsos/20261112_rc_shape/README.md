# (R,C)/B 形状重分区：no-go（2026-11-12）

目标：在 20 mHa 误差门内把化学 DF-THC 的 rows = 76 + R·B 降下来。
结论：**三条路线全部 no-go**，门是误差而不是成本：

1. **B=143 下改 (R,C)**（R=5/6/7，R×C≈350–400）：rows 能降到 791–1,077，但那些形状的
   basis 原子总数 R·B 只有 715–1,001，而所有过门的公开/自建表都在 **1,020–1,287**。
   实测 (5,143,75) 从结构 seed 训练 1,000 步仍在 **95.8 mHa**（连续），离所需的 ≈13 mHa 差 7 倍。
2. **截公开 R4/B255/C120 表的 B**：B=255→220 的 seed 误差 **360.5 mHa**，1,000 步 L-BFGS
   压到 19.69（连续），但完整 8-bit 渐进量化后是 **35.06 mHa**（`error_2`），是门的 1.75 倍；
   B=200/180 的 seed 分别是 593.6/848.0 mHa，更差。
3. **成本侧**：本地 `tensorqrom8` 的 rows 缩放是非线性的（791 行 4,608 T/pass，1,220 行 5,148），
   任何 R≤7 的形状都比当前 14,840 **更贵**；即使换成 Maoxin v22 的 4,089（线性外推），
   R=5/B=143 也只有 −17.8%，而它的误差差 7 倍。

**验证范围**（重要）：本记录只有本机实测的浮点/8-bit 词表指标，走官方 verifier 代码路径
（`dfthcsos.verify.evaluate_words`、`refine.py` 的 offsets/一体行），**没有构建 ANGLE 电路、
没有跑 78,080-shot 官方全量验证、没有提交**。所有 e1/e2/Λ/E_gap/λeff 都是
"官方代码、非全量 verifier"口径，不是排行榜成绩。

## 0. 对照：当前 (8,143,44) 复现

从 `artifacts/20261112_frontier/chem14840/submission.npz`（表 `8afd4c67`，Maoxin 4,089 loader）读出
给定词表，用官方 `evaluate_words` 复核：

| 量 | 值 |
|---|---:|
| error_1 | 19.999980 mHa |
| error_2 | 19.999997 mHa |
| Lambda | 282.973982 |
| E_gap | 3.914898003 |
| lambda_eff | 46.907378 |
| T / Q / cost | 14,840 / 427 / 297.24M |

该表 U/W 的**浮点** error_2 也是 20.0000 mHa（U 就是 8-bit 词解码后的向量），所以本记录里
"连续误差"指重新自由拟合 U/W 后的 error_2，与提交表的词表误差不是一回事。

## 1. 硬约束一：目标张量的秩（误差墙）

`error_2 = ||AᵀA − T||_F`，`T` 是 2,926×2,926 的 packed 目标。实测：

| 量 | 值 |
|---|---:|
| ‖T‖_F | 12.1001 |
| trace(T) | 48.5854 |
| T 的前 6 个特征值 | 7.23, 5.06, 3.77, 3.75, 3.23, 2.92 |

最佳 rank-k 逼近的误差（= 任何 R·C = k 的表在无结构约束下的下界）：

| k | 64 | 88 | 120 | 176 | 240 | 352 |
|---|---:|---:|---:|---:|---:|---:|
| 误差 (mHa) | 356.7 | 249.2 | 173.8 | 74.8 | **21.5** | 3.7 |

**rank-240 就已经压在 20 mHa 门上**。所以 R·C 不能低于 ~250，R·C≈350–400 是合理区间——
这一条把"R=4/C=60、R=3/C=107 这类便宜形状"直接排除（它们只有 240–320 项，且结构更死）。
同时也说明：20 mHa 门要求表把 T 的 ~250 维小特征结构都表示出来，任何压缩都必须近无损。

## 2. 硬约束二：basis 原子数（B 截断不可逆）

过门表的原子总数 R·B：

| 表 | R·B | 来源 |
|---|---:|---|
| 当前 8,143,44 | 1,144 | 本仓库提交表（20.0 mHa） |
| 公开 9,143,39 | 1,287 | manifest（19.9 级别） |
| 公开 4,255,120 | 1,020 | `729cd14c088f.npz`（19.94 mHa） |
| 候选 5,143,75 | 715 | 本实验（-37%） |
| 候选 4,180,90 | 720 | 本实验（-37%） |

**每一个过门表都在 1,000+ 原子**。原子不是冗余的：公开 R4 表（B=255）截到 B=220 后，
即使把权重在 verifier 的 pair 度量下对"完整 255 原子的贡献"重解最小二乘，seed 误差也从
19.94 跳到 **360.5 mHa**。

## 3. 实测 A：公开 R4/B255/C120 的 B 截断曲线

seed 构造 `btrunc.py`：每组按 OMP（对组内全部项的 top-C 方向）或按 importance 选 B 个原子，
权重用 pair 度量的最小二乘重解；C 保持 120。

| B | OMP seed (mHa) | importance seed (mHa) | importance 质量* |
|---:|---:|---:|---:|
| 255 | 19.94（公开表本身，8-bit） | — | 1.000 |
| 220 | **360.5** | 498.8 | 0.935 |
| 200 | 593.6 | 690.8 | 0.889 |
| 180 | 848.0 | 913.6 | 0.839 |
| 160 | 1,055.1 | — | — |
| 143 | 1,248.6 | — | — |

\* 主 session 用 `sum_c |W|·||U||²` 算的每组质量均值，与这里的误差单调对应。
斜率约 **12–15 mHa / 原子**（B≈200 附近），远大于任何 refit 能回收的量级（见下）。

## 4. 实测 B：唯一跑完整条 8-bit 流水线的点 R4/B220/C120

步骤（全部本机 CPU，float64）：

1. seed：公开 `729cd14c088f.npz` 每组 OMP 选 220 原子 + 权重 LS → **360.5 mHa**；
2. 连续 L-BFGS（`fit2.py`，scipy L-BFGS-B + jitted grad，`error_2 + 5e-5·D(w)`）：
   1,000 步 → **19.685**；再 6,000 步 → **16.316 mHa**（3.2 it/s，31 min）；
3. 8-bit signed-gauge 渐进量化（`quantize.py`，13 段冻结 + Adam/L-BFGS refit）：
   18.103 → 段 1（30% 冻结）就跳到 171.4，压回 35.31；最终 **35.063 mHa**；
4. offsets/一体行（`refine.py`）：官方指标如下。

| 量 | 值 |
|---|---:|
| error_1 | **5.65 mHa** |
| error_2 | **35.063 mHa**（门 20，**1.75×**） |
| Lambda | 289.672 |
| E_gap | 4.081644 |
| lambda_eff | **48.4563** |
| shape / rows | (4,220,120) / 956 |

要点：
- 8-bit 舍入代价 ≈ **+17 mHa**（18.10 → 35.06），比当前表族的 15.1 mHa 更大；
  把连续拟合做到 16.32 再量化仍得 **35.95 mHa**（短日程复测），所以不是"再练练就好"。
- 该表的 8-bit error_1 很好（5.65 mHa），说明一体行能吸收误差；**卡死的是 error_2**。
- 这个点没有过门，因此按约定**没有**构建 ANGLE 电路、没有跑全量 verifier。

## 5. 实测 C：B=143 下改 (R,C)

### 5.1 从小 R 形状从零训练（`compact_seed.py` = 加权 Cholesky 叶子 + 轨道 k-means + OMP）

同一优化器（scipy L-BFGS-B，`error_2 + 5e-5·D(w)`）、同样 1,000 步预算：

| shape | 原子 R·B | seed (mHa) | 1,000 步后 (mHa) |
|---|---:|---:|---:|
| 9,143,46（对照，已知可达 12.08） | 1,287 | 791.1 | **71.3** |
| 6,143,64 | 858 | 1,105.4 | **89.7** |
| 5,143,80 | 715 | 1,381.7 | **93.8** |
| 5,143,75 | 715 | 1,364.8 | **95.8** |

对照行是校准：`(9,143,46)` 在本仓库记录里要 6×60k 步才到 12.08 mHa；同样预算下
R=5/6 的轨迹比它差 30–35%。这些形状**没有**做 8-bit 量化（连续误差已是门的 4.5–4.8 倍，
量化只会更差），所以没有 e1/e2/λeff 可报。

### 5.2 从当前 8 组表 merge+重选原子（`seed_rc.py`）

把 8 组按对的项空间残差最小配对合并，每组用 OMP 从 2B 个旧原子中选 B 个、权重 LS，
C 取 top-C 项方向（单组补零）：

| target | R·C | seed (mHa) |
|---|---:|---:|
| 7,143,50/52/55 | 350–385 | 1,521.9 |
| 6,143,60/64/72 | 360–432 | 2,082.3 |
| 5,143,72/75/80 | 360–400 | 2,554.0 |
| 4,143,96/120 | 384/480 | 2,924.8 |

即"精确 merge 再截 B"即使配合 refit 起点也在 1.5–2.9 Ha，比结构 seed 还差，不是候选路径。

## 6. 成本：修正的 2×loader 因子

T_total = heurT + **2 ×** loader(per pass)（forward + reverse，见 verifier 的 `resource_costs`）。
主 session 的 R4 表中 T_total 只加了 1 次 loader（例如 R4/B220/C120 写成 13,119 = 10,484 + 2,635），
**修正后是 15,754**（按该表的 2,635/pass）或 **16,889**（按 4,089/1,220 的 3.35 T/row/pass 线性），
两种口径都使该点比当前 297M 更贵。下表统一用 3.35 T/row/pass；λeff 取 46.9074（R4/B220 用实测 48.4563）：

| shape | rows | heurT | Q | Maoxin 线性* T | cost | tensorqrom8 T | cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| 8,143,44（当前） | 1,220 | 6,662 | 427 | 14,836 | **297.2M** | 16,958 | 339.7M |
| 7,143,55 | 1,077 | 6,987 | 427 | 14,203 | 284.5M | 16,923 | 339.0M |
| 6,143,64 | 934 | 6,976 | 427 | 13,234 | 265.1M | 16,552 | 331.5M |
| 5,143,75 | 791 | 6,889 | 427 | 12,189 | 244.1M | 16,104 | 322.6M |
| 4,220,120（实测 λeff 48.456） | 956 | 10,484 | 429 | 16,889 | 351.1M | 20,115 | 418.1M |
| 4,200,120 | 876 | 9,964 | 429 | 15,833 | 318.6M | 19,394 | 390.3M |
| 4,180,120 | 796 | 9,444 | 429 | 14,777 | 297.4M | 18,672 | 375.7M |
| 4,180,100 | 796 | 8,407 | 427 | 13,740 | 275.2M | 17,635 | 353.2M |
| 4,180,90 | 796 | 7,894 | 427 | 13,227 | 264.9M | 17,122 | 342.9M |

\* Maoxin 线性 = 3.35 T/row/pass（4,089/1,220 的斜率），只是"如果 Maoxin 构造能移植"的上界投影；
本机 `tensorqrom8` 实测 rows→per pass 为 791→4,608、934→4,778、1,220→5,148
（≈3611 + 1.26·rows，固定 monomial/selection 成本占主导，**不是线性**）。M 的 Maoxin 逆向已 no-go
（128Q 内上限 5,142 T/pass，791 行代理 4,601，+8.4%）。

结论：
- 用本地 loader，**所有** R≤7 形状都比当前 14,840 更贵（+8.5%~+14%），形状线没有成本收益；
- 用"Maoxin 线性"上界投影，只有 rows≤800 的点有收益（R5/143 −17.8%、R4/180/90 −10.9%），
  而这些点的误差分别是 95.8 mHa（连续）和 848 mHa（seed）——都离门 4–40 倍。

## 7. R=5/B=180/C=75–100：**未测**

按指示没有启动这组训练（也没有构建电路）。已有的可迁移证据：

- B=180 的 seed 误差（R4 表、C=120、OMP 选原子）是 **848.0 mHa**，importance 选择 913.6；
  B=220 的同类 seed 是 360.5，跑满 6,000 步连续 + 完整量化后仍是 35.06 mHa。
- R5/B143 的对照轨迹（95.8 @1,000 步）比 B=180 的 seed 还低一个量级，
  但离门的距离仍是 7 倍。
- 用 B=220 的"seed→8-bit"经验（360.5 → 35.06，回收 10×）外推 B=180 的 848 mHa，
  8-bit 会落在 **55–70 mHa** 量级（投影，非实测）。

因此这组没有 e1/e2/λeff 原始数字可报——**未完成，且按现有证据判定 no-go**。

## 8. 判定

- **R×C / R=5,6,7 的 shape 线：no-go。** 误差墙来自两处不可压缩的资源：
  T 的 ~250 维小特征结构（rank）和 1,000+ 的 basis 原子数；B=143 下降低 R 同时减少这两者。
- **B 截断线：no-go。** 公开 R4 表截 35 个原子（255→220）就要 360 mHa 的 seed 修复量，
  完整 8-bit 后 35.06 mHa；B=200/180 更差。
- **成本侧：即使形状过门也没有收益**，因为本地 loader 的固定成本占主导（791 行仅省 10.5%），
  而 Maoxin 4,089 的构造无法在本地复现。

后续只有两条路有意义：(a) 换更便宜的 loader 构造（M 已判定当前不可行）；(b) 不改形状，
在 1,220 行上继续压 λeff/angle T。

## 9. 复现命令

```bash
cd .worktree/dfthcsos/artifacts/20261112_rc_shape
export DFTHC_DATA=/Users/zhaohuaxiang/ccjjllt/quantum/data/competition DFTHC_STARTER=$PWD/starter
PY=./env/bin/python          # 独立 venv：numpy scipy jax optax kickmix（未动共享环境）

$PY probe2.py                                   # 对照表 + T 的谱 + 各表 float/words 指标
$PY spectrum.py                                 # term 谱与 rank 墙
$PY costs.py; $PY feasible.py                   # heuristic T/Q 与 cost 可行域
$PY btrunc.py 220 seeds/pub4_B220_C120_omp.npz --select omp
$PY fit2.py seeds/pub4_B220_C120_omp.npz runs/fit_B220C120.npz --iters 1000 --every 250
$PY fit2.py seeds/pub4_B220_C120_omp.npz runs/fit_B220C120_long.npz --iters 6000 \
    --every 500 --resume runs/fit_B220C120.npz
$PY dfthc_refit/quantize.py runs/fit_B220C120_long.npz runs/quant_B220.npz --brot 8 \
    --free 1.0,0.7,0.5,0.35,0.25,0.17,0.11,0.07,0.045,0.03,0.0 \
    --stage-steps 600 --fit-steps 1500 --final-steps 1500 --kappa 5e-5
$PY dfthc_refit/refine.py runs/quant_B220.npz runs/ref_B220.npz --brot 8 --rounds 1 --maxiter 1000
$PY dfthc_refit/experiments/compact_seed.py seeds/compact_5x143x75.npz 5 143 75
$PY fit2.py seeds/compact_5x143x75.npz runs/fit2_5x143x75.npz --iters 1000 --every 250
```

## 10. 文件

- `artifacts/20261112_rc_shape/dfthc_refit/`：管线副本（未改逻辑；`fastfit.problem` 只修了
  starter-kit 版本的 `H2_sqrt` 形状 `(1,1,P)`）。
- `artifacts/20261112_rc_shape/seeds/`：`pub4_B220_C120_{omp,imp}.npz`、`pub4_B200_C120_imp.npz`、
  `pub4_B180_C120_imp.npz`、`pub4_B220_C90/C100_omp.npz`、`compact_{5x143x75,5x143x80,6x143x64,9x143x46}.npz`、
  merge+重选 seed（`*_R{4,5,6,7}_C*.npz`）。
- `artifacts/20261112_rc_shape/runs/`：`fit_B220C120{,_long}.npz`（连续 19.685 / 16.316）、
  `quant_B220.npz`（8-bit 35.063）、`ref_B220.npz`（官方 offsets/一体行，e1 5.65、e2 35.063、
  λeff 48.456）、`quant_B220_final.npz`（16.32 连续再量化 = 35.95）、以及 R5/R6/R9 的 1,000 步 fit。
- `artifacts/20261112_rc_shape/logs/`：B220 长跑、量化、refine 的完整日志。
- 脚本：`common.py`（路径/目标/指标）、`seed_rc.py`（merge+OMP 重选）、`btrunc.py`（B 截断）、
  `fit.py`/`fit2.py`（optax/scipy L-BFGS）、`spectrum.py`、`feasible.py`、`summary.py`。
  同一批脚本在 `experiments/dfthcsos/20261112_rc_shape/` 留了一份记录副本；在那边运行时
  `common.py` 会把路径解析到 `artifacts/20261112_rc_shape/`（大文件与 venv 不进 Git）。
- 独立环境：`artifacts/20261112_rc_shape/env`（numpy/scipy/jax/optax/kickmix），未改共享 `.venv`；
  starter kit 只读复制自 `artifacts/20261112_coded2/pipeline/dfthc` 到
  `artifacts/20261112_rc_shape/starter/`（未修改对方目录）。
