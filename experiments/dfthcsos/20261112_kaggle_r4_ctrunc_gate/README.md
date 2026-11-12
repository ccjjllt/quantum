# R=4 C-truncation gate on Kaggle

## 目的

保持公开 R=4 表的完整 B=255 基，只截断每个 group 的 copy rank C。做法：对 group 贡献
`X = w^T A` 做 SVD，保留 top-C 方向，再用完整 255 原子重解权重，最后让官方 verifier 的
`evaluate_dfthc_angle_words` 评 `error_2`。angle-word 表（76+4*255 行）不变，所以 loader
T 不变；只有 outer/inner state-prep 的 rank 项减少。

## 结果（Kaggle，2026-11-12 22:5x 完成）

内核：`ccjjllt/quantum-rc-r4-ctrunc-gate`
挂载：比赛数据 + `manwithacat/vqcc-apache-public-circuits` 的 `729cd14c088f.npz`

| C | error_2 (mHa) | SVD tail (relative, 4 groups) | 门 |
|---:|---:|---|---|
| 120（control） | **19.94** | 0 | PASS |
| 115 | 22.30 | 2.95% / 2.97% / 2.56% / 2.45% | FAIL 1.12× |
| 110 | 26.70 | 4.75% / 4.53% / 3.88% / 3.83% | FAIL 1.34× |
| 105 | 33.10 | 6.45% / 5.97% / 5.02% / 5.06% | FAIL 1.65× |
| 100 | 42.97 | 8.38% / 7.34% / 6.15% / 6.21% | FAIL 2.15× |
| 95 | 56.26 | 10.49% / 8.70% / 7.25% / 7.30% | FAIL 2.81× |
| 90 | 74.66 | 12.81% / 10.15% / 8.35% / 8.40% | FAIL 3.73× |
| 80 | 138.39 | 18.77% / 13.39% / 10.83% / 10.69% | FAIL 6.92× |

本机同一脚本预跑与 Kaggle 逐位一致；`diagnostic_ctrunc.json` 在
`artifacts/20261112_kaggle_r4_ctrunc_gate/`。

## 结论

- C=115 只差 2.3 mHa，但只省 ~4% 的 C；即使过门，chem cost 大概只降 2-3%，GM +0.7-1%。
- C=110 的 SVD 截断已 26.7 mHa，需要 joint U/w 优化才可能过门；单独 SVD 不够。
- 这条线交给 `20261112_ctrunc_joint` subagent 继续；若 90 分钟内 C=110 不过门，就 no-go。
