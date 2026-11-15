# invsqrt 前沿评估：46Q 增量盘点与 Q45 判决（2026-11-15）

范围：只做**只读**核查（下载公开件、静态读电路、读生成器源码），未跑官方 verifier，
未做任何量子模拟，未提交。所有"PASS/成本"数字都标了来源；本文件没有一条是本机验证结果。

---

## 0. 判决（先给结论）

1. **公开最好件不是我们现在用的 `e46d90c3`，而是 `1ba197b02771`（manwithacat HW-26）。**
   46Q、static 1,550、mean 1,478.75、cost **78,673.57**（作者本机官方 verifier PASS）。
   我们的 `e46d90c3` 是 78,719.529147，贵 **1 个 Toffoli（= 46 cost）**。
   换成它是**唯一确定可拿**的增量：GM **27.30661 → 27.31193（+0.00532）**。
   HW-26 已经包含 e46 的那一处 measured-CZ 改写（逐 op diff 证实，见 §2.3），不存在"两处合并"的额外收益。

2. **公开空间不存在 Q < 46 的 invsqrt。** 497 件聚合集（manwithacat v125，2026-11-14 11:49）
   里 invsqrt 的 Q 直方图最小是 46（6 件）；54 件 Atlas（2026-11-12 快照）最小是 62Q。
   46Q 这一档的 6 件成本是 78,673.57 / 78,719.53 / 78,765.51 / 78,765.55 / 78,765.64 / 80,162.6~7。

3. **Q=45 在当前架构下是负收益，而且不是"差一点"。**
   公开已有三次 Q45 尝试（`asteriospanoras/qcc-27-30-what-works-what-fails-and-why`，2026-11-14），
   结论是：46 线上最便宜的精确覆盖在 `4560ac0c` 上要 **+196 Toffoli**，在 `321aff83` 上要 **+257**。
   1 个 qubit 的盈亏平衡是 **≤ 38 个 Toffoli**（`46·C / 45 = 38.03`）。所以 +196 意味着
   cost 85,828（GM **−0.776**），+257 意味着 88,573（GM **−1.053**）。
   触发点不是稳态宽度，而是 261 段瞬态里的 257 段由 alternating-carry adder 的进位线打开。

4. **T 侧也已经饱和**（下面 §4 逐项）：33 个旋转是 2⁻⁴…2⁻³⁶ 的二进制阶梯（删一个就 2.3×
   超出 margin，LP 重拟合只值 −0.08 cost）；64 行表受精度约束（margin 只剩 ≈20%）；
   divider 578 已是该校验和结构的低点；严格 dead-write 扫描（含输入寄存器线、把 Z_POW 视为读取）
   在 `e46d90c3` / `1ba197b0` / `321aff83` 上是 **0 处**。

5. 因此**唯一还值得花的"研究级"Kaggle 实验**不是再去试 Q45，而是把 Q45 从"公开的发射级估算"
   变成**分配器级判决**：一次 notebook（约 15–25 分钟 build）给出确定的分阶段超宽清单与每处最低补价。
   gate 是 `Σ 最低补价 ≤ 38`。过则按 §6 建 Q45；不过就永久关闭 invsqrt 的宽度线，记录归档。

---

## 1. 当前口径（main 已提交的 58349843）

| 项 | 值 | 来源 |
|---|---|---|
| 本账号上一版 GM（本机默认 salt） | **27.306613** | `experiments/frontier/20261115_upgrade/README.md`、本文件 §5 复算 |
| invsqrt `e46d90c3` | 46Q、**78,719.529147** | maoxin v27 notebook 官方 verifier 输出 |
| DQI `821bf8d1` | 889Q、360,209,905,486.02 | 同上 |
| chemistry `3f864a7a` + 4,033 loaders | 427Q、294,991,455.82 | 同上 |
| 参考成本 R_inv | **2,076,774.233715** | ahoirg v028 REF 与 maoxin v27 REFERENCE 一致 |
| 参考成本 R_dqi / R_chem | 24,439,463,583,672.93 / 3,355,599,588.3155 | 同上 |

GM = (R_inv/c_inv · R_dqi/c_dqi · R_chem/c_chem)^(1/3)。
单项 1% 降本 → GM ×1.00334。

`e46d90c3` 的静态结构（本机 `kickmix` 直读，未模拟）：

```
Q 46   ops 23,877   num_bits 387
CCX 1413  CCZ 9  CSWAP 129   → static Toffoli-like 1,551
其中 142 个 Toffoli 在 PUSH_CONDITION 块内 → 实际 mean = 1551 − 142/2 = 1,479.75
T 1   generic rotation 33（另有 4 个 Clifford + 1 个 T 的 Z_POW，共 38）
CX 13055  CZ 2225  HMR 1278  X 3267  SWAP 11
```

成本分解（可复算）：`C = 1479.75 + 1/4 + 231.294 = 1711.294`，`cost = 46·C = 78,719.53`。
旋转项 **231.294 = 13.5% of C**，等价 33 个旋转每个 7.0095 Toffoli-equivalent（28.04 T）。
由旋转项反推 phase margin ≈ **1.26×10⁸** units of 2⁻⁶⁴（worst/tol ≈ 0.797）；
公开 post-mortem 给 `4560ac0c` 的是 `116,320,642 units`（0.813），生成器 `cost_model`
默认 `margin_units64 = 124,370,688`（0.800）。三者同一档，本文用 ≈1.2×10⁸ / 0.80。

> 注：`mizeroluckygall` 的 walkthrough 写 e46 的 worst/tol = 0.99867，与该口径不一致
> （0.99867 会要求旋转项 ≈264、cost ≈80,224）。本文不采用该数字。

---

## 2. 公开检索：Q < 46 或 cost < 78,719.5

### 2.1 数据源

| 源 | 版本/日期 | 用法 |
|---|---|---|
| `manwithacat/vqcc-apache-public-circuits` | v125，2026-11-14 11:49，497 行 | `manifest.csv` 全表，Q/成本/作者/首发日 |
| `asteriospanoras/qcc-circuit-atlas` | 2026-11-12，54 件 invsqrt | `circuits.csv`，Q/static Toffoli |
| `manwithacat/vqcc-hedge-wizardry` | 2026-11-14 16:33 | HW-26 件本体 + `README`/`SHA256SUMS` |
| `heliosli/qcc-circuits-live`、`junmiaotiao/qcc-frontier-20261114f`、`masonbradleygilhool/qcc-frontier-merge-v3` | 11-14 | 三者的 `invsqrt.kmb` 都是 `e46d90c3`（逐字节一致） |
| `syed3000/vqcc-own-circuit-portfolio` | 11-12 | `invsqrt_source_zip`（生成器源码）+ `invsqrt.kmb` |
| `xianyu3/vqcc-v52-asterios-invsqrt-source-20261114` | 11-14 | `base_submission/invsqrt.kmb` = `dcde7078`，含 v52 source receipt |

### 2.2 结果（46Q 档全部）

| SHA-256 | 作者 / 来源 | Q | static | mean | cost | 备注 |
|---|---|---:|---:|---:|---:|---|
| `1ba197b027713aac164056d12505c87f286c3fcd94f403c522073325763bf2f9` | manwithacat **HW-26**（hedge dataset，11-14） | 46 | **1,550** | **1,478.75** | **78,673.57** | **公开最低**，官方 verifier PASS |
| `e46d90c36d1beb3ce7731a3e0b5c3659b3cda7f5f290b73c6c34513d96c005b6` | asterios（measured-CZ）/ 在 maoxin v27 中 | 46 | 1,551 | 1,479.75 | 78,719.529147 | 我们在用 |
| `dcde70780434501912c5cc032c6dfad25ac694d50da4e8e45cdb65115baa81b2` | Atakan Aldemir fine-angle | 46 | 1,552 | 1,480.75 | 78,765.5131 | HW-26/e46 的母本 |
| `e0db1ac70e25…` | ozertuu | 46 | – | – | 78,765.5451 | |
| `4560ac0c017bf6d1bf27c73320f2e30c247a2a18143d58ff92a601f8bc20b218` | ahoirg 64-row table | 46 | 1,552 | 1,480.75 | 78,765.6368 | Q45 分析用的另一母本 |
| `b6f7d70510e8…` | ThomasG | 46 | – | – | 80,162.6774 | |
| `6530283ef666…` | PhilipLinHan | 46 | – | – | 80,162.6853 | |
| `321aff83636214196daa9cbc9dcc9c5e12a155bcff8d9989e98b8cee40935177` | Syed Asad Ali v12 | 46 | 1,599 | 1,511.57 | 80,162.7321 | 生成器可复现该文件 |

- 62Q 最好仍是 `9c708f7b9abc…` 93,555.2627（已被 46Q 线淘汰 14.3%）。
- **Q < 46：0 件。** 聚合集 Q 直方图（invsqrt 87 行）：46×6、62×53、63×10、64×1、66、68、76、82、89、90、93、95、105、140、145、208、256、258、260×2、273。
  Atlas 54 件：62×29、63×4、66、68、82×3、90×2、92×2、93×3、95、115×2、194、259、260×3、273。
- **cost < 78,673.57：0 件。**

### 2.3 `1ba197b0` 与 `e46d90c3` 的关系（逐 op diff）

对 `dcde7078 → 1ba197b0` 做 op 级 diff，只有 6 个 hunk，全部是测量改写：

```
a[3239:3241] CX q37 q21 / CX q38 q21            → HMR q21 b61 + 条件 Z q37 / Z q38
a[3252]      CX q38 q21                          → 条件 Z q38
a[3288:3291] CX q16/q17/q18 q21                  → 条件 Z q16/q17/q18
a[3292]      CCX q16 q20 q21                     → 条件 CZ q16 q20      ← 这条就是 e46 的 measured-CZ
a[3297]      CCX q10 q11 q13                     → CCX q10 q11 q21 + CX q21 q13
a[3399]      CCX q10 q11 q13                     → CX q21 q13 + HMR q21 b387 + CZ q10 q11 if b387
a[3403]      HMR q21 b61                         → 删除（已提前）
```

即 **HW-26 = e46 的改写 + 额外的 measure-out（q10·q11 借 q21 中转后测掉）**，
1,551 → 1,550。两者不能叠加，只能二选一，而 HW-26 严格更便宜 1 个 Toffoli。

---

## 3. 46Q 是怎么来的：stage / peak 账本

生成器源码在 `syed3000/vqcc-own-circuit-portfolio` 的 `invsqrt_source_zip`
（2,563,106 B；解包 561 个文件、19 MB）。构建链：
`build.sh` → `tools/build_variant.py`（`builder.set_max_qubits(Q)`，超宽即抛异常）
→ `tools/pipeline.sh`（held-AND / affine / Z 合并的全域机械 pass + 精确全域证明）
→ `agents/composer/post_inplace.sh`。`src/patches/PATCH_ORDER.txt` 末尾写死 `Q 46`。

`src/work/c10/narrow/arithmetic_round2/native/candidate10/COMPLETE_GATE.json` 里有 **Q48 时代的
peak ledger**（这是唯一公开的分阶段宽度账本）：

| stage | data owners | scratch ≤ | peak |
|---|---|---:|---:|
| normalization | input 22 + flags 4 | 20 | 46 |
| consuming_root | 22 + 4 | 13 | 39 |
| first_loader | root 12 + residual 10 + flags 4 + D 13 + H 3 | 6 | **48** |
| first_coefficient | + snapshot 1、H 5 | 3 | **48** |
| product_forward | root 12 + word 16 + flags 4 + D 13 | 3 | **48** |
| phase_endpoint_and_divider_inverse | root 12 + remainder 14 + history 13 + flags 4 | 5 | **48** |
| second_loader | retained_root 8 + product 15 + flags 4 + D 13 + H 3 | 5 | **48** |
| second_coefficient | retained_root 7 … | 3 | **48** |
| inverse_product_after_v3_retirement | retained_root 6 + word 16 … | 5 | **48** |
| v3_restoration | 7 + 16 … | 0 | 44 |
| coefficient_inverse | 7 + residual 10 … | 5 | 45 |
| root_decoder | restored_root 12 + residual 10 + flags 4 + A 13 + H 5 | 0 | 44 |

Q48 → Q46 是**两轮"每阶段同时 −1"**，由 13 个 patch 模块完成（每条都在 docstring 里写清了
它省的是哪根线）：

| patch | 省的线 | 代价 |
|---|---|---|
| `patch_fwd_narrow.py` | normalization 局部峰 46 → **37**（奇数前缀测掉重算） | 0 Toffoli（同 18+1+32） |
| `patch_w47_body.py`（MICRO47） | `a6 = v[11]` 在 prepare_H3_initial 后立刻 X 测，跨第一系数 forward/seed/product forward 都不在（coef1 的第 46 根线余量） | 0 |
| `patch_coef2_q46.py` | 第二次系数 forward 把 D12 测掉（`D12 = H4^H3^D11·H3`），事后 1 个 Toffoli 重建 | **+1 Toffoli** |
| `patch_proddisp.py` / `patch_coefdisp.py` | 前向每行的 rounding carry 提前释放（disposable carry） | 0 |
| `patch_seedinv.py` | v0/v1/v3 跨整个 inverse product 退休，用 3 条 seed 行的逆恢复 | 0 |
| `patch_h2ret.py` | H2 跨 inverse product 退休，3-AND 精确重建 | +3 |
| `patch_hret_sat_s15k7a.py` | divider cleanup：history signs 13..15 在 phase endpoint 后退休，逐条按 SAT-AND 程序重建；cap=46 时末行 j12 走自适应 inverse_add | 少量 |
| `patch_endpoint_v9e2.py` | endpoint 把 root bit **v9** 也跨 walk8 退休（v10 用 v9 程序的 1 个 AND 重建） | 少量 |
| `q46_loaders.py` / `patch_ld_first20_56b8.py` / `patch_second46_c19_70nb1.py` | loader work cap 20 / 19 → 两个 loader 峰 46 | loader 由 56+70（128 行表）降到 **27+29**（64 行表） |

**结论：46 不是"平均宽度"，是 7 个 stage 同时钉在 46。**
要拿 Q=45，必须让 first_loader / first_coefficient / product_forward / second_loader /
second_coefficient / phase_endpoint+divider-cleanup / inverse_product **同时**各让出 1 根线，
而且每个都要一个新的精确重建程序。

顺带一个结构性下界：root 之后 22 根 x 线变成 (v 12, h 10)，这是一个**双射**（v+h 就是 x 的
另一种基），任何一根都不可退休；工作集最低是 D13 + H3 + flags4 = 20。所以
**Q ≥ 42 是结构下限**，现在的 46 里只有 4 根是加法器/进位开销。理论上 Q44 可及，
但每根的价格就落在下面这个数字上。

### 3.1 已发射电路的实测宽度轮廓（本机静态，非模拟）

`1ba197b0`：23,894 ops，其中 **18,559 ops（77.7%）恰好 46 根线同时在用**，
且是**一整段连续区间**（op 2364 → 20922），不是散点。`e46d90c3` 同形（18,542，2364→20905）。
这说明"峰值段"占全电路 3/4，不存在"只在几个 op 上冒一下"的便宜修法。

### 3.2 公开的 Q45 三次尝试（同一结论，量化更强）

`asteriospanoras/qcc-27-30-what-works-what-fails-and-why`（2026-11-14）：

- `321aff83` 在 46 根线共 8,137 ops / 485 段；精确重调度（消 swap、重命名经典位、
  提前 437 个测量）压到 1,792 units / 261 段，**其中 257 段由交替进位加法器的进位线打开**。
- in-place adder 要 **+257 Toffoli**；`4560ac0c` 上最便宜的精确覆盖（rebuild + 单进位加法器）
  要 **+196**。
- 把 63 个输入才触发的 rare shift flag 藏进空闲线的仿射奇偶：**0 个候选**。
- Q47 时"保留乘积"的精确打包：46 根线保留 0 个，47 根线保留 2 个（每根线值 38 个 Toffoli，
  完全不划算）。

**我的独立复核与之一致**（本机静态，未跑模拟）：严格 dead-write 扫描
（窗口 = 上一次 HMR 到本次 HMR；把 `Z_POW`/`NEG` 视为对该线的读取；控制位/CZ 视为读取；
不跳过输入寄存器线）在 `e46d90c3`、`1ba197b0`、`321aff83` 上都是 **0 处**。
把 Z_POW 当"非读取"时会跳出 8 个窗口（全部是 q21 的旋转累加 gadget，ops 8063–8295），
那 8 处都靠 `Z_POW q21 θ` 把值变成相位，**不可删**——这正是 asterios 说"旧窥孔扫描漏掉
输入寄存器线才找到 1 处"的同一类误判。

---

## 4. T 侧逐项（每个杠杆的单价已算成 GM）

单价（以 GM 27.306613、C = 1711.294 为基准）：

| 动作 | 成本变化 | ΔGM | 备注 |
|---|---:|---:|---|
| −1 无条件 Toffoli | −46 | **+0.00532** | = HW-26 的全部价值 |
| −1 条件 Toffoli（1/2 执行） | −23 | +0.00266 | 把 Toffoli 变成 HMR 条件门 |
| −1 rotation | −322.4 | **+0.03718** | 每个 7.0095 T-eq |
| −1 qubit（46→45） | −1711.29 | **+0.20079** | 盈亏平衡 = 38 个 Toffoli |
| 46→44 / 43 / 42（0 Toffoli 代价） | — | +0.4076 / +0.6208 / +0.8407 | 纯理论 |

### 4.1 表行数 64 → 32：不可行

64 行表 = 6 个地址位 + 13 intercept + 7 slope 位，两个 loader 合成 27 + 29 = 56 Toffoli
（原 128 行版 56 + 70 = 126，这正是 78,765.6 vs 80,162.7 的来源）。
32 行把线性插值段长加倍 → 插值误差 ∝ h² 变 4×。当前 margin 只剩 ≈20%（1.2e8 / 621.1e6 units），
4× 直接越界。要补回精度得多跑一次 Newton 细化 ≈ **+230 Toffoli**，净 −20 + 230 = **+210（GM −0.9）**。
反方向 128 行也只省不到一次 Newton，且 loader 涨回 +70。**64 行是局部最优。**

### 4.2 旋转/相位折叠：不可行

33 个旋转的相位是精确的二进制阶梯 `2⁻⁴, 2⁻⁵, …, 2⁻³⁶` turns（本机枚举，见下表节选），
这就是输出精度的位数，不是可压缩的冗余：

```
q21 2^-4 … 2^-2 (clifford)   q21 2^-3 (T)   q26 2^-17   q30 2^-36 = 1.4815e-11 turns
```

- 最小权重 `2⁻³⁶ turn = 2.685e8 units`，是 margin（≈1.2e8）的 **>2×** → 删任何一个都越界。
- 公开 LP 重拟合（相位对角度是线性的，所以是精确 LP）：在 `4560ac0c` 上只值
  `116,291,417 → 116,320,642`（cost −0.08），在 `9c708f7b` 上只值 2 units。
- "删一个再重调其余"：32/33 infeasible；唯一 feasible 的那个反而变成 **79,369.55**（比 78,765.26 贵）。
- 没有任何旋转落在条件块里（本机核对：38 个 Z_POW 中 0 个在 PUSH_CONDITION 内），
  所以也不存在"让旋转只执行一半"的空间。

### 4.3 Divider 578：结构已到位

`candidate10` 的逐组件 Toffoli 账（`COMPLETE_GATE.json`）：normalization 94.75、root 192、
**divider 578**、product 228.5、coefficient 118、seed 17.5、first/second loader 61+79、
shared cleanup 9、phase endpoint 139，合计 1,548.75（Q48 版）。
divider 占 static 的 37%，是最大单块。但它是"22 位被除数 / 12 位除数 → 12 位商"的
逐位多项式商，578/12 ≈ 48 Toffoli/位；换成 Newton 倒数需要一次 ≈24 位乘法（≈576 AND，
比整个 16×16 product 228.5 还贵 2.5×）再加修正，**不可能更便宜**。这和老 62Q 线
"Newton-CORDIC 4.8×–28× 超预算"的结论一致。

### 4.4 measurement-based uncompute：已用尽

1,279 个 HMR、709 组条件相位、142/1,550 的 Toffoli 已经是条件门（这就是 static 1,550 →
mean 1,478.75 的全部来源，正好 142/2 = 71.25）。严格 dead-write 扫描 0 处（§3.2）。
唯一已知的剩余模式（measure-out，需要一段空闲线）已被 HW-26 用掉。

---

## 5. 候选清单与期望分数（按性价比排序）

| # | 动作 | invsqrt cost | GM | ΔGM | 风险 | 工作量 |
|---|---|---:|---:|---:|---|---|
| A | 换成 `1ba197b02771`（HW-26） | 78,673.57 | **27.31193** | **+0.00532** | 极低（作者已 PASS） | 一次 notebook |
| B | Q=45，补价 0 → 38 Toffoli | 77,008.24 → 78,718.24 | **27.50740 → 27.30676** | **+0.20079 → +0.00015** | 高（公开 3 次失败，最便宜覆盖 +196） | 数周生成器工作 |
| C | 32 行表 + 一次 Newton（净 +210 T） | 88,379.53 | 26.27311 | −1.03351 | 高 | 数周（重拟合 + 重新证明） |
| D | 再删 1 个旋转 | 已证不可行 | — | — | 公开：删一个再重调 = 79,369.55（比 78,765.26 贵） | — |
| E | Q=45 按公开 +196 落地 | 85,828.24 | 26.53090 | −0.77572 | — | 不要做 |
| F | Q=44/43（0 代价，仅供定级） | 75,296.94 / 73,585.65 | 27.71423 / 27.92743 | +0.40762 / +0.62082 | 需每个 stage 都让线 | — |

A 是**唯一确定为正**的动作，但它只有 +0.005 GM（公开榜上大概是 0.005 分，不是 0.05）。
B 是唯一 ≥0.1 的杠杆，但按现有证据 P(GO) 明显低于 10%，EV 量级只有 +0.01~0.02。

---

## 6. 推荐的单一 Kaggle 实验：`INV-45C`（分配器级 Q45 判决 + 第一次让线）

**为什么是这个**：Q=45 的 +0.20079 GM 是整个 portfolio 里最大的单点杠杆
（对照：化学 1 个 qubit = +0.078，DQI 1 个 qubit = +0.038）。
公开结论（+196 / +257）是在**已发射电路**上做的重调度估算，它看不到 builder 的
"这根线的用途"和"此刻有没有脏线可用"，因此既可能高估（有免费的 dirty borrow）
也可能低估。一次 build 就能把这个不确定性消掉，成本是一个 notebook。

### 6.1 输入（全部有 hash / 版本）

| 输入 | 用途 | 关键 hash / 大小 |
|---|---|---|
| competition data（`kickmix/` + `verifiers/`） | build.sh 必需，且会校验 host 文件 | `kickmix.so` sha `c66b3216c4029e0cdfd09054306aa0feadf53ab2f50c1164e37f752874e5005e`；`verify_submission_invsqrt.py` sha `ddef520dec6b68d1cf0a6f328ddd36d79eb84570b9192cf3f7acaf073f06733a` |
| `syed3000/vqcc-own-circuit-portfolio` | `invsqrt_source_zip` | 2,563,106 B；重建出 `321aff83…35177` |
| `manwithacat/vqcc-hedge-wizardry` | 对照件 `circuits/invsqrt/1ba197b02771.kmb` | sha `1ba197b027713aac164056d12505c87f286c3fcd94f403c522073325763bf2f9`，198,631 B |

### 6.2 步骤（CPU、internet off、一次会话）

0. **工具链回归（必过）**：按原样 build（`PATCH_ORDER.txt` 里 `Q 46`），断言输出
   sha256 = `321aff83636214196daa9cbc9dcc9c5e12a155bcff8d9989e98b8cee40935177`。
   这一步证明源码树、host 文件、Python 3.13 环境都对；不通过就停。
1. **加一段 10 行插桩**（不改任何 pinned 源）：在 `build_variant.build()` 里
   `monkeypatch builder.alloc_qubits / free`，记录 `(调用序号, count, 当前 allocated 数,
   调用栈里的 patch 模块名, CUT_HOOK 最近一次 label)`；并把 `set_max_qubits` 临时设为
   `float('inf')` 之外的"软上限"：超过 45 时**不抛异常**，只记一条 `over` 事件并继续。
   这样**一次 build 就拿到全部超宽点**，而不是每改一处重跑一次。
2. **cap 放宽到 45 跑一次**，输出 `q45_census.json`：
   - 每条 over 事件的 stage / 超宽根数 / 是谁申请的；
   - 该时刻是否存在"脏线"（allocated 但 owner_trace 已无 live reader）→ 可 0 代价借用；
   - 该时刻是否存在"可在别处重建的 live 值"（用 `agents/composer/p/*.json` 同款 SAT-AND 形式的
     最便宜重建价；`src/tools/minand_sat.py` **未随源码发布**，需要按
     `agents/normroot/q47_t2_rewrite.json` 的格式自己写一个最小 AND 搜索，k ≤ 4 的
     exhaustive/DP 即可）。
3. **判决行**：`Σ(每 stage 最低总补价, 含 loader work cap 降 1 的 Toffoli 涨价) ≤ 38 ?`
   - `≤ 38` → GO：按 §6.3 建 Q45 候选，成本落在 **77,008.24（补价 0）… 78,718.24（补价 38）**，
     GM **27.50740 … 27.30676**（补价越接近 38，收益越接近 0）。
   - `> 38` → **NO-GO，永久关闭 invsqrt 宽度线**，把 census 归档进本目录。

### 6.3 GO 分支的验证计划（唯一允许的验证口径）

1. `bash build.sh` 自带：全域精确证明必须返回
   `PASS_EXACT_NATIVE_TEXT_ALL_REQUESTED_INPUTS_ALL_HMR_TRANSCRIPTS`
   （3,133,452 输入 × 全部 HMR transcript，1,268+ measurement variables）。
2. 官方 verifier 原样、默认 batch：
   `python verifiers/invsqrt/verify_submission_invsqrt.py <kmb>`（200,540,928 shots，2 个 salt：
   默认 + `s1`）。要求 `PASS` 且 `score ≤ 78,719.53`（哪怕只低 1）。
3. 只有 1+2 都过，才进 `submissions/`；不进 main 之前不写"已验证"。

### 6.4 预期与 EV

| 分支 | 概率（按公开证据估） | 结果 | ΔGM |
|---|---:|---|---:|
| GO 且补价 ≤38 | <10% | 77,008.24 … 78,718.24 | +0.2008 … +0.0002 |
| NO-GO（补价 +196 一类） | ~90% | 关闭宽度线 | 0 |
| EV | | | ≈ **+0.01 ~ +0.02**（不如 A 的 +0.00532 稳，量级同阶且能终结一条线） |

**因此建议并行做 A（换 HW-26，稳拿 +0.005），把 INV-45C 当作"一次会话内给 Q45 定生死"的判决实验，
而不是当作一个高胜率的生产任务。** 如果 INV-45C 判 NO-GO，invsqrt 就只剩 A，之后本任务不应再投入。

---

## 7. 风险

1. **换件重抽**：invsqrt 的 HMR 结果由文件 hash 派生，所以同一文件的成本是确定的；
   换文件 = 换种子 = 换分支抽样。200M shots 下 mean 的抖动约 ±0.001 Toffoli（±0.05 cost），
   不影响 A 的判定；但 e46 → 1ba197b0 的 45.96 差距里没有运气成分（差 1 个 static Toffoli）。
2. **精度余量**：e46/1ba197b0 的 phase margin ≈ 1.26e8 units（worst/tol ≈ 0.80）。
   任何新的测量改写都会动相位；A 不需要改写，安全。任何 Q45 候选都必须重跑全域精确证明。
3. **源码不完整**：发布的 `invsqrt_source_zip` 缺 `tools/minand_sat.py`（宽度工作的核心工具），
   也缺 width2 的其它 hold-set 变体。Q45 的第一步实际上包含"重建这个搜索工具"，工时不能按
   "改一个 patch"估。
4. **公开扫描的时效**：本文件基于 2026-11-14/15 的快照。11-15 之后若有新公开件，
   先按 §2.1 的三张表复核，再看是否有 Q<46 或 cost<78,673.57。
5. **不要相信单 salt 的门级搜索**（本仓库已有 FAIL 记录）；任何删门候选要过全域证明，
   不是抽样。

---

## 8. 本次验证范围（明确边界）

- **执行过**：下载公开数据集/notebook 源码；`kickmix` 直读 `.kmb`（Q/op 统计/Z_POW 角度分类/
  条件门计数/live-wire 轮廓）；op 级 diff；静态 dead-write 扫描；成本算式复算（本机 Python）。
- **未执行**：官方 verifier（任何任务、任何 salt）、量子模拟、生成器 build（需 CPython 3.13 +
  Linux `kickmix.so`）、任何 Kaggle 提交。
- 因此本文所有 cost / PASS 数字都来自**公开回执或作者本机验证**，不是本机验证结果；
  GM 27.306613 是按使用中的三件成本复算，与 `experiments/frontier/20261115_upgrade/README.md` 一致。

---

## 9. 复现命令

```bash
# 公开最好件（HW-26）
KAGGLE_API_TOKEN=$(cat ~/.kaggle/access_token) ~/.local/bin/kaggle datasets download \
  -d manwithacat/vqcc-hedge-wizardry -f circuits/invsqrt/1ba197b02771.kmb -p artifacts/20261115_invsqrt/hedge --unzip
shasum -a 256 artifacts/20261115_invsqrt/hedge/circuits/invsqrt/1ba197b02771.kmb   # 1ba197b02771…

# 生成器源码（46Q builder）
KAGGLE_API_TOKEN=$(cat ~/.kaggle/access_token) ~/.local/bin/kaggle datasets download \
  -d syed3000/vqcc-own-circuit-portfolio -f invsqrt_source_zip -p artifacts/20261115_invsqrt/syed --unzip

# 静态读（Q / static Toffoli / 条件门 / 宽度轮廓）
.venv/bin/python scripts/inspect_circuit.py artifacts/20261115_invsqrt/hedge/circuits/invsqrt/1ba197b02771.kmb

# 公开件索引
KAGGLE_API_TOKEN=$(cat ~/.kaggle/access_token) ~/.local/bin/kaggle datasets download \
  -d manwithacat/vqcc-apache-public-circuits -f manifest.csv -p artifacts/20261115_invsqrt/mwac --unzip
KAGGLE_API_TOKEN=$(cat ~/.kaggle/access_token) ~/.local/bin/kaggle datasets download \
  -d asteriospanoras/qcc-circuit-atlas -f circuits.csv -p artifacts/20261115_invsqrt/meta --unzip
```

来源链接：

- HW-26：`https://www.kaggle.com/datasets/manwithacat/vqcc-hedge-wizardry`，
  `https://www.kaggle.com/code/manwithacat/vqcc-hedge-wizardry-notebook`（v28）
- 45Q 失败分析：`https://www.kaggle.com/code/asteriospanoras/qcc-27-30-what-works-what-fails-and-why`
- measured-CZ 解释：`https://www.kaggle.com/code/mizeroluckygall/quantum-circuits-one-toffoli-less-in-invsqrt`，
  源：`https://www.kaggle.com/code/asteriospanoras/qcc-27-30-public-frontier-free-cz-fix-in-invsq`
- 46Q builder：`https://www.kaggle.com/code/syed3000/vqcc-own-circuit-portfolio-notebook`（v12），
  源码数据集 `https://www.kaggle.com/datasets/syed3000/vqcc-own-circuit-portfolio`
- 64 行表：`https://www.kaggle.com/code/ahoirg/qcc-submit-verify-and-package`（v028），
  `https://www.kaggle.com/datasets/ahoirg/qcc-portfolio-gm-27-28999`
- 索引：`https://www.kaggle.com/datasets/manwithacat/vqcc-apache-public-circuits`（v125），
  `https://www.kaggle.com/datasets/asteriospanoras/qcc-circuit-atlas`（11-12）

## 10. INV-45C 已启动（2026-11-15，Kaggle CPU）

`qingyu1232/qcc-inv45c-census`。实现方式比计划更简单：`build.sh` 的宽度就是从
`src/patches/PATCH_ORDER.txt` 的 `Q` 行读的

```bash
Q=$(awk '$1=="Q"{print $2}' "$X/patches/PATCH_ORDER.txt")
$PY ... build_variant.py --out "$X/build" --name "${NAME}raw" --Q "$Q" "${ARGS[@]}"
```

所以把 `Q 46` 改成 `Q 45` 就会让 `builder.set_max_qubits(45)`，超宽时生成器直接抛错，
日志会指出第一个超限点及其所在 stage —— 这正是 INV-45C 要的"软上限"行为，不需要自己
写 allocator 探针。

两段构建：

1. **工具链闸门**：`Q 46` 重建，必须得到 SHA `321aff836362…35177`（否则说明环境/版本不对，
   后续结论无效）。
2. **软上限**：`Q 45` 重建。GO 判据不变：若最便宜精确修复的 Toffoli 总和 ≤ 38，
   则 invsqrt cost ∈ [77,008.24, 78,718.24]，GM ∈ [27.307, 27.507]；否则关闭宽度线。

全程在 Kaggle CPU 上跑（kickmix 只有 Linux 版），本机不构建、不模拟。

## 11. 为什么 `Q 46` 仍可能是 45 的（这次要回答的问题）

`PATCH_ORDER.txt` 末尾是 `with q46_loaders.py` + `Q 46`，而 `q46_loaders.py` 里有

```python
assert builder.max_qubits>=spec['peak'] and builder.num_allocated_qubits==spec['entry']
```

即两个 loader 的 certificate 是按 peak 46 / entry 46 写死的。所以 `Q 45` 大概率在
**loader 阶段**就断言失败，而不是在 peak 段。如果确实如此，那么 Q45 不是"重新调度 46 条线"
的问题，而是"重新搜索两个 loader 的 certificate"的问题——这与公开三次尝试给出的
+196/+257 Toffoli 结论一致。本次 build 会把这个判断变成实测。

## 12. 修正：`score ∝ Q²`，Q45 的价值比 §4 表里写的高得多

§4 的表用的是线性近似（"−1 qubit = −1711.29"），但官方公式是 `score = rep · Q² · T`，
Q 是**平方**进入的。以 HW-26（78,673.569，T_mean 1,478.75）为基准重算：

| Q | cost | GM | 相对现值 |
|--:|--:|--:|--:|
| 46 | 78,673.57 | 27.3119 | — |
| **45** | **75,290.16** | **27.7151** | **+0.4032** |
| 44 | 71,981.11 | 28.1334 | +0.8215 |
| 43 | 68,746.42 | 28.5679 | +1.2560 |
| 42 | 65,586.09 | 29.0196 | +1.7077 |

盈亏平衡（Q45 允许的额外 Toffoli）：

```
(46/45)² · (1 + ΔT/T) = 1  →  ΔT = 0.04494·T
T = 1,478.75 (mean) → ΔT ≤ 66.5
T = 1,711.294 (plan §4 的 C) → ΔT ≤ 76.9
```

所以 `Q 45` 只要补价 **≤66 个 Toffoli 就是正收益**（0 补价 → GM 27.715），而不是
§4 写的 38。公开最便宜的精确覆盖是 +196（3× 于盈亏平衡，仍为负），但**余量比原先认为的
宽 1.75×**，这使得"让生成器直接以 45 条线重新发射"这条路的期望值明显上升——
这正是 INV-45C 在测的东西（builder 级 0 补价即 27.715，远高于 27.5）。

## 13. INV-45C 结果：工具链 PASS，但生成器**根本没有 45 线的 body**（实测）

`qingyu1232/qcc-inv45c-census`（Kaggle CPU，COMPLETE）。两段构建都在同一个会话里跑完，
而且比计划预期的 15–25 min 快得多（85 s）：

```
TREE /kaggle/working/inv45/src/invsqrt_source
KSO_SHA match True VER_SHA match True
python3.13: /usr/bin/python3.13
PATCH_ORDER tail: ['with q46_loaders.py', 'Q 46', 'post agents/micro47/scripts/relocate_cs2.py']
==================== q46 Q 46
build: s15k7a at Q46, 26 patch args
generator done (11 s)   pipeline done (63 s)   post pass done (84 s)
proof: PASS_EXACT_NATIVE_TEXT_ALL_REQUESTED_INPUTS_ALL_HMR_TRANSCRIPTS
wall time 85 s
BUILT invsqrt.kmb 321aff83636214196daa9cbc9dcc9c5e12a155bcff8d9989e98b8cee40935177
GATE_Q46 PASS
==================== q45 Q 45
-- q45 rc 1
build: s15k7a at Q45, 26 patch args
Traceback (most recent call last):
  File ".../tools/build_variant.py", line 105, in build
    v, h = emit_body(builder, v, h, flags, ctx.tables, old.divider, ctx.decoder.decode_root, trace=owner_trace)
  File ".../patches/patch_w47_body.py", line 210, in emit_body
    assert builder.max_qubits in (46, 47, 48)
AssertionError
```

判决（这是**结构性**答案，不是推测）：

1. **工具链闸门 PASS**：同一份源码 + 比赛 kickmix 在 85 s 内逐字节重建
   `321aff83…35177`，exact proof 状态 `PASS_EXACT_NATIVE_TEXT_ALL_REQUESTED_INPUTS_ALL_HMR_TRANSCRIPTS`。
   所以下面的失败是真实的宽度限制，不是环境问题。
2. **Q45 在 body emitter 的第一行就断言失败**：`patch_w47_body.py:210`
   `assert builder.max_qubits in (46, 47, 48)`。也就是说生成器只有 **46 / 47 / 48**
   三种 body；**没有 45 线 body 这种东西**。
3. 该文件头自述这三个 body 都是**手写的宽度专用合成**：
   - `Q46 body: retire a6 through the product forward (+1 Toffoli)`、
     `A6_EARLY=True ... This gives coef1 its 46th-wire headroom at zero extra Toffolis`；
   - `Q47 BODY: free h0 packing into the exponent flags + Pro 2 snapshot2 table-cleanup tail`。
   即 46 线的余量**已经被作者用掉**（a6 提前 X-measure 换来的第 46 条线头寸）。
4. 再加上 `q46_loaders.py` 的两个 loader certificate 钉死 `peak 46 / entry 46`
   （`assert builder.max_qubits>=spec['peak'] and builder.num_allocated_qubits==spec['entry']`），
   Q45 需要的是**重新合成一个 45 线 body + 重搜两个 loader certificate**，
   而不是"在现有 46 线排布里找回 ≤66 个 Toffoli 的余量"。

因此 INV-45C 的 GO 条件（`Σ 最便宜修复 ≤ 66`）**无法被满足**：不存在可加价的 46 线排布，
可加价的对象尚未被写出来。这与公开三次尝试的 +196/+257 Toffoli 一致——那些数字也是
"强行从已发射电路里挤"，而不是"生成器原生 45 线"。

**宽度线正式关闭**（除获准开展一次新的 body 合成项目）。补充：构建只要 85 s，
所以一旦有 45 线 body，验证成本很低——瓶颈纯粹是合成工作，不是算力。

## 14. INV-45D：Q45 可能只是"两个省线开关没叠加"（2026-11-15）

重读 `patches/patch_w47_body.py` 的头注释，发现 width 阶梯是**逐个技巧叠加**的：

```
Q48（naive）
Q47 = Q48 + 「把 h0 打包进 exponent flags」(PACK=True)，代价 3 个 Toffoli 解包
Q46 = Q47 + 「a6 提前 X-测量退休」(A6_EARLY=True)，0 额外 Toffoli
```

而**出厂发行的 Q46 body 写的是 `PACK=False, A6_EARLY=True`** —— 两个技巧**没有叠加**，
且 `patch_w47_body.py:210` 硬断言 `builder.max_qubits in (46, 47, 48)` 让 Q45 连跑都跑不到。

如果两个技巧互相独立，那么 `PACK=True + A6_EARLY=True` 就应该给出 **45 线 body**，
代价只是解包的那 3 个 Toffoli。Q45 的盈亏平衡是 **ΔT ≤ 66**，所以 3 个 Toffoli 是白送的：
Q45 在 `T_mean ≤ 1,545` 时 invsqrt cost 75,290 → **GM 27.715（+0.40）**。

已上线 `qingyu1232/qcc-inv45d-stack`（Kaggle CPU），依次尝试并记录每一档死在哪里：

| 变体 | Q | PACK | A6_EARLY | 作用 |
|---|--:|---|---|---|
| A | 46 | False | True | 工具链闸门（必须复现 `321aff83…`） |
| **B** | **45** | **True** | **True** | **叠加，真正要试的那个** |
| C | 45 | True | False | 只打包 |
| D | 45 | False | True | 对照（INV-45C 里死于 body 断言的那个） |

判据：B 能构建出 `num_qubits == 45`，静态 T ≤ 1,550 + 66，且官方 verifier 在 200,540,928 shots 上
PASS；否则记录每一档的断言位置，把"45 线需要新合成"这一结论钉死。

## 15. INV-45D 结果：Q45 现在只差**一条线**，而且是一个具体站点

`qingyu1232/qcc-inv45d-stack`（Kaggle CPU，COMPLETE）。四档变体，逐档原文：

```
PATCH_ORDER tail ['with q46_loaders.py', 'Q 46', 'post agents/micro47/scripts/relocate_cs2.py']
BODY PACK/A6 ['A6_EARLY = True ...', 'PACK = False   # agent loader2: no h0 pack']
====================== q46            Q=46 PACK=False A6_EARLY=True
generator done (18 s)  pipeline done (105 s)  post pass done (141 s)
proof: PASS_EXACT_NATIVE_TEXT_ALL_REQUESTED_INPUTS_ALL_HMR_TRANSCRIPTS
BUILT invsqrt.kmb 321aff83636214196daa9cbc9dcc9c5e12a155bcff8d9989e98b8cee40935177
GATE_Q46 PASS
====================== q45_stack      Q=45 PACK=True  A6_EARLY=True
ValueError: Attempted to allocate more qubits than the maximum.
  allocated: 45  requested: 1  allocated+requested: 46  max: 45
  File ".../engine/fusion/arithmetic.py", line 38, in _compute_carry
    outgoing = builder.alloc_qubits(1)[0]
====================== q45_pack_only Q=45 PACK=True  A6_EARLY=False
（同上，同一个 arithmetic.py:38）
====================== q45_a6_only   Q=45 PACK=False A6_EARLY=True
ValueError: Attempted to allocate more qubits than the maximum.
  allocated: 26  requested: 20  allocated+requested: 46  max: 45
  File ".../patches/patch_ld_first20_56b8.py", line 60, in load_joint16
    available = list(builder.alloc_qubits(cap))
```

**这是一个实质进展，不是又一次"不行"：**

1. 之前（INV-45C）Q45 死在 `patch_w47_body.py:210` 的 `assert builder.max_qubits in (46,47,48)`，
   也就是**连 body 都跑不到**，结论只能写成"没有 45 线 body"。
2. 现在把打包开关叠上去（`PACK=True`）并把断言放宽到 45 后，**Q45 的 body 真的跑起来了**：
   - 对照（`PACK=False`）死在 **loader**：`26 + 20 = 46`；
   - 一旦 `PACK=True`，loader 那关过了（打包确实省下一条线），前进到 **`arithmetic.py:38`**，
     死在"45 已分配、还要 1 条"。
3. 也就是说 Q45 的缺口被定位到**唯一一处**：分段 measurement-carry 加法要一个 `outgoing` carry 线，
   而那一刻 45 条线全满。`_compute_carry` 里 `incoming` 与 `outgoing` 在最后一行
   `cx(incoming, outgoing)` 同时被读，所以**不能**简单共用；需要第三条路线：
   - 再退休一个可从其余活线重建的操作数（作者给 a6 用过的手法：
     `hmr(v[11]); free(v[11]); v[11]=None`，再用 `current-D` 恒等式 1 个 CCX 重建，并用 Z 补 HMR 符号）；
   - 或让 carry 边界的 `outgoing` 落在某个此刻已死的线上。

**因此 invsqrt 的下一件事非常具体**：在 `emit_body` 里再造一个"可重建操作数"的提前退休
（候选是 v[10] / h[9] / flags[3]，判据是它的值可由其余活线在 1–2 个 Toffoli 内重建），
使 `_compute_carry` 那一刻只剩 44 条活线。成功后 Q=45，
盈亏平衡 ΔT ≤ 66，收益 **+0.20（ΔT=66）… +0.40（ΔT=0）GM**。

附带记录：`PACK=True` 的代价是 `unpack_h0` 的 3 个 Toffoli（`patch_w47_body.py` 头注释），
即这条路线即使成功，ΔT 也只有个位数水平，远在盈亏平衡之内。

## 16. INV-45E/F：Q45 的峰值定位到 `product_forward`，并证伪"推迟解包"

### 16.1 INV-45E：body 级 MARK 表把峰值钉在一个阶段

`qingyu1232/qcc-inv45e-marks`（CPU，COMPLETE）。给 `patch_w47_body.py` 的 `_mark` 加一行
`print('MARK', label, live)`，Q=45 + `PACK=True` + `A6_EARLY=True`：

```
MARK body_entry 25
MARK first_table 41
MARK first_coefficient 43
MARK first_metadata_retired 37
MARK seed_ready 44
<crash> arithmetic.py:38 _compute_carry: allocated 45 + requested 1 > max 45
```

即：`seed_ready` 时 **44 条活线**，峰值发生在**紧接其后的 `baseline.product_forward`**
（`patch_proddisp.py`）。此前只知道"死在 `_compute_carry`"，现在知道是**哪一个阶段**。

附带发现：`engine/fusion/arithmetic.py` 受 `INPUTS.json` 的**字节长度锁**
（`arithmetic_variant.check_manifest` → `assert len(raw) == pin['bytes']`），
所以不能直接给 carry 加法打补丁，只能改 `patches/` 下的文件。

### 16.2 INV-45F：为什么"把 h0 解包推迟到 product 之后"不成立（已实测）

观察到 h0 的解包（`unpack_h0_after_seed`）正好发生在 `seed_forward` 与 `product_forward`
之间，等于把打包刚省下的那条线**在峰值前又还回去**了。于是试了推迟：

```
q45_defer   Q=45 PACK=True A6=True DEFER=True
  File ".../patches/patch_proddisp.py", line 45, in product_forward
    builder.cx(q, t)
  TypeError: Expected a q | b | bool | km.array | ... but got control=None
q45_nodefer Q=45 PACK=True A6=True DEFER=False   （对照，复现 INV-45E 的崩溃）
  arithmetic.py:38  allocated 45 + requested 1 > max 45
gate46      Q=46 -> 130 s，SHA 321aff83…，GATE PASS
```

`control=None` 说明 **product 真的读 h[0]**，所以解包不能推迟。这条最省事的思路被实测否证。

### 16.3 Q45 现在到底缺什么（精确结论）

1. Q45 的 body **能跑**（`PACK=True` 让 loader 的 26+20=46 那关通过）；
2. 峰值 = `seed_ready` 的 44 + `product_forward` 自己的 1 条 carry 线 + 1 = 46；
3. 作者已有的退休补丁（`patch_seedinv` v0/v1/v3、`patch_endpoint_v9e2` v9、
   `patch_h2ret` H2、`patch_coef2_q46` D12、`patch_hret_sat_s15k7a` history signs）
   **全部已在 `PATCH_ORDER.txt` 里启用**，没有现成的手法是空的；
4. 所以 Q45 需要**一条新的、覆盖 `product_forward` 的退休恒等式**：某个在 product 期间
   空闲、且可由其余活线在 1–2 个 AND 内重建的 wire。作者造这类恒等式用的工具是
   `tools/minand_sat.py`（`v9_form_e2.json` 就是这么来的：8 输入 SAT 直线程序）。

**这就是 invsqrt 宽度线的真实剩余工作量**：一次 8 输入级别的 SAT 重建搜索，
而不是"再调一个开关"。构建只需 130 s，所以一旦有恒等式，验证成本极低。

## 17. INV-45G：活线集合正式导出（Q45 的候选退休对象与前置条件）

`qingyu1232/qcc-inv45g-wires`（CPU，COMPLETE）把每个 MARK 的 owner → 真实 wire id 打了出来。
Q=45 + `PACK=True` + `A6_EARLY=True` 时：

```
MARK body_entry              25  v=12(w10..w21) h=10(h0=None) flags=4(w22..w25)
MARK first_table             41  + D=13(w34,36,0,30,32,28,35,33,31,29,26,27,37) + H=3(w38,39,40)
MARK first_coefficient       43  v[11]=None（a6 已退休）  H=5(w38,39,40,w44,w21)
MARK first_metadata_retired  37
MARK seed_ready              44  v=11(w10..w20, None)  h=10(w41,w1..w9)  flags=4(w22..w25)
                                 D=13  seed=6(w43,w40,w39,w38,w21,w44)
<crash> arithmetic.py:38  _compute_carry  allocated 45 + 1 > 45
```

关键事实（这是判定任何 Q45 方案所需的形式化结果）：

1. `product_forward(builder, D, seed, h)` 的签名与实现**只读 `D`、`seed`、`h`**
   （`patch_proddisp.py`：`word = list(seed) + list(h)`，`C = [False] + list(D)`）。
2. 因此在 `product_forward` 整个执行期间，**`v` 的 11 条与 `flags` 的 4 条共 15 条线完全空闲**。
   峰值 44 + product 自己的 1 条 carry + 1 = 46 > 45，缺的就是这 1 条。
3. 但 `seed_ready` 之后紧接着的分段 carry（`_compute_carry`，在 `engine/fusion/arithmetic.py:38`，
   受 `INPUTS.json` 字节锁保护，不能改）**立刻**就要第 46 条，所以空闲的 v 必须在
   **product 之前**退休、在 **divider 之前**（`divider_module.compute_phase_cleanup(builder, v, P, flags)`
   会读 v 和 flags）重建。
4. 现成的重建先例只有 a6：`a6 = D10^D11^D12^(D10^a5)(D11^a5)`，用 **v[10]** 和 D[10..12]，
   1 个 CCX + 2 个 CX（`patch_w47_body.py:249-256`），"exact on all 4096 roots"。
   注意它**依赖 v[10] 存活**，所以 v[10] 自己不能当候选。

## 18. Q45 的真正阻塞：作者的重建搜索工具没有随源码发布

作者造这类恒等式用的工具是 `tools/minand_sat.py`（`patch_endpoint_v9e2.py` 头注释明确引用
`tools/minand_sat.py` 与 `agents/composer/p/v9_form_e2.json`：8 输入、SAT 求出的直线 AND 程序）。
但本仓库的 `src/tools/` 里**只有**：

```
audit_affine.py   audit_pairs.py   build_variant.py  env.sh  hold_pass.py
kmsim.py   kmx_to_kmb.py   macrun.py   merge_zpow.py   pipeline.sh   postpass.py   prove_any.py
```

**没有 `minand_sat.py`**。而 `audit_affine.py` / `audit_pairs.py` / `hold_pass.py` 解决的是
**T 轴**（找可被 CX 替代的 CCX、把重算的 AND 积挂在空闲线上），不是"某条线能不能用别的线重建"
这条 Q 轴问题。

所以 Q45 的剩余工作是一次**符号推导**：对 15 条空闲线中的某一条 k，在 GF(2) 上求
`v[k] = f(其余活线)`，要求 1–2 个 AND（最好纯 XOR，零 Toffoli）。这需要
(a) 作者未发布的 `minand_sat.py` + 语义模型，或 (b) 手工推 EEA 的域代数。
本会话拿不到 (a)，(b) 不是能在会话内可靠完成的推导（猜错的恒等式会被生成器自带的
`PASS_EXACT_NATIVE_TEXT_...` exact proof 直接否掉，不会污染提交）。

**结论：invsqrt Q45 已把"缺什么"压缩到一条可判定的命题——"15 条空闲线里存在一条 1–2 AND 的
重建恒等式"——但证明它需要的工具不在公开源码里。** 构建只要 130 s，一旦有恒等式，验证成本极低。

## 19. INV-45I：仿射重建搜索（全域 3,133,452 输入）——**否定**

用作者自己的 `tools/kmsim.py`（位切片模拟器，官方域 MAX_X = 3,133,452）在 Q46 的真实 kmx 上做：

```
build rc 0   BUILT 291626  321aff8363…  GATE PASS
kmx lines 34812  num_qubits 46
cuts file s15k7araw.build.json  n 24
CUT seed_ready                     instr 5697  live 44
CUT signed_product15               instr 6699  live 44
CUT coefficient_retired_for_divider instr 6712  live 31
ops 34789   quantum wires 46
official inputs 3133452
snapshot at 5697: nonzero wires 45
referenced in the product window (5697→6699, 1,002 ops): 39 wires
IDLE wires 10  ['q14','q15','q16','q17','q18','q19','q22','q23','q24','q25']
none q14 / q15 / q16 / q17 / q18 / q19 / q22 / q23 / q24 / q25
SATURATED 45 live, 10 idle, 0 expressible
```

**结论（实测，不是推断）：**

1. 在 `product_forward` 的 1,002 条 op 里，**真正完全未被引用**的活线是 **10 条**，不是先前按
   owner 数推的 15 条 —— 其中 6 条是 `v` 段（q14–q19）、4 条正是 `flags`（q22–q25）。
2. 对这 10 条逐一做 GF(2) 消元（**把被测线自己排除在基之外**；第一版忘了这一步，
   得到"全部 = 0"的假结果，已修正重跑）：**没有任何一条能表示成其余活线的仿射函数**
   （含常数项，全域 3,133,452 个输入）。
3. 也就是说：**零 Toffoli 重建（纯 XOR）不存在**。剩下唯一可能是 1–2 个 AND 的重建，
   而求这个的工具 `tools/minand_sat.py` 不在公开源码里（§18）。

因此 reviewer 指定的这条判据——"若有仿射重建 => 退休该线 => Q45"——**已按实测关闭**：

```
PASS 条件（仿射）: 存在 w ∈ idle 使 w ∈ span{其余活线} ∪ {1}   -> 实测 0/10
```

## 20. invsqrt 宽度线最终状态

| 路线 | 判据 | 结果 |
|---|---|---|
| Q45 body 存在？ | `patch_w47_body.py:210` 断言 | 叠加 `PACK=True` 后可运行（§15） |
| Q45 差多少 | `_compute_carry` 需第 46 条 | 峰值在 `product_forward`，44 活 + 2（§16、§17） |
| 空闲线 | product 窗口内未被引用 | **10 条**（6 v + 4 flags）（§19） |
| 仿射重建 | 全域 GF(2) 消元 | **0/10，不存在**（§19） |
| 1–2 AND 重建 | 需 `minand_sat.py` | 工具未发布（§18） |

**invsqrt Q45 到此为止**：三条子路线（body / 峰值 / 仿射重建）全部有实测结论，
唯一未测的是"1–2 AND 重建"，它缺工具而不是缺算力。
构建 138 s、官方域模拟数秒，所以一旦补上 SAT 工具，这条路可以在一次会话内跑完。

## 21. INV-45J/K：1-AND 与 2-AND 重建搜索——两条都是 0 命中（全域）

在 `invsqrt_plan.md` §19 的仿射搜索（0/10）之后，把搜索扩到含 AND 的重建恒等式。
两轮都用作者自己的 `kmsim` 位切片值，判定域是**全部 3,133,452 个官方输入**。

### 21.1 INV-45J：一个 AND（reviewer 指定的那一版）

对每条空闲线 w、每一对活线 (a,b)（946 对），检验
`w ⊕ (a&b)` 是否落在其余活线的仿射张成内（含常数项）：

```
build rc 0  GATE PASS 321aff83…
official inputs 3133452   live 45
idle ['q14','q15','q16','q17','q18','q19','q22','q23','q24','q25']
done q14..q25  pairs 946 each
N_HITS 0
```

### 21.2 INV-45K：两个 AND（`w = (a&b) ⊕ (c&d) ⊕ XOR(others)`）

利用「商空间」把 44 万组合压成哈希查找：因为其余活线张成 GF(2) 子空间，
`canon(x⊕y) = canon(x) ⊕ canon(y)`，于是只需把 946 个单 AND 积规范化一次，
再问有没有一对规范化向量异或等于 `canon(w)`。

```
w q14 distinct canonical products 902  -> none2
w q15 902 -> none2   ...   w q24 903 -> none2   w q25 903 -> none2
N_HITS2 0 []
```

### 21.3 三条子路线的合并结论

| 重建形式 | 搜索规模（每条空闲线） | 全域结果 |
|---|---|---|
| 纯 XOR（0 AND） | 1 次消元 | **0/10**（§19） |
| 1 个 AND + XOR | 946 对 | **0/10**（§21.1） |
| 2 个 AND + XOR | 946²/2 ≈ 44.7 万组合（哈希压缩后 902×902） | **0/10**（§21.2） |

也就是说：**在"≤2 个 AND"这个预算内，10 条空闲线没有任何一条可以在 product 期间被安全退休。**
作者造 v9 用的那类恒等式（8 输入、多级 AND 直线程序）是 ≥3 个 AND 的量级，
既超出本轮判据，也超出可枚举范围（组合数按阶乘增长），必须靠 SAT 求解器。

**invsqrt Q45 到此正式结束**：body 可运行（`PACK=True`）、峰值定位（`product_forward`）、
空闲线 10 条、0/1/2-AND 重建全部为 0 —— 四件事都是全域实测。
官方 200,540,928-shot 验证器**从未运行，因为 Q45 从未构建成功**；
按"不把未执行的验证写成通过"的约定，这里如实记录为**未验证**，而不是失败或通过。

## 22. 本会话在 invsqrt 上的最终账

- 已交付并保持的最好件：HW-26 `1ba197b02771`（46Q，78,673.569，比公开件 78,719.526 好一个 Toffoli）。
- 研究驱动的净增量：**+0.00532 GM**（27.30661 → 27.31193）。
- Q45（+0.20…+0.40）需要 ≥3-AND 的重建恒等式与 SAT 工具，本轮无法兑现。

## 23. INV-45L：≤3 AND 的 meet-in-the-middle 搜索——仍然 0/10（全域）

`qingyu1232/qcc-inv45l-threeand`（COMPLETE，2,924 s）。因为 `canon` 在 GF(2) 上是线性的
（`canon(x⊕y)=canon(x)⊕canon(y)`），3-AND 搜索被压成一次哈希连接：

1. 946 个单 AND 积的规范形（每条空闲线一次）；
2. 把全部 **40.7 万个** 2-和的 64 位指纹存进字典；
3. 对每个单 AND，查 `fp(target ⊕ c_i)`；
4. 命中者再做全域精确复核。

```
official inputs 3133452  live 45
idle ['q14','q15','q16','q17','q18','q19','q22','q23','q24','q25']
w q14 two-sums 407167 build 277 s -> none3
w q15 two-sums 407164            -> none3
... （q16..q25 同）
SUMMARY [["q14","none3"], ..., ["q25","none3"]]
```

每条空闲线的 2-和空间约 **40.7 万**个不同规范向量，没有一个能再用一个单 AND 补到 target。

## 24. 重建恒等式阶梯：0/1/2/3 AND 全部为 0

| AND 数 | 搜索空间（每条空闲线） | 全域结论 |
|---|---|---|
| 0（纯 XOR） | 1 次消元 | **0/10** |
| 1 | 946 对 | **0/10** |
| 2 | 44.7 万对（哈希压缩 902²） | **0/10** |
| 3 | 40.7 万 × 946（meet-in-the-middle） | **0/10** |

10 条空闲线（q14–q19 = 6 条 `v`，q22–q25 = 4 条 `flags`）在**≤3 个 AND**的重建预算内
**没有一条**可以安全退休。作者造 v9 用的 8 输入多级 AND 直线程序属于 ≥4 AND 量级；
而 GF(2^12) 上的自然代数关系（如 a6 的 `D10^D11^D12^(D10^a5)(D11^a5)`）是二次的，
已经被 1-AND 那一档完整覆盖并判空。

**invsqrt Q45 的重建搜索到此终止**：0/1/2/3 AND 四档、全域 3,133,452 输入，全部为负。
Q45 从未构建成功，因此官方 200,540,928-shot 验证器**从未运行**（记为未验证，不是通过/失败）。
