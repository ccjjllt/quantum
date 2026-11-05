# 2026-11-04：原始最高分公开组合提交

用户明确要求使用公开最高分方案进行一次 submission。按本次查询时比赛 Code 页的
Public Score 降序，Heliosli V5 排首位，公开成绩 **24.54651**；第二位 yoyobar 为 24.54649。
该排名指可见公开 notebook，不等于整个比赛排行榜第一。

固定来源：
https://www.kaggle.com/code/heliosli/the-dataset-is-public-now-enjoy?scriptVersionId=365542459

## 文件与验证范围

- 原始输出 `submission.zip`，版本 5 / run365542459；下载后没有重打包或替换成员。
- 实际提交文件：`submissions/20261104_heliosli_v5/submission.zip`。
- ZIP 大小：28,366,980 bytes；SHA-256：
  `7c7f618cef71886b51bb46223668ec13e6d975ccbf39f171aa6c1152cf1f675f`。
- 18 个成员的布局、CRC 和 SHA-256 已检查；全部 18 个哈希逐项匹配作者公开运行日志。
- 已从 Kaggle 重新下载提交 57980157 做流式校验，远端 28,366,980 bytes 和整个 ZIP SHA-256
  均与原始公开文件相同；证据 `remote_zip_readback.json`。
- 作者日志显示三任务均用原始官方验证器完整 PASS；本次没有在本地重跑该组合的三任务全量验证。
- invsqrt `15118bfa…e64c`：62Q，作者成本约 98185.1，SomeJoint 的两处跨 HMR 合并。
- DQI `748b01a7…154c`：891Q，作者成本约 3.75374e11，yoyobar 的第二处付费门改写。
- Chemistry NPZ `85c420b6…760a`，加 15 个 Syed 新 loader：作者成本约 3.12443e8，T15525、Q428。
- 本地 `aac6ce…61c3` 研究候选没有混入本次提交。

## 提交记录

- 账号：`ccjjllt`。
- 提交 ID：**57980157**，API 返回 Successfully submitted。
- 创建时间：2026-11-04 09:44:07 UTC / 北京时间 17:44:07。
- 说明：`Heliosli V5 run365542459, public 24.54651; unchanged ZIP; all18 SHA256 match author full PASS. No local patch.`
- 评分状态：**COMPLETE**；2026-11-04 10:15:15 UTC / 北京时间18:15:15读回。
- 本账号实际 **Public Score：24.54651**，与源公开方案一致。
- 此前已完成提交 57876561 的 Public Score 为 23.83790。
- 本次绝对提升 **0.70861**，约 **2.9726%**。这是本账号实际 Kaggle 分数，非本地 GM 预测。
- 最终读回与分差见 `artifacts/20261104_submission_refresh/final_submission_summary.json`。

第一次创建请求在文件上传后返回 HTTP 400。随后读取账号提交列表，确认没有产生新提交；
第二次使用标准文件名和缩短说明后成功创建上述唯一新提交。不能将第一次请求断言为已提交。

Kaggle MCP 多次返回 transport error；依用户指示，用 `.kaggle/` 中 ccjjllt 对应 Token
仅在当前进程内调用官方 Kaggle SDK/API。没有修改全局默认凭据，没有显示或记录 Token。
公开排名和固定 run 的网页核对完成后，依用户要求停止电脑控制，后续均为 API 调用。

源码、公开运行日志、下载收据、18 文件哈希、请求结果和评分读回位于
`artifacts/20261104_submission_refresh/`；签名下载 URL 和凭据没有写入研究记录。

来源归属保留 Heliosli、SomeJoint、Syed、yoyobar、Kirill、Lera、Ahmed Berat Özer 及
公开 notebook 完整上游链。此处是原始公开组合复用，不主张这些电路为本地原创。
