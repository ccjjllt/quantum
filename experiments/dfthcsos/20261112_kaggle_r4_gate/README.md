# R=4 B-truncation gate on Kaggle

## 目的

用 Kaggle 挂载的数据（不本机跑、不上传私有数据集）复核 R=4 公开表 `(4,255,120)` 的
B 截断是否还能过 20 mHa 的 `error_2` 门。`error_2` 只由 `(U, w)` 决定，offset solve
和列旋转都不改变它，所以这个门可以先于任何电路构建独立判定。

## 数据

- 比赛数据：`google-verifiable-quantum-circuit-compilation`（competition source）
- 公开表：`manwithacat/vqcc-apache-public-circuits` 的
  `factorizations/729cd14c088f.npz`（dataset source，公开 Apache-2.0）

内核：`ccjjllt/quantum-rc-r4-btrunc-gate`
（`kaggle kernels push -p .worktree/dfthcsos/experiments/dfthcsos/20261112_kaggle_r4_gate`）

## 方法

对每个 group 按 `sum_c |w|` 取 top-B 原子，保留完整 255 原子的贡献作为最小二乘目标，
重解权重；把 `U` 编码成 10-bit Givens words，直接调用 verifier 的
`evaluate_dfthc_angle_words` 计算 `error_2`。B=255 原表作对照。

## 结果（本机预跑与 Kaggle 完全一致）

| 结构 | error_2 (mHa) | 门 |
|---|---:|---|
| B=255 原表（control） | 19.94 | PASS |
| B=220 | 498.75 | FAIL 25x |
| B=200 | 690.79 | FAIL 35x |
| B=180 | 913.61 | FAIL 46x |

Kaggle 内核于 2026-11-12 22:19 完成；挂载路径实际为
`/kaggle/input/competitions/google-verifiable-quantum-circuit-compilation` 与
`/kaggle/input/datasets/manwithacat/vqcc-apache-public-circuits/...`。
输出 `diagnostic.json` 已下载到 `artifacts/20261112_kaggle_r4_gate/`。

结论：B 截断在 10-bit 下不是“误差风险”，而是数量级失败；R=4 的 B=180/200/220
路线全部 no-go。只有 B=255（完整表）能过门。

## 验证范围

- 本机：本地 `uv` 环境、官方 verifier 的 `evaluate_dfthc_angle_words`，只评 `error_2`。
- Kaggle：内核全量挂载数据跑同一脚本，输出 `diagnostic.json`；日志见 kernel 页面。
- 未构建 ANGLE 电路、未跑 78,080 shots 全量；因为 `error_2` 已独立超门 25 倍以上，
  构建候选没有意义。
