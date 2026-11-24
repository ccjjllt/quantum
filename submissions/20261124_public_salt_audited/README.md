# 2026-11-24 公开 33.17 盐审计组合

提交 ref `58815065`，状态与 Kaggle 线上分数见下方回执。

## 公开前沿扫描（2026-11-24）

- 榜首 **34.15280**（Entangled Team，2026-11-23T13:58Z），无公开 notebook 或提交包。
- 公开 notebook 中仍以 **33.17067** 为最高确认档（goodpjw2008 v12，已由本账号提交为 `58806317`，线上 33.17067）；排行榜约 270 队并列此分。
- 讨论帖 [Pricing the remaining headroom](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/discussion/761431)（2026-11-24T02:53Z）用官方验证器给出上界：公开文件重组已饱和（默认 salt 复算 33.17057，与 33.17067 档差在 salt 噪声内）；λ_eff、DQI 失败项、invsqrt 相位余量等可调旋钮合计至多约 0.5% GM；与榜首的约 3% GM 差距需改变电路构造本身。
- 逐个核对的新候选：Atakan V15 `dbb2ada3`（kawh1111 打包，105,143,160 字节）本地估计 33.17074，但其 V14 线上实测 33.07723，且 alexchilton v40 明确不采用；lucifer19 v22 为 33.17033；均不高于 33.17067。

## 选件

唯一有理论上限提升的公开包是 [aslan007x/qcc-v4-portfolio](https://www.kaggle.com/code/aslan007x/qcc-v4-portfolio) v6（与 [alexchilton v40](https://www.kaggle.com/code/alexchilton/33-17-lb-which-circuits-survive-private-salt) 同一 salt 审计谱系，ZIP 均 77,999,677 字节）。相对 v12 只换 invsqrt，并把化学权重表换成 Atakan 的重拟合版本：

| 任务 | 成员 SHA-256 | 来源 | 公开报告成本 |
|---|---|---|---|
| invsqrt | `6b59214530108d8c49c648f96c53b963d9b8477f8813db1edcf478bf45f6cf03` | prvsiyan 37Q 重构（alexchilton 8-salt 审计） | 约 60,927（v12 的 varianceofx `bb676b95` 为 60,927.5774，本件低 0.5774） |
| DQI | `6f78ecdd636051d4d2dd8f24aaece1d454eb220aaf0df2c1d64c3d96fe22081d` | goodpjw2008 在 tonylica `4b572141` 上的 10 处零测试削门 | 板面成本 305,033,681,034.67（mean 316,122.957 T，900Q） |
| dfthcsos | `17a7658245230231974ce517e596396de184d7f86d9301bd99eac1f70c251edf`（`submission.npz`） | 3,357-T 装载链 + Atakan 权重重拟合，λ_eff 46.917982145460485 | 251,089,557.51（T 13,214，405Q） |

15 个 `angle_k_*.kmb` 与 `submissions/20261123_public_3317067` 包逐字节相同（`angle_k_0` = `f2004c1f1d12f4a0028252aa3febd713856d246ff21134ca91a92348c4bf2994`，`angle_k_14` = `5cef55cf6208b2cfd4f52a13b63241b4ce7b5196f9dddfe0349e484030db07cd`）。

按公开成本估算，组合 GM 约 **33.17077**，比 v12 的 33.17067 高约 0.0001（salt 噪声内，不构成可靠提升）。

| 文件 | 字节数 | SHA-256 |
|---|---:|---|
| `notebook_output/submission.zip` | 77,999,677 | `cd1e720be3b26f77790aaa95b28a21777126d0494503c52aaf8779e6d27f51e6` |

## 验证范围

- 本地逐个核对 ZIP 全部 18 个成员，关键成员 SHA-256 与公开 notebook 打印值一致；未在本地重跑官方验证器。
- invsqrt `6b592145` 在 alexchilton v40 的 8-salt 表中通过；DQI `6f78ecdd` 的零测试削门仍非精确，极稀有输入下会返回错误相位，私有 salt 下失败风险沿用 v12 回执的说明。
- Kaggle 线上评分使用秘密 salt，以提交回执为准。

## 回执

- ref `58815065`，提交时间 2026-11-24T06:15:39Z，提交账号 `ccjjllt`。
- 线上 public score：**33.17067**（`COMPLETE`），与 `58806317` 同档；估算的 33.17077 未在线上实现，两份提交并列账号最高分。

## 致谢

电路与权重均为公开作品：prvsiyan、goodpjw2008、tonylica、evgendvorkin、ozertuu、varianceofx、Atakan Aldemir、maoxin123、leotang09、alexchilton、Syed Asad Ali、ThemBones 及原 notebook 列出的全部贡献者（Apache-2.0）。