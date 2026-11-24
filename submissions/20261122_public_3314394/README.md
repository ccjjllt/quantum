# 2026-11-22 公开 33.14394 方案

提交 ref `58718917`，状态与 Kaggle 线上分数见下方回执。

## 公开来源与选件

今日榜首为 33.73732，但无对应公开包；公开 notebook 中最高且带完整 `submission.zip` 输出的是 [goodpjw2008 v10](https://www.kaggle.com/code/goodpjw2008/qcc-3-t-phase-fold-table-refit-lb-33-14394)（LB 33.14394）。通过 Kaggle CLI 下载该 notebook 输出原包（Kaggle MCP 本次未授权，改用同账号 CLI），未改动任何成员。

| 任务 | 成员 SHA-256 | 来源 | 自检成本 |
|---|---|---|---:|
| invsqrt | `bb676b95f94c923cc5482f6cd8d457ab5ff3e8180c8f7cfd2c9678335d0ba56b` | varianceofx 三项 T 门相位改写，父电路 rithvikredrouthu `d2148a7c`（37Q） | 60,927.5774 |
| DQI | `4b5721411adc239f61fc11c773a2358b75dfe7cb15586efae4f0459c77d77e52` | tonylica `4b572141`（900Q），源自 ThemBones 解码器线 | 305,041,647,011.3978 |
| dfthcsos | `eb4b5d79603e3d0d3fd25e9442590176a3ece88c1fe1d05e7a28247bb44f5736`（`submission.npz`） | Areeb Ali 3,372-T 装载链 + leotang09 `fd02c7f7` 表 + goodpjw2008 权重重拟合 | 251,688,793.54（λ_eff 46.923422774，T 13,244，405Q） |

组合自检 GM 为 **33.14398478024653**。

| 文件 | 字节数 | SHA-256 |
|---|---:|---|
| `notebook_output/submission.zip` | 77,979,564 | `27229d4f477d7a98bf634aa9a690aac9dfb49fcc2ba5c39440401862cfa79aba` |

## 验证范围

- 原 notebook 使用未修改的官方验证器（默认 salt）验证三项，日志与 `receipt.json` 均为 PASS：invsqrt 60,927.5774；DQI 0/0 错误；dfthcsos 误差 19.9999999 mHa、E_gap 3.914898000017、Λ 条件满足。
- 本地核对了 ZIP 全部 18 个成员，成员 SHA-256 与 `receipt.json` 完全一致。未在本地重跑官方验证器。
- Kaggle 线上评分使用秘密 salt，以提交回执为准；DQI 线上分数可能与默认 salt 自检不同。

## 回执

- ref `58718917`，提交时间 2026-11-22T11:36:07Z（`qingyu1232`），提交后剩余 4 次/日。
- 线上 public score：**33.14394**（`COMPLETE`，约 37 分钟后返回），与公开 notebook 报告一致。

## 致谢

电路均为公开作品：Syed Asad Ali（VQCC 原始生成器线，Apache-2.0）、rithvikredrouthu、tonylica、varianceofx、leotang09、Areeb Ali、maoxin123、mizeroluckygall、ThemBones、Atakan Aldemir 及原 notebook 列出的全部贡献者。