# Maoxin loader 的 T 上限：gate-level 可删 ≈ 0%，两篇 QROM 新构造在 (N=1220, b=40, Q≤128) 下不可映射（no-go）

2026-11-12 · 分支 `codex/dfthcsos-research` · 工作区 `artifacts/20261112_loader_opt/`

## 结论（先读这段）

1. **gate-level 扫描：可删 T = 0（实测），不是 5%，是 0.0%。**
   重复 monomial、重复 product、同型 product 合并、常数控制、相邻 CX 抵消
   —— 六类全部**精确为 0**（不是"没找到"，是逐电路计数为 0）。唯一看起来可删的
   两类（"零效应 CCX" 51 个、"未被读取的 AND" 18 个）**都被真实 stateful 仿真否决**：
   k=4 删 5 个 → `268→263` 但 words 立刻错；k=0/1/13 删 2–4 个 → 同样错。原因是这些
   AND 的控制位带 stateful flag（`b7⊕b6`），在 z=0 的 delta 模型里恒为 0，在
   verifier 的真实路径（z=batch_{k−1} / batch_k）里不为 0。
2. **两篇 QROM 新构造不可映射——而且不是 qubit 不够，是"任何 qubit 数都不行"。**
   本 circuit 的 `N=1,220, b=40`。按论文原始整数公式穷举：
   Q≤128 内最好 **1,048 T/circuit**（dense Eq.9, μ=14, L=4, 56 dirty, Q=107）；
   全局最优 **928**（dense, D=80, **Q=131**）、SelectCopy 最优 **852**（D=160, Q=211）、
   干净 ancilla SelectSwap 最优 **442**；**当前 Maoxin 是 268/circuit**。
   即：Q=128 装得下，但落地后比现状差 **3.9×**。
   原因：Maoxin 不是 flat QROM，是**张量结构 loader**（高 7 位 monomial cache +
   低 4 位 chunk + product），成本 O(#cache + #products)，已经**低于 flat QROM 的
   "每地址 1 T" unary-iteration 下界**（268 < 1,220）。任何 leading term 为
   `N/λ`（λ≥1）的构造都不可能赢它。
3. **杠杆是 2×（`T_total = 2T + 6,662`，见 §7），目标 T：2,850→247.6M（GM 27.0）、
   2,045→215.4M（GM 28.3）。** 在 Maoxin 的型空间里 −50%（2,045）低于
   2 product/bit 的列计数下界（2,250），不可达；现实区间是 3,450（−15.6%，≈271M）。
   唯一可能到 −50% 的方向是把型扩到 **full low support（每 bit 1 product，投影 ≈206M）**，
   需要重新设计分解搜索（§9），不是删门。

## 1. gate-level 扫描（15 个 Maoxin 电路，逐电路精确计数）

数据：`artifacts/20261112_loader_re/kmx_maoxin/`（15 × `.kmx`，Q=126–128）。
总计 `CCX 4,089 / CX 217,829 / R 1,142 / HMR 1,142 / X 2,586`。
本次精化拆分（比 README 的 `cache 1,142 / product 2,947` 更准）：

| 成分 | 数量 | 判据 |
|---|---:|---|
| cache AND（两控制位单 monomial） | 1,082 | `CCX` 到 ancilla 且 `len(ANF(c1))=len(ANF(c2))=1` |
| wide AND（控制位是 flag 型 2 项式） | 51 | 同上，`len>1`（`q18=b7⊕b6` 等） |
| product CCX（打在 word bit 上） | 2,956 | target 属于 word 寄存器 |
| **CCX 合计** | **4,089** | 与 `num_toffoli_like` 一致 |

### 1.1 六类"可删大项"的实测

| 类别 | 上界（构造允许） | 实际可删 | 说明 |
|---|---:|---:|---|
| 重复 monomial（同 mask 多次 cache） | 任意 | **0** | 15 电路 `cache_distinct == cache_count`；无 re-live |
| 重复 product（同 c1,c2,target） | 任意 | **0** | 2,956 个 product 的 `(target, frozenset(c1), frozenset(c2))` 全互异 |
| 同函数 product 在同一 target（XOR 抵消） | 任意 | **0** | `(target, tt)` 分组无 size>1 |
| product 合并（同 usage set + 共享一个控制型） | 任意 | **0** | 807 个"相邻且无 tap"的 pair 中，共享型 = **0** |
| 控制位常数化（const-0 → no-op，const-1 → CX） | 任意 | **0** | 全部 4,089 个 CCX 在真实态下控制位非常数 |
| 相邻 CX 抵消 | 任意 | **0** | 自反 CX / 相邻互逆 pair 均为 0（pivot 用 running-accumulator + `X` 翻转，本身已最省） |
| pivot 复用 | — | 已最优 | 全部 product 只用 2 个 pivot（q126/q127），且用 `CX p1 p2; X p1` 把两个型叠在一个累加器上 |
| cache 共享 | — | 已最优 | 70–80 个 monomial 被 190–212 个 product 复用；无重复项可省 |

**关键否证（真实 stateful 仿真，非 delta 模型）**

- k=4：删 5 个"零效应"CCX → `num_toffoli_like 268→263`，但
  `words_equal=False`（fwd/rev 双向都错）。符号化 delta 重放却报 `same_final=True`
  —— 证明 delta 模型（word 起始为 0）会把这些 flag AND 误判为恒 0。
- k=0/1/13：删 2–4 个"未被读取的 AND" → 同样 `words_equal=False`。

所以：**这 51 + 18 个候选的真实可删数是 0**。gate-level 天花板 = **0 T（0.0%）**。

### 1.2 为什么必然接近 0

- 2,956 个 product 函数在 GF(2) 上**线性无关**（每电路 `rank == count`，如 k=4 的
  `rank=193/193`）。所以**现有 product 池内任何子集都无法少用一个**：每个 product
  都被至少 7 个 word bit 用到（usage 7–31）。
- 要减少就必须引入**新的** product（新的 `A·B`），这已不是 gate-level 手术，而是
  重新做 4×4 low-chunk 矩阵的 rank 分解（见 §3.3）。

## 2. 两篇 QROM 构造的映射判定：不可行（且与 qubit 预算无关）

### 2.1 参数与论文公式

本 loader 每个 circuit：`N = 1,220` 地址，`b = 40` bit（J=5 字 × brot=8），
地址 11 位，可用 workspace `= 128 − 11 − 40 = 77`。论文的 dirty 预算是 `b·λ`
（或 dense 的 `μ·L`）。

**arXiv:2605.20334（SelectCopy + sequential bit packets）**

- SelectCopy：`τ = 2N/λ + 2b(λ−1) + 2λ − 6`，`D = b(λ−1)`
- α 个 sequential packet（Eq. 6）：
  `τ = (1+1/α)N/λ + (b+b/α)(αλ−1) + (α+1)(αλ−3)`，`D = bλ − b/α`
- 有效条件 `N ≫ b²λ²` → 本处 `N=1220`、`b²λ²=1600λ²`，**条件完全反向**，
  所以 subleading 项统治，leading 的 2× 完全拿不到。

**arXiv:2610.02321（dense encoding）**

- dense-only（Eq. 6）：`τ = N/λ + (4b+2)λ − 6`，`D = bλ`
- dense + packets（Eq. 7）：`τ = (1/2+1/2α)N/λ + (α+1)(2b+α)λ − 3(α+1)`
- α=b（Eq. 8）：`τ = ½(1+1/b)N/λ + 3b(b+1)λ − 3(b+1)`

### 2.2 数值（每 circuit 的 T；λ 允许连续取值以求最小值）

| 构造 | λ=1（D=40，**预算内**） | λ=2（D=80，超 3） | λ=4（D=160） | 连续最优 | 最优时 D |
|---|---:|---:|---:|---:|---:|
| 现状 Maoxin v22 | — | — | — | **268** | 77 |
| 裸 unary iteration（无 ancilla） | 1,220 | — | — | 1,220 | 0 |
| 干净 SelectSwap（Low et al.） | 1,260 | 690 | 465 | **442** | 222 |
| SelectCopy（2605.20334, α=1） | 2,436 | 1,298 | 852 | **884** | 160 |
| dense（2610.02321, α=1） | **1,376** | 928 | 947 | **883** | 110 |
| dense + packets α=2 | 1,152 | 940 | 1,204 | **940** | 154 |

要点：

- **预算内（D≤77 → λ=1）最好的是 dense α=2 的 1,152 T/circuit，是现状的 4.3×。**
- **即使给无限 dirty qubits，两篇论文的最优也只有 883/884，是现状的 3.3×。**
- 连"干净 ancilla SelectSwap"的全局最优（442）都比现状差 1.65×。
- 因此：**不是 Q=128 卡的，是 flat-QROM 这个族本身在 (N=1220, b=40) 输给张量 loader。**
  把 268 代回 `N/λ + 162λ − 6 = 268` → `162λ² − 274λ + 1220 = 0`，判别式
  `274² − 4·162·1220 < 0`，**无实数 λ**。SelectCopy 同样无解。

### 2.3 为什么张量 loader 会赢，以及唯一可能的借用点

Maoxin 的成本是 `cache AND + product`，不是 `N/λ`：
`a = 16q + r`（q 高 7 位被缓存，r 低 4 位当"小维度"），product 的乘积本身生成新行
（`m·m' = m∪m'`），一个 CCX 覆盖 2.85 个 rank-1 项。等价说法：**每地址 0.22 T**
（268/1,220），已经打破 flat QROM 的 1 T/地址下界。

唯一有理论价值的借用点是 dense encoding 的"一个 dirty qubit 存 2 个经典 bit"
（Z/X 两个基底）。本 loader 的 cache qubit 必须**同时**作为大量 CX 的控制位
（固定的 computational basis），不能在 X 基底里再存一份；product 的 CCX 也不是
"copy"。所以 dense encoding 无处落地。

## 3. 预算与投影

派生常数：`score = λ_eff · T_total · Q_total`，由已公布基线反解
`λ_eff = 297.237M / ((2·4089 + 6889) · (84+40 + max(303, 128−11−40))) = 46.2007`。
（`heuristic_costs(76, R=5, B=143, C=75, brot=8) = 6,889 T / Q 387`，与既有 README 的 6,889 一致。）

### 3.1 各 shape 在现有 4,089 下的分数

| shape (R,C) | T_heur | Q_total | score @4,089 | 追平 297.237M 所需 T | 到 247.6M 所需 T |
|---|---:|---:|---:|---:|---:|
| **R=5, C=75（当前）** | 6,889 | 427 | **297.2M** | 4,089 | 2,831 (−30.8%) |
| R=4, C=120 | 7,930 | 429 | **319.3M（+7.4%）** | 3,533 (−13.6%) | **2,281 (−44.2%）** |
| R=4, C=100 | 7,133 | 426 | 301.3M | 3,985 | 2,724 |
| R=3, C=120 | 6,741 | 426 | 293.6M | 4,181 | **2,920（最松）** |
| R=4, C=75 | 6,152 | 426 | 282.0M | 4,475 | 3,214 |
| R=3, C=75 | 5,385 | 425 | 266.3M | 4,876 | 3,612 |

（T_heur 与 Q 只取决于 (R,B,C,brot)，B=143 固定；accuracy gate 未验证，纯成本投影。）

**R=4/C=120 单独看是 +7.4% 的负收益**；要靠 loader 先补 22.1M。

### 3.2 R=4/C=120 的公式

```
T_total = 2·T_angle + 7,930
Q_total = 429            # (85+40) + max(304, 77)
score   = 46.2007 · T_total · 429
```
- `T=4,089` → 319.3M
- `T=3,966（−3%）` → 311.7M，仍比当前差 +4.9%
- `T=3,533` → 297.2M（打平）
- `T=3,525（4 product/bit 的现实上限）` → 296.9M
- `T=2,281` → 247.6M（需要 −44%）

### 3.3 loader 的真实上限

每 circuit 的 40 个输出 bit，每个 bit 需要 16 个 low-chunk 列的任意高 7 位函数。
一个 product（两型各带 ≤2 个 r-side monomial）最多覆盖 3×3=9 列，且这 9 个函数是
rank-1 外积。所以：

- **计数下界**：`⌈16/9⌉ = 2 product/bit` → 80 + cache 70 ≈ **150/circuit（2,250 T/pass）**。
  这只在"rank-1 恰好对上"时可取，实际不可达。
- **现实下界（rank-4 4×4 分解）**：4 product/bit → 160 + 70 ≈ **230/circuit（3,450 T/pass，−15.6%）**。
- 现状 4.83 product/bit（193/40）。

即：**loader 的现实区间是 −15.6% 左右（≈296.9M @R=4/C=120、275.0M @R=5/C=75），
到 247.6M 需要 −44%，落在计数下界之下。** 结论：loader 单线封顶 ≈270–297M。

## 4. 验证范围（严格区分）

- **做了**：15 个 Maoxin `.kmx` 的逐门符号化重放与精确计数（`dissect2.py`、
  `usage.py`、`lifetimes.py`、`merge_bound.py`）；k=4 的删门原型用 **kickmix 真实
  stateful 仿真**（1,220 地址 × fwd/rev 两条路径）验证 `num_toffoli_like` 与 words。
- **没做（按约定）**：没有构建完整候选、没有跑 15 电路全量 words、没有跑 78,080 shots、
  没有跑官方验证器、没有提交 Kaggle、没有 push。
- 因此本文件的 0%/no-go 是**局部门级实测 + 解析界**，不是官方结论；
  §3 的分数全部是 `λ_eff·T_total·Q_total` 的投影，accuracy gate 未验证。

## 5. 文件

```
experiments/dfthcsos/20261112_loader_opt/
  README.md        本文
  dissect2.py      逐电路 cache/product/重复/常数控制统计（含 pkl dump）
  targets.py       prefix-tap 分解尝试（模型在 flag 参与时失效，记录于此）
  usage.py         每 word bit 的入向函数多重集、pool rank
  lifetimes.py     AND 生命周期读取计数 + 零效应门定位
  merge_bound.py   "合并两个 product"的上界：相邻无 tap 且共享控制型 = 0
  prototype.py     删门原型 + kickmix 双向 words 检查（k=4 失败，证明不可删）
  rank_bound.py    失败的 rank 下界尝试（union 结构使 rank 不是下界，见 §9）
artifacts/20261112_loader_opt/
  （无大文件；maoxin.pkl 由 dissect2.py --dump 可重建，115MB 已删除，不入库）
```

## 6. 一句话给决策层

Maoxin 的 4,089 已经是**张量结构 loader** 的下界附近（每地址 0.22 T，低于 flat QROM
的 1 T 下界），gate-level 可删 0%、两篇 QROM 新构造在 (N=1220,b=40) 下最优也只有
883/884（3.3× 更差，且与 qubit 数无关）。**loader 单线现实封顶约 −15.6%（270–297M）；
27.0 目标（247.6M）必须由 C 截断/结构改动承担，或由 R=3/C=120 这类 shape 打底
（现 loader 已 293.6M）后再叠 loader 的 −16%。**

---

# 追加（修正后的杠杆与 dense-encoding 精确判定）

## 7. 修正 score 模型：`T_total = 2·T_loader + 6,662`

`heurT = 14,840 − 2×4,089 = 6,662`（此前用 `heuristic_costs()` 估成 6,889，差 227；
以实测 14,840 为准）。反解

```
λ_eff = 297,237,077.47 / (14,840 · 427) = 46.9027
score(T) = 46.9027 · (2T + 6,662) · 427        # R=5/C=75, Q_total=427
```

| loader T/pass | T_total | score | GM |
|---:|---:|---:|---:|
| 4,089（现状） | 14,840 | 297.2M | 25.4 |
| 2,850 | 12,362 | **247.6M** | 27.0 |
| 2,045（−50%） | 10,752 | **215.4M** | 28.3 |
| 1,500 | 9,662 | 193.5M | 29.2 |
| 1,300 | 9,262 | 185.5M | 29.75 |

（与前台给的 215.4 / 193.5 / 185.5 逐项对上。）

## 8. arXiv:2610.02321 dense encoding：精确公式与最小 Q

参数：每 circuit `N=1,220`、`b=40`（J=5 字 × brot=8）、地址 11 位。
可用 dirty = `128 − 11 − 40 = 77`（clean helper ≤7，可复用）。

**公式（论文原文，Eq.6/7/8/9）**

```
Eq.6  dense-only        τ = N/λ + (4b+2)λ − 6                       D = bλ
Eq.7  dense+packets     τ = (½+1/2α)N/λ + (α+1)(2b+α)λ − 3(α+1)     D = bλ
Eq.8  α=b               τ = ½(1+1/b)N/λ + 3b(b+1)λ − 3(b+1)
Eq.9  integer μ,L       τ = (m+1)(⌈N/2L⌉+L−3) + 2L(b+μ)             D = μL
                        m = ⌈b/μ⌉,  L 为 2 的幂
```

**Eq.9 穷举（μ=1..40, L=2,4,…,512）**

| 构造 | μ | L | dirty D | Q_circuit | **T/circuit** |
|---|---:|---:|---:|---:|---:|
| dense Eq.9 | 14 | 4 | 56 | **107** | **1,048** ← Q≤128 最优 |
| dense Eq.9 | 19 | 4 | 76 | 127 | 1,088 |
| dense Eq.9 | 40 | 2 | 80 | 131 | **928** ← 全局最优 |
| dense Eq.9 | 40 | 4 | 160 | 211 | 948 |
| dense Eq.7 | α=2, λ=1 | — | 40 | 91 | 1,152 |
| SelectCopy Eq.6 | α=5, λ=1 | — | 40 | 91 | 1,668 |

结论：

- **Q=128 装得下**（Eq.9 用 μ=14, L=4 只要 56 个 dirty，Q=107），T=**1,048/circuit**。
- **族的最优是 928/circuit，需要 Q=131**（只超 3 个 qubit）。再往上加 qubit 不再改善
  （L=4、D=160 反而 948）。
- 两者都**远差于现状 268/circuit**：1,048 = 3.9×，928 = 3.5×。
  折成 pass 总量：1,048×15 = 15,720（对应 score ≈763M）。
- 原因不是 qubit，是 **Maoxin 不是 flat QROM**：
  - 每地址 **0.22 T**，已低于 flat QROM 的 unary-iteration 下界 1 T/地址（1,220）。
  - 它的数据主要装在 **217,829 个 CX（Clifford，计分免费）** 里：product 的
    `A·B` 一次覆盖 ~52 个 monomial，等于把表压进 Clifford 模式。
  - 论文的有效条件 `N ≫ b²λ²` 在这里反向（1,220 vs 1,600λ²），λ=1 时 subleading
    `(4b+2)λ = 162` 就已不可忽略；`N/λ` 的 2×/4× 提升完全拿不到。
  - dense encoding 的载体是"dirty qubit 的 Z/X 双基底"，而本 loader 的 cache qubit
    必须始终作 computational-basis 控制位（每个 product 的型里同时用到），无法双基底；
    product CCX 是"AND 两个型"，不是 "copy"。**dense 无处落地。**

## 9. loader 的下界：−50% 需要跳出"≤2 个 r-side monomial"的型

**在 Maoxin 实际使用的型空间内（每个型带 0–2 个 low(r-side) monomial）：**

- 每 bit 需要 16 个 low-chunk 列（低 4 位 = 16 个 chunk），每列一个 7 位任意函数。
- 型有 `|S| ≤ 3`（常数 + 2 个 low monomial）→ 一个 product 最多覆盖 **3×3 = 9 列**。
- 列计数：`≥ ⌈16/9⌉ = 2 product/bit` → `40×2 = 80` product + `≈70` cache
  = **150/circuit = 2,250 T/pass（−45%）**。
- 加上 rank-1 一致性（3×3 块的 9 个函数必须是 `a_P·c_Q` 外积），实际要
  **4 product/bit**（4×4 low 矩阵一般 rank 4）→ 230/circuit = 3,450 T/pass（−15.6%）。
- **−50%（2,045 = 136/circuit）在这个空间里低于 2/bit 的列计数下界，不可达。**

**唯一的逃逸口（未证明可行）：把型扩到 full low support。**
若型携带全部 16 个 low monomial（常数 + 4 个单 bit + 6 个 pair + 4 个 triple + 1 个四元，
其中 11 个 pair/triple 需要 11 个 cache AND，一次性成本 11 T），则一个 product 可覆盖
全部 16 列，参数计数为 `s·(k_A+k_B) ≥ 16` → `s=1` 不再被计数排除
（32 个未知高函数 vs 16 个方程）。若真能每 bit 1 个 product：
`70 + 11 + 40 = 121/circuit = 1,815 T/pass` → **score ≈ 46.9027·(3,630+6,662)·427 = 206.2M
（GM ≈ 28.8）**，即超过 −50%。

但这需要解 16 个非线性方程（每列 `h_K = Σ_{P∪Q=K} a_P c_Q`），且反例很强：
**k=0 的 cache 已经包含 r-side pair（README §2.1），仍然用了 212 product = 5.3/bit**。
所以参考实现考虑过低支撑型并仍然需要 4.8–5.3/bit。本时间盒内无法验证 s=1 是否可解，
**这是唯一可能突破 −15.6% 的方向，属于重新设计分解搜索，不是删门。**

顺带记录一个失败的尝试（`rank_bound.py`）：把每 bit 写成 16×128 GF(2) 矩阵求 rank
作下界是**错误**的——列指标是 `P∪Q`（并集），不是 `(P,Q)` 笛卡尔积，多个 (P,Q) 对会
落进同一列并相消，所以 rank 不是下界。实测 k=1..3 rank=7/bit、k=4..8 rank=6–7、
k=9..14 rank=11–14、k=0 rank=16，而实际只有 4.7–5.3 product/bit，正好证明该界无效。

## 10. 结论修正

- 目标从"≥10%"改为"−50% 起步"后：在 Maoxin 的型空间（≤2 r-side monomial）里，
  **−50% 低于 2 product/bit 的列计数下界（2,250 T/pass），不可达**；
  该空间内可争取 2,850（GM 27.0，需 3.0 product/bit）到 3,450（−15.6%，≈271M）。
  两条都必须**重写 product 分解**，不是删门。
- 唯一可能到 −50% 以下的是**把型扩到 full low support（每 bit 1 product）**，
  投影 ≈206M，但需要解 16 个非线性方程，且 k=0 已用 r-side pair 仍 5.3/bit
  是强反例；这是下一个 session 唯一值得投的算法方向。
- dense-encoding QROM 这条线：**Q=128 装得下（Q=107/56 dirty），但 T = 1,048/circuit，
  是现状的 3.9×**；族最优 928 需 Q=131，仍 3.5×。故不可映射。
- 表数据本身也无结构可捡：`angle_words` 75 列、每列 126–245 个不同值、
  无重复列、仅 2.7% 为零，不能靠稀疏/重复省 T。
