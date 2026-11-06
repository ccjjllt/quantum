# dfthcsos 高收益方向研究：从现有基线到可执行路线

2026-11-06，北京时间；分支 `codex/dfthcsos-research`。
任务：结合官方比赛数据、优秀公开实现和前沿研究，筛选当前值得投入的降成本方向。
这是一轮研究与局部测量，**没有产生已验证的新低成本电路，没有新增榜分**。

## 决策

**高收益主攻应从单独削 C / 同空间配对，转向 R/B/C、量化和 loader 的联合设计。**
优先结构目标为 `R7/B135/C50`，其次 `R6/B143/C59`：保留接近当前352的SOS项数，
把角度地址从1220压到1021/934，跨到10位地址，同时避开B≤128的高Q阶梯。
按products/helper/λ均保持的条件，仅缓存与固定资源变化已有2.6393%/3.2741%的
化学成本预算；达到5%还需分别减少353.3/258.3个双遍Toffoli，或取得等价的λ收益。
这些是**值得检验的目标，不是已成功训练的分解**。

**先做的低投入实验则是当前表的物理等价字修改与更小特征空间综合。**
本轮新测出1385个精确零父幅值角度；保持coded bit0和helper高位，仍有6925个
bit1–5自由变量，不消耗物理误差预算。将它们作为don't-care参与规划，比继续固定
当前W重新配对更有理由。若小块不见实际门数收益，再转向需要refit的低曲率soft-word编辑。

高投入项目以**化学成本降低至少5%（其余任务不变时总GM约+1.7245%）**为研究目标尺度；
1%化学改善可作为值得保留的中间结果。这只是本报告的投入分级，不是新候选成绩。

| 优先级/角色 | 方向 | 为什么值得做 | 必须得到的证据 |
|---|---|---|---|
| 先做，小规模筛查 | 精确零幅值字自由度 + 更小可实现W；再尝试priced soft words | 当前真实表有6925个不改物理的低位自由变量；公开源码已有规划器与word pricing | 同时计相邻loader、缓存和清理后的实际全家族门数下降；单独张量rank下降不够 |
| 高收益主攻 | compactness初始化的R/B/C共训，重点7/135/50与6/143/59 | 地址和缓存阶梯有可量化收益；公开Lera代码可训练U/W并量化，缺口已具体化 | 固定官方shift下连续拟合、量化后两误差/gap/λ、实际loader成本均成立 |
| 次优编译路线 | 新W/大块关系搜索，或小块深层AND SAT | 当前浅层配对已饱和，需扩大搜索类；公开chained_and及Polytof思想可借鉴 | 少门解的布尔等价、存活位≤128、HMR相位清理及全家族净收益 |
| 配套/对照 | C43/C42再训练、J3/J4重规划 | 都未被理论排除，且可量化打平条件 | C43/C42固定资源收益仅0.5212%/1.0490%；J4要实算19槽，不能只报少8Q |

## 基线与比赛中真正可改变的部分

固定输入为Syed notebook V9/run366109544、dataset V9，在本工作区只读链接主仓库产物。
本轮读取既有实际恢复字，再调用原版数学函数复算：

| 项目 | 数值 |
|---|---:|
| 化学成本 λ_eff × T × Q | 299,673,103.4280182 |
| λ_eff / raw Lambda / gap | 46.8936620787 / 282.8096560491 / 3.91489810005 Ha |
| 总Toffoli / 总Q | 14,966 / 427 |
| ANGLE双遍 / 固定prepare+Givens | 8,304 / 6,662 |
| R/B/C；brot/J | 8/143/44；8/5 |
| 两误差的门限余量 | 各约0.010005 μHa |
| gap下限余量 | 约0.100051 μHa |

这里T表示官方Toffoli-like计数，不是Clifford+T文献的T门数。
官方计分固定 `KEEP_BITS=10`、PREPARE资源公式、Givens公式、S和beta1。
当前inner临时位303主导总Q，单纯减少loader的77个scratch不会降Q。
因此新PREPARE电路、另做BLISS shift、再次谱放大、物理硬件速度提升都不能直接计作比赛收益。
依据为未修改的 `data/competition/verifiers/dfthcsos/verify.py`、`costs_prepare.py`、
`dfthc_math.py` 与 `SCORING_README.md`；详细资源扫描见 [RESOURCE_FRONTIER.md](RESOURCE_FRONTIER.md)。

## 新的本地证据一：195-product计划已读回，配对界全部饱和

发现并静读公开 `dfthc_refit 1.7.0` 后，用其symbolic reader和gauge模块读取真实电路。
本地封装为 [recover_current_plans.py](recover_current_plans.py)，没有调用其可能自动执行
完整验证的CLI。全部15槽的恢复函数在1220个真实地址上等于实际delta，保存全部terms与padding表。

| 槽 | products | 当前特征空间dimW | ceil(dimW/2) |
|---|---:|---:|---:|
| k0 | 217 | 434 | 217 |
| k1–3 | 216各 | 432各 | 216各 |
| k4–14 | 195各 | 390各 | 195各 |

每槽已经有179–206个跨块乘积，coded槽有12–17个coded/non-coded共享乘积。
一个paired-affine Toffoli可承担两个mixed rank-one项，纯low/high项用缓存CNOT补偿。
因此普通CP rank与195不是同一计价，固定当前W再配对也不能少门。
可改变的是W、数据、缓存或AND深度；此界**只约束当前W，不是全电路下界**。

这修正了上一轮“195 plans不可得”的工作状态：**具体计划现在已从电路恢复**；
Syed原始训练和原规划搜索过程仍未复现，且本轮未重发射电路。
reader忽略CZ/HMR相位，故Boolean恢复不是相位证明或完整官方验证。
证据：`artifacts/20261106_high_yield/recovered_plans/summary.json`、`k0.json`…`k14.json`。

## 新的本地证据二：精确零幅值提供不耗误差的字自由度

按整数角度字准确判断sin/cos为零，逐步追踪Givens树支持。
当一条边执行前parent幅值为零，child也尚未激活，该旋转作用在两个零分量上，角度任意改变
不影响物理向量。本轮找到**1385/91500个位置**（one-body50、two-body1335）。
保持bit0和bit6/7，单独释放bit1–5，得到**6925个自由bit坐标**。

手动把这些位置的bit1–5清零，实际改变1348个字：

- 与原表解码向量的最大浮点差为1.75584e−16；
- coded bit0、gauge两高位完全不变；
- λ_eff与原始报告完全相同，error1/2仅浮点末位变化，原版数学误差检查仍通过。

这证明“允许修改的表空间”存在，**不证明清零后的表更易综合**。
当前无对应新loader，没有门数收益，不能把该字表单独打包提交。
与上一轮五helper上界不矛盾：这里允许按地址改变低位；旧结论限制的是五个全局二次高位函数。

执行代码 [word_freedom.py](word_freedom.py)；证据为
`artifacts/20261106_high_yield/word_freedom/{summary.json,inactive_angle_mask.npy,zeroed_words.npy}`。
后续先对这些确切自由变量做小块约束综合；若需改变非零父幅值位置，再使用公开price_words
的误差影子价格和受约束refit，不能假装当前0.010μHa余量足以随意扰动。

## 新的本地证据三：结构下界与无收益路线

[numerical_bounds.py](numerical_bounds.py) 将固定shift两体目标表示为2926维正交对称pair矩阵：
对角元素权重1、非对角权重sqrt(2)，保留完整N⁴ Frobenius范数。
候选是Σ vec(X)vec(X)^T，必为PSD且rank≤R*C。
舍去目标负谱、保留最大的k个正特征值，给出所有PSD rank-k近似的最小误差。

packed残差与原版error2相差1.04e−17。结果：

| rank k | 最优PSD松弛误差（mHa） |
|---|---:|
| 288 | 20.51435 |
| 289 | 20.18731 |
| 290 | 19.85843 |
| 296（8×37） | 17.94036 |
| 336（8×42） | 9.12971 |
| 344（8×43） | 8.16835 |
| 352（当前8×44） | 7.36114 |

因此数值必要条件为**R*C≥290**；固定R8时C≤36应排除。
这不是区间算术的形式证明，但289/290两侧距离20mHa门限均远大于浮点末位。
它忽略共享U、lambda/gap、one-body误差、量化与电路成本，**rank≥290绝不等于可训练成功**。
C42/C43仍有松弛空间，旧谱裁剪失败不能否定再训练；C37离必要界近，风险更高。

另外两个量化诊断直接压低了旧路线优先级：

1. **固定每个物理X及native offset W，只换rank-one展开的收益上限很小。**
   三角不等式Σ|w_b|≥||X||_*；即使每列可独立用核范数最优分解、完全放开共享B基，
   lambda_h2仅269.250425→269.140640，lambda_eff最多46.893662→46.884496，
   即**0.01955%化学收益**。该松弛不约束改变整个X族/offset的重新拟合或正交混合。
   raw Lambda组成是lambda_h1=13.559231、lambda_h2=269.250425。
2. **7bit直接舍入不可用。** floor/nearest/ceil三种均失败；nearest的error1=2.13188Ha、
   error2=0.42510Ha，远大于0.020Ha；只量化one-body也有127.887mHa。
   7bit需要重新训练，不能当免费精度压缩。

将gap从当前值推到严格下限的极限，仅能降低lambda_eff约1.269e−8相对，已无高收益空间。
详见 `artifacts/20261106_high_yield/numerical/bounds.json` 和保存的目标特征值。

## 公开实现与前沿方法改变了什么

详细固定版本、原始来源及已知反例见 [PUBLIC_IMPLEMENTATIONS.md](PUBLIC_IMPLEMENTATIONS.md)
和 [FRONTIER_METHODS.md](FRONTIER_METHODS.md)。本轮主要发现：

- **manwithacat/dfthc-refit V5，1.7.0**：真实源码，不只是打包。包含固定字的活动集refit、
  shared/block planner、plan recovery、price_words与chained-AND CNF；已保存并检查。
  它不训练新的U或R/B/C，不能单独完成结构路线。
- **Lera compact pipeline V7，git704091b**：compact_seed、shrink、quantize_rm等支持从
  shifted-Hamiltonian pivoted-Cholesky叶子、按轨道profile聚类、OMP基开始训练。
  公开结果显示初始化的轨道紧凑性和量化余量很重要；旧R6/R7失败不构成新形状的下界。
  某些入口自动全量verify，后续使用时应拆开训练与手动候选验证。
- **Atakan V11所用五helper compiler数据集V1**：真实emitter和11个plans，适合作复现参考；
  其已公布成本约302.196M，劣于当前299.673M，且emitter硬编码1220地址，不能直接冒充新基线。
- **公开soft-word工作**：已有按误差价格修改角度以增加张量依赖的例子；这是与当前零幅值
  自由度相接的算法来源。公开省一门的例子不证明当前表有相同收益。
- **Polytof 2602.15285v2（2026-10-26）**：可借flip/plus、依赖消除与多样性搜索；必须适配
  paired-affine真实成本，不能把一般CCZ相位分解直接当ANGLE XOR loader。
- **2026 SelectCopy/dense-QROM**：按本题128Q和输出宽度算完整构造公式，40bit分别约1098/1048
  Toffoli，远高于当前270–297；这是所列构造的上界而非复杂度下界，但足以否定直接套论文
  “减半/四倍”的主张。dense还存在本机kickmix显式H不支持的适配障碍。

公开刷新还发现Heliosli V11/dataset V65沿用Syed V9 loaders的小幅权重refit，作者lambda_eff
约46.8935908；相对当前仅约0.000152%化学成本，不能视为高收益突破。本轮未下载/验证该整套候选。

## 下一轮最小实验、保留条件与停止条件

1. **当前表的零幅值/soft-word联合规划**：先选k11及其相邻槽（inactive位置207，为当前最多），
   同时约束两侧delta。以恢复的当前plans热启动，尝试新W/关系或局部SAT，不只在原W重配对。
   用实际完整代价比较；不接受“k11省1门但k12多2门”。先得到一个全可达、清理正确的更小loader，
   再看能否推广到多批数门，朝1%–3%化学收益扩展。若只有相同W内零收益，及时停止该搜索类。
2. **两种新形状的小规模可行性筛查**：Lera compact_seed多初值，以固定官方shift为目标。
   比较7/135/50、6/143/59和当前8/143/44对照，记录连续误差、轨道compactness、L1/gap，
   再对优秀初值逐步量化与coded字训练。公开旧表“连续约12.5mHa才留够量化余量”只作起始经验，
   最终以本表量化后指标为准。若固定资源+真实ANGLE+λ无法打平，不因地址数小就继续投入。
3. **编译算法扩大类**：从真实plan中截取小输出块，比较rank2与general chained-AND界，
   有差距才跑少一门SAT；跨块关系搜索须容许必要的暂增代价路径并保留可重放变换。
   所有结果计入cache、gauge、反计算和scratch，不将数学乘法数直接当最终Toffoli。
4. **最后才验证候选**：先检查全地址正反行为、scratch和HMR相位；构造出实际有收益的完整
   家族后，手动运行原版78,080-shot官方本地验证。数值表通过、Boolean相同、完整本地PASS、
   Kaggle成绩分别记录。没有自动提交、远程推送或GPU资源申请。

对于5%目标，当前形状需省748.3总Toffoli；若只动11个coded槽，合计至少省375个单遍product；
若要求每槽减少相同整数数量，则每槽需省35个。
195→194仅省0.1470%化学成本/0.04905%总GM，是有用的小步但不是高收益终点。
结构路线的意义正是同时减少缓存、表规模与产品数，避开只能逐门抠收益的局限。

## 本轮执行、复现与验证范围

所有新研究文件在本dfthcsos工作区；官方数据、共享环境和主仓库提交包未改。
使用现有Python3.12/NumPy/SciPy/native kickmix；没有安装依赖、创建测试或CI。
手动运行的新增局部研究：

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python experiments/dfthcsos/20261106_high_yield/numerical_bounds.py
DFTHC_GF2_BACKEND=python OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python experiments/dfthcsos/20261106_high_yield/recover_current_plans.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python experiments/dfthcsos/20261106_high_yield/word_freedom.py
.venv/bin/python experiments/dfthcsos/20261106_high_yield/resource_frontier.py
```

数值边界约7.47秒、零幅值探针约4.63秒、资源扫描约0.32秒；计划恢复耗时见summary.json。
资源扫描7496个形状；公开源码只执行了明确审查过的symbolic recovery相关路径，未运行训练器。
完整官方验证本轮执行次数为0，新增已验证成本收益为0。
外部一手来源、版本、源码快照和局部原始输出都在 `artifacts/20261106_high_yield/`；
大产物与来源下载签名链接不进入Git。此次研究已经筛定路线及量化门槛，尚未证明任一路线可达目标收益。
