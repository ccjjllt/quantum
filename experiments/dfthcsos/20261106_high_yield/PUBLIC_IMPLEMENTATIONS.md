# 公开实现核查：可再生成源码、适用范围与高收益线索

核查日期：2026-11-06（北京时间）。工作区 `codex/dfthcsos-research`。
本子研究只读取 Kaggle MCP、下载小型公开源码、用 AST/ZIP/LZMA 静态解包、审阅程序；没有执行下载的训练器、优化器或验证器，没有提交、发布或推送。主研究另行运行的本地探针见同目录报告。

## 结论

**原来的“没有可用规划器源码，所以只能等待 Syed”判断过于悲观。** 目前至少有三条真实源码链：

1. James Barlow 的 `dfthc_refit 1.7.0`：实际有固定字约束重拟合、已发电路计划恢复、五块 shared/block planner、gauge-aware emitter 包装、word-move 定价、chained-AND SAT 编码。不是只打包二进制。
2. Lera 的 `dfthc-compact-pipeline` V7：具有任意 (R,B,C) 的轨道聚类初值、U/W 联训、渐进裁剪、Reed–Muller 约束量化及 tensor emitter。其依赖官方 starter kit，能够启动新形状研究。
3. Atakan V1 source bundle：11 个五 helper C44 loader 的 emitter、固定 plans 与 phase 证明脚本可用，但总成本 **302,196,075.20** 高于现 Syed V9 的 **299,673,103.43**；价值在于实现参考，不能作为收益直接替换。

**高收益搜索需要改变表示空间/分解形状。** 固定现有 plans 只重配 pairing、同模型 helper 编码、已经贴近误差门的普通 weight polishing 都不像主线。可实施路线是：

- 新 (R,B,C) 形状的结构感知共训，争取更少地址和跨地址位阶梯；
- 固定形状上，用有物理价格的字修改、近零父幅值自由度或新 block partition 降低 tensor feature 空间维数，再重新配对；
- chained AND 是逃离 rank-2 product 限制的研究性后备，公开源码可支持小块 SAT，但已有旧表局部 UNSAT/超时，不宜把它当高确定性收益。

## 当前公开前沿与源码分类

本次查询比赛按 DateRun 排序的最新 40 个 notebook，并进一步审阅下列有相关方法的条目。没有声称穷尽所有私有/公开研究；组合榜分也不等价于 chemistry 单项优劣。

| 来源、固定版本 | 观察到的状态与单项数字 | 真正源码范围 | 对当前工作的价值 |
|---|---|---|---|
| [Syed notebook V9](https://www.kaggle.com/code/syed3000/vqcc-own-circuit-portfolio-notebook?scriptVersionId=366109544)，[dataset V9](https://www.kaggle.com/datasets/syed3000/vqcc-own-circuit-portfolio/versions/9)，2026-11-06 08:02 | dataset 当前仍 V9；299,673,103，14966 Toffoli，427Q；本仓库此前局部恢复结果一致 | notebook 仅打包；方法正文详细描述，未提供本人训练器/195-product 搜索过程 | 当前比较基线；其“完整官方 PASS”为作者声明，不能追溯改写本机验证范围 |
| [Heliosli notebook V11](https://www.kaggle.com/code/heliosli/the-dataset-is-public-now-enjoy)，[dataset V65](https://www.kaggle.com/datasets/heliosli/qcc-circuits-live/versions/65)，2026-11-06 10:08 | 复用 Syed V9 全部15 loader，dataset notes：λ=46.8935908 | notebook 验身份、运行官方 verifier、打包；没有 refit 生成器 | 相对 λ=46.8936620787 仅约 0.000152% 化学成本下降；不能当高收益主线；此处未下载其NPZ复算 |
| [dfthc_refit notebook V5](https://www.kaggle.com/code/manwithacat/dfthc-refit)，内部 release **1.7.0** | 2026-11-06 最新搜索记录；Kaggle元数据版本5 | 9模块、文档、HW23旧plans均嵌入脚本；已静态解包 | **最直接的研究工具源码**，尤其 recover、shared、price-words |
| [Hedge Wizardry V26](https://www.kaggle.com/code/manwithacat/vqcc-hedge-wizardry-notebook)，HW24 | 作者报告301,875,698.74，15076 Toffoli，427Q；使用Syed V4表 | notebook旧文仍称planner未公开，但当前独立utility已发布1.7.0 | 文档时间不一致须用真实文件能力判断；HW24已被V9超过 |
| [Lera pipeline V7](https://www.kaggle.com/datasets/marculera/dfthc-compact-pipeline/versions/7)，commit **704091bf1e1325b090202343e4d8130ff1c80b64**，2026-11-03 | 自有(8,143,45)连续/量化表及日志；更老README段落仍列9组结果 | 真正训练与编译源码，固定版本文件清单已保存 | **新形状路线的主要可复现起点** |
| [Atakan notebook V11](https://www.kaggle.com/code/atakanaldemir/qcc-gap-3-residue-repair-and-c43-native-compiler)，[source dataset V1](https://www.kaggle.com/datasets/atakanaldemir/qcc-c44-five-helper-release-sources/versions/1)，2026-11-06 04:51/源包11-06 02:30 | 当前标题含C43，实际主候选为C44；比Syed V4少28总Toffoli，但仍比V9多126 | 11 loader源代码+固定plans；4 plain loader仍复用；不是独立分子训练器 | helper提取/dirty恢复/phase审计的可读参考 |
| [Soft-word write-up V1](https://www.kaggle.com/code/iwanttorungemma9b/vqcc-df-thc-loaders-what-worked-and-what-didn-t)，2026-11-05 09:10 | 作者报告305,652,489.65，15175T/427Q；旧表 | notebook本体是方法说明、打包、已有receipt读取；不是完整自有planner | word edits改变rank的具体成功案例；James工具补上部分可复现实现 |
| [Kirill V17](https://www.kaggle.com/code/kirilltym/quantum-circuits-pi-gauge-weight-refinement) | 302,756,736.86，15120T/427Q，作者完整官方验证 | 采用Syed旧C44表，主要独立审计 | 验证参考，未超过V9 |
| [Full-XOR V16](https://www.kaggle.com/code/leoprovorov/full-xor-chemistry-no-borrowed-bits) | C44/15120T旧前沿，未改loader；H2/H3权重研究 | 有SLSQP/augmented-Lagrangian实现；标题不代表新全XOR低成本loader | 权重/offset优化比较，已有饱和风险 |
| [From Source V54](https://www.kaggle.com/code/dmitriigluzdov/quantum-circuit-compilation-from-source) | 公开表列15245T/427Q/λ47.21 | 主路径仍装配固定公开组件 | 标题不保证当前最优组件的源头再生成 |

注：上表 notebook URL 是持久入口，版本整数以本地metadata固定；未取得run ID的条目没有伪造version链接。本地metadata+source与SHA清单才是本次抓取的版本证据。Kaggle `get_notebook_info.metadata.last_run_time` 在多条返回中是较早日期，与 DateRun 搜索不一致；日期采用搜索或dataset version creation_date，未用旧时间冒充更新时刻。

## dfthc_refit 1.7.0：能力与限制的源码核查

静态文件：`artifacts/20261106_high_yield/public/dfthc_refit_1.7.0/`。

- `femoco_problem()` 从官方 `load_fixed_shifts()` 得到 Hsym_lower/H1_I，重建固定 S/β1；从实际整数 words 和提交树恢复 u。**不优化固定shift**。
- `Problem` 的变量为 w(R,B,C) 与 w_B(R,C)，维度取输入形状；固定 u、树、精度和R/B/C。它支持任意已有形状的 fixed-word refit，但本身没有训练新u、增删组或列的步骤。
- 最终指标走原版 dfthc_math；优化梯度为PyTorch float64实现。约束包括两误差20mHa、E_gap floor、Lambda floor及gap domain。
- refit以约束面投影L-BFGS、Gauss–Newton回缩、Armijo回溯执行，处理精确零权重活动集、KKT释放以及近零 h1′ 特征块。gauge有多列平滑L1初值及小随机kick后精确Jacobi，因此比“再扫描所有两列”更广，但仍没有已证实V9收益。
- `recover.py` 能从已发缓存乘积电路读回低/高form与fanout；`planner_shared.py` 支持五个低单项式三元块、共享relation、padding与exchange；`planner_block.py` 处理plain批。
- 自带 HW23 plans 只有 k8/k11/k12/k14，旧表每槽276T，**不含Syed V9 195 plans**。REFERENCE记录旧表shared 196产品、generic217等结果，并非V9最优再现。
- 主研究本轮已利用已审阅 recover/gauge 在实际V9上恢复15份plans；k4–14为195产品、feature维390，当前所选feature空间pairing已完美。证据在 `artifacts/20261106_high_yield/recovered_plans/`。这补上当前计划读回，**没有复现作者搜索过程，也没有完成重发射/全HMR phase证明**。
- `price_words.py` 提供KKT/有限响应价格、精确固定权重成本、受限refit与bit0 rank-drop编辑。其默认rank planner只算下界式节省，实际收益必须重新发射电路才成立。π-gauge兼容路径须先看 convention/支持范围；不能绕过拒绝检查把canonical signed程序直接用于任意gauge。
- `chained_and.py` 给出一般AND与rank-2深度1的不同界，并有CNF/CEGAR。旧块rank-2需10，一般AND下界只有6；9-AND问题曾超时。这是有依据的“尚未排除”，不是现有正收益。

依赖：NumPy/SciPy；refit/word prices需PyTorch；读取/发射需native kickmix；发射依赖Lera tensorqrom。Rust `kickmix_analysis` 可选且公开包未含；Python消元可用但时间预算搜索会因此走不同路径。重放固定plan不依赖CPU搜索时限。
注意CLI `refit`/部分流程会默认调用完整verify，`finish_rm.py`末尾也如此；后续仅用审阅后的局部函数或明确手动触发，不能为导入/一般编辑自动跑全量。

## 新形状：已有源码比“直接删一组”更可行

Lera `compact_seed.py` 明确接受任意R/B/C：

1. 固定官方shift，在正确的pair-space乘数范数下做pivoted Cholesky，取 R×C 个叶子；
2. 按叶子的轨道profile做balanced k-means，将每组限制为C个叶子；
3. 每组从叶子特征向量做simultaneous OMP选B个共享向量，再最小二乘初始权重；
4. 多个k-means seed以轨道有效数/集中程度筛选，再float64 L-BFGS/Adam联合优化U,W；
5. 结构感知量化、coded bit约束、重新做one-body/refit和loader规划。

这直接支持主研究提出的(7,135,50)/(6,143,59)初始化；不是证明它们能过门。
Lera旧实验 (6,159,80)/(7,143,64)连续误差已19.7/20.4mHa，量化前预算不足；新R7/R6路线必须先证明比这些旧basin更强，不能只用资源账本宣布收益。
旧公开“C44不可行”也已被Syed C44成功反例推翻，说明历史null只限当时表/训练过程。

`shrink.py` 固定shift、联合U/W、先fade再删B/C；目标仅error2 + sign-mixing penalty。它**不在每步同时保证error1/gap**，且merge后R固定，不能直接把8组压为7组。新R应从compact seed或独立设计的重分组开始。
`quantize_rm.py` 同样支持任意R/B，提供每16地址块Reed–Muller码、延迟锁定codewords和连续refit；`finish_rm.py`串联one-body刷新、refine、refit_al、build_family。
这套源码是可改造基线，并不是Syed自己的CUDA-graph/Babai最近平面训练器的精确副本。

缓存基础成本可直接从Lera `tensorqrom.cost` / James `expected_cache_toffolis`读出：
L=16，H=ceil(A/16)，base=(15−4)+(H−1−bit_length(H−1))。

| 形状 | 地址 A=76+RB | high chunks H | base AND/遍/loader | 当前对比 |
|---|---:|---:|---:|---|
| (8,143,44) | 1220 | 77 | 80 | 当前 |
| (7,135,50) | 1021 | 64 | 68 | 基础cache少12；产品数需新表重算 |
| (6,143,59) | 934 | 59 | 63 | 基础cache少17；产品数需新表重算 |

下降不只是selection少1位：高地址cache函数空间和tensor问题同时缩小。但λ、C成本、可量化误差会反向抵消，需总账。
Atakan emitter硬编码1220地址/11 selection/69 high缓存/5字，不能直接套新形状；Lera emitter与James的若干核心函数参数化，仍需审计π-gauge移植和128Q约束。

## Soft words：公开成功案例与保留条件

旧公开soft-word工作（作者receipt/正文，本机未复跑）给出比“任意加角度噪声”更具体的策略：

- 用837个priced bit0编辑使一批coded mixed rank 20→18，以9个而非10个LSB产品实现，最终省1个loader Toffoli；
- 在父Givens幅值平方约1e−33…3e−32的条目上做18个编辑，新增3个依赖，使plain loader到215产品；
- 所有编辑必须同时考虑相邻delta批，不把词表局部rank下降直接当总loader下降；
- 衡量的是“重新refit后λ增加的价格”与“真实发射后省T”，不是只看局部误差或裸rank；
- 旧表的价格约1900成本单位/μHa、1个每遍loader Toffoli约40300成本单位，**这些价格不能迁移到V9**，必须重新估计（当前误差门余量极紧）。
- 其旧表小窗口最多4产品替换更少一般AND无解、9-AND LSB SAT超时，是降低chained路线优先级的证据；不证明新表全局无解。

主研究本轮已完成当前表的第一步：整数词精确追踪发现1,385/91,500个角度位置在执行前父幅值严格为零；固定coded bit0及gauge bit6/7后，bit1–5共6,925个自由位。统一置零实际改1,348个词，重建向量最大差1.756e−16，原版数值λ不变、两误差仍过门。见 `artifacts/20261106_high_yield/word_freedom/summary.json`。尚无重新综合loader或省门结果，因此这证明物理自由度存在，未证明可兑现收益。

建议最小判定：在已确认的零父幅值自由度上，保护现有5 helper和相邻批成本，生成少量新增依赖；原版指标与等预算未编辑refit作对照；无真实发射或λ代价不打平即停止该候选。

## 保存与再现

- 原始精简notebook文本、metadata、dataset file lists、源码、公开许可证放在 `artifacts/20261106_high_yield/public/`，不入Git。
- `LOCAL_SOURCE_MANIFEST.json` 给出已获取每个文件的大小与本地SHA-256。没有持久化Kaggle签名下载链接、token。
- James包为script AST读取 `_BUNDLE` 字面量再base64/ZIP解包；**没有import或运行外部脚本**。包声明SHA为 `00dee3d2518ed8f442438041aa3f7d28d7222203dd2a21f92a0dd94c999e892b`。
- Atakan源包1,929,760B，下载实际SHA `a0f705ea88b888cfaa89b84ddc7c988fa4aa5702c1ffc81cb9b2f917e149b95c` 与notebook固定值相同；只选取chemistry子目录及两个phase proof源文件解包，未执行。
- Lera `tensorqrom.py` 31,084B，实际SHA `e6bbcaf1ad7ad025f2105f0233aa9e232a211d1d76bac867da9282b21d4ed017`；V7 VERSION全文commit在上表。
- Lera本轮保存的是重点源码子集，不是可直接启动的完整环境：仍需按已保存V7文件清单补齐 `df_init.py`、`onebody.py`、`refine.py`、`refit_al.py` 等依赖及官方starter库。不要把“已取得关键源文件”写成“端到端复现成功”。
- 官方[starter kit V4](https://www.kaggle.com/datasets/sohier/verifiable-circuit-compilation-starter-kit/versions/4)，2026-10-23北京时间，data-prep commit `f02280140eb100d604a077f4c774f85d68e1269f`，含训练/angles/circuits三阶段、JAX/Optax库和Qualtran固定依赖。主训练链需要JAX、Optax、SciPy与float64能力；本工作区共享环境未修改。

本子研究没有产生新电路候选或本机官方PASS。公开来源的成功/失败数字与本轮真实本地探针必须分别引用。

