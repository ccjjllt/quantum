# 公开 invsqrt 实现复核与研究方向（2026-11-06）

## 本次可确认的结论

本次通过 Kaggle MCP 外部查询比赛按 DateRun 排序的前 40 个 notebook、近期讨论及相关源作者版本，读取 Syed、yoyobar、Heliosli、Kirill、Qiu、Alex Chilton、manwithacat、Özer 的当前公开正文/代码及 mrmeows 的固定源码说明。**在该检索范围内，没有找到比本地 Syed V9 + nofallback 的 97,700.776777236 更低、并有足够完整验证证据的公开 invsqrt 电路。**这不是全平台或私有方案最优性结论。

最新聚合 notebook 的约 24.94 总分主要混入 DQI/化学变化，不能据其标题推断 invsqrt 更低。多个更新更晚的组合仍使用 Syed 较早的 inverse。当前科研起点继续用已有本地完整验证的 nofallback；公开方法的作用是确定有前例的机制与成本边界。

唯一新见的小增量是 **yoyobar notebook V33 / dataset V26**：把其条件相位融合迁到 **Syed V5/run366034280**，作者称期望 score 减少 **0.36334038**，约 **0.00586033 C**，投影成本约 97,746.81061。该源只有 32,768 paired SDK shots、5 个全输入 GPU measurement profiles，以及负控；作者明确 GPU 检查省略 SDK R phase，且不是 full64 官方验证。本次未下载其 KMB 做逐指令比较，因此**是否已被 Syed V9 吸收、是否与 nofallback 重叠、是否可叠加均未证明**。不计入本地新增收益，也不应抢占宽度/结构优化主线。

## 固定来源与复核范围

原始公开查询响应和小型源码文件保存在本 worktree 的 `artifacts/20261106_direction_research/public/`。只读取 notebook，不运行其代码；没有修改比赛 verifier、安装环境、打包或提交。

| 来源与固定版本 | 本次读取的信息 | 对当前起点的含义 |
|---|---|---|
| [Syed V9 / run366109544](https://www.kaggle.com/code/syed3000/vqcc-own-circuit-portfolio-notebook?scriptVersionId=366109544)，dataset V9 | 公开作者 inverse 97,747.22；正文给出完整机制，notebook 代码只打包 18 个已有文件 | 与本地 baseline 一致；作者多 salt kickmix-engine 声明与本地原版全量验证分开 |
| [yoyobar V33](https://www.kaggle.com/code/yoyobar/lb-22-99-invsqrt-101-62-qubits/version/33)，[dataset V26](https://www.kaggle.com/datasets/yoyobar/qcc-local-sota-20261031/versions/26) | Syed V5 上条件 phase fusion，0.36334038 score 期望减量，验证范围如上 | 仅作低优先级兼容性线索 |
| [Heliosli V11](https://www.kaggle.com/code/heliosli/the-dataset-is-public-now-enjoy/version/11) | portfolio v76_sy5_ay3，inverse 原样采用 Syed V5 | 总分更新不代表新 inverse |
| [Alex Chilton V114](https://www.kaggle.com/code/alexchilton/24-86-lb-verified-three-task-portfolio/version/114) | 保留作者逐项官方验证成本表；最优所选 inverse Syed V4 97,747.2154 | 是独立公开复验线索，非新的比本地更优方案 |
| [Kirill V17](https://www.kaggle.com/code/kirilltym/quantum-circuits-pi-gauge-weight-refinement/version/17) | 引用 Yoyo V31 inverse，当前变化主要 pi-gauge/chemistry | 未看到新的低于本地的 inverse 声明 |
| [Qiu pi-gauge V1](https://www.kaggle.com/code/qiuqiuh/qcc-pi-gauge-verified-portfolio/version/1) | inverse af469847，保留既有 quadratic accumulator 与 forced-phase-bit 收益 | 旧机制已进入后续公共家族 |
| [Hedge Wizardry V26](https://www.kaggle.com/code/manwithacat/vqcc-hedge-wizardry-notebook/version/26) | 当前新增是 Syed chemistry loaders 的重规划 | 不作为 inverse 增量 |
| [Özer 24.941 V4](https://www.kaggle.com/code/ozertuu/24-941-sota-multi-task-quantum-frontier/version/4) | inverse observed cost 97,747.22，读取 Syed dataset | 组合/runner，未发现新的 inverse 算法 |
| [mrmeows dataset V8](https://www.kaggle.com/datasets/mrmeows/qcc-1375-open-circuits/versions/8) | 原始 README、20.0565x 生成器及研究边界，Apache-2.0 | 提供真实架构与已尝试方向的第一手来源 |

API `get_notebook_info.metadata.last_run_time` 与按 DateRun 搜索返回的时间存在明显不一致；固定版本号、明确 run ID 和保存源码用于定位，未据该字段判断谁先发表。版本 URL 与 run ID 不混写。新下载文件只是上述公开 README/generate.py，未执行下载脚本。下载签名链接仅用于内存中的请求，未写入研究文件。

## 当前家族已吸收的机制

Syed V9 正文是本表第一手来源；是否在本地当前候选保留，依据本地迁移只改双选择器窗口这一事实。不能把下列历史减量累加为未来预期。

| 机制 | 公开描述的规模 | 研究启示 |
|---|---:|---|
| 8-bit semi-log lookup + degree-2 Horner + two-pass phase | 256 个地址，41 一般旋转 | piecewise polynomial/MBU 不是未使用的新技术 |
| Deferred fan-in coefficient decode | 169 ANDs | 优化对象应是多输出联合表示及调度，而非整张稠密表的字面存储 |
| 进位 measurement uncompute、carry-save/reverse-row merges | 多处算术阶段 | 单纯把反计算换测量已做；需识别新的相位还债契约 |
| 小窗 exact quadratic resynthesis | 7 个 3→2；另一个 5→4 decode | 剩余 blind small-window 扫描的边际收益有限 |
| 多输出/同目标 quadratic factorization | 四乘积 rank-2→2 CCX | 免费 CX 可换付费非线性门；有可达条件才能用受限域恒等式 |
| 跨 HMR/延后产品复用 | 两对复用；V9 又省一次 swap-control CCX | 选择跨阶段共享乘积要证明测量相位和寄存器恢复 |
| 9 个 conditioned T blocks 重构 | 每块 −0.125 C | 已吸收；当前 T 均值仅 1，不再是大成本池 |
| shift-register thermometer top-down measurement erase | 每步一个 CCZ | 尾部“改成 thermometer”本身不是新方向 |

## 62Q 的真实结构与宽度优先级

[manwithacat 的公开 63→62 复盘](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/discussion/754152)修正了其早先“63 已最优”说法：旧 63Q 电路的 q23=[x<2^20] 与其余 62 根线有 612,723 个冲突状态，不能按原调度简单重算；yoyobar 成功时没有删除这个 flag，而是重综合**每一个** 63-wide 阶段。系数 lookup 的 32 个 AND 产品有 27 个直接建在最终输出线上，只留 5 个 temporary；后续用经典奇偶和已有 live-wire 的线性组合替代新的 helper。作者给出的交换约为 +4.5 C 换 −1Q。

本次取得了 [circuit-viewer/stages.json](https://github.com/manwithacat/kickmix-macos/blob/main/tools/circuit-viewer/stages.json)，固定 Git blob `362b71f39297d5edf834fb47687e429c88a784d6`，保存为 `viewer_stages_62q.json`。它描述**旧 67482db6 的 62Q 电路**，不是 Syed V9 的坐标：

- q0…q21 为输入/归一化 mantissa；q14…q21 是 8-bit coefficient 地址。
- q42…q46 是五个 normalization count/control 位；q22…q41 的 unary leading-zero 前缀在 stage0 已 HMR 擦除。故不能将“20 根 unary flag 一直占位”当作进一步压缩的依据。
- 10 根 derivative seed 与 8 根 raw-address copy 在后期相位消除中有角色；它们的存活换来免费 Clifford phase repair。
- lookup 以及 early-phase/phase-merge 的临时物理编码共同决定峰值；仅压缩低峰的尾部不改变 Q。
- stage 标签有 documented/inferred 区别，必须在当前 Syed 指令流重新定位，不直接套用旧 op 区间或 wire 名。

**优先研究假设：**在当前所有 62-wide 时段中，寻找以输出线承载乘积、阶段间回收/重算、measurement-aware retiming 实现 61Q 的共同方案。以 C=1575.818980278 计，61Q 的额外成本上限为 C/61≈25.8331 C，超过即失去净收益；若不加 C，则节省约1575.82 score。此为严格预算门槛，不是已证存在的 61Q 候选。历史 63→62 是可行前例，现有满 affine rank/区间染色只能排除原功能与原调度下的线性压缩。

## 大收益要把相位函数与实现调度一起改变

mrmeows V8 原始说明（本地 `mrmeows_v8_root_readme.md`）记录过两类真正较大收益：把三个晚期 phase taps 改成早期可得的四个 gated-quadratic controls，将旋转44→41；以及保留10个 derivative seeds、raw address 与已有 monomial caches，在 rank256 的 quadratic span 中用7个 helper 完成相位消除，替代11个AND。这些历史收益已继承，启示是优化“何时保留什么非线性信息”，而不是简单删门。

该来源也给出两个明确尚未完成的数值路线：

1. 128-entry constant seed，8 fractional seed bits，degree3，residual24+2 guard，output fraction26：作者全输入数值模型 worst/tolerance=0.617，**未编译**。可作为新分段/精度/运算调度设计的对照，但其已尝试 cubic single-pass 架构估到175Q，说明浮点或定点函数逼近通过远不等于低成本量子实现。
2. 33-rotation 合并模型在旧 round14 上全域数值通过，margin=35,960,695 units；但所需 Boolean controls 在实际相位时点不属于检查过的低阶可恢复 span。没有发出满足预算的 KMB，不能把少8旋转的账面收益计作成功。

上述两条均适合“先编译成本账，再投入综合”的中高风险支线。主线仍应优先在现有精度完全不变时做全阶段存储/非线性乘积布局；低成本先导证据是所有峰值可同时消除以及总额外 C 预算，而不是原电路某一处出现空线。

## 最小下一步与停止规则

1. 对当前 Syed+nofallback 建立真实阶段/寄存器语义映射，定位每个 62Q 峰值，区分 input、lookup outputs、retained seeds、history caches、phase controls。每次拟删一条长期值，算入所有重算和相位修正成本。
2. 选一个主导峰值做可达域上的“61Q输出内嵌乘积”构造；若只是旧调度重染色无解，不扩大为全局无解。若所有峰值的共同方案预计额外≥25.8331C，关闭该具体设计。
3. 跨 HMR 多乘积/共享目标研究继续做，但每个小窗收益约1–2C应与61Q的预算对照，集中有代数结构的大段，避免重跑旧枚举。
4. Yoyo V33 条件相位融合仅保留为低成本差异审计；确认窗口、独立测量条件、相位恢复及与 nofallback 的不重叠之前不计收益，不为其先做全量。

验证层级：本报告外部资料为作者声明或源代码阅读；本次没有运行新候选、局部模拟或官方 verifier。当前 97,700.776777236 来自已有 `20261106_syed_v9/invsqrt/official_nofallback.log`，不是本次重新测得；公开方案更低/兼容性的空缺已显式标明。
