# 2026-11-23 公开 33.17067 方案

提交 ref `58806317`，状态与 Kaggle 线上分数见下方回执。

## 公开来源与选件

2026-11-23 公开 notebook 中最高且带完整 `submission.zip` 输出的是 [goodpjw2008 v12 DQI Zero-Test Cuts](https://www.kaggle.com/code/goodpjw2008/qcc-dqi-zero-test-cuts-lb-33-17067)（公开 LB 33.17067）。通过 Kaggle MCP 下载该 notebook v12 的输出原包，未改动任何成员。其固定 invsqrt 与 chemistry 沿用了 v10 组合，DQI 换成 `6f78ecdd6360`。

| 任务 | 成员 SHA-256 | 来源 | 自检成本 |
|---|---|---|---|
| invsqrt | `bb676b95f94c923cc5482f6cd8d457ab5ff3e8180c8f7cfd2c9678335d0ba56b` | varianceofx 三项 T 门相位改写，父电路 rithvikredrouthu `d2148a7c`（37Q） | 60,927.5774 |
| DQI | `6f78ecdd636051d4d2dd8f24aaece1d454eb220aaf0df2c1d64c3d96fe22081d` | goodpjw2008 在 tonylica `4b572141`（900Q）上做 10 处零测试削门；8 处自研 CCX→CX、evgendvorkin CCZ→CZ、ozertuu 删除 CCZ | 306,435,716,269.51（900Q，316,124.13 mean T） |
| dfthcsos | `e337917c9b72da104e999233827e82005f43920e6f8955e567d5d499be29555a`（`submission.npz`，15 个 angle 成员同 receipt） | 3,357-T 装载链 + maoxin123 表 + goodpjw2008 权重重拟合 | 251,089,557.51（λ_eff 46.917982145460485，T 13,214，405Q） |

组合自检 GM（默认 salt）为 **33.00336099668257**；公开 notebook 与本次线上评分使用比赛 salt，见回执。

| 文件 | 字节数 | SHA-256 |
|---|---:|---|
| `notebook_output/submission.zip` | 77,998,789 | `1d031873abd36a3b23acdf86aecb87e0fb00bc09c33da2445af1209716aacbf3` |

## 验证范围

- 原 notebook 使用官方验证器（默认 salt）验证四项，`receipt.json` 全为 PASS：invsqrt 60,927.5774；DQI 306,435,716,269.51（102,400 shots 中 4 个 value errors，改写非精确）；dfthcsos 误差 19.9999999 mHa、E_gap 3.914898000017、Λ 条件满足。
- 本地核对 ZIP 全部 18 个成员，成员 SHA-256 与 `receipt.json` 完全一致。未在本地重跑官方验证器。
- DQI 的零测试削门不是精确改写：官方注释与 RezOps 复核均指出在极稀有输入下会返回错误相位。本包遵循作者定价规则，期望错误成本低于节省的 Toffoli 成本。
- Kaggle 线上评分使用秘密 salt，以提交回执为准。

## 回执

- ref `58806317`，提交时间 2026-11-24T02:22:31Z（`ccjjllt`），本日剩余提交次数以 Kaggle 页面为准。
- 线上 public score：**33.17067**（`COMPLETE`），与公开 notebook 报告一致，为账号当前最高分。

## 致谢

电路均为公开作品：goodpjw2008、varianceofx、rithvikredrouthu、tonylica、evgendvorkin、ozertuu、maoxin123、leotang09、Areeb Ali、Syed Asad Ali、ThemBones、Atakan Aldemir 及原 notebook 列出的全部贡献者（Apache-2.0）。