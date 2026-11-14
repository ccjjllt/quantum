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
