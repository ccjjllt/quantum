# 新形状/新种子切口 GPU 验证（2026-11-10）— 待批准，未推送

分支 `codex/dfthcsos-research`，工作区 `.worktree/dfthcsos/`。
R5/B135/C70 L-BFGS 已封顶 40.24 mHa（50k GPU 467 秒）、R4 20k 止于 73.07
（见 `20261110_gputrain/README.md`）：basin 问题，不在同一形状上烧卡。
本轮开两个未被证伪的新切口，用 qingyu GPU 配额验证。

## 1. 切口选择依据（对照 closed 表逐项排除）

已证伪（不重复）：固定 (8,143,44) KKT 极限；R5 50k 40.24 / R4 20k 73.07
盆地；Huber（500 步 440.80）更差；joint e2+α·eL1（α=1.25e-4，全程贴 L2，
2000 步 86.01 vs 85.31）同盆地；换基 rand 372.99 / dft 593.17（500 步）；
分阶段 U250+joint250（297.65）更差；brot=6 e1 地板（训练梯度恒零）；
J 扫描 J=5 已最优；R4 翻转 signed 空间为空；R6/B143/C59 四 seed 家族
33–37 mHa、grow 25.80（T 更差）shrink 回弹；B160/C59（−3.46%）、C70、
B180/C59 负收益不训。详见 `CLOSED_RESEARCH.md`、`20261109_longloss/`、
`20261109_ubasis_retrain/`、`20261110_shapes/`、`20261110_brot6/`。

**本轮新增证伪（CPU 成本屏，零训练）：B≤128 小 B 形状已死。**
`heuristic_costs`（官方 verifier，`Tcons=8304+heur` 复现 closed 数：
R5 −0.23%、R4 −1.70%、R6/B143/C59 +0.13% 逐位一致）显示 B=128→130 处有
temp 悬崖：B≤128 时 inner temp 303→574/575，Q 427→~697，
T×Q **+45%∼+51%**（(6,120,59)/(5,120,70)/(4,120,83) 全灭）。
故"R6 小 B"方向不进 GPU 队列。B≥130 恢复 temp=303：
(6,130,59) −0.04%（≈零收益，不训）、(5,143,70) −0.13%、
**(4,143,83) −1.54%**、(4,131,83) −1.70%（已训 closed）。

**切口一（形状）：R4/B143/C83，cluster_chol 种子。**
- 未被证伪：closed 表只训过 (4,131,83)；本形状 B 131→143（+48 向量），
  保守 T×Q 仍 −1.54%，在 R4 预算（−8.53% 上限）内留足余量。
- 论证：R4 在 B131 下 20k 到 73.07（欠收敛；渐近线未知）；加 B 直接加
  表达力，而 T 代价仅 +24T（14746→14770）。与 R6 小 B 不同，本形状不在
  temp 悬崖侧（B=143>130，Q=426）。
- 打平线：−1.54% 要求 λeff 上升 ≤ ~1.56%（参 compact 换算口径）。

**切口二（种子族）：R5/B135/C70 + eig/roundrobin/omp（Lera 规范初始化）。**
- 未被证伪：eig/rr 只在 R4 上训过（500 步 180.11，同盆地）；R5+eigrr
  组合从未训练。R5 侧 eig/rr 种子误差 1849.7 mHa（`20261106_train_r5`
  §2 记录值，本轮复现 1849.70，确定性一致）。
- 论证：R4-eigrr 是全部 500 步探针中最优（180.11 < 基线 182.00）；
  该种子族是 Lera 公开配方的规范入口，cluster_chol 只是其中一种。
  prob 与形状无关（见 §2），复用 `prob_r5.npz` 零边际成本。
- 不选 loss 加权/两阶段：Huber 与 joint-α 已分别证伪（更差/同盆地），
  U-only 分阶段已证伪（+115.65 mHa）。换优化器（Adam/自然梯度）仍开放，
  留作本轮两切口若换盆地失败后的下一候选，不在本次 job 内。

考虑过但拒绝：(5,143,70)（种子在盘，−0.13%，同 R 增 B 有限，收益太薄，
列为可选 Job C）；R7/B143/C50 quantize（29.36 连续 + 量化必加误差，
保守收益 −0.13%，期望为负）；(6,130,59)（−0.04%，过门也无收益）。

## 2. 本地冒烟（CPU，slim 路径，≤200 步，均已实测）

`slim_train.py` + `fastfit.py` + `prob_r5.npz`（float32 T/M；prob 与
(R,B,C) 无关，复用，无需重算）+ 新种子。`uv run --no-project
--with jax --with optax --with numpy`，jax backend cpu。

| 切口 | 种子误差 | 100 步 | 200 步 | 用时 | 同步对照（closed） |
|---|---|---:|---:|---|---|
| R4/B143/C83 cluster_chol | 789.18 | 344.58 | **274.86** | 6.0 s | R4-eigrr@200 294.50；R5 基线@200 314.32 |
| R5/B135/C70 eig/rr/omp | 1849.70 | 391.20 | **253.22** | 6.3 s | R5 基线@200 314.32（种子 793.56 出发） |

结论：脚本通、起点合理；两个切口 200 步均**优于各自同步对照**
（−19.6 / −61.1 mHa）。200 步不能证盆地，只证"值得上 GPU"；
门判断以 GPU 长训为准。

种子生成（`.venv/bin/python` + `seed_numpy.py`，CPU 十秒级）：
`seed_4x143x83_cluster_chol.npz`（789.18 mHa，14.5 s，743 KB）、
`seed_5x135x70_eig_rr.npz`（1849.70 mHa，13.7 s，804 KB）。
产物：`artifacts/20261110_gpu_newshape/`（2 种子 + 2 冒烟 npz）。

## 3. 待批准的 Kaggle job 定义（未执行，需用户批准）

- **Dataset 增量**：`qingyu1232/qcc-dfthc-train-bundle` 发 v2，
  在 v1（slim_train.py + fastfit.py + prob_r5.npz 68M + seed_r5/r4）基础上
  只加 2 个种子文件（~1.5 MB）；prob 不重传（形状无关）。
- **Kernel**：新建 `qcc-r4b143-r5eigrr-gpu-train`（GPU + internet），
  脚本 `experiments/dfthcsos/20261110_gpu_newshape/train_gpu_new.py`
 （v3 `train_gpu.py` 同款动态发现挂载，`find_bundle` 照搬）：
  Job1 R4/B143/C83 30k（chunk 300）→ `train_r4b143_30000.npz`；
  Job2 R5-eigrr 30k（chunk 300）→ `train_r5_eigrr_30000.npz`。
- **预估 GPU 分钟**：v3 实测 R5 9.34 s/1k、R4 9.7 s/1k；
  新形状同量级 → 60k 步约 580 s ≈ 10 分钟 + pip/启动 2–3 分钟
  ≈ **13–15 分钟**。配额约 29.7h（11-10 查询），占比 <1%。
- **回填**：job COMPLETE 后取回 npz 到 `artifacts/20261110_gpu_newshape/`，
  在此 README 补 1k/10k/30k 轨迹与渐近外推，再判盆地/门。

## 4. 验证范围声明

- 本轮本地只有连续 L-BFGS 探针（float64/JAX CPU，`fastfit.error2` 值，
  非候选）+ 官方 `heuristic_costs` 纯算术成本屏。**未经 8-bit 编码 +
  `evaluate_words`，未跑官方验证器。** 训练探针 NPZ 非候选。
- 明确未执行：任何 `datasets create/update`、`kernels push`、Kaggle 提交；
  用户批准前不碰。凭据/token 未入 Git（`.gitignore` 覆盖，大文件未进 Git）。

## GPU 实测（v2 bundle + 新kernel，2026-11-10，COMPLETE）
- kernel `qingyu1232/qcc-r4b143-r5eigrr-gpu-train` COMPLETE（2卡，dataset v2含2新种子已确认）。
- R4/B143/C83 30k（seed 789.18）：300:231.42 / 3300:77.44 / 12300:56.28 / 24300:51.49 / **30000:50.46**（283秒）。优于旧R4/B131 20k的73.07，但距20仍~30，27000后每3000步仅降~0.4，渐近~48-50。
- R5-eigrr 30k（seed 1849.70）：300:196.91 / 3300:72.71 / 12300:57.31 / 24300:54.05 / **30000:53.29**（295秒）。差于R5基线50k的40.24——种子族切换未换盆地，反而更高。
- 结论：两新切口均未过门。R4加B（131→143）把盆地从73拉到~50，但仍是basin；R5换eigrr种子无增益。下一候选只剩换优化器（Adam/自然梯度）或新loss范式，不再加B/换种子。
- 产物：`artifacts/20261110_gpu_newshape/train_r4b143_30000.npz`、`train_r5_eigrr_30000.npz`（Kaggle原样取回，连续探针非候选）。配额约10分钟。
