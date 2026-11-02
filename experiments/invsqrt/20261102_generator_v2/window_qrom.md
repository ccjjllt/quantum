# window_qrom.md：查表与小窗口算术（§4第二优先第一步）—— 两对比均保留现状

分支 `invsqrt-generator-rebuild`。基线 `width_opt62.py`（A1两级分裂版，Q=149，
SHA `4d43d989…bfe8efd`，官方 PASS score 2714467.64，见 `a1split.md §5`）。
本步只做对比实验，**生成器零改动**（`width_opt62.py`/`prescreen_width_opt.py`/
`narrow_proof.py` 均未动；REC_SHA 不变；B/C 沿用 `a1split.md §4` 记录，本步重跑 A 确认基线 intact，见 §4）。

纪律：不建测试目录/CI；不提交 Kaggle；不改官方 verifier；不跑官方 200M-shot 验证；
不读旧 KMB/tray；不数值拟合、不截位（冻结表 `int_tables_7_8_16_5_trunc.json`，
`fit_sha256=72154a80…`）；探针/证明脚本放仓库外 tmp（不进产物）；本目录新增本文一件；
`artifacts/` 未写新文件。失败/保留现状如实记（输了就认）。

## 1. 基线（同一布局内对比的对照面，`width_liveness.py` + `resource_stats` 实测）

| 口径（静态实测） | 值 |
|---|---|
| Q（`num_qubits`） | 149（峰值 R1_J0，extra 34；A1 行 extra 27 退居次峰） |
| 文本 SHA | `4d43d989…bfe8efd`（本步结束仍为 REC_SHA，见 §4） |
| `num_instructions` / CCX / CSWAP / CX | 124412 / 17546 / 446 / 48876 |
| `toffoli_like`（CCX+CSWAP） | 17992 |
| Q×toff（静态） | 149×17992 = **2,680,808** |
| F_A1 段 toff（正向 14 行） | 3982（J0..J12：299→275；J13：251） |
| F_R1 段 toff（正向 12 行） | 1908（J0..J11：170→148，行对和 `Σ=1908`） |
| QROM sweep（B×2/A×4/R×4，共 10 扫） | **254/扫**（load/unload 对 508/表·方向；10 扫共 2540） |

单行对基准（孤立探针，`extra=num_qubits−base`，全局 `=115+extra`，基座 `x22+lz5+coef33+V55=115`）：
R1 单行 extra 34（全局 149，`a1split.md §2`）；R 单表 sweep extra 8（decode 暂存）。

## 2. 对比一：单行 vs 双行窗口（选 R1）

选 R1 不选 A1，理由三条：(a) R1_J0 是当前 Q 峰值（149），窗口化峰值杠杆最大，
A1 已优化至 extra 27（非峰值）；(b) R1 12 行全为同号加，A1 J13 为变加——跨正负号的
行对窗口需额外符号处理，天然不公平；(c) 文献 no-go 对两者同等适用（下）。

文献（已用 websearch 核对原文）：arXiv:1905.07682（Gidney《Windowed quantum arithmetic》）
用小表查找把控制位成组迭代，以经典常数为乘数时降 Toffoli；但该文 §4 明确：
若 `x += a·b` 的三个寄存器**全为量子寄存器**，"we are not aware of a way to use
windowing to optimize the operation"。本电路 R1（`V += R·S`，R 与 S 均由 QROM 装入量子寄存器）
与 A1（`V -= 2·A·D`，A 量子、D 量子）正属此情形——预期窗口落败，仍按任务做一次
同布局实测证伪（证伪也是证据）。

### 2.1 双行窗口 W2 设计（R1 行对 `(2k,2k+1)`，k=0..5）

真值：行对贡献 `(c0·S + c1·2S)<<2k`，`S<2^17`，故组合倍数
`U=c0·S+2·c1·S ≤ 3·(2^17−1)=393213 < 2^19`，**U 取 19 位**（不是 18，
初版取 18 即错，见 §2.2）。并集片 `T=V[2k:45)`（`len≥35≥19`，真和 `<2^45`，
低 19 精确 + 全片进位链，`V[45:55)` 恒零论证同单行）。

正向（逆向为严格镜像：重建 U → 大减 → 解散 U）成本逐项：
- 地址表：`Cp0=c0&S`、`Cp1=c1&S` 两组 17×CCX（建/散各一次，68 CCX/对·方向）；
- U 装配：`U[0:17]+=Cp0`、`U[1:19]+=Cp1` 两次非受控通用加（copy 串行复用，峰值友好）；
- 进位：copy-free 窄大加（低 19 Cuccaro MAJ/UMA + `cout` + 高通用 + `flip(Tlow<U)` 清零，
  U 全程存活故免重建，进位贯穿并集全片——**无截断**）；
- 空间：U 19 + 串行 copy 17 + 各段 ripple 暂存（峰值见 §2.3 实测）；
- 卸载：U 解散（重建 copy → 两次 `isub` → 散 copy → free，逆序）+ 大加镜像。

### 2.2 小例证明（先证后进生成器；证明抓到两个真 bug，如实记）

脚本仓库外（tmp，不进产物），`nS=2` 源、`nT=6` 目标全范围穷举，
oracle `(tv + c0·sv + 2·c1·sv) mod 2^nt`，另做加后紧接减的 roundtrip：

- 初版 FAIL（一）：U 取 18 位且大加只进 `T[0:18]`——高位进位被切片丢弃
  （`c=01,s=1,t=6: got=0 want=8`，即 `T[0:3]+2` 的进位丢失）。
  修正：U 19 位 + 进位链贯穿全片（§2.1）。
- 修正版 FAIL（二）：`U[1:17]+=Cp1` 切片装不下 `2·Cp1`（`c=11,s=3: got=tv+1 want=tv+9`，
  第二加在 2 位片内回绕）。修正：目标片 `U[1:19]`（18→19 语义，`2·Cp1<2^18` 精确）。
- 终版：`w2-fwd ns=2 nt=6: 1024/1024 ok`，
  `w2-roundtrip ns=2 nt=6: 1024/1024 ok`，`W2-PROOF PASS`。

```text
window pair fwd (S17/T45): qubits=116 extra=52 global=167 toff=306 (CCX=306 CSWAP=0 CX=770)
w2-fwd ns=2 nt=6: 1024/1024 ok
w2-roundtrip ns=2 nt=6: 1024/1024 ok
W2-PROOF PASS
```

### 2.3 完整成本（Q×toff 实测）与决策：保留单行

全电路变体（仓库外：`import width_opt62` 后把 `build_r1/r1_rev` 换成 6 个 W2 对，
其余调度/表/寄存器不动；Q_CAP 断言 bypass 以暴露真峰值；double-build `eq=True` 确定性成立）：

| 口径 | 单行（现状） | 双行 W2（变体，实测） | 变化 |
|---|---|---|---|
| 行对 toff（正向，J0+J1 形） | 170+168=338 | **306** | −32（−9.5%，省一次高位通用 pass，如实记） |
| 行对 extra（单行/对探针） | 34（全局 149） | **52（全局 167）** | +18（U 19 + 装配/大加暂存并发） |
| 全电路 Q | 149 | **167** | **+18，且 >160 硬上限，宽度否决** |
| 全电路 toff | 17992 | **17728** | −264（−1.5%，正逆合计；R1 段 3816→3552） |
| 全电路 Q×toff | 2,680,808 | **2,960,576** | **+10.4%，落败** |
| 全电路 `num_instructions` / CX | 124412 / 48876 | 127208 / 50748 | +2796 / +1872（U 装配/解散 illuminates 门增） |
| 正确性 | A/B/C+DUMP-V PASS（基线） | 小例 1024+1024 PASS + 全电路变体前向 DUMP-V 16/16 PASS（`V` 与 `contract62.model_phase` 逐位一致） | 变体功能正确，纯成本落败 |

```text
double-build eq=True
variant Q=167 instr=127208 toff=17728 CCX=17282 CSWAP=446 CX=50748
variant Qxtoff=2960576
variant sha=9c209a40…e0ef19286209
VARIANT-DUMP-V PASS (16/16)
```

决策：**保留单行**。否决两项皆硬：(1) 宽度否决——167 超出 `Q_CAP=160`，
且比现状 149 高 18（U 物化 + 装配/解散加法器的空间税 > 省下的一次 ripple）；
(2) Q×toff 否决——+10.4%。−1.5% 的 toff 节省真实但无关大局。
机理与 Gidney §4 no-go 一致：双端皆量子时，组合倍数 U 必须在量子侧物化
（含装配/卸载两套加法），其空间+门税天然超过合并一次 ripple 的收益。
变体 SHA `9c209a40…` 仅为 tmp 测量产物，不进仓库、不碰 REC_SHA。

## 3. 对比二：unary vs 分包 QROM（选 R 表）

选 R 表（12 位）不选 A（22）/B（33），理由：分包开销（mux/暂存）随 `b` 线性涨，
R 是对分包最仁慈的战场；B 的 33 位行暂存连 QROM 期空闲（160−131=29，见下）都放不下，
属宽度预否决；R 上落败则 A/B 更败。比较基准：unary 现状 254/扫（§1）。

文献（已核对）：arXiv:2605.20334（Motlagh–Pocrnic《Halving the cost of QROM》）把
`b` 位 QROM 切成 `α` 个顺序 `b/α` 位子查找（SelectCopy 架构 + 背靠背去重 + 测量式卸载），
总价 `Eq.(6): (1+1/α)·N/λ + (b+b/α)·(αλ−1) + (α+1)·(αλ−3)`，`N=256, b=12` 代入：

```text
paper Eq.6 sweep, R table N=256 b=12 (compute+paper-uncompute; kickmix needs +coherent mirror, no-H):
  alpha= 1 lam=1: cost=   508.0 fits29 vs unary-pair 508
  alpha= 1 lam=2: cost=   278.0 fits29 vs unary-pair 508
  alpha= 1 lam=3: cost=   218.7 fits29 vs unary-pair 508
  alpha= 2 lam=1: cost=   399.0 fits29 vs unary-pair 508
  alpha= 3 lam=1: cost=   373.3 fits29 vs unary-pair 508
  alpha=12 lam=1: cost=   537.3 fits29 vs unary-pair 508   (lam=2/3 行从略，趋势同，见 §3.3)
```

纸面确有 `<508` 的格子（如 `α=1,λ=3 → 218.7`），**但不可直接兑现**，两项阻断如实记：
(i) 该式含测量式卸载（H + 测量 + fixup），kickmix 生成侧无独立 H 原语
（`qrom.md §3` 已验 `hasattr(builder,'h')==False`），相干镜像强制 → 每卸载加约 `N/λ`，
纸面 margin 大部被吃掉（此为估计，非证据，不做结论用）；(ii) SelectCopy 的共享解码
copy-network 是全新解码器架构，需独立证明 + 全电路集成，超出本步
"只实现最有希望的一种"预算。用 `unary_iteration` 逐片重扫冒充数据分包
（`α×254` 解码）是 strawman——不予实现；本步以地址分包线（§3.1，可表达、可证明、可实测）为准，记录在案。

### 3.1 本工具链可表达的分包族：地址块暂存（1/2/4 位）与最有希望者

`unary_iteration` 下任何覆盖 256 项的两级解码都不省钱（4+4：`15+16×15=255`；
1 位：`2×127=254`；2 位：`4×63=252`—— decode 独项最好也只是 252≈254，见 §3.2 实测 254），
真正的分包税在数据搬运。按"块大小只选真实可用工作位支持的值"：
R-mini 期已分配 `115+8(addr)+8(unary)=131`，空闲 `160−131=29`——
12 位块暂存 T2 + 1 位 match + 7 位 lo-unary（共 20）≤ 29 ✓ 可行；
B 的 33 位块暂存 >29 ✗（宽度预否决，与上呼应）。

纸面分包税（load，decode + mux12 + mirror + match）：1 位 `254+24+254+≈4=536`；
2 位 `252+48+252+≈8=560`；4 位 `255+192+240+≈32≈719`。
**1 位暂存分包税最小，为"最有希望的一种"，予以实现并实测**（2/4 位被纸面支配，
不再实现——支配关系写清即是证据链完整）。

实现（仓库外探针，全真实 R 表）：`hi=addr[7]` 定块，`lo=addr[0:7]`；
每块：match（`CX+X` 自逆，**等值选择无比较器 → 借用/进位 0 bits by construction**，
建/散计入）→ lo 扫 128 项进 T2（CX 免费）→ mux 12×CCX → 镜像扫清 T2（127）→ unmatch；
卸载 = 重建 T2 → 反 mux → 镜像扫 → unmatch（全 temps 现配现释，**零活位借用**，
恢复 = free 纪律）。地址展开/进位/空间/卸载/借用位恢复五项全部落进实测数。

### 3.2 小例证明 + 全尺寸实测：保留 unary

小例（4 位地址、R 派生 4 位表、1+3 分包，全 16 地址穷举）：装载 flat/split 均
`==table`（32/32），split 卸载归零（16/16），`QROM-PROOF PASS`。

```text
flat R sweep:   qubits=28 extra=8 toff=254 (CCX=254 CSWAP=0 CX=1598)
split1 R load:  qubits=40 extra=20 toff=528 (CCX=528 CSWAP=0 CX=3198)
split1 R pair:  qubits=40 extra=20 toff=1056 (CCX=528 CSWAP=0 CX=6396)
qrom-small-load flat+split: 32/32 ok
qrom-small-unload split: 16/16 ok
QROM-PROOF PASS
```

| 口径（R 表，12 位，全 256 项实测） | unary（现状） | 1 位暂存分包（实测） | 变化 |
|---|---|---|---|
| 单扫 decode（load） | **254**（extra 8） | 528（extra 20：T2-12 + match-1 + lo-unary-7） | **2.08×，+274** |
| load+unload 对 | **508** | **1056**（unload 528：重建 127 + 反mux + 镜像 127） | **2.08×，+548** |
| 全电路外推（仅 R 的两对：F+R） | Q 149 不变（R1 峰值主导） | toff +1096 → Q×toff 149×19088=2,844,112 | **+6.1%，落败**（宽度持平，纯门落败） |

决策：**保留 unary**。分包在 decode 独项已无胜算（252 vs 254），数据搬运的
mirror+mux 税（每对 +548）是致命项；纸面更优的 SelectCopy-λ 格子受 H 缺失与新解码器
证明负担阻断，转 §5 未来工作，不在本步冒充实现。

## 4. 生成器状态：零改动，基线 intact

- `width_opt62.py`、`prescreen_width_opt.py`、`narrow_proof.py`、`width_liveness.py`：
  本步无任何编辑（`git status` 仅本文一件新增）。
- REC_SHA 仍 `4d43d989…bfe8efd`；新 SHA 无（两个变体 SHA 只活在 tmp：`9c209a40…` 窗口变体）。
- 预筛 A 本步重跑（基线 intact 证据；B/C/DUMP-V 沿用 `a1split.md §4`，电路未变故不重跑）：

```text
sha1=4d43d989b9f9520fec11991b90f7bd511aa76a6df7bfd3a60822ed755bfe8efd
sha2=4d43d989b9f9520fec11991b90f7bd511aa76a6df7bfd3a60822ed755bfe8efd
recorded=4d43d989b9f9520fec11991b90f7bd511aa76a6df7bfd3a60822ed755bfe8efd
PRESCREEN-A PASS
```

- Q/门数记录：现状 Q149 / toff17992 / Q×toff 2,680,808 维持；两变体完整成本如 §2.3/§3.2 表。

## 5. 下一步二选一建议：选 HMR 清理重引入评估，不选 CSD 行裁剪约束重拟合

建议 **HMR 清理重引入评估**（即：对 QROM 卸载扫 `10×254=2540` 与各 temp-clear 镜像，
评估测量式卸载的可行性与净收益），理由：

1. **靶子够大**：相干镜像税共约 `2×2540`（装+卸）占全电路 toff 17992 的 ~28%；
   测量式卸载若成立，卸载半价趋零量级，潜在收益上千 toff——是本步两个落败方向之外
   唯一数量级对得上的钩子。CSD 在冻结 fit 下只能做**精确重编码**
   （常数加 `8192/256/11/8/+1` 等屈指可数几处，CSD 省门 ~ dozens vs 17992，可忽略）；
   任何有损行剪裁都要动合同重拟合 = 越权（`fit_sha256=72154a80…` 冻结）。
2. **证明路径 crisp**：用户代码全程无 H、无叠加产生门（`z_pow` 仅对角加相位；
   `iadd/isub/flip/unary` 内部已含 HMR 测量式 uncompute，先例存在）——每 shot 状态恒为
   计算基态，测量式清理的"塌缩安全性"在小例穷举 + B（scratch 归零）+ C（相位差 0）
   下可判定，无需新数学。风险也在明处：verifier 对含测量清理电路的计分口径需先用
   孤立探针确认（测量门是否进 `toffoli_equivalent`/shots 语义），先探针再证明再集成，
   每次只动一处（沿用本轮工作流）。
3. **与 §3 衔接**：正是 2605.20334 纸面 margin 的阻断点（i）——HMR 评估通过之日，
   SelectCopy-λ 解码器（§3 纸面 `α=1,λ=3 → 218.7` 格）才值得立项做证明+集成；
   通不过，则该线彻底关闭。CSD 线无此枢纽价值。

CSD 不选的补充记录：平方 9 行/U 符号位、A1/R1 行控制全是量子位，无经典可剪；
唯一经典侧是 address 形成 8×CX（已最优）与常数加——精确 CSD 重编码可作为 HMR
评估后的顺手优化（非独立步骤），不单独立项。

---

证据命令索引（本步全部手动运行，非测试/CI）：
`uv run python width_liveness.py`（基线 §1，无 diff）、
`uv run python <tmp>/window_probe.py`（§2.2）、
`uv run python <tmp>/gen_window_variant.py`（§2.3）、
`uv run python <tmp>/qrom_probe.py`（§3.2）、
`uv run python -c <Eq.6 sweep>`（§3）、
`uv run python prescreen_width_opt.py --a`（§4）。
官方 200M-shot 验证：未跑（仍为门禁，不在本步触发）。
