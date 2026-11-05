# 2026-11-05：Maoxin V2 原始公开组合提交

用户明确授权使用刚推荐的 Maoxin V2 进行一次 Kaggle submission，并要求跳过哈希匹配。

## 来源与文件

- 固定来源：https://www.kaggle.com/code/maoxin123/lb-24-786-pi-gauge-loaders-transferred-weights?scriptVersionId=365853243
- 版本 2 / run365853243；作者公开提交 58010361 的实际 Public Score 为 24.78590，已通过 Kaggle MCP 的团队公开提交接口核实。
- 使用该版本原始输出 `submission.zip`，没有替换成员或重打包。
- 本地文件：`submissions/20261105_maoxin_v2/submission.zip`，28,227,528 bytes，18 个 ZIP 成员。
- 依用户要求，没有计算或匹配文件哈希；只检查下载完成、ZIP 目录可读及三任务必要文件存在。
- 没有在本机运行官方验证器。作者本次公开运行重新验证了 DQI 和化学；invsqrt 复用既有完整验证回执。
- 作者保存日志的本地 GM 为 24.74808，DQI 有一次 phase error；该数值与实际 Public 24.78590 分开记录。
- 本地 invsqrt 研究候选未混入本次提交。

## 本账号提交

- 账号：`ccjjllt`。
- 提交 ID：**58014726**；Kaggle MCP 返回 Successfully submitted。
- 创建时间：2026-11-05 07:37:27.593 UTC / 北京时间 15:37:27.593。
- 说明：`Maoxin V2 run365853243, public 24.78590; original ZIP, no local patch.`
- 最后一次读回尚未返回分数；随后按用户要求停止监控，后续成绩未查询。
- 上次已完成提交 57980157 的 Public Score 为 24.54651。

下载工具遇到 DNS 失败后改用本机下载。首次上传超时，随后查询同一上传会话并从
服务端确认的位置续传，最终 HTTP 200；只创建了上述一次比赛提交。

机器可读回执：`artifacts/20261105_submission_maoxin_v2/receipt.json`。
签名下载/上传 URL 和上传 token 未写入记录；ZIP 继续由 Git 忽略。

本组合复用 Maoxin、Kirill Tymchishin、busyaprime、Atakan Aldemir、Syed Asad Ali 等人的
公开工作，具体来源与完整上游归属以固定 notebook 为准，不主张这些组件为本地原创。
