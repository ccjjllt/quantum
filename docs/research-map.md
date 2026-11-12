# 研究地图

资料快照：2026-10-30（北京时间）。通过 Kaggle MCP 读取比赛页面、公开 notebook 源码、保存的运行日志与讨论；另已读取官方 verifier。本文不是本仓库的实验成绩。
复盘快照见末尾「2026-11-10 系统性复盘结论」。

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
4. 按 [实验记录约定](../experiments/README.md)，在对应子任务的实验目录写下观察与下一步；失败结果同样保留。

## 2026-11-10 系统性复盘结论（北京时间；证据在各研究分支）

### 当前位置
- 本账号最好成绩 **25.22676**（自研三件套 `58190972`，COMPLETE；与 gengsr 作者数 25.2268 差 0.00004，P0 的 −160K 被 DQI salt 噪声淹没）。
- 公开榜首 **29.30**（Entangled Team，11-08），差距约 16%；27–29 分段无公开代码，差距结构性解释暂无。
- 比较基线：gengsr 25.2268（`references/public-baseline.json`）；Syed V9 与 Public Frontier 留作历史对照。

### 三线复盘总账
1. **invsqrt**：旧 family（7c10edba）全部饱和——单删/辛秩/HMR/脏借用（实测 +1/处）/T 融合/重排序/跨守卫缓存（全电路 True+clean+同守卫 0/190），外加 2 次 FAIL 仲裁。新 family（gengsr 26ebf39d，shifter-46 + A3 shift-select 循环）已审计：−11 Toffoli 中 A3 占 −72 但不可迁回（支撑集不同）；新电路自身窥孔亦饱和。方向①（S1/S2 Hosen + A3 微角）closed。
2. **DQI**：局部缓存枯竭（残余 0/1618，载体 0，主因归零线供给恒为 0）；e9 差分 −55 已定位（convert/unconvert 对称 −48 CSWAP 模板 A + unextract −7 模板 B）。Q−1：粗区间无结论 → 精确后向活性 M_exact=892（真值）→ 零 paid 重命名不可能；但 7 处切口 0-paid spill 各自成立、D+E 与 D+H 合并全等通过；全电路构建 closed（q845/q849 缺口 31.8 万/19.9 万触碰）。唯一剩余杠杆是 R 项（w17/accidental-zero），需 72-salt 约 7M shots 算力。
3. **dfthcsos**：固定 (8,143,44) 已死（KKT 切空间、第二折点、联合 Newton、LSB、预算再分配全 closed）。自研 P0（规范 303 翻转移植，T−8）78k-shot PASS 299497670.48（−160.18K），已随三件套提交。训练盆地：R5 2000 步 85.31 mHa、渐近 63.3；brot=6 的 −18.61% T×Q 因 e1 字宽地板（9620 mHa 缺口，训练梯度恒零）不可兑现；换基/范式/形状均会于同一 ~130–180 盆地。

### 新架构判断
- 唯一被验证的"整族更换"是 gengsr invsqrt（−893，A3 循环代替 CCX 树）——采用而非自创。
- 自研新机制（脏借用恒等式、spill borrow-reroute 模板、规范翻转移植）均为补丁级（≤0.2%），且多数方向已被证伪。
- 16% 差距若存在，必为榜首未公开的整族更换；无公开代码则无法复盘，只能等榜首放出或押注 DQI-R/化学新训练范式。

### 后续切口（需算力或立项）
- DQI：R 项 72-salt 实证；Q−1 统一 spill 调度（干扰图着色：MIS 唯一 {D,H,S}，S 系 bit-exact 关闭；5 合并 CONFLICT 机理清楚）。
- 化学：GPU 长训（本机 JAX cpu 已到渐近；brot=6 证明 GPU 改变不了字宽地板，新形状/新 loss 才值得烧卡）。
- invsqrt：S1-M1 级改写已证伪（0/13）；整族重综合未立项。
- 提交策略：三件套 58190972 COMPLETE 25.22676 为当前最好；DQI salt 噪声 ±0.46% 远大于各补丁收益，改包重提的期望值约等于抽奖。

## 2026-11-11 公开前沿刷新与结构判断（北京时间）

### 已兑现
- 本账号 `58235797`（Grimoire 33 三件套，三件全本机官方验证）**COMPLETE，public 25.33133**；
  本地 GM `25.331334272` 与线上逐位一致。三件 SHA 与本地分数见
  `submissions/20261111_grimoire33/README.md`。
- 公开 notebook 前沿刷新为 busyaprime 25.33133 / Ozer 25.32234；LB 榜首仍
  29.30100（Entangled Team，11-08），前三未变。

### 结构事实（本轮实测或读码）
- **DQI 的 R 固定**：`R(eps_plus)=ln2/-ln(1/2+2√eps_plus)`；0 失败 + 102,400 shots +
  δ=2^-128 → `eps_plus≈8.66e-4` → R=1.19126。所有零失败方案相同，不能从 R 取分。
- **DQI T 分解**（9f 实测，cd71 同形）：extract 59,169 + synthesis 31,635 + convert 60,663
  + scan 44,275 + unconvert 62,534 + unsynthesis 40,429 + unextract 96,881 = 395,586；
  uncompute 三段占 **50.5%**。
- **uncompute 目标分布**：CCX 大量以 syndrome 线 S（q<840）为目标（unextract 75,899/94,293；
  unsynthesis 28,967/40,143；unconvert 37,403/56,794），故 unextract 不是纯 ancilla 清理；
  ancilla-only 可删约 48,961 门（−12.4% T，GM≈26.48）。
- 论文 arXiv:2610.22367（Gu, Kemeny, Yelin, Lukin）的 DQI 任务明确允许
  **X-basis measurement-based uncomputation**，并声明电路不必构造 error word、不必沿用 EEA；
  其 discovered 电路为 442,397 T / 1,837 Q（Q²T 比我们差），但方法学支持 MBU 与 direct phase bit。
- **化学**：15 个 loader 被验证器前向、反向各计一次，8,246/14,908 T；
  `Q_total = 84 + 40 + max(303,77) = 427`，loader 的 temporary 不影响 Q。
- **invsqrt**：`6c6a734d` 静态 max 1,380 vs 均值 1,218.83，161 门为条件执行；
  跨 family 拼接（gengsr 开头 + 免费 Z_POW 修相位 + maoxin 主体）已被公开件采用并本地复现。

### 已关闭（2026-11-11 晚）
- **DQI unextract→HMR**：liveness 实测 0 dead targets（unextract 93,787 CCX + 1,536 CSWAP 的所有目标
  在此后仍被使用）；且 kickmix 只有 **X-basis HMR**（对计算基态随机），没有 Z-basis 测量，
  无法把 syndrome 读入 classical bits。uncompute 是 phase-load-bearing，A/B 均关闭。
  证据：`experiments/dqi/20261111_unextract_hmr/`。
- **DQI Q-batching**：验证器契约要求 S0..S69 各 12 个 disjoint qubit（Q≥840），b=2 的 446Q 直接非法；
  可行 b≤892/840=1.0619，整数只有 1。现实最窄公开件 883Q 仅 +2.01% 上界，且要 8,081 T 预算。
  证据：`experiments/dqi/20261111_qbatch/`。
- **DQI 当前点 (892Q, 394,416 T) 已在 Q²T 前沿**：889Q 公开件 T +43.5k，净差 +10.3%；
  当前设计用 T 优势换 Q，是局部最优。

### 局部优化面关闭（2026-11-11 晚，证据在各工作区）
- **invsqrt**：公开 73 个电路清单（`manwithacat/vqcc-apache-public-circuits` v115）最高仍是
  `6c6a734d` 93,863.36；均值 Toffoli 普查的可用条件化池仅 6 门（上限 3 mean ≈ 186 分）；
  单 splice 最优已是现有 S0 切点（−1.00 mean）；S2 后缀切点小域验证 FAIL（x=5，0.5 turn）；
  62→61Q 纯重标号不可能；HMR 清理关闭。**invsqrt 不再投入。**
- **化学公开件**：`8afd4c67` 字表仍是 298,600,061.56 最低；heliosli 8d4c99a2 +200.73、
  junmiaotiao +259,374、catalog 最好 +200.73。
- **化学 loader 新公开件**（2026-11-11 12:38 UTC）：`maoxin123/qcc-v22-4097-toffoli-chemistry-loaders`
  在**同一张 `8afd4c67` 表、同一角度字**上把 15 个 loader 从 4,123 降到 **4,097 Toffoli/pass**，
  T 14,908→14,856，chem 298,600,061.56→**297,558,526.59**（−0.349%）。本机 78,080-shot PASS，
  e1/e2/λeff 逐位不变。已提交 `58239559`，本地 GM **25.360855**。
- **化学 MBU**：公开 15 个 loader 已经是 forward+MBU；1,142 个前缀/setup ancilla 由
  X-basis 测量 + 条件 CZ 以 0 Toffoli 清除，剩余 4,123 CCX/pass 是前向 oracle 本体。
  **MBU 方向已兑现，无剩余收益。**
- **化学形状 (5,129,68)**：精确 Q_total=427（recon 的 387 是 heuristic 字段，漏了 J·brot=40）；
  用今日 loader 仅 −0.98%；连续训练 5k 步 67.82 mHa，外推 50k≈38.3 mHa，**过不了 20 mHa**。
- **化学 7-bit**：直接重量化 e1 2,041.7 mHa / e2 450.8 mHa，λeff 78.15；**关闭**。
- **DQI**：unextract HMR 与 Q-batching 已关闭（见上）；公开 cd71 已用 886 个 template-C。
  可再嫁接的 template-A 仅 48 门（≈−0.012% T）。`cd71_tmplAB` 在同 seed（20261111）下
  PASS 0/0、score 373,798,635,029.88；但换 SHA 会重抽 salt，默认 seed 下候选与未改父件
  都出现 1 次 value error。按 72-salt 实测 15/72 单失败、单失败 +0.46%，期望惩罚
  ≈0.096% ≫ 0.012% 收益，**不提交新 DQI SHA**；保留已在线 0/0 的 `cd71c482`。
  证据：`experiments/dqi/20261111_cd71_diff/`。

### 仍开放（大工程，需独立立项）
1. **化学新分解**：R=8/B=129/C=44（同 R·C，仅缩 basis B，words 1,108，约 −3~5% T）与
   R=3/B=129/C=114（words 463，成本模型 0.647×，GM 29.3）正在 GPU 试训；后者精度风险高。
2. **DQI 换算法**：按 arXiv:2610.22367 的 BM + direct phase bit 重写，绕开 convert/unconvert
   的 123k T；论文 1,837Q/442k T 整体更差，只有 scan/phase 构造可借鉴。
3. **invsqrt 换算法**：S1 shift-select 重算降级或 61Q 值级重算证明；两者都是大工程。
