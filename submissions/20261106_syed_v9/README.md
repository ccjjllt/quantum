# 2026-11-06：Syed V9 公开组合提交

用户明确授权以 Syed V9 进行一次 submission，再以此为公开研究基线。

- 固定 notebook：[Syed V9 / run366109544](https://www.kaggle.com/code/syed3000/vqcc-own-circuit-portfolio-notebook?scriptVersionId=366109544)。
- 固定数据集：[vqcc-own-circuit-portfolio V9](https://www.kaggle.com/datasets/syed3000/vqcc-own-circuit-portfolio/versions/9)。
- 作者公开提交58039042的实际 Public Score为24.94081，由此前Kaggle MCP公开提交接口确认；不是本账号本次成绩。
- 本账号 `ccjjllt` 提交 **58041132**，API返回 Successfully submitted；创建时间2026-11-06 01:26:34.167 UTC / 北京时间09:26:34.167。
- 创建后只读回一次，平台确认文件 `submission.zip`，28,072,501 bytes。未持续监控评分。

## 包装与验证范围

作者原ZIP使用ZIP_STORED，536,814,718 bytes；首次下载240秒超时，只得到149,932,601 bytes，未用于提交。
改为下载固定数据集V9的压缩档，18个文件的名称和大小与V9清单一致，总计536,812,576 bytes。
按作者打包代码相同的 `__` → `/` 映射保留全部电路和NPZ原始字节，只改用ZIP_DEFLATED level6。
最终ZIP为28,072,501 bytes、18成员，没有混入invsqrt无回退或DQI−42研究候选。

沿用用户要求，没有计算或匹配SHA，没有在提交前运行本地全量验证；解压只进行了标准ZIP读取和文件布局/大小检查。
Syed当前notebook仅打包，方法正文引用作者kickmix-engine验证；不能将当前保存运行称为本机或原版官方全量复跑。
研究分支后续的局部检查或候选验证分别记录，不追溯标为本次提交前验证。

来源、版本清单、源notebook和机器回执保存在 `artifacts/20261106_syed_v9/`。
公共只读电路在 `artifacts/20261106_syed_v9/release/`，研究工作区以链接读取。
唯一创建的提交是58041132；没有推送代码、发布数据或额外提交。

提交前为避免重复查询最近提交时，平台也返回上一份Maoxin V2提交58014726已COMPLETE，实际Public24.78590；该被动读回保存在本次机器回执中。
本方案的电路与方法归属Syed及其完整公开上游链，不主张为本地原创。
