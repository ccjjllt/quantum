# Maoxin v22 loader 逆向：构造已完全识别，但 ≤4,089 无法用本地构造器落地（no-go）

2026-11-12 · 分支 `codex/dfthcsos-research` · 工作区 `artifacts/20261112_loader_re/`

## 结论（先读这段）

- **Maoxin v22 的 4,089 T/pass 构造已经逆向到机制层**：地址按 **a = 16·q + r** 切成
  `q = a>>4`（高 7 位，q4..q10，被缓存）与 `r = a mod 16`（低 4 位，作为“小维度”），
  **缓存 70–80 个 monomial AND**，**产品项 190–212 个 CCX**，每电路
  `Q = 128 = 11 sel + 40 word + 2 pivot + 75 cache`，pivot 固定为 q126/q127。
- **但它是 stateful 电路，不是通用 XOR oracle**：入口 `CX bit6→bit7` 把每个字的顶位变成
  `b7⊕b6`（地址的已知函数），该“flag”被并进产品线性型，出口再 CX 还原。实测 z=0 时
  k≥1 全部 40 个 word bit 都错；z=batch_{k−1} 或 z=batch_k 时 1,220×5 字全对。
  verifier 恰好只跑这两条路径（正向从 0、反向从 batch_k），所以合法。
- **差距归因（精确到计数）**：cache 不是差距（Maoxin 1,142 vs 本地 1,200，−5%）；
  差距 100% 在**产品项**：Maoxin 2,947 vs 本地 3,942（−25%），以及 CNOT：
  Maoxin 全家族 217,829 vs 本地 702,587（3.23×）。产品项效率（k=4 实测）：
  Maoxin 550 个 rank-1 项 / 193 CCX = **2.85**，本地 550 / 263 = **2.09**。
  （注意：2 不是上界。当线性型建立在 **monomial 索引**上时，两个 monomial 相乘
  `m·m' = m∪m'` 直接落到另一行，所以一个 Toffoli 能覆盖远多于 2 个 rank-1 项；
  这正是本地 `shared` 没有利用的自由度——它把 pure 项当 CNOT 修正，要求整轴 monomial
  都缓存。）
- **本地构造器在 128-qubit cap 下的上限就是 5,142 T/pass**（J=5/lowbits=4/shared，
  已验证 words 等价 + 官方全量 PASS）。要达到 4,089 需要 Maoxin 那套
  **“稀疏 monomial 基 S（|S|≈70）+ 产品型建立在 monomial 上（m·m' 覆盖未缓存行）+
  每个线性型可携带 0–2 个 r-side monomial”** 的联合搜索；`tensorqrom8` 的
  `shared`/`per_output` 都不做“两个缓存 monomial 相乘去覆盖未缓存行”这件事，
  所以**这不是参数问题，是缺少那套优化器**。
- **纯解析可达但 Q 不可行**：lowbits=7 全基（cache 125 AND，Q=176）在 35 输出
  （b7 用 d7⊕d6 替代）下是 4,500 T/pass；在 791 行上是 **3,645**。这是“如果有
  Maoxin 构造器”的投影，不是可落地数。
- **R=5 仍是 no-go**：实测本地 loader 在 791 行（当前表截断代理）是 **4,601 T/pass**
  （T_total ≈ 2×4,601 + 6,889 = 16,091，比当前 14,840 **+8.4%**）。只有复现
  Maoxin 构造（投影 3,645）才能把 R=5 做到 −4.5%。
- **本轮没有可提交候选**：没有产物 cost < 297.237M，因此**没有跑官方全量验证**
  （按仓库约定，验证器只在有候选时手动跑）。所有 T 都是静态计数 + 局部 words 检查。

## 1. 结构对比（逐电路实测）

Maoxin：`artifacts/20261112_frontier/chem14840/angle_k_*.kmb`（Q=128，15 件，words 与
`artifacts/20261112_eae_candidate/dfthcsos/submission.npz` 逐 word 相同，已复核
`words_equal=True`、`toffoli_per_pass=4089`）。
本地：`artifacts/20261112_jbatch/J5_l4/`（J=5、lowbits=4、full-8bit、sizes=(7,6,6,6,5,5)）。

| k | Maoxin Q | Maoxin T | Maoxin CX | 本地 Q | 本地 T | 本地 CX |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 128 | 292 | 19,117 | 124 | 358 | 50,377 |
| 1 | 126 | 287 | 16,697 | 124 | 340 | 46,112 |
| 2 | 126 | 287 | 16,713 | 124 | 340 | 46,237 |
| 3 | 126 | 287 | 16,725 | 124 | 338 | 46,266 |
| 4 | 128 | 268 | 13,769 | 124 | 343 | 47,562 |
| 5 | 128 | 268 | 13,712 | 124 | 337 | 45,616 |
| 6 | 128 | 268 | 13,664 | 124 | 345 | 47,914 |
| 7 | 128 | 268 | 13,588 | 124 | 345 | 47,039 |
| 8 | 128 | 268 | 13,627 | 124 | 336 | 45,463 |
| 9 | 128 | 265 | 13,498 | 124 | 345 | 47,407 |
| 10 | 128 | 266 | 13,496 | 124 | 352 | 48,173 |
| 11 | 128 | 266 | 13,241 | 124 | 344 | 46,608 |
| 12 | 128 | 266 | 13,217 | 124 | 336 | 45,295 |
| 13 | 128 | 266 | 13,200 | 124 | 333 | 44,062 |
| 14 | 128 | 267 | 13,565 | 124 | 350 | 48,456 |
| **合计** | | **4,089** | **217,829** | | **5,142** | **702,587** |

（`angle_k_0` 的 ops：Maoxin 19,883 vs 本地 50,996；k=4：14,388 vs 48,164。T/ops：
Maoxin 0.0147 vs 本地 0.0070 —— 与前台观察一致。R/HMR 数 = cache AND 数：
Maoxin 75–80，本地 80。X 数 Maoxin 105–305，本地 17–27。
**全家族总计**：Maoxin `CCX 4,089 / CX 217,829 / R=HMR 1,142 / X 2,586 / ops 228,785`；
本地 `CCX 5,142 / CX 702,587 / R=HMR 1,200 / X 304 / ops 712,488`。
本地 ops 是 Maoxin 的 3.11×，其中 CX 是 3.23×。）

**cache vs 产品项拆分**（R/HMR 数即 cache AND 数；CCX 总数 − cache = 产品项）：

| | cache AND（15 电路） | 产品项 CCX | T/pass |
|---|---:|---:|---:|
| Maoxin v22 | 1,142 | **2,947** | **4,089** |
| 本地 J5/l4 | 1,200 | **3,942** | **5,142** |

即：**cache 只差 5%，产品项差 25%，T 差 26%。**

## 2. 逆向出的构造（可据此重写）

### 2.1 几何：地址切分方向与本地相反

- 选择寄存器 q0..q10 = 地址位 0..10。
- **被缓存的 monomial 全部落在 q4..q10**（= `a >> 4`，7 位，128 个 offset）；
  **q0..q3**（= `a mod 16`，16 个 chunk）作为“小维度”，其线性型只有 0–2 项。
  - 与 `tensorqrom8` 相反：本地是 low = `a mod 16`（11 个 AND）、high = `a>>4` 的 77 个 chunk
    （69 个 AND）。
- k=4 的 cache 实测 70 个 monomial，度数分布 `{2:20, 3:26, 4:17, 5:6, 6:1}`，
  即**稀疏基 S**（不是完整的 127 个 low monomial，也不是按度数截断）。
- k=0 的 cache 是 80 个、度数 `{2:25, 3:30, 4:18, 5:6, 6:1}`，且跨到 q0..q3
  （因为该电路的分解用到了 r-side 的 pair）。

### 2.2 电路骨架（k=4 逐门）

```
CX q17 q18 ; CX q25 q26 ; CX q33 q34 ; CX q41 q42 ; CX q49 q50     # 5 个字的顶位 := b7⊕b6
R q51 ; CCX q4 q5 q51 ; R q52 ; CCX q4 q6 q52 ; ...                # 稀疏 monomial cache（每项 1 CCX）
R q120 ; CCX q18 q2 q120 ; R q121 ; CCX q18 q3 q121 ;              # 带 flag 的 cache 项
R q122 ; CCX q2 q3 q122 ; R q123 ; CCX q26 q3 q123 ; ...
CX q5 q126 ; CX q10 q126 ; CX q53 q126 ; ...                       # 在 pivot q126 上物化线性型
CX q71 q127 ; CX q72 q127 ; ...                                    # 在 pivot q127 上物化线性型
CX q45 q13 ; CX q45 q14 ; ... ; CX q45 q48                         # fanout 到多个输出字位
CCX q126 q127 q45                                                  # 一个产品项
...                                                                # 共 193 个产品项
CZ ... if b0 ; HMR ... b0                                          # 每个 cache AND 用测量擦除
CX q49 q50 ; ... ; CX q17 q18                                      # 还原 5 个字的顶位
```

- **pivot 固定 q126/q127**（Q 的最顶两位），每个产品项 `CCX q126 q127 <word bit>`；
  另用 CX 链把该产品项扇出到同组的其它 word bit（`fan_ccx` 同款）。
- 每个 cache AND 都是 `R + CCX`（init_and）配 `HMR + CZ`（del_and），**不走 Toffoli**。

### 2.3 产品项：型建立在 monomial 上，乘积自己生成新 monomial

一个产品项是 `CCX pivotA pivotB <word bit>`，pivotA/pivotB 各持有一个**以缓存 monomial
为基**的线性型（k=4 时每个型 26–59 项）。两个型相乘：

```
(Σ_{m∈S} α_m·m)(Σ_{m'∈S} α'_m'·m') = Σ α_m α'_m' (m·m'),    m·m' = m ∪ m'
```

即**乘积本身合成新的 monomial（行）**，而型里携带的 r-side monomial 决定它落进哪个
chunk 列。所以一个 Toffoli 覆盖的不是 2 个 rank-1 项，而是 |supp1|×|supp2| 个 monomial
对（k=4 平均 30–59 项/型 → 数百个对，去重后仍覆盖几十行）。

按“每个型里有几个 r-side（q0..q3）monomial”分类（k=4 的 193 个产品项）：

| (#r-side 项 in c1, in c2) | 产品项数 | 作用 |
|---|---:|---|
| (0,0) | 30 | 只落在 M=0 列：生成 pure-low 部分的行（本地靠 CNOT 从缓存 monomial 扇出） |
| (0,1) / (1,0) | 38 + 43 | 占 1 个 chunk 列 |
| (1,1) | 63 | 覆盖 r1、r2、r1·r2 列 |
| (1,2) / (2,1) | 8 + 11 | 更多列 |

**这就是 26% 差距的机制**：本地 `build_circuit` 的 pure 修正（`low_correction` 与
`high[m]` 的 CX 扇出）要求**整轴 monomial 都在缓存里**，所以 lowbits=7 必须 120 个 AND；
Maoxin 把这些行交给产品项自己生成，缓存只放 70 个“种子”，于是
`Q = 11 + 40 + 70 + 2 = 123~128`。`shared`/`per_output` 的分解模型里“产品项”是
rank-1 对（行是固定的），**不允许生成新行**，因此它们的缓存必须完整——这是结构性差异，
不是搜索参数差异。

### 2.4 stateful：顶位 flag 是“免费基函数”

- 入口 `CX bit6→bit7` 后 `q18 = b7⊕b6`（不是 0！），该值被直接当作基函数使用
  （`CX q18 q126/q127`、`CCX q18 q2 ...`），出口 `CX bit6→bit7` 再把它折回去。
  代数上：出口 `q18 = (b7⊕b6) ⊕ g ⊕ (b6⊕d6)`，只要 `g = d7⊕d6` 就得到 `b7⊕d7`。
- **实测（`stateful.py`，1,220 地址全表）**：
  - 输入 z = batch_{k−1}：15 个电路全部 0 mismatch；
  - 输入 z = batch_k：0 mismatch（反向路径）；
  - 输入 z = 0：k≥1 全部 **40/40 word bit 错**；z=all-255：37–40/40 错。
  - 单 bit 扰动测试：只有每个字的 **bit6 与 bit7** 会非线性影响输出，其余 30 个 bit 都不参与。
- 结论：这是**合法的 stateful 优化**（verifier 只喂这两条路径），但**不能当作通用
  XOR oracle 移植**；重写时必须显式复刻“入口置 flag、出口还原”的两条 CX。

### 2.5 qubit 预算

`128 = 11 (sel) + 40 (word 5×8) + 2 (pivot q126/q127) + 75 (cache)`。
k=0 的 80 个 cache AND 中有 5 个落在借用的 word 顶位上，所以 ancilla 仍是 75。
**这正是“稀疏基 70”存在的原因**：cap 只允许 ≈75 个 cache 位，而完整 7-bit low 基要 120 个，
Q 会到 176。

## 3. 为什么本地构造器到不了 4,089（上限测量）

`tensorqrom8` 的两条分解路径都把“产品项”当成**行的 rank-1 对**，pure 部分靠 CNOT 从
缓存 monomial 扇出，因此**没有“产品项生成新行”的自由度**：

- `shared`：按输出分组（6–7 个）求特征，pure 修正要求**该轴 monomial 全缓存**；
- `per_output`：逐输出对 15×H 混合矩阵做行 rank 分解 + 配对。

解析/实测上限（当前 1,220×75 表，J=5，T/pass 为 15 电路合计）：

| 构造 | cache AND | 产品项 | T/pass | Qmax | 128-cap |
|---|---:|---:|---:|---:|---|
| **Maoxin v22（实测）** | 1,142 | 2,947 | **4,089** | 128 | ✓ |
| **本地 shared l4（实测，已 PASS）** | 1,200 | 3,942 | **5,142** | 124 | ✓ |
| per_output l4 full40 | 1,200 | 4,520 | 5,720 | 131 | ✗ |
| per_output l4 + b7:=d7⊕d6 | 1,200 | 3,906 | 5,106 | ~136 | ✗ |
| per_output l7 full40（完整 low 基） | 1,875 | 3,000 | 4,875 | 176 | ✗ |
| **per_output l7 + b7:=d7⊕d6** | 1,875 | 2,625 | **4,500** | 176 | ✗ |
| per_output l7（Maoxin 的切分方向，完整基） | 1,935 | 4,550 | 6,485 | 176 | ✗ |
| per_output l6 + b7:=d7⊕d6 | 1,065 | 5,235 | 6,289 | ~150 | ✗ |

要点：
- **lowbits=7 是解析最优点**（`L + O·N/(2L)` 在 L≈128 取极小），产品项只有 175–200，
  但完整 low 基要 120–125 个 cache 位 → Q=176，超出 cap。
- lowbits=6 虽能进 cap（cache 71），产品项涨到 350 → 6,289，更差。
- **加 “b7 := d7⊕d6” 只值 −12.5% 产品项**（40→35 输出），且需要保存 b6_in（+5 qubit）
  才能还原 bit7；在 Q=124/131 的边界上直接顶到 129–136，**不可行**。
- 因此本地构造器在 cap 内的上限 = **5,142**（已实测、已验证），与 Maoxin 的差距
  **1,053 T/pass（+25.8%）**，与前台给出的 26% 一致。**这是构造能力差距，不是参数差距。**

已有的 J 扫描（`20261112_jbatch`，lowbits=4、sizes=默认 6、trials=6）证明 5,142 不是
漏扫：`J=1 9,765 / J=2 7,205 / J=3 5,958 / J=4 5,562 / J=5 5,142`（每个 T/pass，全部
words 等价；J=1..4 的 cost 分别 +63.1% / +33.9% / +20.4% / +17.5%）。J 轴在 J=5 之后
被 qubit cap 挡住（J=6 在 lowbits=4 需要 132 > 128），lowbits=5 又让乘积项爆炸
（同电路 510–546 vs 239–265）。

## 4. rows 缩放与 R=5 投影

### 4.1 解析（同一 75 列，把 N 行之后置零；仅用于看缩放，不是真 R=5 表）

| N | lowbits=4 per_output | lowbits=7 per_output（完整基） |
|---:|---:|---:|
| 791 | 5,330 | **3,645** |
| 934 | 5,467 | 4,260 |
| 1,220 | 5,720 | 4,875 |

lowbits=7 对 rows 很敏感（−25%），lowbits=4 几乎不缩放（−7%）——因为后者的固定
成本（69 个 high-cache AND）占主导。**这与“Maoxin 构造的固定成本更低”的判断一致**。

### 4.2 实测（本地构造器，791 行截断表）

```
N791_l4_t2: 15 电路, brot 8, J 5, qmax 104,
            toffoli_per_pass 4601, words_equal=True（局部 1 shot/address 检查）
```

即本地 loader 在 791 行是 **4,601**（不是 5,142，也不是 ≤4,089）。
投影（用前台给的 R=5/C=75 heuristic `T=6,889`）：
`T_total ≈ 2×4,601 + 6,889 = 16,091` vs 当前 14,840 → **+8.4%**，**R=5 no-go**。
只有当 Maoxin 构造被复现（791 行投影 3,645）时：
`T_total ≈ 7,290 + 6,889 = 14,179` → **−4.5%**，那才是 R=5 的唯一路径。

## 5. 验证范围（严格区分）

- **Maoxin v22 words 等价**：`experiments/dfthcsos/20261112_jbatch/check_words.py`
  对 `artifacts/20261112_frontier/chem14840` 实测 `words_equal=True`、
  `toffoli_per_pass=4089`、`qmax=128`（局部 1 shot/address）。
- **官方全量**：本轮**未跑**。理由：没有任何产物 cost < 297.237M（本地 5,142 → 339.4M；
  791 行代理 4,601 → T_total 比当前高 8.4%），按仓库约定不空跑验证器。
  已 PASS 的两条历史记录（`20261112_jbatch/README.md`）仍是：
  Maoxin v22 `297,237,077.47`（−0.108%）、本地 J5/l4 `339,419,104.77`。
- **rows791 代理**：只做了局部 words 检查（`words_equal=True`），**不是**官方验证，
  也**不是**真正的 R=5 表（真正的 R=5 表需要用 rc_shape/gauge 流水线生成，本工作区没有）。

## 6. 复现/移植清单（给下一个 session）

1. **几何**：ANF 张量按 `m = m_hi·16 + m_lo` 切，`m_hi` 覆盖 q4..q10（127 行），
   `m_lo` 覆盖 q0..q3（15 列）。等价于把 `anf_tensor(delta, 8, 4)` 的行列角色对调。
2. **稀疏基 S**：选 ≤75 个 `m_hi` monomial（向下闭合地可由 1 个 CCX 从父项×地址位构造），
   使 S² 覆盖全部非零行、且 S 本身覆盖 pure 修正。k=4 的实测 S：70 个，
   `{2:20,3:26,4:17,5:6,6:1}`。
3. **产品项搜索**：每个输出的混合矩阵用“两个线性型（各可带 0–1 个 `m_lo` monomial）”
   覆盖 1/2/4 个 rank-1 项；目标是让 `rank-1 总数 / CCX` 逼近 2.85（本地是 2.09，上界 4）。
4. **pivot**：2 个专用 pivot（q126/q127），先 CX 物化两个型，再 `CCX pivot pivot target`，
   用 CX 链扇出，最后反序撤销。**不要**像 `shared` 那样把缓存 qubit 当 pivot。
5. **stateful flag**：入口 `CX bit6→bit7`、出口同一条；产品型里可自由使用该 flag
   （及其与 q0..q3 的 AND）。
6. **预算**：`Q = 11 + 8J + 2 + |cache| ≤ 128` → `|cache| ≤ 75`（J=5）。

## 7. 文件

```
experiments/dfthcsos/20261112_loader_re/
  README.md          本文
  tensorqrom8.py     只读复制的本地构造器（未改）
  dump.py            .kmb -> .kmx 文本
  sym.py             11-bit truth-table 符号重放（门统计、控制多项式度数）
  dissect.py         cache monomial / 产品项 / 目标统计
  stateful.py        stateful 语义测试（z=0 / batch_{k-1} / batch_k / all-255）
  anf_report.py      ANF 支撑、per_output 配对成本、lowbits 扫描（解析）
  split_test.py      两种地址切分方向的 ANF 张量对比
  scan.py            tensorqrom8 扫描（lowbits/sizes），写 artifacts/.../scan/
  rows.py            行截断代理构建（N 行，写 artifacts/.../rows/）
  probe_sizes.py     只做分解、不建电路的 output 分组探针（[40] 组在 76×40=3040 维特征空间上
                     太慢，3 分钟后终止；宽分组不是免费收益，本地 shared 的 6–7 分组是扫出来的最优）

artifacts/20261112_loader_re/
  kmx_maoxin/        15 个 Maoxin 电路的 .kmx（19,883 / 13,769 ... 门序列）
  kmx_local/         15 个本地 J5_l4 电路的 .kmx
  rows/N791_l4_t2/   791 行代理电路 + submission.npz（4,601 T/pass, Q 104）
  scan/              lowbits/sizes 扫描输出（若完成）
  scan_l7.log        lowbits=7 扫描：命令行启动后 15 分钟未出第一个 ROW，已终止（分解搜索太慢，
                     与解析表一致：l7 需要 125 个 cache 位，本来就不可行）
  scan_l6.log        lowbits=6 扫描：同样未完成（>15 分钟无 ROW），已终止；l6 的解析值见 §3
  rows_791_l4.log    791 行代理构建日志（4,601 T/pass）
```

## 8. 一句话给决策层

Maoxin 的 4,089 不是“同一分解器的更好参数”，而是**另一套构造**：稀疏 monomial 基
（≈70，受 128-qubit cap 逼出来的）+ 两个专用 pivot 上的宽线性型 + stateful 顶位 flag。
本地 `tensorqrom8` 在 cap 内的上限是 5,142（已 PASS）；差距 1,053 T/pass 只能靠重写
分解搜索来消除。**在复现那套搜索之前，R=5/R=6 shape 线用本地 loader 一律是负收益。**
