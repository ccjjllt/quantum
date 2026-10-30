# 研究地图

资料快照：2026-10-30（北京时间）。通过 Kaggle MCP 读取比赛页面、公开 notebook 源码、保存的运行日志与讨论；另已读取官方 verifier。本文不是本仓库的实验成绩。

## 任务与目标

总分为三项相对基线改善倍数的几何平均，越高越好：

```text
improvement_b = reference_cost_b / candidate_cost_b
overall_score = (improvement_invsqrt * improvement_dqi * improvement_dfthcsos) ** (1/3)
```

官方参考提交的线上总分为 1.0。子任务 verifier 返回的 `score` 是成本，越低越好；它与 Kaggle 总分的方向相反。

| 任务 | 核心契约 | 成本 |
| --- | --- | --- |
| `invsqrt` | 22 位 `x`；对所有 `x=1…3,133,452` 施加 `1/sqrt(x)` turns 相位；恢复输入并清空 scratch | `Q × (Toffoli-like + T/4)` |
| `dqi` | GF(2¹²) 上 RS(4095, 4025) 的可逆解码；恢复 syndrome 并施加所需符号相位 | `R(ε+) × Q² × T` |
| `dfthcsos` | FeMoCo76o113e 分解、旋转树及 ANGLE loader；由实际加载的角度字重建并计分 | `lambda_eff × T_total × Q_total` |

权威来源：[Data](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/data)、[Evaluation](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/overview/evaluation)、[完整 metric 源码](https://www.kaggle.com/code/metric/google-quantum-ai-metric)。本地官方契约位于 `data/competition/verifiers/`。

## 影响实验设计的细节

### invsqrt

- 穷举全部输入，每个输入 64 shots，共 200,540,928 shots。salt 改变测量随机性，不改变输入集合。
- 每个 shot 的相位误差须不超过 `2^-24/sqrt(x)` turns；输入或 scratch 错误、相位超限均拒绝。
- 一般角度旋转的 T 成本还取决于剩余合成误差预算；静态门数不足以给出最终成本。
- 优先考察归一化、分段/多项式近似、相位融合、查表和寄存器生命周期。

### DQI

- 默认 102,400 shots。`S0…S69` 是 12 位量子寄存器，`E0…E4094` 是 12 位经典记录。
- 输入错误权重按任务分布采样，不是均匀取 0…35。脱离任务分布的诊断仍可做，但须单独解释。
- `value_errors + phase_errors` 进入失败率估计；上置信界 `ε+` 必须严格小于 `1/16`，并影响重复次数惩罚 `R`。零失败也不代表 `R=1`。
- 比较相近方案时，记录 salt、平均实际执行 Toffoli 和失败数，避免只比较 qubits 或一次总分。

### 化学

- 每个 ANGLE 电路最多 128 qubits。总成本模型的 `Q_total` 可超过 128，二者不要混用。
- `error_1` 与 `error_2` 均须不超过 20 mHa；同时要求 `Lambda > 49.0`、`E_gap > 3.914898` Ha 及 `0 < E_gap < 2*Lambda`。`lambda_eff` 没有单独阈值。
- `Q_total` 合并持续存活寄存器，并对可复用临时 workspace 取最大值。减少某个 loader 的宽度未必降低整体成本。
- 官方示例基线为 12-bit 角度、每组 `J=8`；文档给出 `T_total=93,237`、`Q_total=730`、成本约 `3.3556e9`。这些是官方说明中的数值，本仓库尚未复跑。
- 固定角度字重拟合系数、改变分解形状、量化精度和专用多字 QROM 是值得拆开研究的方向。

固定规范电路、salt 和参数时，验证可复现。hash 基于规范电路内容，单纯更改 ZIP 包装或文本注释不一定改变 seed。线上使用秘密 salt，本地分与 LB 不应混为同一结果。

## 公开 notebook 索引

以下是 2026-10-30 的读取快照，标题和版本可能继续更新。MCP 的 notebook 搜索/详情没有返回官方 score 字段；按分数排序不构成官方成绩证明。

| 来源 | 当时可核查的分数依据 | 适合学习的内容 |
| --- | --- | --- |
| [官方 Starter](https://www.kaggle.com/code/sohier/verifiable-circuit-compilation-starter) | 教程；无本仓库复跑结果 | 化学分解 → 角度 → 电路 → 验证 → ZIP；示例 `J=7` 比基线略差 |
| [Dmitrii：Compilation from Source](https://www.kaggle.com/code/dmitriigluzdov/quantum-circuit-compilation-from-source) | 保存的运行日志：本地 GM 23.028 | 三项算法解释和源码集合；当前快速路径仍会复用固定电路 |
| [Heliosli：The dataset is public now](https://www.kaggle.com/code/heliosli/the-dataset-is-public-now-enjoy) | 保存的运行日志：本地 GM 23.0290，三项 PASS | 强公开组合、组件来源与成本分解；主要复用公开二进制 |
| [yoyobar：62-qubit invsqrt](https://www.kaggle.com/code/yoyobar/lb-22-99-invsqrt-101-62-qubits) | 正文自报 Public LB 22.99252；该 notebook 主要验 hash 和打包 | 62-qubit 逆平方根，作者给出的成本约 101,002.54 |
| [SomeJoint：889-Qubit DQI](https://www.kaggle.com/code/somejoint/quantum-circuits-22-77-local-gm-889-qubit-dqi) | 正文报告本地 GM 22.77139；默认复用已有验证记录 | 有嵌入生成器，适合从源码研究 DQI |
| [Ahmed：DF-THC Group Compression](https://www.kaggle.com/code/ahmedberatozer/quantum-ai-df-thc-group-compression) | 保存的运行日志：本地 GM 22.90331826，明确不是 LB | 固定角度字下的系数重拟合、15 个 loader、相位审计 |
| [Kirill：Exact Gauge + 5-Word QROM](https://www.kaggle.com/code/kirilltym/quantum-circuits-exact-gauge-5-word-qrom) | 正文自报 V24 Public 22.79549 | QROM 与 DQI 宽度、门数、失败惩罚之间的权衡 |

Heliosli 当时保存的本地日志：invsqrt 为 62Q、改善约 20.5616 倍；DQI 为 889Q、改善约 59.8421 倍；化学为整体计分 430Q、改善约 9.9257 倍。组合 GM 约 23.029。不要把这些快照当作最优界。

许多组合共用 [hengck23 的 DQI 电路](https://www.kaggle.com/code/hengck23/dqi-kmb-at-59-56854)。标题的 59.56854 是 DQI 单项改善倍数，不是总榜分数；当时公开材料没有 `generate.py`。研究复用时记录组件来源和生成链条。

## 讨论索引

| 主题 | 已确认的含义 |
| --- | --- |
| [获奖源码交付要求](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/discussion/752010#3545855) | 主办方要求能产生完全相同电路的生成器，适用于所有任务和奖项。研究过程中同步保留生成代码与参数即可 |
| [ANGLE 可达输入范围](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/discussion/753092#3545739) | 主办方确认只需在规定 forward/reverse 遍历的可达状态上正确，为专用 loader 留出空间 |
| [DQI 稀有 phase errors](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/discussion/752344#3545879) | 主办方解释 HMR 清空 ancilla 后仍须处理相位修正；value errors 为零不足以说明相位正确 |
| [kickmix 发布 PyPI](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/discussion/753307) | 主办方公告支持本地安装和 macOS；公告本身没有证明线上 metric 已迁移至 PyPI 版 |
| [DQI 阶段优化经验](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/discussion/753607) | 参赛者经验：按算法阶段拆开，分别观察 Q/Toffoli，再组合有收益的修改 |
| [Measured nulls](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/discussion/753185) | 已测失败路线可帮助避免重复尝试；只在其参数与版本下成立，旧的 63Q 限制已被后续 62Q 方案突破 |
| [Salt effect](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/discussion/753424) | 参赛者观察到近似 DQI 的抽样波动；适合提醒相近候选做多 salt 比较，不代表普适波动上界 |

## 初始研究顺序

1. 熟悉官方基线的寄存器、成本组成和手动验证输出。
2. 每项选择一个可读、可重建的公开实现作为参考，先解释成本差异。
3. 一次实验围绕一个明确假设；有收益再组合，不要求搭建通用框架。
4. 在 [实验记录](../experiments/log.csv) 写下观察与下一步；失败结果同样保留。
