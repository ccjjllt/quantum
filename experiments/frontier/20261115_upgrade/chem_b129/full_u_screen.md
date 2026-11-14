# B=143 → 139 full-U shrink screen (Kaggle GPU)

Follow-up to `stage_a.py`: the cheap W/H2_I-only refit at B=139 failed e2 (64.31 mHa).
This screen instead uses Lera's public Apache-2.0 `dfthc_refit/experiments/shrink.py`,
which fades the weakest bases and **refits U and W together** with on-device L-BFGS.

- Kaggle notebook: `qingyu1232/qcc-chem-b139-shrink` (T4 GPU, internet on).
- Seed: `maoxin123/qcc-chemistry-4033-toffoli-loaders` `submission.npz`
  (`U (8,143,76)`, `W (8,143,44)`), pinned SHA-256
  `3f864a7aeaa4d78984c8822761782b63be2d553b229f487e79640a73be147c44`.
- Schedule: `139x44` with `--merge 1 --pre 0 --fade 500 --fit 2500 --final 8000
  --save 139x44 --select impact --device --kappa 5e-5`.
- Gate for B=129: continuous error_2 must fall well below 20 mHa (target ≤15);
  otherwise the B=129 full retrain is not worth starting.
- The run is on Kaggle only; no local simulation or verifier.

If this passes, the next step is `139x44 → 135x44 → 131x44 → 129x44` with the same
pipeline, then 8-bit rounding, refit and the official 78,080-shot verifier. If it
fails, the B<143 line is closed and the current 27.31193 submission remains best.

## 2026-11-15 18:03 UTC 状态

- `qingyu1232/qcc-chem-b139-shrink`（T4）已启动；只跑到 139x44，作为快速闸门。
- `qingyu1232/qcc-chem-b129-full`（T4）已启动；schedule
  `139x44,135x44,131x44,129x44`，`--fit 2500 --final 8000 --select impact --device`。
  两个 run 都在 Kaggle GPU 上，使用 Lera 的公开 Apache-2.0 `dfthc_refit` 和
  starter kit；本机不跑模拟。
- 当前提交：`58350759` **COMPLETE 27.31193**，MCP 名次 **159 / 3053**。
  只有 B=129 连续 fit 的 error_2 足够低（目标 ≤15 mHa）才继续 rounding/build/verify；
  否则 B<143 线关闭，27.31193 保留。

## 2026-11-15 19:xx UTC 状态

- `qcc-chem-b129-full` 仍为 RUNNING，尚无 `list_notebook_session_output` 输出；
  `get_accelerator_quota()` 显示 GPU time_used ≈ 1,131s。
- 未读到最终连续 error_2；没有达到 GM 27.5 的候选，当前最佳仍是 27.31193。
- 未在本机跑模拟；B=129 的运行和后续 build/verify 都在 Kaggle。

## 2026-11-15 后续

- B129 full GPU 版本在读取结果前被改写为占位版本，旧 version 的 output 无法通过 MCP
  `kernels.get` 取回；未得到最终 `error_2`，不能据此下结论。
- 已改在 **Kaggle CPU** 上跑决定性的 B=139 full-U 闸门：
  `qingyu1232/qcc-chem-b139-cpu`，`139x44`，`--fade 300 --fit 1500 --final 4000
  --select impact`，下载 starter+pipeline，不下载 994MB competition zip。
- 若 B=139 full-U 连续 e2 仍 >20 mHa，则 B=129 直接关闭；若接近 15 mHa，再等 GPU
  槽位跑 B=129。所有计算在 Kaggle，本机不跑模拟。

## 2026-11-15 19:xx UTC 更正

- `qcc-chem-b129-full` 的 **v1** 仍在 RUNNING（`versionLabel:"v1"` 查询，GPU true），
  没有最终输出；v2 是后来写入的占位 CPU 版本，不代表 v1 结果。
- 同时 `qcc-chem-b139-cpu`（CPU full-U 139x44 闸门）仍在 RUNNING。
- 两者都未产出连续 error_2；当前没有 GM ≥27.5 的候选，最佳仍是 27.31193。
- 所有计算在 Kaggle；本机未跑模拟。

## 2026-11-15 19:xx UTC（最终状态）

- `qcc-chem-b129-full` v1（GPU）仍 RUNNING，无输出；`qcc-chem-b129-full` v2 是占位 CPU 版本。
- `qcc-chem-b139-cpu` 和 `qcc-chem-b139-quick` 均仍 RUNNING，无输出；Kaggle CPU 队列未返回。
- 没有最终连续 error_2，没有 GM ≥27.5 候选，未提交新包；当前最佳 27.31193。
- 本机未跑模拟或官方验证；所有计算都在 Kaggle。
