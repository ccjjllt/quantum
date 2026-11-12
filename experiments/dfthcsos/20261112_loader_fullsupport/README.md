# full-support product 型：1 product/bit 不可解（rank 15 封锁），最好情形仍比现状差

2026-11-12 · 分支 `codex/dfthcsos-research` · 工作区 `.worktree/dfthcsos/experiments/dfthcsos/20261112_loader_fullsupport/`

## 结论（先读这段）

1. **「full low support → 1 product/bit → 1,815 T/pass」不成立：product/bit 差 8 倍（8 vs 1）。**
   一个 product（一个 CCX，两个 pivot 各持 `u(r)+v(q)`）对 16×128 ANF 张量的
   **interior（15×127）最多贡献 rank 2**。而真实表每 bit 的 interior rank：
   **k=0 全部 40 bit = 15；k=4 有 32 bit = 15**（另 8 个 bit 的 rank 5 是零填充假象，
   随便填 828 个 don't-care 地址就变 15）。所以**每 bit 至少 8 个 product**
   （k=4 的 8 个 LSB 例外，≥3）。1 product/bit 需要 rank ≤ 2，被直接否证。
2. **最小 product/bit = 8（一般 bit）/ 3（k=4 的 8 个 LSB），不是 1。** 对应单电路
   k=4：295 product 下界 + 75 cache = 370 T/circuit（折算 5,550 T/pass）；k=0：
   320 + 80 = 400（折算 6,000）。**15 电路按各自 rank 求和的下界 = 5,720 T/pass
   → 362.6M（+22%）**。即 full-support 在**最好情形下也比现状 4,089 差 36–40%**。
   实际构造（已做精确多项式恒等式验证）是 k=4 **346 T/circuit**、k=0 **371**，
   15 电路 **6,345 T/pass → 387.6M（+30%）**，比 Maoxin 的 4,089 差 55%。
3. **「1 个 product 覆盖 16 列」这句话本身是对的（已用 kickmix 门级验证）**，但
   「覆盖 16 列 ⇒ 1 product/bit 就够」是错的：16 列不是 16 个独立函数。
   真实系统是 **1,905 个方程的 interior（15×127）对 ~286 个未知数**，不是 16 个方程。
   列计数（⌈16/9⌉=2 或 16/16=1）只数"覆盖"，没数"列与列互相独立"。
4. **顺带把 loader 的真实天花板钉死了**：40 bit × 1,220 地址 = 48,800 bit 的随机表，
   一个 CCX 最多带 2·D bit 描述（D = 工作区可用的多项式 span 维数 ≤ 128），
   D 从 12（1 + 11 个地址位）每个 CCX 长 1 → **每 circuit ≥ 243 个 CCX**（= 3,645 T/pass）。
   Maoxin 平均 272.6，**只剩 ~10% 余量**，对应 **279.5M（−6%）**，不是 −45%，也不是 −17%。
   2,850（247.6M）落在最乐观形式的下界（191 CCX，假设第一个门就有 128 维 span）边缘，
   实际不可达；1,815/2,045 连最乐观下界都过不去。
5. **对三档目标的判定**：1,815（206.1M）✗ 差 8×；2,045（215.4M）✗ 差 ~6×；
   2,850（247.6M）✗ 需要 190 CCX/circuit，低于现实下界 243。**loader 单线现实值
   ≈3,600–3,700 T/pass ≈ 278–282M（GM ≈26.5），不是 247.6M。**
   → 27.0 必须由 shape / C 截断承担，不能记在 loader 账上。

## 1. 计数口径复现（独立重数 `.kmx`，`recount.py`）

对 `artifacts/20261112_loader_re/kmx_maoxin/` 15 个 `.kmx` 逐门重数，与
`20261112_loader_opt/README.md` 的口径逐项对上：

```
k= 0 Q=128 T=292 (cache R=80, products=212) CX=19117 HMR=80 X=234
k= 4 Q=128 T=268 (cache R=75, products=193) CX=13769 HMR=75 X=126
k= 9 Q=128 T=265 (cache R=76, products=189) ...
k=14 Q=128 T=267 (cache R=78, products=189) CX=13565 HMR=78 X=162
TOTAL T/pass=4089  cache=1142  products=2947  CX=217829  HMR=1142  X=2586
T_total = 2*4089 + 6662 = 14840      cost 297.24M（λ_eff = 46.9074）
```

- `T = CCX + CCZ + CSWAP`；cache AND 数 = `R`（init_and 的 reset）数 = `HMR` 数；
  products = T − cache。**1,142 / 2,947 / 4,089 全部复现**。
- λ_eff 精确值 `297,237,077.47/(14,840·427) = 46.9074`（loader_opt 写的 46.9027
  是笔误，差 0.01%，不影响任何结论）。每减 1 T/pass 省 `2·λ·427 = 40,055`。
- **qubit 预算**：`Q = 11 sel + 40 word + 2 pivot + cache`。k=0 的 80 个 cache 里有
  5 个落在借用的 word 顶位（b7⊕b6 技巧），所以 cache 槽位上限 = **75 ancilla + 5 借用
  = 80**。这决定了 full-support 的 11 个 r-monomial 只能和 **69 个 q-monomial** 共存。

## 2. 模型：full-support 型的显式 GF(2) 方程组

地址 `a = 16q + r`，`r` = bit0..3（16 个 monomial `ρ_R`），`q` = bit4..10（128 个
monomial `q_Q`）。一个 pivot 上的"型"是 monomial 的 GF(2) 和；full-support 型是

```
A = u(r) + v(q),    u ∈ F2^16 任意（1 + 4 单 bit + 11 个 pair/triple/quad），
                    v ∈ F2^128 支撑在 cache（69 个）+ 7 个 q 单 bit 上
```

11 个 r-side pair/triple/quad 只需 **11 个 CCX 一次性 cache**，之后任意 `u` 都是
纯 CX（0 T）。输出 bit o 的 ANF 是 16×128 矩阵 `M_o[R][Q]`。一个 product（一个 CCX
`CCX pivotA pivotB target`，A 持 `u_A+v_A`，B 持 `u_B+v_B`）贡献

```
A·B = u_A u_B + u_A v_B + v_A u_B + v_A v_B
    → M += col0(u_A·u_B) + u_A⊗v_B + u_B⊗v_A + row0(v_A·v_B)
```

**interior（15×127）每 product 最多 rank 2**。1 product/bit 要求

```
M_o[1:,1:] = u_A⊗v_B + u_B⊗v_A      （rank ≤ 2）
```

即 1,905 个标量方程对 2×(15+127) = 284 个未知数。**这是强超定系统**，
而实测 `rank(M_o[1:,1:]) = 15`，所以 1 product/bit 无解。

### 2.1 门级语义验证（真实 kickmix，不是 delta 模型）

`product_semantics.py`：7 地址位（4 r + 3 q）、11 个 r-monomial cache、4 个
q-monomial cache，三组 `(u_A,v_A,u_B,v_B)` 在 **128 个地址全表**上比对：

```
u1=0xFFFF v1=010 u2=0xFFFF v2=101: pivotA ok=True pivotB ok=True product ok=True toffoli=16
u1=0xFFFF v1=110 u2=0x0003 v2=011: pivotA ok=True pivotB ok=True product ok=True toffoli=16
u1=0x0003 v1=001 u2=0xFFFF v2=111: pivotA ok=True pivotB ok=True product ok=True toffoli=16
```

结论：**「11 T 一次 cache → 任意 u(r) 免费 → 一个 CCX 输出整个 16 列 × |v| 行矩形」
在门级是真的**。所以任务的假设没错，错的是"覆盖 16 列就能 1 product/bit"。

## 3. rank 实测与最小 product/bit（`fullsupport_solve.py` / `limits.py`）

| 量 | k=4 | k=0 |
|---|---|---|
| `rank M_o`（16×128） | 16（32 bit）/ 6（8 个 LSB） | 16（40 bit） |
| `rank M_o[1:,1:]`（interior） | **15**（32 bit）/ 5（8 个 LSB） | **15**（40 bit） |
| 零填充换成随机填充后 | 全部 15 | 全部 15 |
| 最小 product/bit（= ⌈rank/2⌉） | **8** / 3 | **8** |
| Σ 下界 products | **295** | **320** |

- **8 个 LSB 的 rank 5 是零填充假象**：把 828 个 don't-care 地址随机填，
  k=4 的 40 个 bit 全部变成 rank 15。所以不要指望"LSB 特殊"。
- 40 个 bit 的 Hamming weight 都在 541–653/1220（≈50%），**没有稀疏 bit 可捡**。
- 该 rank 界与 cache 无关，只依赖"型 = u(r)+v(q)、product = 两个型相乘"，所以
  **对任何 q-cache 选择都成立**。
- 模型边界（不算漏洞）：若 cache 里放**混合 monomial**（`ρ_R·q_Q`，跨 r/q），型的 ANF
  矩阵不再是"轴支撑"，一个 product 理论上可贡献 >2 rank。但每个这样的 monomial 要
  1 个 AND 且只买 ≤1 个 rank-1 项，而一个 product 花 1 个 T 买 2 个 rank-1 项 + 2 个轴项
  ——严格更差。所以混合 monomial 只会把下界变成 `⌈(rank−m)/2⌉ + m`（m = 混合 monomial
  个数），不可能把 15 降到 2。

## 4. 构造性分解（精确验证）与它的可行性

把 interior 做 GF(2) 秩分解、两两配对成 product，再用 1 个 product 修 col0/row0
（`u_A = 1, u_B = p, v_B = q` 一次给出任意 p 到第 0 列、任意 q 到第 0 行）：

```
k=4: products [4,9,9,9,9,9,9,9] ×5 组 = 335，+11 r-cache = 346 T/circuit   verified=True
k=0: products 9 × 40 = 360，            +11 r-cache = 371 T/circuit   verified=True
```

`verified=True` = 在 **2,048 个 monomial 上逐系数相等的多项式恒等式**（不是抽样）。

**但这条构造不可直接落地**：它用到的 q-monomial 平均 127 个/bit（128 个几乎全用），
而 cache 只有 69 个槽位。所以 346/371 是**该构造的 T 下界**，真实可行电路只会更高。
这进一步巩固 no-go，不影响结论方向。

**15 电路投影**（`limits.py`，同一个构造器，全部 verified）：

| k | 0 | 1 | 2 | 3 | 4–9 | 10 | 11 | 12 | 13 | 14 |
|---|---|---|---|---|---|---|---|---|---|---|
| products | 360 | 360 | 360 | 360 | 335 | 333 | 335 | 335 | 332 | 335 |
| T/circuit | 451 | 441 | 441 | 441 | 416 | 414 | 416 | 416 | 413 | 416 |

```
TOTAL 6,345 T/pass  →  T_total 19,352  →  cost 387.6M（+30.4%）
```

（表里的 cache 取 k=0 用 80（含借位）、其余用 70 q + 11 r，共 81 槽——比 80 槽预算
多 1 个，对 T 的影响 ±1，不改变任何结论。）

## 5. 到底还能不能到 2,850 / 2,045 / 1,300

用信息计数（软界，非定理）：40 bit × 1,220 地址 = **48,800 bit**，表是随机的
（rank 15/16、weight 50%、无重复结构）。一个 CCX = 一对工作区多项式之积，
每边是 span（维数 D ≤ 128）里的任意元素 → **每门 ≤ 2D bit 描述力**。span 从
12（1 + 11 地址位）起、每个 CCX 长 1：

| 假设 | 每 circuit CCX 下界 | T/pass | cost |
|---|---:|---:|---:|
| span 一开始就满 128 维（不现实） | 191 | 2,865 | 248.2M |
| span 12→128（真实冷启动） | **243** | **3,645** | **279.5M** |
| Maoxin 实测（平均） | 272.6 | 4,089 | 297.2M |

即 **loader 自己的余量 ≈ 10%**，落点 278–282M。三档目标：

| 目标 | 需要 CCX/circuit | 判定 |
|---|---:|---|
| 1,815（206.1M，full-support 的原目标） | 121 | ✗ 低于下界 2×，且 full-support 实测 6,345 |
| 2,045（215.4M） | 136 | ✗ 低于下界 1.8× |
| 2,850（247.6M，GM 27.0） | 190 | ✗ 低于现实下界 243；只在"span 一开始就满 128 维"的乐观界内，实际不可达 |

唯一没被 rank 论证封锁的出路是**型里携带非地址多项式**（已算出的输出位 / b7⊕b6 flag）
——那正是 Maoxin 已经在用的 stateful 字典，它把 product/bit 压到 4.8：k=4 用 268 个 CCX
（75 cache + 193 product），比计数下界 243 只多 25 个。

## 6. 验证范围（严格区分）

- **做了**：15 个 `.kmx` 独立重数（4,089 / 1,142 / 2,947 / 217,829 / 2,586 全对上）；
  k=0 与 k=4 的 40 个 bit 的 ANF 16×128 张量与 rank（零填充 + 5 次随机填充）；
  显式 GF(2) 系统的 1-product 判定；**构造性分解在 2,048 个 monomial 上的精确
  多项式恒等式验证**（k=0、k=4 全部 80 个 bit，`verified=True`）；
  门级语义的 **kickmix 真实 stateful 仿真**（128 地址全表、纯 X/CX/CCX，pivot 与
  product 三项全对）；15 电路的 T 投影。
- **没做**：没有构建 15 电路候选（模型最好情形 4,215 T/pass、实际构造 6,345，都劣于
  现状 4,089，按约定不构建、不跑 kickmix 全量 words、不跑 78,080 shots）；
  没有跑官方验证器；没有提交 Kaggle；没有 push。
  因此 §5 的 191/243 是**软计数界**，§3 的 rank 15 是**对给定扩展的定理**，
  don't-care 自由度下的 rank 下界 10 是**维数计数（generically empty，非定理）**。
- **口径说明**：§4 的 346/371 是"构造+"，其 q-cache 需求（127）超过 69 槽位，
  所以它是该构造的**下界**而不是可落地电路的 T。§3 的 5,550/6,000 同理是下界。

## 7. 文件

```
experiments/dfthcsos/20261112_loader_fullsupport/
  README.md              本文
  recount.py             15 个 .kmx 独立重数（复现 4,089 / 1,142 / 2,947 与 λ_eff）
  fullsupport_solve.py   显式方程组：ANF 16×128 张量、rank、秩分解配对、col0/row0 修正、
                         2,048 个 monomial 上的精确恒等式验证
  limits.py              (a) don't-care 随机填充的 rank / (b) 维数计数 / (c) 信息计数下界
                         / (d) 15 电路投影 / (e) 三档目标 / (f) bit 权重 / (g) 最好情形
  product_semantics.py   kickmix 门级语义验证：full-support 型 + 一个 CCX = 16 列矩形
```
无大产物，无 dump。

## 8. 一句话给决策层

**full-support 是死路：表在 (r-monomial, q-monomial) ANF 基下是满秩随机的（rank 15），
一个 product 最多贡献 rank 2，所以每 bit 至少 8 个 product，15 电路 6,345 T/pass
（+55%），最好情形也要 4,215（+3%）；而"每电路 ≥243 个 CCX"的信息计数把 loader 的
天花板钉在 ~3,645 T/pass ≈ 279M（−6%）。27.0（247.6M）不要再记在 loader 账上。**
