# 2026-11-20 公开 28.24094 组合

Kaggle 已接收提交 `58589263`，评分待返回。提交账号为 `qingyu1232`，时间为 `2026-11-20T01:52:03.970Z`。

## 公开来源与选件

通过 Kaggle MCP 核对近期比赛 notebook、高分关键词搜索和 `vqcc` 数据集。已查到最高且提供完整公开包的是 28.24094 档。选用 [arsen123 notebook v1](https://www.kaggle.com/code/arsen123/qcc-28-24094-public-frontier-verified/versions/1) 输出的原始 `submission.zip`。该 notebook 汇集下列三项，运行验证器并输出 ZIP。通过 Kaggle CLI SDK 核对已配置凭据的账号并上传原包一次，再用 Kaggle MCP 核对回执。

| 任务 | 成员 SHA-256 | 公开验证成本 |
|---|---|---:|
| invsqrt | `acc7b9c86b4f65c0204194779a85d2c6b6631538316ffab2091c416a178f60a0` | 74,361.66973599327 |
| DQI | `f6b555a64f5924254bb8478c7f95179f49aa1383434c2e8e9b692cde1c44c76b` | 345,118,737,157.6359 |
| dfthcsos | `6ef06081cb9c5752ee7235c86d480ddfc5db027f01e5d5d66a544dbda85d1958`（`submission.npz`） | 294,642,169.5116752 |

本地检查了 ZIP 全部 18 个成员。三个主要成员的 SHA-256 前缀与公开日志一致，15 个 ANGLE 电路的完整 SHA-256 与[上一份最佳提交](../20261118_sota2823/README.md)一致。

| 文件 | 字节数 | SHA-256 |
|---|---:|---|
| `submission.zip` | 50,445,813 | `0767c890dffc136059956d166923e46a1d827ea46c1328427132bd83cd28525d` |

## 验证范围

- 公开 notebook 的三项验证日志均为 PASS，按验证成本计算 GM 为 **28.2409631759**。
- 本次本地核对包内容与 SHA-256。未重跑官方验证器。Kaggle 线上评分由提交回执记录。
