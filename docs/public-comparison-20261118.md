# 从 28.18067 出发的公开方案比较与研究入口

2026-11-18。团队 `ccjjllt` 的提交 `58487952` 已 COMPLETE，Public Score **28.18067**。同一包在未改动官方验证器上的三项成本为 74,560.906873、346,409,762,292.72 和 294,643,137.73，本地几何平均为 28.180659421。本页的预算使用本地值。[团队回执](../submissions/20261118_281806/README.md) · [原始验证 JSON](../submissions/20261118_281806/receipt.json)

## 哪些公开成果可以直接用

| 固定来源 | 可以复用的内容 | 与现役结果的关系 |
|---|---|---|
| junmiaotiao，Public Frontier U，notebook v1 / dataset v1 | maoxin123 的 `563d0583`，boristown 的 `5f901c55`，4,022 门单程化学 loader 与 `703843d3` 权重表。作者给出三项官方验证数据 | 按所报成本重算 28.180837，比现役本地组合仅高约 0.00018。两包共有同一 invsqrt。 |
| QVC v0.4.0，Git `eea36a54e77c151b903ecd5e081458e24147aa1a` | 含原作者 Syed Asad Ali 的 46Q invsqrt 与 889Q DQI 生成器、上游 NOTICE、构建方法和回执。发布方还给出完整组合的 Public Score 26.94027 | 有明确源码和竞争力的比较对象。889Q decoder 为 `7cbe8ecf`，现役 890Q 为 `575b043f`，需按两者各自的有效代码路径核算收益。 |
| marculera，DF-THC merge pipeline v7 | `B239_b8.npz` 提供四组已量化轨道、权重、树和角字，可检查较小分解的真实精度 | 此形状能满足二体精度。其中心列数、loader 门数及 λ 高于现役组合的相应成本预算。 |
| Caesura 等，BLISS-THC 作者数据 v1 | 同一 FeMoCo 体系的 290、310、330、450 个轨道及中心矩阵，可用来初始化其他分组结构 | 论文和竞赛采用不同的对称性偏移及误差契约，需先用官方张量重算。 |

公开检索覆盖当时 Kaggle 按最近运行排列的 50 个竞赛 notebook、按更新排列的 20 个 “qcc frontier” 数据集，以及相关讨论和固定 GitHub 发布。对前三队的公开提交接口只返回总分和时间。所见榜首是 **31.50404**。从一个总分无法反演唯一的三项成本，也不能据此判断哪队用了何种解码器。[公开榜](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/leaderboard) · [U 组合 v1](https://www.kaggle.com/code/junmiaotiao/qcc-28-181-public-frontier-combo-u/versions/1) · [QVC v0.4.0](https://github.com/Agnuxo1/qvc-chemistry-compiler/releases/tag/v0.4.0) · [marculera v7](https://www.kaggle.com/datasets/marculera/dfthc-merge-pipeline/versions/7) · [BLISS-THC 数据 v1](https://doi.org/10.5281/zenodo.14712662)

QVC 固定提交中的 `studies/source_portfolio889/upstream/inverse46-source.zip` 的 SHA-256 为 `0ddbc852ddf36233248da558d1a99b308f1b630ddce5fe210926cde405b2e852`，内含 `invsqrt_source.zip`，SHA-256 为 `7d9801ae20e942dba2211a656bba6014a0a16d57da534c0b60328d1c5d9d8254`。其中包含归一化、查表及算术生成代码。相邻的 `dqi_source.zip` 的 SHA-256 为 `49e2b331d4008afb724985caf1038765b7a910f08838b590bf6e8fb692772763`。本轮已读取这两个归档，46Q 源有了可访问的固定入口。未找到先前被删除的本地归档的独立哈希，不能确认两份存档逐字节一致。[构建说明](https://github.com/Agnuxo1/qvc-chemistry-compiler/blob/eea36a54e77c151b903ecd5e081458e24147aa1a/docs/SOURCE_PORTFOLIO.md)

## 谈大幅提分时使用的预算

设新旧成本比为 f₁、f₂、f₃，则新 GM 为 `28.180659421 / (f₁*f₂*f₃)^(1/3)`。下表各“仅改”栏独立计算。DQI 栏固定 890Q 和基线的失败惩罚；宽度或错误率有变化时须连同 Q²、R 一起计算。

| 研究目标 | 仅改一项所需成本降幅 | 三项均摊时各需降 | 仅改 invsqrt，成本上限 | 仅改 DQI，平均 Toffoli 上限 | 仅改化学，成本上限 |
|---:|---:|---:|---:|---:|---:|
| 29.0 | 8.24% | 2.83% | 68,418 | 336,870 | 270.37M |
| 30.0 | 17.11% | 6.06% | 61,802 | 304,294 | 244.22M |
| 31.5 | 28.40% | 10.54% | 53,387 | 262,860 | 210.97M |

一个可核查的组合目标是 invsqrt 降 6% 至 70,087、DQI 降 10% 至约 330,404 门（宽度及惩罚固定）、化学降 3% 至 285.80M。代入得 **30.10027**。这是对研发目标的分摊，尚无三项均达到该配置的电路。[官方基准与验证设计](https://arxiv.org/abs/2610.23832) · [本仓库评分计算](../scripts/gm.py)

## 研究工作区

三个保留分支已在约定目录重新检出。本轮算法、原型和实测证据分别保存在各工作区。公开包的采用与提交记录仍由 main 管理。

| 研究优先级 | 本轮取得的证据 | 什么结果会改变投入决定 |
|---|---|---|
| 首选一项小实验：invsqrt 融合查表与相位 | 141 行的近似在全域过精度线；固定指数的直接相位外乘为 45Q、298 CCX、93 个任意角旋转。普通拼接的查表和归一化超出 29 分所剩预算 | 做一段真实可变指数的融合电路。观察同一地址判断能否同时产生斜率位、常数相位并恢复辅助位；以全部存活 qubits 和合成旋转计价。 |
| 高风险、较大收益空间：DQI 改写跨支点算术 | 旧 1,373Q 完整解码器少 37,632 门；在 889Q 生成器中相同优化已被吸收或绕过。889Q 实际查询段仍花约 117,216 门，逐段矩阵共享与三剪切的独立成本预算均不够 | 4–8 支点上构造可逆、低宽度的递推，记录正反两趟的实际门数、相位和回收情况。按 35 支点评价时，889Q 从其自身基线单独冲 29 须净省约 45,528 门。 |
| 较低优先级：化学直接在离散角字上学习 | 论文叶字典补上对称性偏移、再补现役轨道可过连续二体门，但固定电路开销过高。四组共享 56 轨道的模型联合训练 4,000 步得到 39.54 mHa，量化后再拟合仍为 169.08 mHa | 从合格的公开 8 位角字出发逐组改变共享行，先过实际 20 mHa，再用真实 loader 计费。对 (4,200,88)、Q427、现役 λ，冲 29 须 ≤2,667 门/程，按原密度只得到约 2,888。 |

本轮交付的是可复算的研究结果与下一次实验的取舍。新设计的验证范围分别为全输入整数近似和局部门级模拟、完整 DQI 电路的固定 seed 4,096-shot 官方对照、真实 FeMoCo 张量的连续与量化数值复算。现有公开榜成绩仍取自提交 `58487952`。

- [invsqrt 的代码、资料和实验记录](../.worktree/invsqrt/experiments/invsqrt/20261118_new_frontiers/README.md)
- [DQI 完整电路 A/B 与连分式实验](../.worktree/dqi/experiments/dqi/20261118_new_frontiers/README.md) · [自适应掩码插值收益上界](../.worktree/dqi/experiments/dqi/20261118_mask_interpolation/README.md)
- [BLISS-THC 共享轨道与离散化实验](../.worktree/dfthcsos/experiments/dfthcsos/20261118_new_frontiers/README.md) · [公开四组分解与 loader 预算](../.worktree/dfthcsos/experiments/dfthcsos/20261118_four_group_budget/README.md)
