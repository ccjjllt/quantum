# 研究地图

资料快照：2026-10-30（北京时间）。通过 Kaggle MCP 读取比赛页面、公开 notebook 源码、保存的运行日志与讨论；另已读取官方 verifier。本文不是本仓库的实验成绩。
复盘快照见末尾「2026-11-10 系统性复盘结论」。

> 2026-11-13 清理说明：本文中引用的 `artifacts/` 历史目录、已关闭实验脚本和大型
> 候选产物已删除；当前最佳提交包和回执保留在 `submissions/20261113_27_078/`，
> 公开源清单保留在 `references/frontier-20261112/`。删除范围与放弃原因见
> [abandoned-research.md](abandoned-research.md)。文中旧路径仅表示当时的证据位置。

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
  证据：`.worktree/dqi/experiments/dqi/ABANDONED.md`（原 `unextract_hmr/` 目录已删）。
- **DQI Q-batching**：验证器契约要求 S0..S69 各 12 个 disjoint qubit（Q≥840），b=2 的 446Q 直接非法；
  可行 b≤892/840=1.0619，整数只有 1。现实最窄公开件 883Q 仅 +2.01% 上界，且要 8,081 T 预算。
  证据：`.worktree/dqi/experiments/dqi/ABANDONED.md`（原 `qbatch/` 目录已删）。
- **DQI 当前点 (892Q, 394,416 T) 已在 Q²T 前沿**：889Q 公开件 T +43.5k，净差 +10.3%；
  当前设计用 T 优势换 Q，是局部最优。

### 局部优化面关闭（2026-11-11 晚，证据在各工作区）
- **invsqrt**：公开 73 个电路清单（`manwithacat/vqcc-apache-public-circuits` v115）当时最高是
  `6c6a734d` 93,863.36（11-11 晚被 `9c708f7b` 93,555.26 取代）；均值 Toffoli 普查的可用条件化池仅 6 门（上限 3 mean ≈ 186 分）；
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
  证据：`.worktree/dqi/experiments/dqi/ABANDONED.md`（原 `cd71_diff/` 目录已删）。

### 2026-11-12 公开前沿再次刷新
- LB 榜首 **29.45296**（Entangled Team，11-11 22:02 UTC），第二 **29.30643**
  （Schrödinger's cat lived，20:48 UTC）。
- 公开 notebook 最高 **25.36727**（`pramitdas/qcc-public-frontier-25-367`、
  `asteriospanoras/lb-25-367-verified-portfolio-dqi-readout-fix`）。
- 新 invsqrt **`9c708f7b`**：WCao24 44-CSWAP normaliser + Thomas Gamet early prefix 的 splice，
  官方 **93,555.2627**（−308 vs 6c6a734d，−0.328%）；本机 200M 全量 PASS 93,555.3164。
- 新 DQI **`eae396ba`**（Atakan iso-gap h5 + readout windows）：892Q、mean T 394,089.4、
  本地 PASS **373,534,939,340.64**（−0.083% vs cd71）；换 SHA 的 salt 重抽期望惩罚更大，未采用。
- 新化学 **`f21b8a87`** + Maoxin v22 4,097 loader：λeff 46.9073833、T 14,856、Q 427，
  本机 PASS **297,557,548.71**（−0.0003% vs 8afd4c67）。
- main 采用“新 invsqrt + 新化学 + 原 cd71 DQI”的安全组合，提交 `58256166`，
  **COMPLETE 25.38868**（本地 GM 25.388681）；不换 DQI SHA。

### 仍开放（大工程，需独立立项）
1. **化学新分解**：B 轴已关闭（B135 量化后 33.12 mHa、loader 9,056 T 超 break-even 8,262）；
   只剩换 factorization/训练范式的算法级工作。
2. **DQI 换件门槛**：用 52 paired seed / 96-draw 期望成本判断，不再用通用 15/72 惩罚。
   `eae396ba` 已确认 **−0.0828%** 期望收益；单门级 T 收益仍小于 salt 噪声。
3. **invsqrt**：公开 splice 仍在演化；若出现新的“同状态 + 免费 Z_POW 修相位”拼接，按同法复核。
   61Q 值级重算与 S1 shift-select 降级仍是独立大工程。

## 2026-11-12 晚：公开前沿 25.39570 与三个判决性探针

- **公开前沿刷新为 25.39570**（`ozertuu/25-39570-sota-vqcc-fast-runner-portfolio`，
  11-12 01:51 UTC）：组合就是本仓库的 invsqrt `9c708f7b` + 化学 `f21b8a87` +
  DQI `eae396ba`；相对 `58256166` 唯一差别是 DQI。
- **eae 的 96-draw 期望成本**（公开 circuits manifest）：
  `eae396ba` 373,856,548,625.22 vs `cd71c482` 374,166,555,017.02，eae 低 **0.0829%**；
  52 个 paired seed 给出 **−0.082843%**、stderr 0.0000060%、失败 18/52 vs 18/52（同 seed）。
  不是单次 salt 抽签。本机 `eae396ba` 全量 102,400 shots **PASS 373,534,784,677.46**
  （salt `eae-20261112-a`，0/0）。据此组装并提交
  `submissions/20261112_eae_253957/`：ref **58265561**，
  **COMPLETE public 25.39570**，与本地 GM **25.39570057** 一致。当前 public 名次约
  **369**；25.3957 的公开 plateau 已扩大到数百队，分数 +0.028% 不足以提升名次。
- **化学 lowbits=3 探针**：`tensorqrom` 在 `refined_845`（R8/B143/C45，λeff 48.137）
  上 lowbits=3 的 ANGLE T 为 3,992/pass（当前 4,097/pass，−2.6%），但官方计分
  会再算一次 reverse（T≈14,725 vs 14,856，仅 −0.9%），且该表 λeff 高 2.6%，
  投影成本 ≈302.7M **更差**；另外最大电路 **195 qubits > 128**，被 cap 直接拒绝。
  lowbits=4 是 128-qubit cap 下的可行点，现有 4,097/pass 已近该构造最优。
- **invsqrt 经典查表探针**：`HMR` 是 X-basis 测量（H+measure+reset），
  指令集没有独立 H，也没有 Z-basis 测量；无法把 x 读入 classical bits 后按 x
  条件相位，故该捷径不可行。
- **化学树搜索**：当前 `tree_edges` 在 path/star/heap + 24 棵随机树的
  `tensorqrom.per_output` 代理下最优（5,119 vs 5,311–5,400），换树无收益。
- **化学表 survey**：Lera `final_refit_*`/`refined_845` 等 R8/R9 变体的 λeff 为
  47.0–49.1，均高于当前 46.907；当前 (8,143,44) 是已扫描表中的最低成本点。
- **化学 J=5/6 重综合**：`refined_845` 的 tensorqrom J=5 为 4,611 T/pass、
  Qmax 119、投影 328.1M，比当前 Maoxin v22 4,097/pass、297.56M 差 10.3%；
  J=6 超时且不具竞争力。loader 重综合路径关闭。
- **化学 batch 分组/顺序**：75 列按 J=5 分组与批次顺序是自由变量；当前连续分组
  proxy 5,120，200 组随机最优仍 5,120，相关性分组 5,155/5,150。无收益。

## 2026-11-12 晚（第二轮）：公开空间饱和与三条未闭合杠杆

- **公开 circuits manifest 全量复核**（`manwithacat/vqcc-apache-public-circuits`，2026-11-12 07:48 UTC，459 行）：
  invsqrt 最优仍是 `9c708f7b` 93,555.2627；DQI 最优是 `eae396ba` 373,534,939,340.64；
  化学最优是 `5d5007a75784` / `92fef6dd17f2` **297,237,044.95**（T=14,840、Q=427、
  λeff=46.907、e1/e2≈20.0/20.0），比当前 `f21b8a87` 低 **0.108%**。公开三件已全部采用或仅剩此 0.1% 级 swap。
- **化学全交叉表**（`parts/compatibility.csv` + factorizations + word_tables，346 个
  passing 组合）用官方成本模型重算：最低就是 297.237M，与 manifest 一致；没有
  “差一点过门”的低成本组合。化学公开空间饱和。
- **化学 J 批量杠杆**：Q_total = heuristic_persistent(84) + J·brot + max(heuristic_temp 303,
  angles_temp)；J=5 时 Q=427。J<5 每步降 8Q，但 loader T 可能上升；已立项扫描 J=1..8。
- **DQI Q 下限**：对 eae396ba 的 52 个 ancilla 做 def-use 活跃区间分析，峰值正好 **52**
  （6,751,317 个 live interval，起点 99.99997% 是 write），即当前结构下 Q=892 已无重编号空间。
- **DQI 死目标普查**：全电路反向 liveness（末端所有 S/ancilla/classical 输出都必需）只找到
  **1,262 CCX + 14 CCZ = 1,276 T（0.32%）** 死写；unextract 之外也没有大块可删。
- **DQI 乘法归因**（stage 直方图）：42-T `mul_xor0` 共 **3,406 次 = 143,052 T**：
  synthesis 659、convert 955、unsynthesis 691、unconvert 993、extract/unextract 各 54。
  99-T `mul24` 共 390 次（extract 76、unextract 311）。GF(2^12) 42 项来自
  Chudnovsky 7 点 × GF(2^3) rank-6；GF(2^24) 99 项是 11 点 × GF(2^4) rank-9
  （已优于公开源码的 105 项）。降秩是唯一 >5% 的乘法杠杆。
- **DQI 源码树复核**：公开 release source 的 `qcc-dqi-nonempty-projective-lean-source-v3`
  （Q=892/static 458,203）与 `carry-q26-892` 的 `decode_best`（本机构建 Q=900/T=484,418）
  都差于 eae；其 stage 编译器（retention/clifford/chain/live/conditional/gl2）已交给 DQI
  subagent 评估能否直接作用在 eae 上。
- **前沿文献**：arXiv:2610.22367 的 RS-DQI 是 4.4e5 T / 1,837 Q（BM + 少量分支存储），
  Q²T 比 eae 差；其方法学（BM、按失败预算裁剪、重算代替存储）不支持“直接照搬能到 341k”。
- **当前公开榜首 29.52446；25.3957 仍是数百队 plateau**。要进 26–28 需要至少一件
  ≥10% 的私有级改进，三条在研线：DQI 低 ancilla 重建、DQI 乘法降秩、化学 J 批量；
  invsqrt 新 family 普查已立项。

## 2026-11-12 深夜：乘法秩的文献校准与公开件 14,840

- **GF(2^12)/GF(2^24) 乘法秩**：当前 42 = Chudnovsky 7 点 × rank(GF(2^3))=6；
  99 = 11 点 × rank(GF(2^4))=9。文献已知 rank(F_{2^3})=6、rank(F_{2^4})=9、
  rank(F_{2^6})=15 均为**已证明最优**（Dumas–Lia–Sheekey 2026, arXiv:2602.09577；
  Ballet–Chaumine–Pieltant–Rolland）；q=2 的通用 Chudnovsky 上界在 n=12 是 51，
  我们的 42 已更优。要低于 42/99 需要非 tower 的专用张量分解（开放问题），
  因此 DQI 降秩的期望收益有限，不能单独支撑 −13.5%。
- **化学公开最优刷新为 14,840 T**：`5d5007a75784`（tiraJoon）与 `92fef6dd17f2`
  （maoxin123 4,089-Toffoli loader）在**同一 (8,143,44) 表、同一 λeff≈46.907** 上
  把 T 从 14,856 降到 14,840（T_angles 8,178 vs 8,194），chem 成本
  297,557,548.71 → **297,237,044.95**（−0.108%）。本地 GM 由 25.39570057
  升到 **25.40482516**（−0.036%）；仍属 plateau 级，不单独提交。
- **公开 portfolio 复核**（`ranjeet258/qcc-nov12-verified-expanded-portfolio`，
  2026-11-12 09:53 UTC）：其 selection report 的三件成本与我们的完全相同，
  唯一差异就是化学 14,840；baseline 25.40482651560744，gain 0.0。
  说明公开三件已无其他未采用件。
- **在研线**（subagent）：DQI 乘法降秩（B）、化学 J 批量（C）、invsqrt 新 family
  普查 + Q+1 换 C（D）、化学 group 重选（E）。只有全量官方 PASS 且实质增益才进入候选。

## 2026-11-12 深夜（第三轮）：14,840 提交与 DQI 两条 no-go

- **已提交 `58271862`**（用户批准）：invsqrt `9c708f7b` + DQI `eae396ba` +
  化学 `5d5007a75784`（4,089/pass loader）。化学件本机官方 **全量 78,080 shots PASS**：
  T=14,840、Q=427、λeff=46.907378146123214、e1/e2≈20.0 mHa、E_gap=3.914898003、
  成本 297,237,044.95。组合本地 GM **25.40482516**（上一版 25.39570057，+0.036%）。
  ZIP 82,261,596 bytes、SHA-256 `67f56f42…1e9b`、18 件。
  回执：`submissions/20261112_14840/README.md`；线上分数待回填。
- **DQI 低 ancilla：no-go**（`20261112_low_ancilla`）。公开 889Q 与 eae 892Q 的
  ancilla 都是 **48 个贯穿全电路的 24-bit external jet word + 1–4 flags**，
  def-use 峰值 = 全部（slack 0）；883Q 公开 baseline 只降 1.3% Q² 却 +30.6k mean T，
  净亏 5.4%。Q 不能靠 noscratch/allocator 降。
- **DQI 乘法降秩：no-go（含新证明）**（`20261112_mulrank`）。
  `rank(GF(2^3))=6` 由**完全枚举 2,869,685 个 5 项候选、0 解**证明（r=6 自检命中）；
  `rank_sym(GF(2^4))=9` 同法证明。42=7×6、99=11×9 在 Chudnovsky/tower 族内最优；
  即使 36+90 也只到 390,211 T，仍高于 377k 目标。公开 889Q 差分实测每个 12-bit
  秩项值 5,183 T、24-bit 秩项值 1,201 T（乘法占 77.9%），提示 eae 的乘法占比
  需要按 186/178 复合块重新标定（不是任务书的 45.3%）。
- **仍开放**：化学 J 批量（C）、化学 group 重选（E）、invsqrt 新 family + Q+1 换 C（D）。

## 2026-11-12 深夜（第四轮）：提交 salt 分析与在研线

- **58271862 的期望分**：本地 25.40482516 假设 DQI 沿用 58265561 的幸运 draw
  （373,534,784,677.46）。eae 的 96-draw 期望是 373,856,548,625.22（+0.086%），
  换 ZIP 会重抽 salt，故**期望 GM 25.39753475**；化学 −0.108% 的增益被 DQI
  期望 +0.086% 抵消大半。若抽到好 salt 可到 25.4048；差 salt 可能低于 25.39570。
  Kaggle 保留历史最好提交，58265561 仍是下限。
- **在研 subagent**（都只做本地构建/只读分析，未提交）：
  - C：化学 J 批量扫描（J=1..8）；目标实际 cost <292M。
  - D：invsqrt 新 family 普查 + Q+1 换 C；目标 ≥3%（≥2,800 分）。
  - E：化学 group 重选（同 B=143 形状，换初始化/局部交换）；目标 <292M。
  - F：化学 tree 真实成本重评（实际 loader T + refit λeff，而非 proxy）；目标 <292M。
- **本 session 已关闭**：DQI branch-recovery（决策机器 14.2%，下界）、低 ancilla
  （52 峰值、48 jet word、Q–T 负斜率）、乘法降秩（rank(GF(2^3))=6 完全枚举证明）、
  化学 loader-aware 训练（λ>0 退化）、公开三件（manifest 459 行 + compatibility 346
  组合全扫，最好即当前/14,840）。
- **判断**：公开+本仓库现有源码内，25.40 已接近上限；26–29 段需要新的解码器/
  factorization 算法族（4–6 周级），不是本 session 能完成的局部改写。

## 2026-11-12 深夜（第五轮）：继续并行立项

在公开+现有源码内已关闭 DQI 三条（branch/ancilla/rank）后，本轮又找到四条**未被公开件覆盖**的具体杠杆，均已立项（subagent 只做本地构建/只读，不提交）：

- **化学 R=7**（G）：公开 manifest 只有 R=4/8/9/10，R=7 从未试过。验证器精确
  heuristic 成本 (7,143,44)=6,230 T（R=8 是 6,662），rows 1,077（−11.7%），
  Q_total 仍 427；按 rows 投影 T≈13,449、成本 **269.4M（−9.4%）**；即使 λeff 升到
  48/49 仍 275.7/281.4M。核心风险是 R=7 的近似误差（8-bit 量化已占 15.1 mHa）。
- **化学 coded2**（I）：`quantize.py` 支持 `--coded2`（每 16 地址块 bit 1 也仿射），
  当前表 `coded2` 为空、历史日志只有 coded bit 0；每条电路再省 ~25 T，15 电路 ×
  两遍 ≈750 T（总 T 2.5%），潜在成本 −2.5%。
- **化学 tree 真实成本**（F）：此前 tree 搜索只用 `tensorqrom.per_output` proxy
  （5,119 vs 5,311–5,400），未用实际 loader T，也未对换树后的字重新 refit λeff。
- **DQI external 乘积共享**（J）：源码里 `external_corrected_product`（c≠0）与
  `external_mul_head` 都调用 `mul24_xor99(combine(head),D,·)`，只是目标 L vs N；
  两者操作数差一个 `scale(h,c)` 线性映射和 `cx(h,a,ct)`，若能用 0-T 线性修正共享，
  每步省 ~75–99 T，196 对 × 两遍潜在 15–39k T（4–10%）。
- **DQI 新解码器族可行性**（H）：half-gcd / BM retain-replace / trace 求根，
  目标 Q≤892、static T≤340k；既有的 “BM/Euclid/时域 Chien ≥190k” 下界口径先核对。
- **DQI 提交回执**：58271862 仍在评估队列；期望 GM 25.39753（salt 重抽），
  本地 25.40483（沿用幸运 draw）。

## 2026-11-12 深夜（第六轮）：external 共享的代数校准与榜首 29.746

- **DQI external 共享的精确关系**（本机推导，待 J 核实）：c≠0 时
  `P1 = c·P2 ⊕ (h·D)`；`c·P2` 是 0-T 线性映射，`h·D` 是两个 `mul_xor0`（84 T）。
  因此每步只省 `99−84=15 T`，不是 75–99；182 步约 2.7k T（0.7%）。
  c=0 的 186 块需要另一个 `a·D`（84 T）才能拆出 `h·D`，共享不省。
  结论：external 共享本身不足以支撑 ≥5%；只有作为 eae 的块级补丁才有 ~0.7% 价值。
- **榜首刷新**：Entangled Team **29.74602**（2026-11-12 10:54 UTC），
  Schrödinger’s cat lived 29.52446 退居第二；公开 plateau 仍 25.3957。
  差距从 16.2% 扩大到 17.1%（score），对应 product cost ≈1.62×。
- 58271862 仍在评估队列；期望 GM 25.39753。

## 2026-11-12 深夜（第七轮）：R=7 快检的管线约束

- 直接对当前 submission.npz 删一行 rho 得到 R=7（(7,143,44)），再用
  `dfthc_refit/build.py --qrom tensor --brot 8 --shots 1` 快检，失败于
  `AssertionError: words must be in the signed gauge`：`tensorqrom` 只接受
  `quantize.py`/`refine.py` 产出的 **signed-gauge** 角度字，`encode.encode` 的
  直编码（无 `angle_words`）不满足该断言。R=7 的误差/成本必须走完整
  quantize→refine→tensorqrom 管线（G 正在做），不能用“删行 + 1-shot”绕过。
- 该失败也说明：任何换 shape（R/B/C）的化学候选都必须重新量化角度字，
  不能复用 R=8 的 `angle_words`。

## 2026-11-12 深夜（第八轮）：invsqrt 四个方向全部 no-go

- **基线 `9c708f7b`**：Q=62、static 1,375（CCX 1,191 + CCZ 92 + CSWAP 92）、
  mean 1,213.8659、C=1,508.9567、score 93,555.3164（200M PASS）、
  worst/tol=0.9993237694、41 个旋转。
- **S1/S2 uncompute 对**：420 个前向同操作数对、305 对条件栈相同，但
  “目标只作对角控制”的 b 类 = **0**——电路已用 859 个 HMR 把 Hosen 清理做完；
  305 对在 485,101 点随机域删除后 0 对中性；15 个“目标未触碰”对全失败。
- **41 个旋转**：41/41 相位差只取 {0,±θ_k}，GF(2) 秩 41，无重复/互补列；
  最小 #15（θ=2.886e-11 半转）单删后 ratio 1.3304，官方 3/3 salt FAIL（x=644）；
  角重拟合 max 残差 1.113（基线 0.999），IRLS 发散。要 2,800 分需删 7 个旋转，差 7 倍。
- **61Q**：峰值 value-liveness=62（op 1618），每个比特 span ≥23,830 op、
  控制读取 ≥52 次；打平 +24.74 C，净赚 1,000 只允许 +8.3 C；释放一比特需
  ≥52 次重算 ≈ ≥52 C。**差 2×**。
- **Q+1/Q+2**：分段池 193+51+372+76+499=1,191 CCX；Q=63 需 ΔC −23.95/−68.40，
  Q=64 需 −47.16/−90.91；计分只数门数（并行前缀/进位保存深度收益=0），
  ancilla 唯一省分方式是消除重算，而 HMR 已把 uncompute 换完。**预算表不成立**。
- **死门普查**：22 个候选只有 3 门通过多 salt 复核，Δ=0.000 分；
  `cand_dead22.kmb` 官方全量 **FAIL**（x 未复原）。方法学：候选相位是
  salt 敏感的，单 seed 全定义域中性仍可能在其他 salt 下 0.5 turn 失败；
  所有候选必须多 salt × 64 shots/x 官方仲裁（22 个里 19 个假阳性）。
- **判决**：invsqrt 在公开 `9c708f7b` 上无 ≥3% 可行改进；四个方向全部关闭。

## 2026-11-12 深夜（第九轮）：58271862 COMPLETE 25.40482

- 提交 `58271862` 已完成：**public score 25.40482**，与本地幸运 draw
  25.40482516 逐位一致；上一版 `58265561` 是 25.39570（+0.036%）。
  说明本次 DQI salt 抽到了与上一版同量级的好 draw，化学 14,840 loader 的
  −0.108% 增益基本兑现；25.40482 已高于 25.3957 的公开 plateau。
- 回执：`submissions/20261112_14840/README.md`（已回填）。
- invsqrt 四方向 no-go 已记录；化学 R=7/coded2/tree/group/J 与 DQI 新族/共享
  仍在跑，任何新候选都需全量 PASS + 用户确认后再提交。

## 2026-11-12 深夜（第十轮）：化学 group 选择 no-go 与 signed-gauge 约束

- **group 选择 no-go**（E，`17b1eaf`）：10 种策略（更硬 AL refit、随机重初始化、2%/10% jitter、
  block-optimal、joint BCD、随机重分组 ×3、co-occurrence partition、局部交换 k=1..40、
  greedy residual fill、eigen-leaf pool）全部不如当前 (8,143,44)/λeff=46.9074。
  结构原因：`A = P M Pᵀ`、M 按组块对角且每块 rank≤44；8 组是 1144 个方向的**划分**，
  换组不改变 words/T/Q；当前 8×143×44（352 个 rank-1 项，每项在 143 维子空间）
  是绑定约束。理想 rank-352 的 M* 97% 块对角，但块对角部分单独 1,529 mHa、
  每块 rank 143——误差是 ‖T‖²≈148 对 4e-4 残差的抵消，极敏感。
  当前结构的误差地板 **19.808 mHa**（Λ≤1000）；换 3w 到 23.5。
  结论：**低于 292M 必须换 shape/行数/字表，而不是换组**——这直接支持 R=7 线。
- **signed-gauge 约束**：用 `dfthc_refit/build.py --qrom tensor` 直接重建**当前
  submission.npz**（Maoxin v22 的 `angle_words`）也报 `words must be in the signed gauge`。
  即 Maoxin 4,089 loader 的字表不是 `dfthc_refit` 的 signed-gauge 量化产物；
  任何 coded2/no-coded 对照必须走 `quantize.py`→`refine.py` 重新产字（I 正在做）。

## 2026-11-12 深夜（第十一轮）：化学 R×C 形状杠杆

- **核心洞察**：DF-THC 的 rank-1 项数是 **R×C**，不是 R 或 C 单独。当前
  (8,143,44)=352 项；rows=76+R·B=1,220，loader T 8,178。
- 保持 `R×C≈352–400`、降 R 增 C，则 rows 大降、heuristic T 几乎不变、Q 仍 427：
  | shape | RC | rows | T_total | cost@46.9 | @48 |
  |---|---:|---:|---:|---:|---:|
  | 8,143,44（当前） | 352 | 1220 | 14840 | 297.2M | 304.2M |
  | 7,143,50 | 350 | 1077 | 13862 | 277.7M | 284.1M |
  | 6,143,59 | 354 | 934 | 12943 | 259.2M | 265.3M |
  | 6,143,64 | 384 | 934 | 13237 | 265.1M | 271.3M |
  | 5,143,71 | 355 | 791 | 11994 | 240.2M | 245.8M |
  | 5,143,75 | 375 | 791 | 12191 | 244.2M | 249.9M |
- **公开表的 λeff 校准**：R=8/C=44→46.907；R=9/C=39→47.017；R=10/C=46→47.494；
  R=4/C=120→48.118（RC=480，仍过 20 mHa 门）。即小 R + 大 C 的 λeff 升幅约
  1–2.5%，远小于 rows/loader 的 12–35% 降幅；即使按 λeff 48–50 投影，
  R=6/C=59 仍 265–277M（−7~−11%），R=5/C=71 仍 246–256M（−14~−17%）。
- 公开 manifest 只有 R=4/8/9/10，**R=5/6/7 + 大 C 从未被扫过**；这是 E 的
  “必须换 shape/行数/字表”判决所指的方向。
- 已立项：K（R=5/6/7 × C 扫描 + signed-gauge 量化 + 官方全量）与 G（R=7/C=50-52）。

## 2026-11-12 深夜（第十二轮）：DQI external 共享 no-go

- 逐门 + 12,800 组随机值证明：c≠0 时 `P_L = c·P_N ⊕ (h·D)`，差项 `h·D` 是新的
  12×24 乘积（两个 mul_xor0 = 84 T），不是已有中间量；c=0 时 `P_L = h·D`，
  `P_N` 的另一半是 `(a⊕ct·h)·D`，同样是新乘积。
- 切片实测：c≠0 每步 **198 T（99+99）**、c=0 **183 T（84+99）**、first 步 0 T；
  共享补丁确实到 183 T，但需 **+24 qubit 暂存**（Q 889→913，成本 ×1.0547）。
- 可寻址节省 207×15×2 = **6,210 T（1.36%）**，实施后 v21 static 450,246
  （eae 401,313，仍高 12.2%）；净成本 **+4.1%**（T −1.36% 抵不过 Q²）。
- eae 的 186/178 块实测不是 v21 链步（乘数 12-bit E62 vs 24-bit E60|E61、
  y 集合不同），属 direct/gap-chart + jet 族；硬套同类关系上限仅 5,880 T（1.47%），
  同样 Q² 净亏。**判决：no-go，无候选。**

## 2026-11-12 深夜（第十三轮）：R×C 的期望与组合

- 公开 (R,C) 校准：R8/C44 λeff=46.907、R8/C45=46.875、R9/C39=47.017、
  R4/C120=48.118、R8/C60=48.256、R10/C46=47.494。λeff 随 R 下降只温和上升；
  项数 RC 越多误差门越安全（R4/C120 的 480 项仍过 19.9 mHa）。
- 最优风险调整点：
  - **R=6/C=64（384 项，rows 934）**：T_total 13,237，投影 265.1M@46.9 /
    271.3M@48 / 282.6M@50（−10.8%/−8.7%/−4.9%）。
  - **R=5/C=75（375 项，rows 791）**：T_total 12,191，投影 244.2M / 249.9M /
    260.3M（−17.8%/−15.9%/−12.4%）。
  - R=7/C=55（385 项，rows 1,077）：284.5M / 291.2M / 303.3M。
- 叠加 coded bit 0（每条电路 ~25 T，15 电路两遍 ~750 T）后，R=6/C=64 的
  T 可到 ~12,500（−16% vs 当前 14,840），R=5/C=75 ~11,450（−23%）；
  即使 λeff 48–50，成本 250–270M（−9~−16%）。
- 已在 K/G 的 brief 中加入 coded/coded2 组合；先 R=6/C=64（safe），
  再 R=5/C=75（aggressive），最后 R=7/C=55。

## 2026-11-12 深夜（第十四轮）：merge 与 B-truncation 的区别

- `structure.py::merge(p,k,C)` 是**精确**合并：R→R/k，但 B→k·B0、C→max(C,k·C0)，
  所有项保留；rows=76+R·B **不变**（8→4 时 B=286，rows 仍 1,220）。
  因此 merge 本身**不产生** R×C 的 T 节省，只能做高质量 seed。
- R×C 的 rows 降低（B 固定 143、R=5/6/7）必须**同时截断 B**（或从头训练小 R/B）；
  误差来自 basis 截断。公开 R=4/B=120/C=120（R·B=480）过 19.9 mHa，
  R=5/B=143/C=75（R·B=715）在两者之间，R=6/B=143/C=64（R·B=858）更稳；
  当前 R·B=1,144。
- 建议路径（已发给 K）：`merge(k=2,C=64/75)` 得 4×286×C 精确 seed → 按 U/W 重要性把 B
  截回 143 → fastfit/refine 短训练 → e1/e2；若 4×143 太小，试 5×143/6×143。

## 2026-11-12 深夜（第十五轮）：B 截断的质量损失

- 用当前 (8,143,44) 的 U/W 算 basis importance
  `sum_c |W[r,b,c]|·||U[r,b]||²`：8 组 mass [56.7,53.1,61.2,48.9,46.4,45.7,46.0,53.3]。
- merge 两组后保留 top-143/286 捕获质量：最好 (2,6)=**78.4%**，greedy 4 配对均值
  **75.4%**，最差 72.5%。即“精确 merge + 截 B 回 143”丢掉 ~22–28% importance，
  seed 误差起点很高，短 refit 很可能救不回；这条路线降级为对照。
- R×C 的正路是**从零/结构训练新 basis**（(6,143,64)/(5,143,75)），而不是截断 8 组。
  公开 R=4/B=120/C=120（R·B=480）能过 19.9 mHa，证明小 basis 可行；关键是新 basis
  的选择/训练。若 (6,143,64) 超门，试 (6,143,72)/(5,143,80)（更多 C，rows 不变）。

## 2026-11-12 深夜（第十六轮）：R×C 的 PCA seed 与公开表 seed

- 硬截断 top-143 只保留 75–78% mass；更好的 seed 是**加权 PCA 合并**：
  把两组 U 堆成 286×76、按 `sum_c |W|` 加权做 top-143 主子空间，投影 W/H2_I，
  得到 (4,143,C) seed 再 refit。保留的是加权二阶矩主子空间，应显著高于硬截断。
- 另两个 seed：公开 `factorizations/` 的 **R=4/B=120/C=120**（λeff 48.118、过门）
  和 **R=8/B=143/C=45**（λeff 46.875，当前形状邻居）。
- 已发给 K；若 PCA seed 仍超门，再退回从零训练。

## 2026-11-12 深夜（第十七轮）：R×C 投影的 B 修正

- 下载公开表后发现 **R=4 的 B=255，不是 120**：
  `729cd14c088f.npz` 是 U (4,255,76)/W (4,255,120)/H2_I (4,120)、rows=1,096、
  T=20,270、λeff=48.118、cost 418M；`9706e2c7ecff.npz` 是 (8,143,45)、
  rows=1,220、T=15,181、λeff=46.875。两文件在 `artifacts/20261112_rc_seeds/`。
- 这说明“小 R”在公开件里是靠**更大的 B**撑住误差的；之前按 B=143 的 R×C 投影
  （rows 791–934、−12~−35%）过于乐观。真实权衡是 **(R,B,C)**：
  rows=76+R·B，heuristic T 也随 B/C 变；若 (6,143,64) 需要 B≈200–255 才过门，
  rows=1,276 反而比当前高，T 节省消失。
- 已让 K 先测 e1/e2 vs B 的曲线（B=143/180/200/255），只有 e1/e2≤19.9 且
  cost<292M 才继续；若“小 R 必须大 B”使 rows≥1,220，直接 no-go。

## 2026-11-12 深夜（第十八轮）：化学 J 批量 no-go

- 精确 J 表（`tensorqrom8`，lowbits=4，8-bit，6 trials；官方 `resource_costs`）：
  J=1 485.3M / J=2 398.3M / J=3 358.2M / J=4 349.6M / **J=5 339.4M**（当前构造，
  静态 CCX 数 == 验证器执行数）。五族都逐 word 等于现件 `angle_words`；J=5 另做
  官方全量 78,080 shots PASS。
- 为什么 J 救不回来：`angles_temporary ≤ 128−11−8J < 303`，故 `Q_total=387+8J`
  严格线性（每步 +8Q，+1.87%）；T 每步只省 `75·cache/J²`（cache≈80，J=5 时 −240 T
  ≈ −1.6% of T_total）；两边相抵的最优点在 J≈6.1–6.6，但 J=6 在 lowbits=4 撞
  128-qubit cap（11+48+69+4=132）。
- 解析上限：把 Maoxin v22 的最佳单电路密度（4,089 T/pass）搬到 J，最优 J=7 →
  **−1.153%（294.13M）**；到 −2% 需 `T_angles` 再降 1.62%，属于换构造器，不是 J。
- 两个阻塞发现：当前字表不在 signed gauge（仅 79.06% 满足 bit7==bit6），
  `w→((w+64)%128)-64` 的 gauge 化不保度量（error_1 0.02→14.299 Ha）；
  必须改构造器输出全部 8 bit（已新增 `tensorqrom8.py`）。
- Maoxin v22 4,089 loader：同表同 words、官方全量两个 salt 都 PASS
  297,237,077.47（−0.108%）——即已提交的 `58271862`（25.40482）。

## 2026-11-12 深夜（第十九轮）：DQI 新解码器族 no-go（DQI 全关闭）

- **目标算术下界**：要 static T≤340k，需 convert+unconvert ≤61,884 T（该块 −49.8%），
  即**每方向 737 个 42-T 乘**。但扩展 Euclid（degree-17、两个 Bezout cofactor、
  正反两方向）的算术下界是 **920 乘/方向 = 77,280 T**；77,280 > 61,884。
- **当前 eae 已在下界附近**：convert 实测 ≈1,148 个 42-T 乘 = EEA 核心 ≈939–955
  + setup/reduce 68 + Hankel ≈141；EEA 核心只比经典 extended Euclid 的 920 高 2–4%。
- **half-gcd 更差**：n=17 时 1,027 乘（比 920 高 12%），最优变体
  **407.4k–408.7k static、Q≥900**（textbook matmat 子块实测 Q=1,296、T=15,120），
  比 eae 差 1.5–1.9%。理论最优 extended EEA（920、其余原样）也只到
  **398.4k–399.7k（−0.4~−0.7%）**，远高于 340k。
- **替代族**：BM 7,560 乘/方向（论文 locator ~140k T、整颗 4.4e5 T/1,837Q）；
  Berlekamp trace 155k–1.85M T（scan 只有 44,275）；Welch–Berlekamp 114k 乘；
  子积树 590k 乘；chirp-z 98k 乘；Paterson–Stockmeyer 48k 乘。全部 no-go。
- **口径更正**：`ABANDONED.md` 的 “decoder2: ≥190k vs extract 59k” 不是 full
  decoder/half-gcd 下界；它是朴素时域 BM/Chien/syndrome 的乘法次数按 1 CCX/乘
  计价、对照 extract 单子阶段 paid。按实测 42 T/乘，朴素时域族是 ≥8.0M T；
  真实 scan 用系数预缩放，每点 0 乘、11 T。已在 ABANDONED 加口径更正。
- **判决：DQI 四条大线（branch/低 ancilla/降秩/external 共享/新解码器族）全部
  no-go；Q≤892 且 static T≤340k 的已知解码器族不存在。** DQI 维持 eae396ba。

## 2026-11-12 深夜（第二十轮）：loader 构造是化学所有 shape/coded 线的共同瓶颈

- J 扫描实测：本地 `tensorqrom8`（J=5、lowbits=4）在当前 1,220 行表上是
  **5,142 T/pass**；Maoxin v22 是 **4,089 T/pass**——本地构造器差 **26%**。
- 按 rows 线性外推（用 5,142 而非 4,089）：
  - R=7（rows 1,077）loader≈4,540、T_total≈16,067（**+8.3%**，比当前差）；
  - R=6（rows 934）≈3,939、T_total≈14,854（wash）；
  - R=5（rows 791）≈3,333、T_total≈13,555（−8.7%，唯一还有收益）；
  - 若 R=5 的 B 必须涨到 180/200（公开 R=4 是 B=255），T_total≈14,993/15,414（+1%/+3.9%）。
- 因此 R=7 已不是候选；R=6 只是误差诊断；R=5/B=143/C=75-80 是唯一 shape 点。
- **最大杠杆变成 loader 构造**：Maoxin 4,089 比本地 5,142 低 26%，占化学 T 的 55%；
  若能逆向并移植，loader 8,178→~6,500（−20%），化学 cost −11% → GM +3.8%。
  已立项 M（从 `.kmb` 逆向 Maoxin 的 coded/lowbits/cache/QROM 构造）。
- coded2/tree 线的绝对 T 也要与 Maoxin 4,089 比；若基座是 5,142，单靠 coded2
  （~750 T）仍差 7%。已把这条校准发给 K/G/I。

## 2026-11-12 深夜（第二十一轮）：Maoxin loader 的 op 结构差异

- 实测 `angle_k_0`：Maoxin v22 是 **Q=128、T=292、ops 19,883**；
  本地 `tensorqrom8` J=5 是 **Q=124、T=358、ops 50,996**。
- Maoxin 的 ops 少 **2.6×**、T 少 18%、Q 用满 128；T/ops 0.0147 vs 本地 0.0070
  ——Maoxin 的 CNOT 密度低得多。不是同一 tensor 分解的参数差异，更像另一种
  QROM 架构（bucket-brigade / 地址缓存 + coded lookup），而不是逐 monomial 分解。
- 已让 M 逐门对齐地址/数据/ancilla 分工，并用 16-address/5-word 原型对比密度；
  若无法归约成可解释构造，写 no-go 并保留“ops 密度 0.0147 vs 0.0070”的归因。
- 这决定化学所有 shape/coded 线能否落地：loader 占化学 T 的 55%，Maoxin 比本地低 26%。

## 2026-11-12 深夜（第二十二轮）：Maoxin loader 的 pair-cache 构造

- Maoxin `angle_k_0.kmb` 的门序列：5 个 `CX`（q17/q18、q25/q26…，数据字成对复制）
  → `R q51; CCX q4 q5 q51`、`R q52; CCX q4 q6 q52`、`CCX q5 q6 q53` …
  即对 **q4..q10 这 7 个低地址位做两两乘积缓存**（q51..q68），再由 pair 组合高阶项。
- 这不是本地 `tensorqrom8` 的 lowbits=4/5 逐 monomial 分解，而是
  **7-bit 地址块 + pair-product cache + 复用** 的张量 QROM；CNOT 密度低
  （ops 19,883 vs 50,996、T/ops 0.0147 vs 0.0070）也支持“pair 缓存复用”。
- 已让 M 写 7-bit block + pair cache 的最小原型，测 T/ops 与本地 lowbits=4/5 对比；
  若密度接近 Maoxin，再扩到 1,220 行与 R=5/R=6 新表。
- 这仍是化学最大的单点杠杆：loader 占 T 的 55%，Maoxin 比本地低 26%。

## 2026-11-12 深夜（第二十三轮）：Maoxin 的分层 monomial cache 精确计数

- Maoxin `angle_k_0` 的 292 个 CCX 按控制/目标分类：
  - `(bit,bit,pair)` **18**：q4..q10 的两两乘积 → q51..q68；
  - `(bit,pair,mid)` **21**：pair × bit → triple（如 `(4,53)->70` = q4q5q6）；
  - `(bit,mid,other)` **21**：triple/quad × bit；
  - 其余 `(mid,other,other)` 19、`(bit,other,other)` 12、`(pair,other,other)` 12、
    `(other,pair,other)` 9、`(other,mid,other)` 9 等为数据字 XOR。
- 即 **pair→triple→quad 的分数阶 monomial cache + 数据 XOR**；pair 被高阶复用，
  所以 CCX 只有 292。本地 `tensorqrom8` 的 358 很可能是逐 monomial 独立算、
  没有 pair 复用——这正是 T 差 18% 的来源。
- 已把精确层次发给 M；若 1,220 行做到 ≤4,089 T/pass（目标 ≤3,900），
  再扩到 R=5/R=6 新表。

## 2026-11-12 深夜（第二十四轮）：loader T 随 rows 非线性，shape 线关闭

- 实测 `tensorqrom8` J=5（lowbits=4、sizes=[6]*6+[4]）在 791/934/1,220 行：
  **4,608 / 4,778 / 5,148 T/pass**。rows −35% 只省 10.5%，固定 monomial/selection
  成本占主导，**不是线性**。
- 用这个 loader 重算：R=5/C=75 T_total=16,105（**+8.5%**）、R=6/C=64=16,532（**+11.4%**）、
  R=7/C=55≈16,887（**+13.8%**）——全部比当前 14,840 差。**R×C/R=7 的 shape 线
  在本地 loader 下 no-go**；已通知 K/G 停止并写 no-go。
- Maoxin 的每电路 292 = 60 monomial（18 pair + 21 triple + 21 quad）+ 232 data XOR
  （1,220 地址）。若 data XOR 随 rows 缩放、monomial 固定，则 791 行 per-circuit
  ≈210、×15≈3,150/pass，R=5/C=75 T_total≈13,189（−11.1%）——这是 shape 线唯一的活口，
  取决于 M 能否复现 Maoxin 构造并验证 232 的缩放方式。
- 已把 fixed/variable 拆分与 R=5 目标（T_total ≤13,500、cost ≤265M）发给 M。

## 2026-11-12 深夜（第二十五轮）：Maoxin 的 7-bit block 与 R=5 目标

- Maoxin 的 q4..q10 = **7 个低地址位 = 128-address block**；1,220/128≈9.5 block。
- 60 个 monomial（18 pair + 21 triple + 21 quad）是对低 7 位 pattern 的缓存、
  **跨 block 复用**，固定 60/电路；232 个 data XOR 是每 block 数据加载
  ≈**24.4/block**。本地 lowbits=4 是 16-address block（77 个），每 block ~4.3，
  block 多导致总 data XOR ~328——固定/变量结构更差。
- 投影：791 行（R=5，6.2 block）≈6.2×24.4+60=**211/电路**、×15=**3,165 T/pass**；
  R=5/C=75 T_total≈**13,219（−10.9%）**；934 行（R=6）≈238/电路、T_total≈14,116（−4.9%）。
- 已让 M 先复现 1,220 行的 292/电路，再测 791 行是否 ≈211（≤270 才继续）；
  若成立，构建 R=5/B=143/C=75 loader + 官方全量，目标 cost ≤265M。
- 注意：R=5 的误差门仍未验证（公开 R=4 是 B=255）；M 只负责 loader 构造，
  误差由 K 的 e1/e2 诊断提供。

## 2026-11-12 深夜（第二十六轮）：R=5 + Maoxin loader 的精确投影

- 精确 heuristic（验证器 `SpinFreeData_V1`）与 Maoxin loader 投影（60 monomial + data XOR
  随 ANF 项数缩放，10-bit 为 11-bit 的 ~50%）：
  | shape | rows | nsel | heurT | loader | T_total | Q | cost@46.9 | @48 |
  |---|---:|---:|---:|---:|---:|---:|---:|---:|
  | R5/B180/C75 | 976 | 10 | 8,088 | ~2,640 | **10,728** | 428 | **215.4M** | 220.4M |
  | R5/B143/C75 | 791 | 10 | 6,889 | ~2,640 | **9,529** | 427 | **190.9M** | 195.3M |
  | R5/B200/C70 | 1,076 | 11 | 8,131 | ~4,380 | 12,511 | 428 | 251.2M | 257.0M |
  | R6/B180/C64 | 1,156 | 11 | 8,202 | ~4,380 | 12,582 | 428 | 252.6M | 258.5M |
- 若 R5/B180/C75 过 20 mHa 门且 Maoxin loader 复现：cost 215–220M（−26~−27.5%），
  GM ≈ **28.2**（当前 25.40482）。R5/B143/C75 若过门：190.9M（−35.8%），GM ≈ **29.4**，
  但 B=143 的误差风险高（公开 R=4 是 B=255）。
- 关键路径：K 的 e1/e2 诊断（R5/B180/C75 vs B143）+ M 的 Maoxin 构造复现
  （791/976 行 per-circuit 是否 ≈176/193）。两者都成立才会构建候选。

## 2026-11-12 深夜（第二十七轮）：R5/B180 的 C 梯度

- rows 976、10-bit、Maoxin loader ~2,640/pass 下，R5/B180 的 C 梯度：
  C75 **215.4M@46.9** / 220.4M@48（−27.5%）；C80 221.8/226.9；C85 228.2/233.6；
  C90 **236.0/241.5**（−20.6%）；C100 248.9/254.7（−16.3%）。
- rank-1 项数从 375（C75）到 500（C100），比公开 R=4/C=120 的 480 还多；
  误差门有很宽的梯度：C75 过门就用 215M；否则 C80/90/100 仍 −16~−25%。
- 已让 K 按 C75→80→90→100 报 e1/e2；一旦过门就停，报最终 λeff/shape。
  M 继续 Maoxin loader 复现（目标 976 行 per-circuit ≈193）。

## 2026-11-12 深夜（第二十八轮）：976 行 ANF 平坦，loader ~2,635/pass

- 976 行（R5/B180，10-bit）的 ANF 项数 **19,046.7/电路**，与 791 行的 19,085 几乎相同
  ——10-bit 的 ANF 是**平坦**的（不是按 rows 线性）。按 Maoxin 的 1,220 行 232 data XOR
  缩放：data XOR ≈**115.6/电路**，+60 monomial = **175.6/电路**，loader ≈**2,635 T/pass**。
- 修正后的精确投影：
  - R5/B180/C75：T_total = 8,088+2,635 = **10,723**，cost **215.3M@46.9（−27.6%）** /
    220.3M@48（−25.9%）。
  - R5/B143/C75（rows 791）：T=6,889+2,635=**9,524**，cost **190.8M（−35.8%）**。
- 结论不变：R=5 的收益取决于 K 的误差门与 M 的 loader 复现；两者都成立时 GM≈28.2（C75）。

## 2026-11-12 深夜（第二十九轮）：Maoxin data-XOR 的门级模式

- 对 `angle_k_0` 的 292 个 CCX 按 qubit 类别（H=q0–q3、L=q4–q10、D=q11–q49、
  A=q51–q127）分类：
  `(A,A,D)` 142、`(H,A,D)` 51、`(L,A,A)` 50、`(L,L,A)` 19、`(A,L,D)` 8、
  `(H,H,A)` 6、`(L,A,D)` 6、`(A,H,D)` 5、`(H,A,A)` 4、`(A,H,A)` 1。
  含至少一个高地址位（q0–q3）控制的 CCX 只有 **67** 个。
- 即 data XOR 不是一个简单的“16 high patterns × 低 monomial”结构；(L,L,A) 19 + (L,A,A) 50
  是低 7 位的 monomial cache，(A,A,D) 142 + (H,A,D) 51 是 data 加载。10-bit 的
  **ANF 项数减半**（19,047/38,214=0.498）是经验比例，不是高位 pattern 的直接减半。
- M 的 R=5 投影应使用 **ANF 比例**（data XOR ≈116、+60 monomial ≈176/电路、
  loader ≈2,635/pass），不要假设 high-bit 分组；原型要按实际 CCX 模式验证。

## 2026-11-12 深夜（第三十轮）：R=4/B 梯度与 10-bit 阈值

- 公开 R=4/B=255/C=120 表只截 B（C 不变）是**最容易构造**的路径；seed 直接来自
  `artifacts/20261112_rc_seeds/729cd14c088f.npz`。
- 精确投影：
  | shape | rows | nsel | heurT | loader | T_total | cost@46.9 | @48 |
  |---|---:|---:|---:|---:|---:|---:|---:|
  | R4/B220/C120 | 956 | 10 | 10,484 | 2,635 | 13,119 | **264.0M** | 270.1M |
  | R4/B200/C120 | 876 | 10 | 9,964 | 2,635 | 12,599 | **253.5M** | 259.4M |
  | R4/B180/C120 | 796 | 10 | 9,444 | 2,635 | 12,079 | **243.1M** | 248.7M |
  | R4/B240/C120 | 1,036 | 11 | 11,483 | 4,090 | 15,573 | 313.4M | 320.7M |
  | R4/B180/C100 | 796 | 10 | 8,407 | 2,635 | 11,042 | **221.2M** | 226.3M |
  | R4/B180/C90 | 796 | 10 | 7,894 | 2,635 | 10,529 | **210.9M** | 215.8M |
- **硬阈值**：B≤220（rows≤956）是 10-bit、Maoxin loader 2,635；B=240（rows 1,036）
  跳 11-bit、loader 4,090，成本 +49M。B=220 是 10-bit 的最大点。
- 已让 K 按 B220/C120（最安全，C 与公开相同）→ B200 → B180 → C100/90 报误差；
  一旦过门，M 接手 loader。R=5/B180 作为并行备选。

## 2026-11-12 深夜（第三十一轮）：B 截断质量与 R=4 的唯一 10-bit 点

- 公开 R=4/B=255 的 basis importance（`sum_c |W|·||U||²`）top-B 捕获质量：
  B180 **83.9%**、B200 **88.9%**、B220 **93.5%**、B240 **97.6%**。
- 结合 10-bit 阈值：**B=220（93.5%、rows 956、10-bit、264.0M、−11.2%）是唯一
  “10-bit + 较高 mass”的点**；B=240（97.6%）跨 11-bit、loader 4,090、313M，
  比当前 297M 还差；B=200/180 的 mass 只有 88.9%/83.9%，误差风险更高。
- R=4 路径优先级：B220/C120（最可能过门）→ C100（221.2M，−25.6%）→ C90
  （210.9M，−29.1%，C 减少会收紧误差）；若 B220/C120 超门，R=4 基本关闭，
  转 R=5/B180/C100（500 项、248.9M，−16.3%）作最后备选。
- 已让 K 把 B220/C120 的 e1/e2 作为最高优先级；M 的 Maoxin loader 在等这个门。

## 2026-11-12 深夜（第三十二轮）：R=4 截断、loader、换树与 R=7 全部关闭

- **R=4 B 截断（决定性 no-go）**：同一公开表 `729cd14c088f`，10-bit，官方
  `evaluate_dfthc_angle_words`。B=255 对照 **19.94 mHa PASS**；B=220 **498.75 mHa**、
  B=200 **690.79**、B=180 **913.61**，全部超 20 mHa 门 25–46 倍。`error_2` 只由
  `(U,w)` 决定，offset/列旋转救不了，故不构建电路。已用 Kaggle 挂载比赛数据 +
  `manwithacat/vqcc-apache-public-circuits` 复跑，数字逐位一致：
  内核 `ccjjllt/quantum-rc-r4-btrunc-gate`，记录
  `.worktree/dfthcsos/experiments/dfthcsos/20261112_kaggle_r4_gate/`。
- **Maoxin loader 逆向 no-go**：本地 `tensorqrom8` 在 128Q cap 内上限 **5,142 T/pass**
  （vs 公开 4,089）；791 行代理 4,601（+8.4%）。只有复现 Maoxin 的 monomial-cache
  构造才能到 3,645，但未在 128Q 内做到；R=5 用本地 loader 是负收益。
- **换树 no-go**：同一张表重建 current/heap/star/path，T/pass 5,414/5,422/5,105/5,428；
  只有 current 过误差门，成本 350.32M（+17.9%）。树间 T 差 ≤6%，生成器才是瓶颈。
- **R=7 no-go**：C=44 drop1 实测 e1 28.94 / e2 215.54 mHa，loader 4,672 T/pass，
  cost 311.94M（+4.95%）；rank-308 PSD 下界 14.48 mHa，叠加 15.1 mHa 量化墙
  理论最好 ~20.9 mHa，仍超门。
- **结论**：化学维持 `5d5007a75784`（14,840 loader、Q=427、λeff=46.907378146、
  297,237,044.95）；R=4/R=5/R=7/换树/loader 五条线全部关闭，不产生新候选、不提交。

## 2026-11-12 深夜（第三十三轮）：C 截断门、评分标定与并行研究

- **C 截断 no-go**：公开 R=4/B=255 表只截 C（SVD top-C + 255 原子重解）：
  C=115 **22.30 mHa**、C=110 **26.70**、C=105 **33.10**、C=100 **42.97**，
  控制 C=120 为 **19.94 mHa**。C=115 只差 2.3 mHa，但只省 ~4% C；单独 SVD
  不够，交给 joint U/w 优化（C=110 不过门则 no-go）。Kaggle 内核
  `ccjjllt/quantum-rc-r4-ctrunc-gate`，数字与本机逐位一致。
- **评分标定**（用 sample submission 独立跑出参考 cost）：
  - invsqrt ref **2,076,774.2337**；DQI ref **24,439,463,583,672.93**；
    chem ref **3,355,599,588.3155**。
  - 当前三件：93,555.26 / 373.53e9 / 297,237,044.95；
    Score=(∏ ref/cost)^(1/3)=**25.40494**，与 public 25.40482 一致。
  - 到 27.0 需单任务 −16.7%（chem ≤247.6M / invsqrt ≤77,934 / DQI ≤311.2e9）；
    到 28.0 需 −25.3%；到榜首 29.76123 需 −37.8%
    （chem ≤184.9M / invsqrt ≤58,192 / DQI ≤232.3e9）。
- **公开 frontier**（RezOps 2026-11-11）：invsqrt 93,863.36、DQI 3.7393e11、
  chem 2.97559e8；我们三件都略优（0.1–0.3%）。公开组合已到顶，榜首差距只能靠
  私有算法突破。
- **并行研究**（5 个 subagent）：公开前沿重扫、invsqrt 新家族、DQI BM/新解码器、
  chem C 截断 joint 优化、chem loader QROM 优化。重点线索：Anthropic 的 BM DQI
  12× 构造（arXiv:2610.22367）与 Xanadu QROM halving（arXiv:2605.20334 /
  2610.02321）。
- 本机所有残留 Python 子进程已清理；后续重计算走 Kaggle。化学仍维持
  `5d5007a75784`，不产生新候选、不提交。

## 2026-11-12 深夜（第三十四轮）：DQI/ invsqrt 封顶，loader 只剩 full-support 逃逸口

- **DQI BM 线索关闭（硬数字）**：官方 EEA 参考实测 **5,725,461 T / 1,893 Q**，复算 cost
  2.4441e13，与官方 ref 比值 1.00006。当前 `eae396ba` 不是 BM，而是 short-Hankel 族：
  密钥方程 60,663 T（两方向 123,197），比 BM locator 便宜 7.87×（1,148 乘 vs BM
  ≈11,360 乘）。把论文 BM 搬到 892Q：477,122 T → cost 4.52e11（**+21.1%**）；
  BM 自报 1,837Q → +414%。正规基全枚举：GF(2^12) 144 vs 现役 42（3.43×）。
  −20% 需 rank ≤30（Winograd 下界 23）或密钥方程 ≤650 乘/方向；本时间盒无候选。
- **invsqrt 封顶**：62Q 无宽度余量（x 比特已被回收，61Q 打平预算 +24.7 C）；C 分解
  prefix 237 / mid 373 / tail 477，C 最多 −5.4%，现实 −2~−3%；要 −37.8% 需再少
  300–511 次 AND/erase，无单点 ≥137 C。20% 新家族不存在。
- **loader gate-level**：15 个 Maoxin 电路逐门精确计数，重复 monomial/product、XOR
  抵消、控制位常数化、相邻 CX 抵消全部 **0**；2,956 个 product 函数 GF(2) 线性无关。
  QROM halving/dense 在 N=1,220, b=40 下反向（N≪b²λ²），Q≤128 内 T 1,048–1,376/circuit，
  比 Maoxin 268 差 3.9–5.1×；Maoxin 是张量 loader（0.22 T/地址），已低于 flat QROM
  1 T/地址下界。
- **loader 真实上限**：4×4 rank-4 分解 + 70 cache → 230/circuit = **3,525 T/pass
  （−15.6%）→ R4/C120 ≈296.9M、R5/C75 ≈275.0M**；loader 单线封顶 ≈270–297M，
  到不了 27.0（247.6M）。**唯一逃逸口**：full low support（16 monomial，1 product/bit）
  → 121/circuit = **1,815 T/pass → chem ≈206M、GM≈28.8**；需解 16 个非线性方程
  `h_K = Σ_{P∪Q=K} a_P c_Q`，已派 subagent 专攻。
- **公开前沿**：400 个 kernel 标题全扫，11-12 后无 27+/28+；唯一新件 DQI
  `maoxin123/qcc-dqi-392k-toffoli-decoder` 892Q、mean 392,016，官方 102,400 shots
  PASS 但 1 value error，cost 373.276e9，仅 **+0.023% GM**，不值得构建。公开 plateau
  仍 25.40–25.41。
- **新并行线**：full-support loader（chem 206M 目标）与 DQI Q=840 重算（−11.3% 目标）。
  C 截断 joint 已停止，低优先级。

## 2026-11-12 深夜（第三十五轮）：C 截断 joint 过误差门，但 R=4 成本 no-go

- 联合 U+w（连续原子，L-BFGS 400 步）在 R=4/B=255 表上：
  **C=110 → e2 18.89 mHa**（过门；SVD-only 是 26.70，w-only 22.55），
  **C=118 → 19.80**（过门且优于 C=120 种子 19.94）。秩不是约束：k=440 自由 PSD
  下界 2.59 mHa；19.94 中约 1.66 mHa 是 4×255 结构税，联合优化回收 ~3.7 mHa。
- **但 R=4/B=255/C=120 的成本基线本身是 336.9M**（rows=1,096 → 11-bit loader、
  Q=429、heurT 8,562、T_total 16,742），比当前 chem 297.237M **高 13.4%**；
  C=110 只省 371 T（2.2%）→ 329.4M，C=105 → 325.4M。**C 截断无成本价值**。
- 当前 chem 不是 R=4，而是 **R=8/B=143/C=44**（rows=1,220、11-bit loader
  4,089/pass、heurT 6,662、T_total=2×4,089+6,662=14,840、Q=427、λeff=46.907）。
  成本杠杆是 **rows / loader**，不是 C。
- 记录：`.worktree/dfthcsos/experiments/dfthcsos/20261112_ctrunc_joint/`（未推 Kaggle）。

## 2026-11-12 深夜（第三十六轮）：full-support loader 归零，chem 天花板 ≈280M

- full-support（型 = u(r)+v(q)，一个 product 覆盖 16 列）被 **rank 否证**：
  16×128 ANF 张量的 interior 每 product 最多 rank 2；实测 k=0 的 40 个 bit 中
  interior rank **15**（k=4 有 32 个 bit=15），所以一般 bit **≥8 product/bit**，
  不是 1。1,905 方程对 ~284 未知数，1 product/bit 无解。
- 精确恒等式验证的构造：k=4 346 T、k=0 371 T；15 电路 **6,345 T/pass（+55%）**，
  cost 387.6M；理论下界 5,720（+40%），302.3M。全部劣于现状，归零。
- loader 软计数界：48,800 bit 随机表，一个 CCX 最多 2·D bit（D≤128），每 circuit
  ≥243 CCX → **3,645 T/pass → 279.5M（−6%）**。Maoxin 平均 272.6 CCX，只剩 ~10%
  余量；2,850（247.6M）需 190 CCX，不可达。
- **结论**：27.0 不再记在 loader 账上；loader 现实落点 ≈3,600–3,700 T/pass
  ≈278–282M（GM≈26.5），必须由 shape/C 截断或 DQI 承担。

## 2026-11-12 深夜（第三十七轮）：DQI 近似解码的失败预算

- 用 verifier 的 Clopper–Pearson（N=102,400、log2_delta=−128）实测：
  k 失败 → ε+ / R：0 → 8.66e-4 / **1.1913**；1 → 1.1967；3 → 1.2056；
  10 → **1.2290**；20 → **1.2548**；50 → 1.3134；100 → 1.3887。
- 所以允许 10–20 次失败（R +3~5%）换 T −20%；按 R≈1.25 重算目标：
  27.0 → T≤311k；28.0 → T≤278k；29.76 → T≤232k。
- 当前 DQI 乘法 288,863 T（72%）；rank-36 近似乘法器省 ~41k（10%），
  rank-30 省 ~83k（21%），rank-24 省 ~124k（31%）。这是 DQI 唯一可能到
  27+ 的路径，已派 subagent 专攻；Q=840 重算作为并行 −11.3% 路径。

## 2026-11-12 深夜（第三十八轮）：DQI Q=840 no-go；loader 试输出基变换

- **Q=840 no-go**：对 eae `eae396ba` 的 835 MB `.kmx` 做 6 遍全量扫描：
  52 个 ancilla 是**活工作寄存器**，不是存储；282,744 / 401,313 paid 门（**70.5%**）
  有操作数落在 q840..q891，134,459 次作控制位、148,285 次作目标位；extract 的
  58,742 T 中 97.4% 就在这 52 条线上。Q=840 的 T 预算只多 **51,224 static T**；
  最便宜 24-bit 乘法读 99 T × 1,358 次 ≈ 134k T，超支 2.6×；整段 extract 重算
  1 次也 +1.66%。Q=888（去 4 flags）仅 −0.89%，flag 重算 ≫ 3,623 T 预算。
- **loader 新逃逸口**：CX 在评分里免费，只有 CCX/AND 计 T。当前直接算 40 个 word
  bit；若先算 40 个 GF(2) **线性组合**（输出基变换），再用 CX 矩阵恢复原 word，
  CX 免费、CCX 可能大降。当前 272.6 CCX/circuit，软下界 243；到 243 → 279.5M
  （GM 26.5），到 200 → ~260M（GM 27.4）。已派 subagent 做多输出 ESOP/基变换搜索。

## 2026-11-12 深夜（第三十九轮）：DQI 近似解码也被数学封死

- GF(2^12) 乘法实际调用 **≈5,910 次**（tag 普查欠计数；99-T 的 GF(2^24) 块 390 个）。
  丢 1 项省 1 T×5,910：rank 36 → −8.84%；rank 30 → −17.67%（刚好 27.05）；
  rank 23 下界 → −27.98%，但无构造。
- **近似不可行**：丢任意非空双线性项集，偏差 `D(x,y)=Σ v_i a_i(x)a_i(y)` 是非零
  双线性型，均匀操作数上 `P(D≠0) ≥ 1/4`（类不变量）。实测丢 1 项 = 0.250000，
  rank 36 = 0.815–0.822，rank 30 = 0.966–0.968；每 shot 5,910 次调用 ⇒ ε=1。
  verifier 在 ε+≥1/16 直接 AssertionError，连分数都没有。
- EEA 轮数截断：真实 syndrome 需 45–69 轮（集中 59–67），砍 2 轮即 2.33% 失败
  （R=3.2，成本 ×2.7）；要 p≤1.3e-3 需 D=69，一轮都砍不了。
- Chien scan 已是 11 T/点 = n−1 下界；跳过低重量方向反了（k=28–35 占 93.6%）。
- **唯一残留**：精确 rank-30 乘法构造（−17.67%，GM 27.05）；下界 23，tower 42，
  是研究级数学问题，无本 session 构造。DQI 线到此封死。

## 2026-11-12 深夜（第四十轮）：loader 输出基变换是 no-op，剩 product 集重搜

- 定理：Maoxin 族成本 `T=|cache|+|products|`，正确性只依赖
  `span(M∪P∪1∪地址位) ⊇ V`；可逆输出基 B 不改变 V，product 扇出是 CX（免费），
  所以 **B 是 no-op**。实测 k=4：identity 268 CCX；随机满秩 B 400；单位下三角 B 395；
  三者 `words_equal=True`（真实 kickmix，1,220 地址）。
- 余量 268→243 全在 **product 集重搜**（193→约 168）；已派 subagent 做
  GF(2) 集合覆盖/ILP。到 168 → 3,645 T/pass → **279.5M（GM 26.5）**；
  若 span 条件允许更小集合，收益会更大，但需真实 stateful 验证。

## 2026-11-13 凌晨（第四十一轮）：3881 loader 撤回；官方 verifier 是唯一判据

- 上一轮 `loader_productset` 的 `4089→3881`、`GM≈25.9` **全部撤回**。官方
  `evaluate_circuits(shots_per_address=1)` 在 slim 15 电路上直接
  `InvalidCircuits: ANGLE_1: uncorrected phase (measurement kickback)`。
- 根因：loader 是 `|a>|z> → |a>|z⊕delta[a]>`，**z 任意**；slim 的“恒零”门
  （5 个 flag cache `w?.7∧sel?`、428 个 `w0.6→w0.7`）只在 z=0 为零，product 的
  pivot 也带 z。官方在跑 `ANGLE_k` 前把上一 batch 写进 word 寄存器，所以 z=0
  检查不是合法判据。只保留 z-safe 替换后 **saved = 0**，15 个电路与原电路逐字节相同。
- 官方对照（同 `shots_per_address=1`）：原 15 电路 + 原 `submission.npz`
  **PASS**，toffoli 14,840、qubits 427、λeff 46.907378、score **297,237,044.95**。
  与当前候选一致。
- 结论：loader 仍是 **4,089 T/pass、T_total 14,840、Q 427、297.237M**；
  product-set 的 2799 只是 z=0 松弛，不是构造。loader 线彻底封死。

## 2026-11-13 凌晨（第四十二轮）：Kaggle MCP 复核公开前沿——我们三件就是公开最佳

- 用 Kaggle MCP 重查（notebooks / datasets / leaderboard / manifest / assembly_best）：
  - 公开最高 notebook 是 **25.40767–25.40768**（Areeb Ali / Knight Fork 的
    retained-product DQI，以及 Kirill 对 Alex Chilton V142 的审计）。它只在我们的
    三件上把 DQI 换成 `8eccde65`（= `eae396ba` + 133 retained products），
    invsqrt/chem 不变；零失败 cost 373,408,958,733，仅比 eae 少 0.0337%，
    GM +0.0029。公开 split 抽到 0 失败才是 25.40767；本地空 salt 为 25.3689，
    1 次失败的 −0.039 远大于该收益。**没有 26+/27+/28+ 公开件。**
  - `manwithacat/vqcc-apache-public-circuits` v122 的 `manifest.csv`（459 条）：
    invsqrt 最佳 `9c708f7b` **93,555.2627**、DQI 最佳 expected `eae396ba`
    **373,856,548,625**（零失败 373,534,939,341）、chem 最佳 `5d5007a75784`
    **297,237,044.9509761**；三者 SHA 与我们当前件**逐字节一致**。
    `parts/assembly_best.json` 也把最佳公开化学 assembly 标为 `5d5007a75784`，
    `verified_status=PASS`、`verified_cost=297237044.9509761`。
  - 公开 frontier GM（dataset 2026-11-12 07:12 快照）为 **25.39754**（约第 249 名）；
    我们 public **25.40482** 已高于它；加上 retained DQI 也只是 25.40768。
  - 排行榜已到 **Entangled Team 29.90871**、Schrödinger 29.76123、yicheng 29.02209、
    taiseiu 28.68861、Some Joint 28.65116；这些队伍没有公开电路/生成器。
- 结论：公开可复现空间已到顶，三件均为公开最佳；追 27+ 只能靠私有级 DQI/化学
  突破。当前 25.40482 不因公开件而改变，不提交新包。

## 2026-11-13 凌晨（第四十三轮）：invsqrt prefix 目标被误算；化学 C 缩减被 error_1 卡死

- **prefix 成本归因（实测 op 区间）**：`9c708f7b` 的 0–8545 不是单一 normaliser。
  - 0–649：**19 CCX + 44 CSWAP = 63 T**（真正的 leading-zero + 44-CSWAP normaliser）；
  - 650–7030：**167 CCX**，纯经典算术块（无 CSWAP/HMR）；
  - 7031–8545：7 CCX。
  上一轮“193 CCX / 22 bit = 8.8 AND/bit，naive 下界 5/bit ≈110，省 83”把
  167 个算术 CCX 误算进 normaliser；真正 normaliser 只有 63 T，已经低于 110。
- **算术块非线性**：把 650–7030 抽成 62Q 独立经典子电路（6,381 ops，无 HMR），
  随机 62-bit 输入上 2–6 阶布尔导数全部非零（16/16 每阶），不是 affine/quadratic，
  不能靠 `CCX→CX`/低阶 ESOP 消掉；167 T 已比论文 reference 的 Horner 1,071、
  squaring 442、mantissa multiply 1,043、final NR multiply 867 低 6–20 倍。
- **化学 C 缩减**：当前 `5d5007a75784` 的 `error_1=19.99998 mHa` 恰好在 20 门槛；
  在固定 angle words/15 电路的前提下，任何 w 改动都会破坏 one-body 矩阵，
  把 C 从 44 降到 36 的固定 U 实验（保留一列 H1、剩余列拟合 error_2）得到
  M_fixed 范数 1,441 vs 目标 T 范数 12.18，error_2 不可行。**C 缩减必须重编码
  one-body rows（即重建电路），不是只改 submission.npz。**
- 记录：`.worktree/invsqrt/experiments/invsqrt/20261113_prefix_audit/`
  （README、audit.py、audit.json，本地 commit）。
- 并行：prefix 算术块全重写 subagent、DQI 392k 组合 subagent 仍在跑；未提交、
  未 push、当前分数不变 25.40482。

## 2026-11-13 凌晨（第四十四轮）：DQI 392k 是逐 draw 严格支配，但只 +0.0447 GM

- `maoxin123/qcc-dqi-392k-toffoli-decoder`：SHA `4c81b726…01e5d9`，892Q，
  mean T 392,016.12（eae 394,089.46，**−0.5261%**）。
- 官方 verifier 16 个 salt × 102,400 shots 全部 PASS：合计 **7 errors / 1,638,400
  shots**（4 value + 3 phase），p=4.27e-6/shot，λ=0.4375/draw，P(0 失败)=0.646；
  直方图 {0:10,1:5,2:1} 与 Poisson(0.4375) 吻合。
- **paired seed 8/8 错误模式与 eae 完全一致**（含 seed 4 phase、seed 29 双 phase），
  cost 比 **0.9947389 ± 3.9e-7**；失败由共享解码器核心触发，与编译 T 结构无关。
  所以 392k 对**每一个 draw** 都便宜 0.5261%，是零风险严格支配。
- 组合 GM：zero-failure **25.44954**；expected **25.4329**（eae expected 25.3882；
  我们 public 25.40482 是 eae 的 0-failure draw）。
- retention：392k 的 52 个 ancilla 窗口全被占用；现有 ancilla 仅省 2 T；
  +1 host 省 138 T 但 Q² 涨 0.224%（需 880 T 打平），+2 省 262 T 仍亏。
  **392k + retention = 392k**，关闭。
- 判定：+0.0447 GM 落在 0.02–0.05「不值得单独打包」区间；但它是**免费替换**，
  若因化学/invsqrt 新件重新组包，应顺手把 eae 换成 392k，无需再评估。
- 验证范围：24 次全量 102,400-shot（16 salt + 8 paired seed），共 2,457,600 shots，
  全部 PASS；未打包、未提交、未 push。记录 `.worktree/dqi/.../20261113_392k_combo/`。

## 2026-11-13 凌晨（第四十五轮）：invsqrt prefix 正式 no-go；−83 C 目标撤回

- **拆分复核（实测）**：`9c708f7b` 的 `[0:8546)` 是 **63 + 167 + 7 = 237 T**：
  - `[0:649)`：19 CCX + 44 CSWAP = **63 T**，真正的 leading-one 检测 + 可变量移位
    （18 级 CCX AND 链 + 44 个 CSWAP，q48 复用为 scratch），**2.86 T/bit**；
  - `[650:7031)`：**167 CCX**，纯 `{X,CX,CCX,SWAP}` 置换，无 HMR/相位/条件；
  - `[7031:8546)`：**7 CCX** 收尾。
- **−83 C 撤回**：上一轮把 167 个算术 CCX 混进 normaliser 的分母；真正 normaliser 63 T
  已低于“5 AND/bit ≈ 110”的朴素下界。这条线上不存在 −83 C。
- **167 T 算术块已高度优化**：纯置换，作用在 47 个比特上；167 个 AND 全部 load-bearing
  （全定义域 3,133,452 个 x 上 fire 集合非空，最稀有者仅 1 个 x）；2 阶 ANF 已有
  **1,081 个不同单项式 / 21,904 个 (i,j,out) 关联**，电路用 167 个 AND 实现，**6.5× 复用**；
  比论文 reference 最便宜的 22-bit squaring（442 T）还便宜 2.6×。删一门在 2,800 点 ×
  2 HMR 分支上全部改变 cut 状态；0 个可删；19 对精确抵消全为 X/CX（0 T）。
- **来源归属纠正**：prefix 实际是 **`94b29cc5`（WCao24）**的逐字拷贝（4 处本地改写），
  不是 ThomasG 的 `5ec4f516`；`5ec4f516` 只在 8664+ 的 ladder 区出现。不影响成本结论。
- **新资产**：`scripts/qsim.py` 精确定点模拟器，与官方 `km.Simulator` 在全定义域
  3,133,452 个 x、三种 HMR 分支上 0 差异；可做“候选 = 基线”的全域等价证明。
- 结论：prefix 已无可行的机械/算术重写；最好仍是 237 T、C=1,508.9567、62Q、
  score 93,555.2627。未生成候选、未跑官方验证、未提交/push。

## 2026-11-13 上午（第四十六轮）：提交 DQI 392k 免费替换（ref 58290992）

- 用户批准后提交 18 件：invsqrt `9c708f7b` + DQI `392k`（`4c81b726…`）+
  chem `5d5007a75784`。ZIP SHA-256
  `818057cdb455c4653d5944e9fd82afef2a74996f454b257ffbc6e6a2b0e58fd6`，
  27,992,059 bytes，18 files。
- DQI 392k 已完成 24 次全量官方验证（16 salt + 8 paired seed，2,457,600 shots，
  全部 PASS）；逐 draw 比 eae 便宜 0.5261%。invsqrt/chem 与 58271862 相同，
  已有全量 PASS。
- 预期：expected GM **25.4329**；0-failure 25.4495；1 failure 25.4107；
  2+ failures 25.3778。当前最佳仍是 58271862 的 **25.40482**。
- 提交 ref **58290992**，2026-11-13 01:26 UTC；截至最后一次检查仍为
  `SubmissionStatus.PENDING`（排行榜队列延迟；此前有 8–9h 延迟记录）。
- 记录：`submissions/20261113_392k_swap/README.md`；未 push。

## 2026-11-13（第四十七轮）：公开 frontier 跃到 27.08；三件全部独立全量 PASS 并提交

- 2026-11-13 凌晨出现新的公开 27.0+ 三件（Syed Asad Ali v12 /
  `ozertuu/quantum-sim-linalg-cache` v25 / `ozertuu/quantum-ai-27-083-vqcc-dqi-cutoff-17`）。
  本机用**未改动的官方 verifier**逐件独立全量复验：
  - invsqrt `321aff83…35177`：**46Q**，cost **80,162.732141**；200,540,928 shots
    PASS，worst/tol 0.9735759969，toffoli_equivalent 1,742.6681。
  - DQI `7cbe8ecf…14cd9`：**889Q**，cost **360,733,280,431.94**；102,400 shots
    PASS，0 value / 0 phase，R=1.1912604648；toffoli_count 383,156.29。
  - chemistry `6418ec8e…a77f`：**427Q**，cost **296,635,967.5936**；78,080 shots
    PASS，error_1 0.0196103713、error_2 0.0199987799；T=14,810（4,074 T/pass）。
  - 组合 GM = **27.0783908611**（若 DQI 抽到 1 失败仍约 27.03）。
- DQI 是 cutoff-17 变体：排除 weight 15–16，附加概率 ≈1.525e-7/shot
  （每 102,400-shot draw 期望 0.0156 次失败）；官方默认 salt 实测 0/0。
- 之前 58290992（DQI 392k swap）已完成：public **25.44039**（高于 25.40482）。
- 已按用户批准提交 18 件新 trio：ref **58299045**（2026-11-13 06:40 UTC，
  `SubmissionStatus.PENDING`）；ZIP SHA-256
  `63c5a0776bb1d91490c2e50e4c04607c78b91472f9da45247901ea4af314657c`。
- 记录：`submissions/20261113_27_078/README.md`；未 push。

### 第四十七轮结果（2026-11-13 更新）

- 58299045 **COMPLETE，publicScore 27.00209**。三件均独立官方全量 PASS；
  invsqrt 80,162.73 / DQI 7cbe8ecf / chem 296,635,967.59。
- 本机默认 salt 的 DQI 是 0 失败（局部 GM 27.0784）；公开 draw 隐含 DQI cost
  ≈363.80e9（约 2 次失败），所以实际 public 是 **27.00209**，仍比之前最佳
  25.44039 **高 +1.5617**，比 25.40482 高 +1.5973。
- cutoff-17 DQI 的公开 draw 比 notebook 声称的 “0 失败” 差；private draw 可能
  是 0–3 次失败，预期 GM 约 27.0–27.08。当前最佳 public 已确认 27.00209。

## 2026-11-15（第四十八轮）：公开 27.3066 与 HW-26 升级

- 公开前沿已从 27.078 升到 **27.3066**：`maoxin123/qcc-v27-4033-toffoli-coded-word-chemistry`
  v2 的 4,033-Toffoli/pass 化学 + `821bf8d1` DQI + 46Q invsqrt。
  本账号提交 **58349843**，MCP **COMPLETE 27.30661**。
- 进一步替换 invsqrt 为 HW-26 `1ba197b02771`（46Q，78,673.569211；未修改官方
  verifier 200,540,928 shots PASS，worst/tol 0.9986660009），提交 **58350759**，**COMPLETE 27.31193**。
- 公开可复现上限 **27.31214**（再把化学权重换成 npz `e52b7cdd`，仅 +0.0002）；
  公开榜 27.31+ 的更高分主要来自 DQI 抽签/私有组件，不能直接用公开件复现。
- DQI retention `max_hops=0/1/2` 实测均只宿主 241 个乘积，逐字节复现 `821bf8d1`；
  cutoff 18 仍最优。化学 B=143→129 是唯一 ≥1% 的公开思路，但截断 warm start
  无法过 e2 门，需要全量重训。
- 研究记录：`experiments/frontier/20261115_upgrade/`；回执：
  `submissions/20261115_public_2731/README.md`。

### 第四十九轮结果（2026-11-15，B<143 实测关闭）

- `qingyu1232/qcc-chem-b129-full` **v1 已 COMPLETE**（T4，上游 `shrink.py` full-U
  L-BFGS，seed 为公开 `(8,143,44)` 表）。实测**连续** error_2：
  B=139 **16.173**、B=135 18.408、B=131 20.713、B=129 **19.830** mHa。
- 上游 `recipes/finish_merged_b8.toml` 写明 "Rounding has cost 6-8 mHa on merged
  shapes, so the fit should be <= ~12.5 mHa"。B=129 的 19.830 高出门槛 7.3 mHa，
  量化后约 26–28 mHa，超过 20 mHa 硬闸门。
- GM 门槛同样独立否证：`dT/dB = -42.40`，GM≥27.50 需 T≤14,428（chem cost ≤288.98M），
  只有 B≤135 才够，而 B=135 的 e2 = 18.408 mHa 也不过门槛。B=139 虽最接近 e2 门槛，
  但只能到 GM 27.42。
- 结论：**B<143 关闭**（不是时间盒，是两条闸门同时不过）。未做 8-bit rounding、
  loader build、官方 78,080-shot 验证（第 1 步未过，后续无意义）。
- 当前最佳保持 **27.31193**（ref 58350759；提交时 159/3053，复核 175/3055）。
- 记录：`experiments/frontier/20261115_upgrade/chem_b129/CLOSED.md`。
