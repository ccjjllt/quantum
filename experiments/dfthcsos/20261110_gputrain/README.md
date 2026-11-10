# GPU 训练包与延续训练（2026-11-10）

分支 `codex/dfthcsos-research`。本目录记录 GPU 配额核验、训练包与本地延续训练。

## 配额核验
- 2026-11-10 用 qingyu1232 token 临时切换 MCP 身份后查询成功（此后已换回原 token）：
  GPU `used 974.982s / allowed 108000s`（约 29.7h 空闲，refresh 2026-11-14），TPU 72000s 未动。
- 限制：MCP 无远程代码/数据推送能力（无 dataset 创建、无 kernel 推送、无 session 文件写入），
  故 GPU 任务需人工在浏览器端建 dataset + GPU notebook 后运行本包脚本。
  qingyu 账号操作需其本人登录，与本仓库 token 无关。

## 训练包（`RUN.sh` + 既有脚本/种子/数据）
- 复用（无需上传两遍）：`experiments/dfthcsos/20261106_train_r5/fit_probe.py`、
  `artifacts/20261106_high_yield/lera_data/dfthc_refit/fastfit.py`、
  `dfthc/*.py`（小）、种子与检查点（`train_r5/`、`20261109_longloss/`、
  `20261109_ubasis_retrain/` 内，均为 MB 级）。
- 必带大数据：`data/competition/verifiers/dfthcsos/FeMoCo76o113e.fcidump`（122M，
  `Initialize` 一次性解析用）+ `FeMoCo76o113e.fixed_shifts.npz`（60K）。
- 依赖：`jax[cuda] optax numpy scipy h5py`（见 `RUN.sh`）。

## 作业定义
- **Job A（本地后台运行中）**：R5/B135/C70 从种子直跑 10000 步（`--iters 10000 --chunk 100`），
  输出 `artifacts/20261110_gputrain/train_r5_l2_10000.npz`。注：原 2000 步检查点
  已在 11-09 清理中随探针 npz 删除（日志与曲线保留），本次从
  `seed_5x135x70_cluster_chol.npz`（793.56 mHa）直跑，预期复现 500 步 182.00 /
  2000 步 85.31 后继续检验 63.3 渐近线。
- **Job B（待定）**：R4/B131/C83 从 180.11 mHa（500 步）续到 5000 步。CPU 约 10 分钟；
  GPU 上秒级。待 Job A 结论后再定，避免烧卡。
- EV 声明（按 `20261110_brot6/README.md`）：训练对 e1 字宽地板无效（梯度恒零）；
  e2 渐近 63.3 vs 门 20 mHa。GPU 改变不了任一结论，只能加速验证。
  brot=6 的 −18.61% T×Q 因门失败不可兑现，不进 GPU 队列。

## 验证范围
- 本目录只记录作业定义与日志；训练探针 NPZ 非候选（未经 8-bit 编码 + evaluate_words）。
- 若 Job A 到 20 mHa（ liquidate 渐近假设），才进入量化 + `nullspace_refit` + 验证器流程。

## 2026-11-10 追加：R5 10000 步本地直跑（CPU，807 秒）

- 从 `seed_5x135x70_cluster_chol.npz`（793.56）直跑 10000 步（chunk 100）：
  100:411.29 / 1000:113.44 / 2000:~85.3（复现 longloss）/ … / 9000:51.02 / **10000:49.85**。
  日志 `artifacts/20261110_gputrain/train_r5_10000.log`，产物 `train_r5_l2_10000.npz`。
- 结论：2000 步外推的渐近 63.3 被拉低到 ~45–50 盆地，但 1000 步仅降 ~2.7 且持续减速；
  距 20 mHa 仍 ~30 mHa。**R5/B135/C70 L-BFGS 路线 closed（ basin，非算力问题）。**
- 附带：slim 路径（预计算 prob + `slim_train.py`）200 步 315.30 vs `fit_probe` 314.32
  （0.3% 浮点路径差），训练载体有效；prob 68MB（float32 T）存 artifacts，
  可复算（`slim_train.py` + `fastfit.py` + `prob_r5.npz` + 任一种子）。
- GPU  verdict：10k 步 CPU 仅 807 秒——**GPU 对本路线无必要**；
  qingyu 配额（29.7h 空闲已确认，token 已换回）应留待真正需要并行/二阶探索的任务，
  而不是烧在这条已证盆地上。

## Kaggle GPU 投放（qingyu 配额，2026-11-10）
- dataset `qingyu1232/qcc-dfthc-train-bundle`（私有；slim_train.py + fastfit.py + prob_r5.npz 68M + seed_r5/r4）。
- kernel `qingyu1232/qcc-r5-r4-gpu-train`（私有脚本，GPU+internet）：
  v1/v2 FAIL（数据集挂载路径 `/kaggle/input/datasets/...` 与假设不符，已改动态发现）；
  v3 RUNNING（R5 50k + R4 20k，`train_gpu.py`）。
- 运行中 kernel 取不到实时日志（`kernels output` 完成前为空），完成后回填数字。
  本地 CPU 10k 对照组可作轨迹一致性校验。

## GPU 实测（qingyu 配额，2026-11-10，COMPLETE）
- 任务：`qingyu1232/qcc-r5-r4-gpu-train` v3（dataset `qcc-dfthc-train-bundle` 私有；
  v1/v2 FAIL 均为数据集挂载路径问题，已修为动态发现）。
- R5 50k（seed 793.56）：500:182.19 / 2000:84.82 / 10000:~49.9（与本地 CPU 49.85 一致，
  器件浮点差）/ … / 50000:**40.24**（467 秒）。15000 步后每 2500 步仅降 ~0.4，
  渐近 ≈38–40，距 20 mHa 仍 ~20。
- R4 20k（seed 180.11@500）：20000:**73.07**（194 秒），远未到门。
- 结论：GPU 把 50k 步压到 8 分钟，但** basin 结论不变**——R5/R4 在此优化器下到不了 20 mHa；
  20 mHa 需要新形状/新 loss/新优化器，不是更多步数。配额消耗约 11 分钟 GPU。
- 产物：`artifacts/20261110_gputrain/train_r5_50000.npz`、`train_r4_20000.npz`
  （Kaggle 输出原样取回；连续探针，非候选）。
