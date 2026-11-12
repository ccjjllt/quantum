# 输出基变换（g = B·f）对 loader 的 T 计数是严格零收益：定理 + 真电路实测

2026-11-12 · 分支 `codex/dfthcsos-research` · 工作区 `artifacts/20261112_loader_esop/`

## 结论（先读这段）

1. **no-go，而且是可证明的零收益，不是"搜得不够"。**
   Maoxin 族 loader 的成本恰好是 `T = |products| + |cache monomials|`，正确性条件是
   `span(products ∪ cache ∪ 1 ∪ 地址位) ⊇ V`，其中 `V` 是 40 个输出函数张成的子空间。
   对任意可逆 `B`，`g = B f` 张成的仍是同一个 `V`（`B V = V`），所以**可达的生成元集合
   与目标函数完全相同，最优 T 只依赖 V**。B 只改变"每个 product 扇出到哪些 word bit"，
   而扇出是 CX，本来就不计 T。→ **B 的收益精确为 0。**
2. **实测（k=4 真实 .kmx 重放）**：193 个 product CCX + 75 个 cache CCX，
   193 个 product 全部被使用（usage 7–26/个），40 个输出张成 **35 维**
   （`b7 = b6` 的 signed gauge 给出 5 对相等函数）。对 3 个随机可逆 B，
   `B f` 全部落在同一个 span 里、精确重构、**生成元数恒为 280（193+75+…）**。
3. **在"每个输出独立分解、不共享"的 per-output 模型里 B 也不能改善**：
   interior（15×127）秩在 `V∖{0}` 上**恒为 15**（40 个基片 + 780 个 pair-sum +
   20,000 个随机组合，无一个例外）。所以 `Σ_o ⌈rank_o/2⌉` 对任何 B 都是
   320（k=0–3）/ ≥295（k≥4）；identity 取到 295 是因为 5 个 LSB 的 rank 5，
   而那是**零填充假象**（随机填 828 个 don't-care 后 40 个 bit 全部变 15）。
   随机 B 实测 315–320，只会更差。
4. **真 kickmix 验证了整套方案（语义正确，但更贵）**：`g = B f` 的 loader（395 CCX）
   + 389 个 CX 的恢复网络（0 T），在 1,220 个地址上 `g`、`f` 双向全对
   （`words_equal=True`）。identity per-output 是 375 T，随机 B 是 395–400 T，
   **都劣于 Maoxin 的 268**。
5. **所以 243 CCX/circuit 的 25 个余量一分钱也不在 B 上**：它只能来自重搜 product 集
   （span 层面，即 `20261112_loader_fullsupport` §5 的方向）。loader 仍然是
   **4,089 T/pass → 297.24M（GM 25.4）**，本轮没有候选、没有跑官方验证器。

## 1. 定理：为什么 B 是 no-op

一族 Maoxin 型 loader 由三样东西指定：

```
M  = 被 cache 的 monomial 集合        每个 1 CCX（init_and）
P  = product 函数集合 {A·B}            每个 1 CCX（CCX pivotA pivotB target）
     A、B 是 workspace span 里的任意线性型（cache monomial + 地址位 + flag）
正确性:  V ⊆ span(M ∪ P ∪ {1} ∪ {地址位})       （CX/X 免费）
T      = |M| + |P|
```

输出基变换 `g = B f`（B 可逆）只要求电路实现 `B V`。因为 `B` 是可逆线性映射，
`B V = V`；而 `M ∪ P` 是与输出基无关的**函数集合**（它们作用在地址寄存器上）。
于是：

```
min_{M,P} |M|+|P|   s.t.  span(M∪P∪…) ⊇ V      ← 与 B 无关
```

**同一个生成元集合可以服务任何基**：每个 product 只需把 fanout 的 CX 目标从
`word_o` 改成 `word_{B^{-1} 的行}`。所以 `T*(B f) = T*(f)` 对所有可逆 B 成立。
这正是"CX 免费"的另一面：既然扇出免费，Maoxin 已经在用**任意**输出基了
（实测每个 product 被 7–26 个 word bit 使用），再换基没有任何东西可换。

## 2. 数据：40 个输出函数的空间结构（15 电路）

`basis_rank.py` / `v_struct.py`。地址 `a = 16q + r`，
`r = a&15`（16 个 monomial），`q = a>>4`（77 个 chunk，7 位）；
每个输出 bit 是 16×128 的 ANF 张量 `M_o[R][Q]`（只前 77 个 Q 有定义）。

| 量 | k=0–3 | k=4–14 |
|---|---|---|
| 40 个基片的 interior rank | 40 × 15 | 35 × 15 + **5 × 5**（下标 0,8,16,24,32 = 每个字的 bit0） |
| `dim span(40 个函数)` | **40** | **35**（相等对 `(6,7),(14,15),(22,23),(30,31),(38,39)` = 每字 `b7=b6`） |
| 20,000 个随机非零组合的 rank | 全部 **15**，0 个零组合 | 全部 **15**，0 个零组合 |
| 780 个 pair-sum 的 rank | 15 | 15 |
| bit 权重 / 最大 ANF 度 | 541–653 / 10–11 | 575–655 / 8–11 |

**关键**：`V∖{0}` 上的 rank 是常数 15。rank 5 只出现在 5 个 LSB 上，而那是
**零填充假象**——把 828 个 don't-care 地址随机填（3 次），k=4 的 40 个 bit 全部变成
rank 15（`v_struct` 的 padding 试验）。所以：

- 任何可逆 B 的 40 个像函数都是 rank 15 → `Σ⌈rank/2⌉ = 320`（k≥4 时 ≥295，
  只有原样保留那 5 个 LSB 才能到 295）；
- identity 已经是最优：**k=4 是 295，k=0 是 320**，随机 B 实测 315–320（只会更多）。

（15 电路 per-output 合计 = **4,520 products + 1,200 cache = 5,720 T/pass**，
与 `20261112_loader_opt` §3 的 `per_output l4 full40` 行逐项一致；
Maoxin 的共享构造是 4,089。）

## 3. 真电路的 invariance 实测（k=4，`.kmx` 符号重放）

`invariance_maoxin.py`：

```
angle_k_4.kmx: qubits=128 CX=13769 CCX=268 products=193 cache=75
  word bits = 40, 终态权重 988..1080（从 z=0 的 stateful 路径，非 delta）
  f 在 span(products, cache, 1, 地址位) 中精确表示: unmatched = []
  products 实际使用 193/193（每个被 7–26 个 word bit 使用）
  dim span(40 outputs) = 35    dim span(generators) = 275
  random B #0/#1/#2: g ∈ span(G) = True, 精确重构 = True, 生成元数 280（不变）
```

即：**现有 268 T 的电路已经对任何输出基成立**，换基只需要改 CX 扇出。

## 4. 端到端构造 + kickmix 真实验证（语义正确，成本更高）

`basis_roundtrip.py`（per-output ESOP，lowbits=4，k=4，full 40 bit，1220 地址）：

| 构造 | Q | CCX | 其中 products | cache | CX | 精确性（1,220 地址） |
|---|---:|---:|---:|---:|---:|---|
| identity | 131 | **375** | 295 | 80 | 42,816 | ✅ 自身 g = f |
| 随机 B（满秩随机） | 131 | **400** | 320 | 80 | 47,521 | ✅ 自身 g = Bf；CX 恢复 f ✅ |
| 单位下三角 B（`unitB.kmx`） | 131 | **395** | 315 | 80 | — | ✅ 见下 |

`kickmix_check.py`（**真实 kickmix 模拟器，1,220 地址全表，不是符号模型**）：

```
A. loader for g=Bf: CCX=395 qubits=131 | g 在全部 1220 地址上正确 = True
B. 恢复网络: CX=389  toffoli=0  qubits=51
C. 恢复网络作用在 g 上得到 f = True
D. 其转置网络作用在 f 上得到 g = True
→ real-simulator roundtrip: True   |   loader CCX 395 + recovery 0 T
```

**结论**：B + 免费 CX 恢复在语义上完全成立（这也验证了"CX 免费"这个前提），
但 T 从 375 升到 395–400，方向与目标相反；即使 identity per-output（375）
也远差于 Maoxin 的共享构造（268）。

## 5. 投影

`score(T) = 46.9074 · (2T + 6,662) · 427`（R=5/C=75，已公布基线反解）：

| T/pass | T_total | score | 说明 |
|---:|---:|---:|---|
| 4,089 | 14,840 | **297.24M**（GM 25.4） | 现状，B 不改变它 |
| 3,645 | 13,952 | 279.45M | 需要 243 CCX/circuit |
| 3,450 | 13,562 | 271.63M | −15.6%（product 重搜） |
| 2,850 | 12,362 | 243.6M | 需要 190 CCX/circuit（低于软界） |

- **本轮产物 T/pass 仍是 4,089**（B 零收益），**没有候选、没有跑官方全量验证**。
- 243 的 25 个余量（k=4 是 193+75=268 vs 243）**全部在 product 集合的重搜上**：
  193 → ~168 才能配 75 个 cache 到 243。这与 B 无关；任何在 g 上找到的更省
  product 集合，对 f 同样有效（同一个 span），所以该方向可以继续做，但不要记在 B 账上。
- 附带观察：k≥4 的 `b7=b6` 使有效表只有 **35 bit**（11/15 个电路），若把这个关系
  计入"每 CCX 最多 2D bit"的软计数，243 这个数还会再降 ~12%（≈213–220），
  即真实余量可能比 25 更大——同样全部在 product 搜索里，与基变换无关。
  （这是软界的缩放，不是新定理，未据此改任何投影。）

## 6. 验证范围（严格区分）

- **做了**：
  1. 15 个电路 40×16×128 ANF 张量、interior rank（identity / 随机 B / 780 pair-sum /
     20,000 随机组合）、零填充 vs 随机填充对照（`basis_rank.py`、`v_struct.py`）；
  2. k=4 真实 `.kmx` 的逐门符号重放 + 生成元 span 判定 + 3 个随机 B 的精确重构
     （`invariance_maoxin.py`）；
  3. k=4 的 identity / 随机 B / 单位下三角 B 三条 per-output 电路的构建 +
     1,220 地址精确比对（`basis_roundtrip.py`）；
  4. **真实 kickmix 模拟器**（`km.Simulator`，1,220 地址全表）上 `g = Bf`、
     CX 恢复 `f = B⁻¹g`、反向 `g = Bf` 三项全过（`kickmix_check.py`）。
- **没做**：
  - 没有构建 15 电路候选（B 是零收益，identity 的 per-output 5,720 / 随机 B 更差，
    都劣于 4,089）；
  - 没有跑 78,080 shots、没有跑官方验证器、没有提交 Kaggle、没有 push；
  - 没有搜索 product 集（193 → 168，那是 `loader_fullsupport` §5 的方向，需要另开）；
  - 没有做真正的"official verify"；本文件的 True 全部是 1,220 地址的局部/全表检查。

## 7. 文件

```
experiments/dfthcsos/20261112_loader_esop/
  README.md              本文
  basis_rank.py          40 个 slice / 随机 B / 2,000 组合的 interior rank 直方图
  v_struct.py            dim V、相等对、20,000 组合、零填充 vs 随机填充、bit 权重
  invariance_maoxin.py   k=4 .kmx 重放：193 products + 75 cache，任意 B 的 span 判定
  basis_roundtrip.py     identity / 随机 B 的 per-output 电路 + 精确 1,220 地址比对
  kickmix_check.py       真实 kickmix：g=Bf、CX 恢复、反向，全部 True
artifacts/20261112_loader_esop/
  identity.kmx   k=4 identity per-output，375 CCX，Q=131
  randomB.kmx    k=4 随机满秩 B，400 CCX，Q=131
  unitB.kmx      k=4 单位下三角 B，395 CCX，Q=131（kickmix 三项验证用的是这个）
```

## 8. 一句话给决策层

**输出基变换是零收益，而且是定理级零收益**：成本是 `|products| + |cache|`、
正确性只要求覆盖同一个 40 维（k≥4 是 35 维）函数空间，`B V = V` 使最优值与基无关；
per-output 模型里 rank 在整个空间上恒为 15，identity 已是最优（295/320）。
真 kickmix 也验证了 `B f + 免费 CX 恢复` 语义正确，但 T 从 375 升到 395–400。
**243 CCX/circuit 只能靠重搜 product 集；loader 仍然 4,089 T/pass → 297.24M。**
