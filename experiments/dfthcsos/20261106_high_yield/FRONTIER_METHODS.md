# 前沿方法对当前 dfthcsos 的可迁移性

2026-11-06（北京时间）。基线为 Syed V9：cost 299,673,103.4280182、lambda_eff
46.893662078700515、14,966 Toffoli、427 qubits；ANGLE 双遍 8,304 Toffoli。
这里的 T 是官方 Toffoli-like 资源计数，不能与论文的 Clifford+T 中 T 门数混同。
本记录基于一手论文、固定版本源码静读、现有本地证据与公式枚举；**没有运行外部优化器、
生成新电路或完成官方全量验证，没有实测新增收益**。

## 结论：前沿优化要针对现有 paired-affine 模型

最值得迁移的是 **GF(2) 分解的跨块代数搜索与小块深层 AND 精确综合**，并与当前
公开 planner 的 paired-affine emitter 共用真实成本模型。不是把通用 QROM、AlphaTensor
的论文改善倍数乘到当前电路上。

在本轮发现的公开 `dfthc_refit 1.7.0` 中，已有 block/shared planner、关系交换、分区搜索、
padding don't-care、coded/non-coded 共享、`chained_and.py` 的深层 AND CNF。这些已存在的
功能不能重新称为原创路线。其具体版本及来源见同目录 `PUBLIC_IMPLEMENTATIONS.md`。

### 当前 195 products 为什么不能直接换成普通 CP rank

静读 `artifacts/20261106_high_yield/public/lera_v7/tensorqrom.py` 与
`dfthc_refit_1.7.0/planner_shared.py`：每个非线性乘积可实现

```
(a1·low + b2·high)(a2·low + b1·high)
 = (a1·low)(b1·high) + (a2·low)(b2·high) + pure-low + pure-high.
```

纯 low/high 函数由完整单项式缓存经 CNOT 实现，因而**一个 Toffoli 覆盖两个 mixed
rank-one 项**。已有 planner 将低单项式分块，找含实际高地址行的子空间 W，再配对其
rank-one 生成元。这比普通双线性“一项一个 Toffoli”计价更强。
`planner_shared.exchange` 已允许同成本中性步，但接受条件仍限制 products 不增。

本轮随后实际符号恢复了全部15个 Syed V9 loader（证据
`artifacts/20261106_high_yield/recovered_plans/summary.json`）：k0 的217 products 对应
dimW434；k1–3的216对应432；k4–14的195对应390。**所有槽均达到固定当前W的
ceil(dimW/2)配对界**。每槽已有179–206个跨块乘积，coded槽已有coded/non-coded共享。
这是Boolean真值恢复与秩计算，不含相位证明或官方全量验证。
因此固定W内重新配对、单纯换一个可逆基、或“开始跨块共享”都不能作为新增收益论据。
必须改变可实现的feature空间W/表数据/缓存构造，或进入不受该界限制的深层AND类。
此界不排除更小的另一个W，亦不构成全电路复杂度下界。

由此得到的可操作增量假设（本轮推断，尚无收益证据）：

1. **用现195-product计划热启动，寻找更小的可实现W**：引入 flip/plus 的多步搜索，
   保留多样性池；当前已有中性 relation exchange，新增点必须是可越过增代价屏障、
   更大块或不同关系空间的搜索。固定W的配对已饱和，局部term重写若不改变W便无门数收益。
2. **目标应为 paired products + cache + cleanup + gauge修复**，不要只最小化 CP rank。
   所有自由变换应保留低/高缓存实际函数依赖与物理 gauge；不得将一般相位电路的等价
   分解直接当作可运行的 XOR oracle。
3. **先测小块是否真的能突破浅层模型**：公开 `chained_and.py` 同时给 rank-2 下界、
   一般链式 AND 下界及完整 CNF。先选择两界有差距的块，再求少一门的深度2/3解。
   其2-AND、linear-fibre维5的小例子只证明搜索类严格扩大，不证明本题存在这种块。
   成功后必须计入中间 AND 存活、清理与 HMR 相位修复，检查每个 loader ≤128Q。
4. **低地址基变换/大块共享也要计缓存账**：任意 GL 基变换可保留地址可逆性，但可达
   截断域在新坐标中可能不再向下闭合，原来只需77高地址单项式的缓存优势可能丢失。
   免费 CNOT 变换不等于总 Toffoli 免费，必须重新合成缓存及 don't-care。

## 可直接借鉴的开源代数优化

[Polytof 论文 v2](https://arxiv.org/html/2602.15285v2)（2026-10-26）直接面向 CCZ/Toffoli：
BCO 基变换、SGE 二次型消元及 flip graph search；论文给普通 cubic 基准的 CPU 结果，
并单列双线性分区模型。当前源码固定为
[0dcac107d15adc34dc646242d222f21ae7d32699](https://github.com/ZIB-IOL/polytof/tree/0dcac107d15adc34dc646242d222f21ae7d32699)
（2026-10-21），MIT；C++20 实现，`BASE` 支持一般双线性张量，SGE 只适用对称 `topp`
模式。已静读固定版 CLI，未构建或运行。

**迁移判断**：优先借 flip/plus、依赖消除、多样性池的算法思想；对真正双线性小块可以
使用 `BASE` 作对照。对 whole-loader 无约束 `topp` 优化会混合输入/输出分区并引入
Hadamard/Clifford 修正，当前 kickmix 不直接支持，因此不是即插即用编译器。
现有 mixed-pair 分解与普通 CP/斜对称 cubic 的等价类不同，不能把输出 rank 当作195的
同口径数字。更不能引用其基准“低于一分钟”作为当前大张量的运行时间承诺。

[AlphaTensor-Quantum](https://www.nature.com/articles/s42256-025-01001-1)（2025-03-20）
提供学习型张量分解与 gadget-aware 奖励。其
[源码固定版](https://github.com/google-deepmind/alphatensor_quantum/tree/3def81a2a42666416a4a8041eea6e1bc98bc8e9f)
主要为算法模块、分解产物及简化可运行 demo；普通 src 不是完整可运行训练流程。
**迁移判断**：可将学习引导留作已有精确变换搜索的后续加速器，当前优先级低于上述
CPU 代数搜索/SAT。没有适配本loader的训练器、奖励和可重放证明前，GPU训练本身不是
“高收益方向已经确认”的证据。

## 2026 新 QROM 方法：真实预算筛除直接替换

一手来源：

- [Motlagh/Pocrnic，Halving the cost of QROM，v1](https://arxiv.org/html/2605.20334v1)
  （2026-05-19）：SelectCopy 与顺序 bit packets。本文筛查使用 Appendix A 式(9)，
  包括有限表长、packet宽度和读出项，未采用大N渐近主项。
- [Motlagh，Dense encoding，v1](https://arxiv.org/html/2610.02321v1)
  （2026-10-01）：利用同一 dirty qubit 的 X/Z 两分量，采用式(9)整数构造上界。
  原文“约4倍”相对通用 SelectSwap 的大N区间，算法还要求输出 Hadamard 夹心。

本地手动公式扫描：N=1220，11地址位+40公共word位，最多77 scratch；枚举所有packet宽度
和合法2幂块大小，并计入论文 helper 上界。结果：

| 输出信息位 | SelectCopy顺序packet最小构造上界 | dense最小构造上界 | 当前实际单遍loader |
|---|---:|---:|---:|
| 40 | 1098 | 1048 | 270–297 |
| 35（乐观免计gauge处理） | 1077 | 992 | 270–297 |

这些数值是**所列构造的参数扫描上界，不是所有QROM的复杂度下界**，也未实际合成。
它们已足以否定“直接搬论文模板会省一半/四分之三”的论证。计算还慷慨允许clean输出，
而后续 ANGLE 的目标寄存器已有上一批字，真实移植必须进一步处理该差异。

native kickmix 1.0.0 对 `H q0`、`S q0` 的手动解析均返回 unknown operation，`CX q0 q1`
可解析。dense原构造因而有明确门集障碍；这不证明其所有代数等价改写都不可能。
跨 ANGLE 保留 dirty cache 同样不合约：官方在每次 ANGLE 后要求 workspace 清零。
只有有物理含义的公共word位允许携带当前字，已有helper路线正利用了这一点。

复算命令（仅算公式，非官方验证）：

```sh
.venv/bin/python artifacts/20261106_high_yield/literature/qrom_budget.py
```

输出在 `artifacts/20261106_high_yield/literature/qrom_budget.json`；源码保留在同目录。

## 分子优化：借训练目标，不能重复计入谱放大与 BLISS

[DFTHC-SOS原论文 v1](https://arxiv.org/html/2502.15882v1)（2025-02-21）式(42)联合考虑
积分误差、归一化与gap，通过JAX/Adam进行结构参数扫描、多初值优化。
[SOSSA理论 v1](https://arxiv.org/abs/2505.01528v1)（2025-05-02）解释低能谱放大的收益。
**迁移判断**：赛事已经使用 `sqrt(gap*(2*Lambda-gap))`，不能再叠加一次谱放大收益。
论文的可调对称平移、CCSD(T)相关能误差容忍，与本赛固定S/beta和两个20mHa Frobenius
门不同，论文低rank结构不是可直接通过的候选。

[BLISS-THC修订版 v3](https://arxiv.org/html/2501.06165v3)（2026-07-30）有正则化因子优化、
rank/精度和硬件空间时间权衡。**迁移判断**：只能借其cost-aware拟合思想。
官方 `load_inputs` 覆盖提交的 `H1_I/Hsym_lower`，新的BLISS平移自由度不能带进来；
active-volume硬件速度提升也不会改变本赛固定资源公式。

对本题可落地的数值目标应写为：

```
min log(lambda_eff(actual quantized words, W, H2_I)) + log(T_actual) + log(Q_actual)
s.t. error_1 <= 0.020, error_2 <= 0.020,
     gap > 3.914898, Lambda > 49, loader_qubits <= 128.
```

这不是平滑一次性目标：T/Q有离散台阶，字也离散。合理流程是先扫描少量结构预算，
对每个结构保留固定shift，连续拟合和离散量化/稀疏活动集交替，使用原版指标选点，
最终必须用能实际合成的字表定价。目前两误差门余量仅约0.010μHa，gap余量约0.100μHa；
直接把文献的error tolerance或“降gap”当自由收益已无依据。另见主研究的rank必要下界与
7bit局部数值探针，避免对明显不可行结构投入重训练。

## 收益尺度与投入门槛

固定lambda、Q和其他任务，若11个coded批都从195 products减少d，每个正反两遍总省22d
Toffoli；下表仅是预算，不是已实现改进：

| 每coded批少几门 | 总省Toffoli | 化学成本降幅 | 总GM提升 |
|---:|---:|---:|---:|
| 1 | 22 | 0.1470% | 0.04905% |
| 5 | 110 | 0.7350% | 0.24621% |
| 10 | 220 | 1.4700% | 0.49486% |
| 20 | 440 | 2.9400% | 0.99966% |

因此，高投入算法要瞄准**至少多批数门、最好每批10–20门**的改进空间；仅找到一个批次
省1门虽然可采用，却不支撑重训练大型RL模型的成本。新的配对/深层方法应先在一个
真实coded loader上证明张量/全可达轨迹等价、scratch和相位清理，再扩大到全家族。

## 其他工具的边界与证据索引

- [QCFDL](https://github.com/XanaduAI/QCFDL) 是 state preparation/vector block-encoding
  资源比较工具，不能直接替代任意ANGLE XOR oracle；本轮只查看默认分支说明，未固定或运行。
- [Qualtran issue 1829](https://github.com/quantumlib/Qualtran/issues/1829) 的维护者于
  2026-05-13表示DFTHC/SOSSA尚无具体实现时间表。不能假设已有端到端生成器。
- 本地官方证据：`data/competition/verifiers/dfthcsos/SCORING_README.md`，
  `verify.py:200`固定shift、`:270`实际字评价、`:373`精度门、`:472`共享workspace资源；
  `scoreinfra/circuits.py` 的逐ANGLE workspace和phase检查。
- 文献版本、固定提交与局部门解析记录：
  `artifacts/20261106_high_yield/literature/source_notes.json`。
- 固定版Polytof接口摘录：同目录 `polytof_cli_excerpt.md`；该代码未运行。

结论的可信边界：已确认公开方法的可用接口、约束不匹配与可量化预算；尚未确认任何
新方法能在Syed V9上产生正收益。优先级指向可检验且更大的搜索空间，不是全局最优证明。
