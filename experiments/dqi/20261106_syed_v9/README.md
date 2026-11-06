# Syed V9 DQI：旧 −42 门迁移检查与新基线研究

日期：2026-11-06（北京时间）；分支 `codex/dqi-research`。
固定输入为主仓库下载的 Syed notebook V9 / run366109544 原始 DQI，
本工作区只读链接 `artifacts/20261106_syed_v9/release/dqi.kmb`。

同日后续：[高收益方向交叉研究](../20261106_high_return_research/README.md)补充了精确阶段计数、实际二次核ANF、近期论文适配及旧C1源bundle。
本文件的阶段SVG估计已被后续精确静态计数确认；Syed V9精确生成器仍缺失，但“公开旧源不可得”不再作为普遍前提。

## 结论

**Syed V9 已优于旧 fd0ef+Leo 合并候选；原 −42 不能直接作为补丁搬过去。**
旧收益是14个局部窗口各省3个CCX。本轮重新从旧实际电路重建这些窗口，
对每窗5根任意输入线穷举32态证明等价；随后从字面、线重命名、CCX控制交换，
一直检查到忽略夹杂免费门的付费门拓扑，在新 unextract 中都找不到旧窗口的骨架。
这证明现有补丁没有找到可合法应用的位置，**不证明全部42门收益已被新方案吸收，
也不证明更大窗口中没有等价改写机会**。没有生成新的DQI候选或运行完整官方验证。

新基线最值得继续研究的是生成器级的算术宽度/重算权衡和恢复表示，
其次是当前 decoder 的失败归因与按概率定价的修复。继续盲扫旧11门模板不值得投入。

## 来源、版本与生成链

- [Syed notebook V9 / run366109544](https://www.kaggle.com/code/syed3000/vqcc-own-circuit-portfolio-notebook?scriptVersionId=366109544)：方法说明、18个公开产物打包；该notebook的代码本身不含解码器生成器。
- [Syed dataset V9](https://www.kaggle.com/datasets/syed3000/vqcc-own-circuit-portfolio/versions/9)：本轮MCP实际读取metadata和文件列表，仅18个编译电路/NPZ，没有生成器。
- dataset版本注记：V6引入892Q交换、pole16重算、mask-skip并称恢复k17；V7加入node3 retained-chain；V8/V9主要更新化学，DQI沿用CH3。
- 旧−42来源是Leo Tang七处unextract改写；本工作区保留的 `20261106_leo_merge/diffhunks.json` 是此次窗口重建输入。

MCP元数据保存在 `artifacts/20261106_syed_v9/dqi/sources/`；主仓库source目录保留
固定notebook原文。没有执行公开下载的Python，没有计算或匹配来源SHA。
缺少当前生成器是进一步改写全局调度的实际障碍，不能把旧SomeJoint源码视为当前生成器。

## 当前实际资源

| 项目 | 旧 fd0ef | 旧 fd0ef+Leo | Syed V9 |
|---|---:|---:|---:|
| Q | 891 | 891 | **892** |
| 静态Toffoli-like | 397177 | 397135 | **395679** |
| 当前本机普通256-shot meanT | 未重测 | 396863.078125 | **395395.47265625** |

新文件有58,286,875 operations、382240 CCX、12060 CSWAP、1379 CCZ。
相对旧merged静态少1456门，但多1Q；上述同一逻辑输入小批次仍显示净成本优势。
此处的meanT不是102400-shot官方成本，不能把新旧随机测量流当作逐门配对。
作者公开零失败口径成本约3.74772e11；实际失败仍影响R。

| 阶段 | 新版静态T估计 | 相比旧fd0ef的观察 |
|---|---:|---|
| extract | 59169 | 旧约59595，node3等改写降低约426 |
| synthesis | 31635 | 基本不变 |
| convert | 60687 | 旧约60796 |
| scan | 44275 | 静态骨架不变，新增经典mask跳过 |
| unconvert | 62558 | 旧约62711 |
| unsynthesis | 40452 | 旧约40539 |
| unextract | 96903 | 旧约97624，恢复段本身已重排 |

阶段数值来自native SVG舍入坐标，是静态估计而非运行时分阶段测量。
六个阶段都达到892Q，scan峰891Q；减少某个局部峰值不直接减少整体Q。
convert+unconvert约123245门、unextract约96903门仍占主要付费工作。

## −42 迁移：做到了什么，没有证明什么

1. 从旧fd0ef实际KMB和保留98个diff hunk重建14个11门→12门窗口，
   每窗7CCX→4CCX，净−3。全部是X/CX/CCX/SWAP，不含相位门或测量。
2. 对每窗任意5根边界线的32态独立穷举，输出完全一致。这证明的是旧局部恒等式，
   不依赖旧解码器输入分布。
3. 新电路中14个旧窗口、14个新窗口的原线号匹配均为0。
4. 将线号任意一一重命名，并允许每个CCX交换控制、SWAP交换目标，
   两种11/12门模板的操作骨架仍为0。没有因物理寄存器重新分配而误判。
5. 进一步只保留连续的付费门序列，忽略中间全部免费门，在unextract的
   96,903个付费门中搜索两种7CCX拓扑，仍为0。这个较宽筛查只判拓扑，
   即使匹配成功也必须重新核查夹杂线性操作和相位，不能直接替换。
6. 原14个位置的最近native语义标签都只有 `unextract` 顶层，没有逐节点标签。
   旧范围5,832,375ops/94,480CCX，新范围5,794,795ops/94,324CCX。
   无法仅凭这一粗标签把旧七组与新七个同义算术内核逐一绑定。

因此不迁移旧行号、不重新宣称−42收益、不拼接新候选。可能性包括新内核已经重综合、
不同分解下需要重新推导、收益分布到更宽的恢复调度；现有证据不能分清这三者。

证据：`migration_census.json`、`leo_windows.json`、`commuted_matches.json`、
`paid_topology.json`、`semantic_contexts.json`。`trace_context.py`首次输出冗余整段文本，
已缩为计数/位置摘要以免保存3.5GB重复数据；没有删除旧研究证据。

## 新版本局部实验一：mask跳过与失败边界

使用原版输入生成和寄存器判定helpers、本机native kickmix，手动10组×256输入，
两个电路使用相同逻辑输入和指定simulator seed。未调用官方verify、没有PASS或榜分。
每个电路共2560 shots；完整错误位置数组和种子保存在 `paired_baseline_probe.json`。

| 输入 | Syed V9 | 旧merged |
|---|---|---|
| 固定w=0/5/6/16/17 | 各256/256 syndrome恢复错误，scratch全0 | 同样全部value错误 |
| 固定w=18/31/35 | 各256零值/相位错误 | 同样零错误 |
| 官方普通分布256 | 零错误，meanT395395.47 | 零错误，meanT396863.08 |
| 官方权重、全部E掩码置0 | 零错误，meanT351129.68 | 零错误，meanT396862.13 |

全零mask探针确认新版scan控制确实省去约44275门；这属于Syed已采用收益。
普通独立12bit掩码下，单点零mask概率1/4096，该跳过的期望量级仅约10.81T；
整段所有mask都零的概率为2^-49140，因此靠这一特殊情形再跳过整个decoder没有实际收益。
这否定了“全零mask一招即可大幅降低平均成本”的直觉，不否定更一般相位融合。

V6版本注记称k17恢复，**V9实际诊断的w17仍全部失败**。不据注记认定其已修复，
也不把这一批结果升级为所有w17必败或归因到node3。需要实际父V6/V7同输入对照才能定位。
0失败的256普通样本远不足以判断稀有失败率。

## 新版本局部实验二：892→891的简单载体回收

`extra_wire_probe.py`检查q891在第一次被引用至下一次R/HMR清理之间的区间，
枚举是否有全程完全未引用的替代线。这只是无重算、整段借用的充分条件筛查；
未证明每个清理的外层守卫和替代线入场为零，不能把候选集合当作合法替换。
共584个实际活跃区间，37个没有全程闲置的私有线：27个在unextract、8个在extract、2个在unsynthesis。
仍有未使用的输入线，但未证明其入场干净，不能直接借用。最终统计见 `extra_wire_probe.json`。
所以没有直接产生全局891Q候选。缩短生命周期、dirty-wire代数、重算仍是不同开放问题。

## 继续研究的优先级和预算

1. **生成器级宽度/算术变体联合选择。** 先取得或重建当前有限域内核及ABI，
   把更宽乘法/求逆、pole flag重算和reverse调度作为整体选择。
   当前892→891在相同R下最多能增加约888 meanT仍打平；892→893至少应省约885 meanT。
   六个达峰阶段一起处理，单独缩一个allocator峰值不能计分。
2. **convert/unconvert或unextract的结构级重综合。** 总GM+0.1%需净省约1184 meanT；
   转换对降低约1%约1232门已到这一尺度。目标是相邻有限域乘积共享、表示转换与相位求值融合，
   计费必须包含恢复和纠相。旧−42等小模板只能作为短预算筛查，不是大收益主线。
3. **失败归因后选择性恢复。** 固定w≤5的官方概率仅4.23e−18，恢复相应guard几乎没有计分预算。
   若假定全部w≤17失败且无其他错误，Poisson计分情景给每shot约143个额外门的修复预算；
   仅w≤16约29门。这不是实测概率或普适上限。应优先追踪较高权重的偶发零/极点反例，
   并明确是 inherited decoder 失败还是新重写引入。
4. **同源公开版本的补丁组合仍可用，但先证明真实重叠关系。** 新892Q与旧891Q在恢复层
   已明显重排，不能只看两个改动在不同文本区间就断言可叠加。取得V6/V7精确内核后，
   可在相同ABI上的小函数层比较多种实现，而不是切整个58M行文本。

数字预算使用当前普通256shot的meanT作近似，成本公式为R×Q²×meanT。
一次额外官方评分失败的R增幅可抵消约1800门收益，需预先固定多seed或逻辑输入，
不选择最好的salt。这里没有承诺新方向必然产生收益。

初版载体调查把第一次引用之前的间隔也计入，过于保守；最终已改为第一次引用起算，
以上37个是修正后结果，不使用初版46个/1个全线耗尽的结论。

## 手动复现

在本工作区使用Python3.12/native kickmix1.0.0：

```sh
.venv/bin/python experiments/dqi/20261106_syed_v9/inspect_migration.py
.venv/bin/python experiments/dqi/20261106_syed_v9/match_commuted.py
.venv/bin/python experiments/dqi/20261106_syed_v9/paid_topology.py
.venv/bin/python experiments/dqi/20261106_syed_v9/trace_context.py
.venv/bin/python experiments/dqi/20261106_syed_v9/probe_dqi.py
.venv/bin/python experiments/dqi/20261106_syed_v9/extra_wire_probe.py
.venv/bin/python experiments/dqi/20261106_syed_v9/failure_budget.py
```

脚本仅做显式调用的静态/局部研究。没有自动全量验证、测试/CI、Kaggle提交、推送，
没有改动共享公开输入。原−42候选保留为历史方法，不作为Syed新基线的额外收益。
