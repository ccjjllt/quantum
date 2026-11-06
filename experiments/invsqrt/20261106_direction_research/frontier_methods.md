# invsqrt：前沿方法适用性与成本门槛

日期：2026-11-06（北京时间）。本记录针对 `codex/invsqrt-research` 的 Syed V9 + nofallback，
不是跨三赛题的统一路线。只读检查原版验证器、参考生成器、既有候选证明；在线读取论文和作者代码。
本轮没有安装依赖、生成新量子候选或运行完整官方验证。

## 结论

优先把**带真实可达条件的多输出逻辑重综合、测量纠相重综合和 qubit 重算调度作为一个联合问题**。
现有局部改写的成功已经说明这一机制可用；2026 年新论文提供了更一般的相位坐标表述。
目标应从“一个 CCX 是否可删”升级为“一个算术/纠相块能否以更少 AND 或更少常驻 scratch 实现”。
但本轮文献调查没有产生比 97,700.7768 更低且已验证的新候选；下文收益门槛是筛选条件，不是收益承诺。

保留一条高风险支线：**按实际整数截断误差联合拟合的分段低阶多项式 + 窄局部坐标 + 原位消费系数**。
这与重启原有固定 41 掩码角度 LP 不同，也与直接照搬多轮 Newton 不同。
应先通过完整输入域的经典定点模型和清楚的 Q/C 预算，再投入可逆电路实现。

## 比赛契约决定哪些论文可用

本机权威来源：`data/competition/verifiers/invsqrt/verify_submission_invsqrt.py`，
尤其 `ProblemSpecInvSqrt`、`reference_values`、`verify`；参考算法见同目录 `nr_reference_circuit.py`。

- 输入只有 22-bit `x`，范围 `1..3,133,452`；输出是模 1 turn 的 `1/sqrt(x)` 相位。
  `x` 必须恢复，所有 scratch 必须为零。逐 x 误差容限为 `2^-24/sqrt(x)`；完整验证每 x 64 shots。
- 评分 `Q * [E(CCX+CCZ+CSWAP) + E(T)/4 + rotation synthesis /4]`。
  经典控制下的执行概率会改变成本；量子控制为零不会让一个 CCX 免费。
- 普通 H、QFT、通用受控旋转、QSVT 的 coherent basis-change 不在 kickmix 的可提交结构中。
  HMR 是特定“测量并清零”的指令，不能替代保留量子态的 H。
- `NEG` 等可以恢复测量相关的全局符号。不能因为某文献在量子态意义下忽略全局相位，
  就忽略验证器追踪的该项；最终应逐测量分支与目标相位一致。
- 当前完整日志：`Q=62`、`C=1575.818980278`，直接 Toffoli-like 均值 `1280.7281563891`，
  T 均值 `1`，一般旋转 `41`。纯 T 类直接收费仅 `0.25C`；其完全消除也只节省 `15.5` score。

伴随比赛的 [Khattar et al., arXiv:2610.23832v2, 2026-10-21](https://arxiv.org/html/2610.23832v2#S2.SS1)
把允许结构、HMR 纠相和 Benchmark I 的验证方式写得明确。论文泛论中允许某些任务有失败预算，
不意味着 invsqrt 可以丢弃罕见 x 或选择性接受 measurement 分支。本地 invsqrt 要求所有执行检查通过。

## 方向 A：把跨 HMR 窗口改为纠相函数的联合综合（近期主线）

### 文献证据与本地已有证据

[Jeon, Huang, Cai, arXiv:2609.31605v1, 2026-09-25](https://arxiv.org/html/2609.31605v1#S4.SS3)
从测量结果诱导的相位出发，先压缩有效 syndrome，再允许冗余相位坐标来降低具体纠相电路成本。
论文 IV.3 的关键不是一味最小化坐标个数，而是同时选择坐标表示和实现。
本文仅采用所有 syndrome 都得到纠正的 deterministic 路线；其 post-selection 方案不直接适用本题。

本地已有的无回退选择器是相近的具体例子：29 个测量源进入经典仿射式，三个失败条件秩为 2、
异或为零，使恰好一个成功分支执行。对 Syed V9 的新净收益是 `393215/524288 C`。
旧 Maoxin/Syed/Qiu 记录还证明：某些改写对任意 dirty 边界输入并不等价，但在真实可达域成立。
因此应保留前缀约束；不能要求每个切口的所有内部量子输出都逐线与旧实现相同。

### 可执行研究问题（本记录提出，未执行）

1. 选择一个含多次 HMR 的完整算术/选择块，保留其真正的存活边界值、后续经典位版本以及总相位。
2. 把测量诱导相位记为 `phi(x,m)=sum_i m_i*g_i(x)`，加入原有 CZ/CCZ 纠相。
   在可达域上，免费 Z/CZ 可以吸收一次与二次 Boolean 相位；重点综合剩余共享乘积。
3. 允许改变临时乘积、HMR 的位置以及纠相表示；不用原骨架“删一个门”的邻域限制搜索。
4. 对支持集的采样只用于发现关系，随后用 SSA/SAT 或可控规模的 ANF 证明覆盖全部合法 x 和自由测量位。
   如果更换测量历史，必须证明最终分支语义，不能用“同 seed”当作相同测量历史。
5. 评分必须计算整个新块的 `E(compute + correction)`，包括新 HMR 后的条件收费和 scratch 峰值。

这里的收益空间来自共享非线性中间量，不来自 HMR 本身免费。原版参考已大量使用 temporary-AND
与免费 measurement uncompute，不能把经典“反计算成本减半”的系数再乘一遍。
一组可重复结构若每处省 1C、可应用 k 次且互不干扰，则潜在 score 改善为 `62*k`；
这是用于决定是否值得综合的条件预算，尚无新的 k 或成功模板。

## 方向 B：XAG 多输出重综合与有预算的 scratch 重算（与 A 联合）

[Meuli et al., arXiv:1908.01609v1](https://arxiv.org/abs/1908.01609v1)
给出了 XOR-AND 网络到低 T-count oracle 的构造，并把 AND 数与乘法复杂度关联；同时研究空间/门数交易。
对本题的可借鉴点是让免费 XOR 做更多工作、尽量共享 AND，而不是最小化总指令数。
该论文的通用 oracle 保持所有输出；invsqrt 应在保留所需 phase 和真实存活输出的约束下使用更专用的目标。

[Yu et al., ASPDAC 2025](https://si2.epfl.ch/demichel/publications/archive/2025/ASPDAC25_YU.pdf)
把 XAG 优化的目标进一步扩展至后端 qubit 和时间。
但其 AND3 合并的 6-T 构造使用 H/平方根 X 等通用 Clifford；不能直接作为 kickmix 新门使用。
论文中的平均改善比例也不构成本赛可获得的收益。可以借用成本感知的 cut/resubstitution 思路，
输出仍须是本赛合法门且显式结算 HMR 纠相。

只降低 AND 数不一定降低 `Q*C`：新增一个常驻 qubit 要求净省
`C0/63 = 25.0129997 C` 才能保持当前分数；增加四个则要省 `4*C0/66 ≈95.5042C`。
反过来，删一个 qubit、以额外重算换空间，只要增加成本少于 `C0/61≈25.8331C` 就盈利。
这使得小型“早清零、按需重算”值得与综合一起测算，而非仅凭当前区间着色峰值 62 宣布 Q 无法再降。

[Reqomp, Quantum 8, 1258 (2024), arXiv:2212.10395v2](https://quantum-journal.org/papers/q-2024-02-19-1258/)
展示了给定 qubit 上限下自动重算/反计算的可行性。其公开实现是旧 Qiskit 环境；
不应把现有 49k 指令、带测量和经典版本的 KMB 直接交给工具并假定语义兼容。
适合先用一个小型依赖 DAG 模型标出“以后要再次使用但现在可廉价重算”的寄存器，
只对 61/60Q 目标构造具体 schedule，并把测量纠相纳入代价。

具体结构的启发不能停在“压缩 unary flags”。本轮读取的旧 62Q 家族 viewer 注释
（`artifacts/20261106_direction_research/public/viewer_stages_62q.json`，
来源 `manwithacat/kickmix-macos/tools/circuit-viewer/stages.json`，blob `362b71f39297d5edf834fb47687e429c88a784d6`）
已把归一化状态保留为五个二进制位；20 个 unary normflags 在早期已测量清理。
相对更值得分析的是十个长期保留的导数 seed、八个地址副本和分段输出字的共存。
这些注释对应旧 `67482db6…`，需要在当前 Syed 指令上重新确认存活区间和功能，不能直接复用旧坐标。

最新 [Liu, Zhou, Meng, arXiv:2608.09578v1](https://arxiv.org/html/2608.09578v1)
研究 clean/dirty ancilla 的统一恢复与 rewrite-based normalization。
它支持“短期不使用的非零线也可借用，但须恢复原量子态”的设计原则；
论文的适用覆盖率并不是本题门数收益证据。本次未取得并运行其原型代码。

### 已固定、可复用的开源入口

通过 GitHub connector 的 commit/file read 核查，均未下载编译或导入：

| 项目 | 固定版本 | 已读文件与用途 |
|---|---|---|
| [caterpillar](https://github.com/gmeuli/caterpillar/tree/4c6f766cd0ffc62d37ab45edfe80c9f1eae44764) | `4c6f766cd0ffc62d37ab45edfe80c9f1eae44764` | README 的 XAG + SAT pebbling mapping 示例；只作为算法参考 |
| [Reqomp](https://github.com/eth-sri/Reqomp/tree/fd2256e2643d6e0d3b3f07db225c979faebb6c69) | `fd2256e2643d6e0d3b3f07db225c979faebb6c69` | README，ancilla 标注与空间上限；依赖 Python 3.10/Qiskit 的示例环境，与本仓库分离 |
| [mockturtle](https://github.com/lsils/mockturtle/tree/4a592f35eccba171b9fb6a47c00d1a68838d4ffc) | `4a592f35eccba171b9fb6a47c00d1a68838d4ffc` | `include/mockturtle/algorithms/node_resynthesis/xag_npn.hpp`；4-input NPN 重综合入口 |

mockturtle 当前固定版本的说明专门更正：默认 ABC rewrite library 不是 size-optimum，
需区分 `xag_incomplete` 与 `xag_complete`。而且“size-optimum XAG”也不等于最小 AND 数、
最小可达域实现或最小 `Q*C`。不能用一次库重写未改善就证明本题局部最优。
本轮未生成电路，所以不存在可声称“已复现 paper benchmark”的结果。

## 方向 C：近似架构重设计（高风险支线）

[Gu et al., arXiv:2610.22367v1, 2026-10-15](https://arxiv.org/html/2610.22367v1#S3)
的数值函数电路采用更细分区、窄局部坐标、直接累加、按实际整数截断拟合以及廉价 lookup 清理。
其中 Coulomb 案例用 128 条直线替换更粗的二次近似，报告 1,140 Toffolis/142 qubits。
**其契约是 48-bit 坐标输入、25-bit 加法输出、绝对误差 `2e-6`，不等于本赛**。
本赛最大 x 的允许绝对相位误差约 `3.37e-11`，而且所有整数 x 都需要覆盖；不能直接引用其成本当候选。

可移植的是共同设计方法：让分段选择与输入位对齐、让局部变量足够窄、在用完系数后用相位纠正清理、
把截断误差直接放入离线整数拟合。它允许跳出固定 41 个相位掩码，但必须重新支付系数准备、算术、
恢复、旋转与 qubit 全部成本。根代理本轮另做经典定点全域数值实验，此处不把数值可行性写成电路收益。

这套一般思路并不全新：[Syed V9 / run366109544](https://www.kaggle.com/code/syed3000/vqcc-own-circuit-portfolio-notebook?scriptVersionId=366109544)
已经描述 8-bit semilog 查表、二次 Horner、两次 phase pass、41 次旋转与 carry 的 MBU。
因此下一项真正要证明的是“更少长期 seed/更窄算术/更少旋转带来的收益，能否超过更大的表与恢复成本”，
而非再次展示 piecewise 或 MBU 可以运行。

建议只保留少数可解释组合：分段数/阶数/局部位宽/累加位宽联合扫描，
先得到严格余量，再用实际 kickmix 算术生成一个关键算子计算代价。
若 `Q=80`，全部 Toffoli 等效预算只能到 `97,700.7768/80≈1221.26C`；
这一预算已包含全部旋转和恢复，不能把 1,200 个 forward AND 误称为有希望。

### 最新 QROM 论文如何影响这条支线

[Motlagh–Pocrnic, arXiv:2605.20334v1, 2026-05-19](https://arxiv.org/html/2605.20334v1)
以 SelectCopy 与 sequential packets 降低 dirty-ancilla QROM 的代价。
其一个基本成本式为 `2N/lambda + 2b(lambda-1) + 2lambda-6`，需约 `b(lambda-1)` dirty qubits；
进一步 packet 变体只在适合的 N/b/workspace 区域接近主项减半。
若未来系数表扩为几十至几百行，可把它与 unary iteration 的实际成本一起比较；
比赛参考的四段系数加载已是少量 AND 选择后的 Clifford 网络；当前 62Q 家族则已使用
经过重综合的 8-bit lookup，二者都不能直接按未优化 SelectSwap 的领先项乘一个“减半”系数。
需要先确认实际 loader 的共享 AND 和受限 scratch 账目，才有可比预算。

[Motlagh, arXiv:2610.02321v1, 2026-10-01](https://arxiv.org/html/2610.02321v1)
又把两份经典信息编码到 dirty qubit 的 X/Z Pauli 分量。
论文 Eq.3 的内核是相位 lookup，但标准 XOR 输出需 `H ... H`。
因此不能直接拿其接近四倍的领先项改善套在 kickmix 的数据加载上。
若探索直接相位 lookup，需要单独推导合法门的标量相位实现和资源；本次没有这样的生成器或证据。

## 不作为当前高收益方向的项目

| 方向 | 不能优先投入的具体原因 |
|---|---|
| 通用 QSP/QSVT、QFT 加法器、phase-gradient catalyst 的标准形式 | coherent H/基变换等超出可提交结构；必须先给等价 kickmix 构造，不能从渐近复杂度直接跳到本赛 |
| 仅优化 CNOT 数、拓扑路由、T-depth、reaction depth | 当前 score 不直接奖励这些；只有减少 Q 或计费门后才有收益 |
| 将现有 CCX 换成通用 4T/6T 分解 | 官方 CCX 已按 1C=4T 收费；通用分解常需不允许的 H，可能无分数改善 |
| 反计算一律换 HMR、post-selection | 大量 temporary-AND 清理已经免费；更复杂垃圾的纠相须支付，不能丢弃失败 syndrome |
| 大规模重复旧单删/同骨架小窗搜索 | 旧基线有大量有限范围负证据；没有新的结构假设时，搜索成本大且增益缺乏依据 |
| 固定 41 个模式只调角度 | 旧有限模型 LP 已无收益；即使精度完全理想，固定 R 的合成节省也有小上界，详见本轮预算记录 |
| 把 Q=62 区间峰值当作全局下界 | 仅限制原调度、原表示；重算、dirty borrow、原位运算改变问题本身 |
| 从“R≥22”推断最多可删19旋转 | 旧记录未覆盖 Clifford/T 相位类别、条件分支与可变执行数；本记录不使用该所谓通用下界 |

## 研究交接条件

近期优先 A+B：先选择一个代价和重复结构都明确的块，输出 prefix 约束、存活值、相位公式、
现有期望收费，以及 61/60Q 或更少 AND 的具体预算。只有这些约束下产生的新电路，
才能把“文献启发”升级为候选收益。C 只在经典全域模型通过且粗预算有明显空间时升级。

所有来源均在 2026-11-06 实际在线打开；arXiv 链接固定到所列版本，比赛论文和 Reqomp 采用 v2，其余为 v1。
这里只列实际读取的一手资料，不声称穷尽所有最新文献。论文结果、已有本地日志、
本记录的分析推断和未来实验严格区分。
