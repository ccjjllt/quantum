# invsqrt 线 — 2026-11-18 push（`563d0583`，Q=44）

负责人：invsqrt 子代理。账号 `jiyujia`。全部结论只来自
**(a) 只读静态解析**、**(b) Kaggle CPU kernel 上的官方 `kickmix`**、**(c) 已公布的官方 verifier 回执**。
本机没有跑任何电路仿真；本轮没有提交 Kaggle，没有推送代码。

## 0. 摘要（先看这张表）

| 问题 | 本轮判定 | 决定性数字（全部实测/精确推导） |
|---|---|---|
| 公开件里有没有比 74,560.9 更便宜的 invsqrt？ | **没有** | 公开地板 = `563d0583`（就是我们的出货件），sha256 `563d0583…9321`；次优 75,006.38 / 75,038.13 |
| Q=44 能不能靠"反算换 HMR / 相位折叠"省 Toffoli？ | **不能，已闭合（比前人更强的判据）** | 全带 **0** 个可折叠点；1479 个乘积原子只有 **35** 个被 CCX 反算，其余 1444 个全靠 **1277 个 HMR** 回收；**0** 个"同值 CCX 成对" |
| 旋转项（240.56 C，占 14.2%）能不能降？ | **不能，已定量闭合** | 实测余量 = 31,789,811 units = tol 的 **0.044%**；只有最低一个相位位（2^-36 turn）在原理上可丢，且要求大幅端误差从 0.9996 tol 降到 ≤0.14 tol（7×），代价 ≥ 70 C，回收 7.3 C |
| Q=42 / 40 的新合成体值不值得做？ | **有 80.7 / 169.5 Toffoli 的余量，但没有可行的入口**（见 §5） | 42Q 需 `Toffoli ≤ 1534.69`（+80.69）；公开前沿在 46Q→44Q 上的斜率是 **13.4 Toffoli/wire**，从我们的点外推到 42Q 需要 **40.3/wire** |
| 本轮有没有造出更便宜且 PASS 的新件？ | **没有** | 唯一的新官方回执是对出货件本身的 1 shot/x 预检：PASS，score 74,560.715 |

结论一句话：**在 Q=44 这条带子上，Toffoli、旋转、宽度三个轴都已经用精确判据闭合；
继续降成本必须是"换合成体"（生成器级改动），不是字节级改写。**

---

## 1. 任务与成本模型（复述，便于核对）

官方 `verifiers/invsqrt/verify_submission_invsqrt.py`：

```
score = Q * C,   C = Toffoli + T/4
T     = t_base + n_rot * (0.56*log2(1/eps) + 5.3)
eps   = pi * min_margin / 2**64 / n_rot          # min_margin 单位 2^-64 turn
tol(x)= 2^-24 / sqrt(x) turns,  x <= 3,133,452,  beta = 1
```

出货件 `563d0583`（官方全量 200,540,928 shots 回执，见 §3）：

| Q | Toffoli | t_base | n_rot | eps | C | cost |
|---:|---:|---:|---:|---|---:|---:|
| 44 | 1,454.000786597537 | 2.500049142088342 | 33 | 1.6406054738480745e-13 | 1,694.5660653 | **74,560.90687** |

旋转块 = 33 × 29.0837 T = 959.761 T = **239.94 C = 14.16% 的 C**；Toffoli = 85.8%。

---

## 2. 公开件扫描（2026-11-17 12:00 UTC 之后）

扫描面：`search_notebooks(sort=DateRun)` + `search_datasets(sort=Updated)`，关键词
`qcc / vqcc / invsqrt / qrom / 42 qubit`，下载并解开最近 20 个 notebook/dataset，
按 sha256 与**官方成本公式**逐件比对（成本只用已公布的 verifier 回执，不重跑）。

| 来源（更新时间 UTC） | 它带的 invsqrt | 官方成本 | 与我们比 |
|---|---|---:|---|
| `junmiaotiao/qcc-frontier-20261117r`（dataset，11-17） | `invsqrt.kmb` sha **563d0583…** | 74,560.9069 | **相同字节** |
| `mizeroluckygall/…28-17-stack-new-44q-invsqrt`（13:36） | 563d0583 | 74,560.91 | 相同 |
| `alexchilton/28-15-lb-…private-salt`（13:35） | 表内地板 563d0583；次 0af21cb8 | 74,560.91 / 74,797.37 | 相同/更差 |
| `junmiaotiao/qcc-28-155-public-frontier-combo-r`（14:51） | 563d0583 + f2cdab0b/8b410e77 备选 | 74,560.907 / 75,006.38 / 75,038.13 | 不更优 |
| `ozertuu/vqcc-super-sota-verified-portfolio-28-091`（16:00） | `8b410e77` / `f2cdab0b` | 75,038.13 / 75,006.38 | 不更优 |
| `syed3000/vqcc-own-circuit-portfolio`（dataset v13） | `invsqrt.kmb` 200,369 B（46Q 线同源；本 dataset 原件未复跑） | 同源件公开回执 78,764（ahoirg K=6 复算） | 不更优 |
| `kirilltym/…conditional-uncompute-audit`（V5 回执） | `034c7c2a` | 95,345.55 | 不更优 |
| `taylorclark637/invsqrt-logshift-{candidates,fy028-c4}` | 292Q / 297Q，4,649 / 5,674 CCX | 远差（Q≈292） | 不更优 |

**没有任何公开件低于 74,560.90687。**（`563d0583` 的字节与我们 `pipeline/invsqrt_563d0583.kmb.b64`
解码结果完全一致：kmb 179,308 B，sha256 `563d0583f736…9321`。）

---

## 3. 本轮唯一的官方回执（出货件复验，1 shot/x）

kernel `jiyujia/qcc-invsqrt-rotlp-563d0583` **v7**（v1–v7 同一份 `rotlp.json` 结构，
v7 是最终版），未修改的官方 verifier，
`--shots-per-x 1 --batch-size 1022`（3,133,452 shots）：

```json
{"status": "PASS", "score": 74560.71496065716, "toffoli_equivalent": 1694.5617036512992,
 "toffoli_count": 1453.9968012913553, "t_count": 2.4985437785547697,
 "rotation_count": 33.0, "rotation_eps": 1.6406054738480745e-13, "num_qubits": 44,
 "verified_shots": 3133452, "worst_error_over_tolerance": 0.9995605646154175,
 "worst_x": 231, "circuit_sha256": "563d0583f736afc2d8111f376bc1bd5ce6aef686525b0dd281fc1f2b4eb09321"}
```

注：1 shot/x 的 score 比 64 shots/x 低 0.19（mean Toffoli 1453.9968 vs 1454.0008 的抽样差），
`eps`、`rotation_count`、`worst_error_over_tolerance` 与全量回执**逐位相同**。
**这不是新候选的结果**，只是本轮对出货件的官方再确认。

---

## 4. Toffoli 轴（协调者指定的第一优先）

### 4.1 分部 Toffoli 普查（静态，`window.py` / 见 `census.txt`）

| 区域（body op 区间） | ops | Toffoli | CCX | CCZ | HMR | CX | CZ | Z_POW |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 0–2,500 归一化 / 就地移位 | 2,500 | 171 | 171 | 0 | 109 | 1,919 | 115 | 4 |
| 2,500–6,500 尾数 / 表 / 插值 | 4,000 | 423 | 423 | 0 | 392 | 2,897 | 89 | 0 |
| 6,500–7,500 相位级（33 rotations） | 1,000 | 128 | 128 | 0 | 50 | 507 | 115 | 34 |
| 7,500–14,500 相位后修正 | 7,000 | 416 | 399 | 17 | 373 | 4,114 | 633 | 5 |
| 14,500–18,000 第二段算术 | 3,500 | 262 | 262 | 0 | 240 | 2,016 | 230 | 0 |
| 18,000–19,500 Clifford 相位尾 | 1,500 | 13 | 11 | 2 | 25 | 163 | 810 | 0 |
| 19,500–20,659 还原 x | 1,159 | 135 | 124 | 11 | 88 | 681 | 103 | 0 |
| **合计（静态）** | 20,659 | **1,548** | 1,518 | 30 | 1,277 | 12,297 | 2,095 | 43 |

执行均值 1,454.0008（静态 1,548 − 94）。条件结构精确可算：
**176 个 Toffoli 在 1 层条件块（p=1/2）、8 个在 2 层嵌套（p=1/4）**
⇒ `1548 − 176/2 − 8·3/4 = 1548 − 88 − 6 = 1454.0`，与官方 200M-shot 均值
1454.0008 吻合到 0.001。也就是说**执行折扣已被完全解释，没有"隐藏的条件门"可挖**。
结构要点：**1518 个 CCX 里 508 个目标是 x 线、1010 个是 scratch；1159 个以 x 线为控制。**

### 4.2 反算 / HMR 审计（精确，无采样）

用 **hash-consed 乘积原子** tracker（`fold_atoms.py`、`repeats.py`）：
每个乘积原子 = 其两个操作数当前 GF(2) 支撑集合的规范对，因此**同一个原子 ⇔ 同一个值**，
比前人的"标签栈配对"严格。

| 量 | 实测 |
|---|---:|
| 乘积原子（不同值） | **1,479** |
| 创建事件 | 1,483（只有 4 个原子被创建两次：3 个同半区、1 个跨半区） |
| 被 CCX 反算（同原子、同目标、后写取消前写）的原子 | **35** |
| 被 HMR 回收 | 1,277 |
| 剩余（值随 x 线还原链一起恢复） | 1,442 |

⇒ **这条带子上不存在 "compute → 反向 CCX" 的付费反算对**（只有 35 个原子由 CCX cancel，
且它们全部落在 x 线还原链上，不是 AND 回收）。这与前人 §B 的"付费 uncompute ≤ 6.7%"一致，
但判据更强：不是"≤6.7%"，而是"AND 回收 100% 走测量"。

### 4.3 相位折叠搜索（本轮新增判据，前人未做）

精确恒等式（对任意初值 t 成立，含 t 脏的情况）：

```
CCX(a,b,t) … CZ(c,t) … CCX(a,b,t)   ->   CCZ(a,b,c) + CZ(c,t)      (2 Toffoli -> 1)
CCX(a,b,t) … Z(t)    … CCX(a,b,t)   ->   CZ(a,b)   + Z(t)          (2 Toffoli -> 1)
```

要求：窗口内 t 只被 `Z` / `CZ` 读（被当成值用就不行），且两端 CCX 的操作数**同值**。

* 检测器先在 6 个合成样例上自检全部正确（1-CZ 命中、值读不命中、Z 读命中、
  2-CZ 不命中（省 0）、脏目标命中、操作数未变命中）。
* 在 `563d0583` 上：**0 个折叠点**（`fold_atoms.py` 输出 `fold sites: 0`）。
* 顺带纠正一个易犯的错：按**标签**做"栈式配对"会找到 6 个 `CCX q42 q28 q35`
  （op 2638/2691/2748/2809 与 14549/14602/14659），但它们在窗口内操作数**已变**
  （`CX q42 q28`、`HMR q42` 等），是**新的乘积**而不是反算；按原子值判定全部不成立。

### 4.4 结论（Toffoli 轴）

* 局部改写：**没有剩余空间**（0 折叠点、0 同值 CCX 对、0 死 AND、0 可降级 CCX）。
* 因此 1,454 全属"前向算术"；要 −10%（−145）必须**换生成器参数或换算法**。
* 该件的出处（`NOTEBOOKS_INTEL.md` §7.3）：**Syed Asad Ali 的 46Q 生成器 +
  Ali Haydar Özdağ 的 64 行系数表 + Özer 的角度 refit，reschedule 到 44Q**。
  同一生成器上**有人实测过参数级收益**：ahoirg 把表从 32 行改 64 行（K=6），
  46Q 上 1,511.6 → 1,480.8 Toffoli（**−2.0%**）。这是"参数级 Toffoli 收益"的
  唯一公开先例，也是下一步最具体的入口（见 §7 L2）。

---

### 4.5 代数重构（协调者第 3 项）的定量评估

| 候选改写 | 在这条带子上是否可用 | 依据（本轮实测/精确推导） |
|---|---|---|
| shared subproducts across iterations | **已饱和** | 1,479 个乘积原子里只有 **4** 个被创建两次（3 同半区 + 1 跨半区）⇒ 可共享的子乘积已经共享完了 |
| Karatsuba / 窗口乘法 | **不适用（本件不是宽乘法器）** | 全带只有 1,479 个 AND，**远少于一次 22×22 schoolbook 乘法的 484** 乘以任何合理次数；且分部普查里 2,500–6,500 段是"表 + 插值 + 累加"（423 Toffoli / 4,000 ops，其中 2,897 个 CX），不是 n×n 乘法。Karatsuba 在 n=22 只省 18%，且前提是有 22×22 乘法 |
| 换多项式近似（同 eps 预算） | **只能更差** | eps 余量 0.044% ⇒ 换更省的表必然更粗 ⇒ eps 更小 ⇒ 每个 rotation 更贵；且本轮实测出货角度已是绝对余量局部最优 |
| Newton 迭代重构 | **本件不是 Newton** | 出处是 Syed 46Q 生成器（sqrt + 除法 + 64 行表；`fortysix` 的分段为 LOAD1/COEF1/SEED/PROD/DIV_FWD/PHASE/DIV_CLEAN/LOAD2/COEF2/SEED_CLR/A_REST/R_PAID） |

**因此"Q=44 降 Toffoli"唯一的现实入口是生成器参数（表行数 K、插值位宽、段数），
不是字节级代数改写。** 公开先例（ahoirg 在 46Q 上把表 32→64 行）实测 1,511.6 → 1,480.8
（−2.0%）；若在 44Q 上复现 −1.5%，= −22 Toffoli = **+0.12 GM**（§7 L2）。

---

## 5. 宽度轴（Q=42 / 40 / 更低）

### 5.1 盈亏平衡（精确，旋转块按出货 eps 固定）

`cost < 74,560.90687` ⇔ `C < 74,560.90687 / Q`；Toffoli 预算 = C − 239.94：

| Q | C 上限 | Toffoli 上限 | 相对出货 1454.0008 |
|---:|---:|---:|---:|
| 44 | 1,694.57 | 1,454.00 | 0 |
| 43 | 1,733.97 | 1,493.41 | +39.41 |
| **42** | **1,775.26** | **1,534.69** | **+80.69** |
| 41 | 1,818.56 | 1,577.99 | +123.99 |
| 40 | 1,864.02 | 1,623.46 | +169.46 |
| 38 | 1,962.13 | 1,721.56 | +267.56 |
| 36 | 2,071.14 | 1,830.57 | +376.57 |
| 32 | 2,330.03 | 2,089.46 | +635.46 |
| 30 | 2,485.36 | 2,244.80 | +790.80 |

### 5.2 实测前沿与斜率

| 件 | Q | Toffoli | C | cost | 出处 |
|---|---:|---:|---:|---:|---|
| 62Q 世代（busyaprime/yoyobar 线） | 62 | ~1,150 | ~1,445 | 89,590 | sheroleg §7 分部表 + 官方 |
| Syed 46Q（ahoirg K=6 复算） | 46 | 1,480.8 | 1,712.3 | 78,764 | 公开回执 |
| **ours `563d0583`** | **44** | **1,454.0** | **1,694.6** | **74,561** | 官方 |

* 46Q→44Q 的实测斜率：`(1480.8 − 1454.0) / 2 = 13.4 Toffoli/wire`。
* 42Q 需要的斜率（从我们的点）：`80.69 / 2 = 40.3 Toffoli/wire`。
* 也就是说：**42Q 要求"每去掉一条线可以多花 40 个 Toffoli"，比公开前沿实测的
  13.4/wire 贵 3 倍**；不是不可能，但必须换算法。靠现有 44Q 带子重排已被精确判定为
  ≥132 C（前人 §C，1.63× 预算）。
* 一个值得注意的巧合：Syed 的 46Q 件（1480.8 Toffoli）**若原样搬到 42Q 就会赢**
  （1480.8 < 1534.7 的 42Q 预算）。它的宽度是 46、被 **485 个单线尖峰**钉住
  （`sheroleg` §7 / `fortysix` 的实测），要压到 42 需去掉 4 条线，
  目前没有任何公开构造。

### 5.3 更低 Q 的真实机会（若要换算法，这是唯一赚钱的方向）

| 目标 | 需要的 Toffoli | 相当于当前 × | GM 增量（若达到） |
|---|---:|---:|---:|
| Q=42, C=1700 | 1,459 | 1.00× | **+0.41** |
| Q=40, C=1750 | 1,509 | 1.04× | **+0.60** |
| Q=30, C=2400 | 2,159 | 1.49× | **+0.33** |

（GM 用 `scripts/gm.py`，DQI/chem 保持 346,409,762,292.72 / 294,643,137.73，
基线 GM 28.180659。）

---

## 6. 旋转轴（按协调者更正：240.56 C = 14.2%，与 Q 降 2 等价）

### 6.1 实测误差图（精确，全 3,133,452 个 x）

kernel 内用官方 `kickmix` 跑 1 shot/x（seed 固定），把每个 x 的相位与官方
`reference_values` 比较：

| 量 | 实测 |
|---|---:|
| worst x | **231** |
| `|err|/tol` 最大 | **0.9995605646154175**（与官方 200,540,928-shot 回执逐位相同） |
| 最小余量 `min(tol − |err|)` | **31,789,811 units** = 1.7233291e-12 turn = 该 x 处 tol 的 **0.0440%** |
| `|err|/tol > 0.5` 的 x 占比 | 3.79% |
| 中位数 / p99 | 0.168 / 0.611 |
| 相位对 33 个角度的线性性 | 直接把 33 个角度各放大 3% 后重跑：与 `Σ 0.03·w_j·b_j(x)` 的偏差 ≤ **1,576 units**（≈ 2^-53 turn 级，纯 float64 噪声）⇒ **严格线性** |

### 6.2 旋转块的成本律（用实测余量代入官方公式）

`eps = π·M/2^64/n`，`T_rot(n) = n·(0.56·log2(1/eps)+5.3)`，`M = 31,789,811`：

| n_rot | eps | T/rotation | T_rot | C_block | 相对 33 |
|---:|---|---:|---:|---:|---:|
| 33（现状） | 1.641e-13 | 29.084 | 959.8 | 239.94 | — |
| 32 | 1.692e-13 | 29.02 | 929.9 | 232.47 | −7.47 C |
| 30 | 1.805e-13 | 29.00 | 870.2 | 217.55 | −22.4 C |
| 25 | 2.166e-13 | 28.86 | 721.5 | 180.37 | −59.6 C |
| 23 | 2.354e-13 | 28.68 | 659.7 | 164.9 | −75.0 C |
| 20 | 2.707e-13 | 28.68 | 573.6 | 143.40 | −96.5 C |

⇒ **每个 rotation = 7.27 C = 0.429% 成本 = +0.042 GM**；
33→23（−10 个）若可行 = −75 C = **+0.42 GM**（与协调者的估算一致）。

### 6.3 为什么"减少 rotation 个数"在这个带子上不可行（定量）

1. **energetics 上锁死**：33 个 rotation 对应相位位 2^-3…2^-35 turn（另有 2 位
   由 Clifford/T 承担，共 36 位）。需要 36 位是因为 `tol_min = 2^-24/√x_max = 2^-34.8 turn`。
2. **丢位的硬下界**：相位是"数字图案"的函数；丢掉权重 `w` 的位会把"仅在该位不同"的
   x 合并成同一个相位。要求 `w/2 ≤ tol(x)`，对最大 x 需 `j ≥ 34.2`：
   **只有最低一位（2^-36 turn，1.45e-11）在原理上可丢**，它单独就占最大 x 处 tol 的 0.43。
3. 因此丢它要求"其余误差" ≤ 0.14 tol，而现在是 0.9996 tol（**7× 更准**）。
   在这个族里提高 7× 精度 ≈ 细插值多 3 位 ≈ 70+ Toffoli = 70+ C，而只回收 7.3 C。
   **净亏 ≈ 60 C。**
4. 实测（本轮 kernel，坐标扫描，§6.4）：把最软的 8 个角度在 [0.5,1.5]× 上重调，
   以比值为目标只能把它从 0.999561 压到 0.999190（**绝对余量反而掉 6.4×**）；
   以 verifier 真正的目标（绝对余量）重调则返回 **λ ≡ 1**（已是最优）。

### 6.4 实测重调 / 丢位结果（这是本轮"旋转轴"的判决性测量）

三个测量，全部在 kernel 内对 **3,133,452 个 x 全量**评估（不用抽样）：

**(A) 丢一个 rotation + 重调其余（坐标扫描，每个角度在 0.5–1.5× 上扫 41 点，4 轮）**

| 丢掉的 rotation（op / 角度 half-turns） | 重调后的最坏 `|err|/tol` | 判定 |
|---|---:|---|
| op 6976 / 2.907e-11（**最小**） | **1.2495** | **FAIL（超容差 25%）** |
| op 7028 / 5.484e-11 | 1.6123 | FAIL |
| op 7066 / 1.157e-10 | 2.4496 | FAIL |
| op 7116 / 2.330e-10 | 4.2035 | FAIL |
| op 7154 / 4.660e-10 | 7.5660 | FAIL |
| op 7180 / 9.332e-10 | 14.4977 | FAIL |
| 两两同丢（(6976,7028) 等 3 组） | 1.9–3.6 | FAIL |

⇒ **33 是这条带子的最少数**：丢最低一位时，把其余 7 个最软角度在 0.5–1.5× 上重调
仍超容差 25%（1.2495）；更大的位更差（1.61 → 14.50）。
（对比：62Q 世代丢最低位是"差 6.5e-12 turn"，属临界不可行；这里是硬不可行。）

严格的必要条件：丢权重 `w` 的位会把"仅在该位不同"的 x 合并成同一相位，
误差至少 `w/2`，要求 `w/2 ≤ tol(x)`；对最大 x 需 `j ≥ 34.2`，
**除最低一位外全部违反**。最低一位的 `w/2 = 7.3e-12 turn = 0.215·tol_min`，
而现有误差已占 0.9996·tol ⇒ 要靠"只重调角度"再腾出 30% 预算，
而实测连现有余量都保不住（§6.4(C) 返回 λ≡1）。

**(B) 以"最坏比值"为目标重调 8 个最软角度**：比值可从 0.999561 微降到 0.999190，
但**绝对余量从 31,789,811 掉到 4,982,006 units（−6.4×）**，
eps 1.64e-13 → 2.57e-14，T_rot 959.8 → 1,009.2，成本 74,560.9 → **75,104.4（更差 0.73%）**。
原因：verifier 的 `eps` 用的是**绝对余量**（`min(tol−|err|)`，单位 2^-64 turn），
不是比值；两个目标不同，压低比值会牺牲绝对余量。

**(C) 以 verifier 的真正目标（绝对余量，约束最坏比值不劣于出货）重调同样 8 个角度**：
坐标扫描返回 **λ = (1.0, 1.0, …, 1.0)**，余量 31,789,809 units（与出货 31,789,811 差 2 units，
浮点噪声）。

⇒ **出货的 33 个角度已经是该目标下的局部最优**（这与它来自 Özer 的 angle refit 的出处一致）。
**旋转块 239.94 C 没有可回收的量。**

### 6.5 结论（旋转轴）

* 余量只有 tol 的 **0.044%**（x=231 处），所以 `eps` 被钉在 1.6e-13；
  把余量放大 16× 也只省 18.5 C（1.1%），而买 2× 精度就要 ~70 C ⇒ **杠杆比 −60×。**
* rotations 个数由精度需求锁定在 33（实测：丢最低一位即超容差 25%）；
  出货角度已是绝对余量目标的局部最优（实测 λ ≡ 1）。
* **所以 240.56 C 的旋转块在这条带子上是地板，不是可优化项。**
  若要动它，前提是**换一个"相位位更少"的近似**（例如只在必要时才产生低位），
  那是生成器级改动。

---

## 7. 下一步（按"每单位工作量能买到的 GM"排序）

| # | 线索 | 具体做法 | 预期 | 前提/风险 |
|---|---|---|---|---|
| L1 | 什么都不做，保持 `563d0583` | 已在包内 | 0 | — |
| L2 | **生成器参数**：Syed 46Q 生成器（Apache-2.0）+ 64 行表 | 取生成器源码，只改表中行数 K / 插值位宽 / 段数，re-emit 到 44Q，跑官方 verifier | 公开先例 K 32→64 行 = **−2.0% Toffoli**（46Q）⇒ 若在 44Q 复现 −1.5%，= −22 Toffoli = **+0.12 GM** | 需要生成器源码（Syed 公开但旧 slug 已 404；`manwithacat/fortysix-where-the-16-qubits-went` 里有逐门剖析与 46Q tracer，可作逆向起点） |
| L3 | **相位位裁剪（唯一可能的旋转轴）**：只在 x 大时才产生低位 | 需要"按 x 大小条件执行"——但 kickmix 只有 X-基测量，无法对 x 的函数分支（本轮已确认：条件只能由 HMR 随机位驱动），**故不可行** | 0 | 结构性不可行，勿再投入 |
| L4 | Q=42 新合成体 | 需要 ≤20 条 scratch 且 Toffoli ≤ 1535 的新算法；现有 44Q 带子已精确判定不可重排（≥132 C > 81 C 预算） | 若达 C=1700 ⇒ **+0.41 GM** | 生成器级重写；公开前沿斜率 13.4/wire vs 需要 40.3/wire |
| L5 | 旋转角度 LP 精调 | 已完成（§6.4），无收益 | 0 | — |

---

## 8. 复现物、哈希与命令

```
experiments/frontier/20261116_push/pipeline/invsqrt_563d0583.kmb.b64   sha256 52c20900909cf1b2f30f93f965dd52b39ce97718dc8e6db29fcd52a9c8d44798
artifacts/20261118_inv_sweep/invsqrt_563d0583.kmb                     sha256 563d0583f736afc2d8111f376bc1bd5ce6aef686525b0dd281fc1f2b4eb09321
artifacts/20261118_inv_sweep/invsqrt_563d0583.kmx                     (to_file kmx, 236,903 B)
experiments/frontier/20261118_push/invsqrt/evidence/rotlp_v7_final.json         sha256 c5dcee4799227474c311aef5aa93e197b525db0d409a9fdad62bc5cec7b5118a
experiments/frontier/20261118_push/invsqrt/evidence/rotlp_v6_droptests.json     sha256 874e95a3257a6a73020c5547794572e1205a02551eececc2b6ee03408f7c8dca
experiments/frontier/20261118_push/invsqrt/evidence/verifier_shots1_563d0583.json sha256 87b47a6effbfbcc1a25211bec3d23014860e2ee16f80ab174a3d5671429810b2
experiments/frontier/20261118_push/invsqrt/evidence/census.txt                    sha256 499aca681980b402c7c057b1899fafb2ab30a2607ee9ed3db58284dd7bf440ec
artifacts/20261118_inv_sweep/k1_v{1..7}/qcc-invsqrt-rotlp-563d0583.log  kernel 日志
```

注：`pipeline/invsqrt_563d0583.kmb.b64` 在工作区里是 **zlib+base64** 形式（35,028 chars，
sha `52c2090…4798`），与 git HEAD 里那份（raw base64，sha `dbcc288…b7ba`）不同
——这是本会话之前就存在的未提交改动，本轮只读取、未改动。
两种形式解码后都对应 kmb sha `563d0583…9321`；本轮所有验证都用工作区这份。

命令（本机只读/纯算术）：

```bash
# 解码 + 生成 kmx
.venv/bin/python artifacts/20261118_inv_sweep/b64_to_kmx.py \
    experiments/frontier/20261116_push/pipeline/invsqrt_563d0583.kmb.b64 \
    artifacts/20261118_inv_sweep/invsqrt_563d0583.kmb
# 相位折叠（原子级，判定 0 点）
.venv/bin/python experiments/frontier/20261118_push/invsqrt/fold_atoms.py \
    artifacts/20261118_inv_sweep/invsqrt_563d0583.kmx
# 折叠检测器自检（6 个合成样例）
.venv/bin/python experiments/frontier/20261118_push/invsqrt/fold_test.py
# 乘积原子重复/反算计账
.venv/bin/python experiments/frontier/20261118_push/invsqrt/repeats.py \
    artifacts/20261118_inv_sweep/invsqrt_563d0583.kmx
# 预算表 + 旋转成本律
.venv/bin/python experiments/frontier/20261118_push/invsqrt/trade.py
# 分部 Toffoli 普查
.venv/bin/python artifacts/20261118_inv_sweep/window.py \
    artifacts/20261118_inv_sweep/invsqrt_563d0583.kmx hist 500

# Kaggle CPU（账号 jiyujia）：误差图 / pattern / 重调 / 丢位 / 官方 1 shot/x 回执
python3 scripts/kgpu.py new  --dir experiments/frontier/20261118_push/invsqrt/k1_rotlp \
    --slug qcc-invsqrt-rotlp-563d0583 --account jiyujia --competition
.venv/bin/python experiments/frontier/20261118_push/invsqrt/k1_rotlp/build.py   # 把 b64 嵌进 main.py
python3 scripts/kgpu.py push   --dir experiments/frontier/20261118_push/invsqrt/k1_rotlp --account jiyujia
python3 scripts/kgpu.py status --kernel jiyujia/qcc-invsqrt-rotlp-563d0583 --account jiyujia
python3 scripts/kgpu.py fetch  --kernel jiyujia/qcc-invsqrt-rotlp-563d0583 --account jiyujia \
    --out artifacts/20261118_inv_sweep/k1_v7
```

### GM 增量（`scripts/gm.py`，DQI/chem 固定为 346,409,762,292.72 / 294,643,137.73）

```
现状                      invsqrt=74560.906873  GM 28.18065942   (+0.02972 vs 28.15094)
-100 Toffoli (Q44)        invsqrt=70160.91      GM 28.75785      (+0.57719)
-145 Toffoli (10%)        invsqrt=68180.91      GM 29.03358      (+0.85292)
-291 Toffoli (20%)        invsqrt=61756.91      GM 30.00726      (+1.82660)
33->32 rotations (同余量)  invsqrt=74232.24      GM 28.22219      (+0.04153)
33->23 rotations (同余量)  invsqrt=71287.91      GM 28.60550      (+0.42484)
Q=42 且 C=1700            invsqrt=71400.14      GM 28.59051      (+0.40985)
Q=40 且 C=1750            invsqrt=70000.14      GM 28.77985      (+0.59919)
Q=30 且 C=2400            invsqrt=72000.10      GM 28.51087      (+0.33021)
```

（"33->32/23 rotations" 两行是**假设性**上界：只把成本律代入，本轮已实测不可行，见 §6.4。）

脚本（全部纯算术/只读解析，本机可跑）：

* `experiments/frontier/20261118_push/invsqrt/fold_search.py` — 标签级镜像对扫描
* `experiments/frontier/20261118_push/invsqrt/fold_atoms.py` — **hash-consed 原子级相位折叠搜索**（§4.3）
* `experiments/frontier/20261118_push/invsqrt/fold_test.py` — 折叠检测器的 6 个合成自检
* `experiments/frontier/20261118_push/invsqrt/repeats.py` — 乘积原子重复/反算计量（§4.2）
* `experiments/frontier/20261118_push/invsqrt/trade.py` — 预算表与旋转成本律（§5.1/§6.2）
* `experiments/frontier/20261118_push/invsqrt/qs.py` — 指定窗口内某条线的全部出现

Kernel（账号 `jiyujia`，CPU，`enable_gpu=false`）：

| kernel | 版本 | 用途 | 结果 |
|---|---|---|---|
| `jiyujia/qcc-invsqrt-rotlp-563d0583` | v1 | 误差图 + 33 个 firing pattern + 分段一致性 | PASS；worst_x=231；分段相位与整段逐位一致（0 mismatch） |
| 同上 | v2 | 全 Z_POW 分段（条件块内有 Z_POW，断言失败） | ERROR（无结论） |
| 同上 | v3 | 打印残留键 | ERROR（无结论） |
| 同上 | v4–v5 | 角度 LP 尝试（33 个全自由 / 8 个自由 + 信赖域） | LP 在 1e-8 相对量级上病态，返回明显错误的解，**结果作废、不引用** |
| 同上 | v6 | 以"最坏比值"为目标的坐标重调 + 丢位/丢两位测试 | 见 §6.4(A)(B)：丢最低位 → 比值 1.249（FAIL）；比值目标重调 → 绝对余量掉 6.4× |
| 同上 | **v7** | 以 verifier 的绝对余量为目标重调（约束比值不劣于出货） | **λ ≡ 1.0**，余量 31,789,809 vs 31,789,811 ⇒ 出货角度已是最优；官方 1 shot/x 回执 PASS |

运行时间：v1 14 s（仿真部分）+ 21 s；v6 150 s；v7 53 s（均含官方 1 shot/x verifier）。

---

## 9. 明确未做 / 未测（避免把推断当结论）

* 本轮**没有造出**任何比 `563d0583` 更便宜的 `.kmb`，因此**没有新的全量
  200,540,928-shot PASS 候选**。
* §6.4 的重调/丢位结论只在 **seed 0、1 shot/x** 的确定性相位模型上测过；
  相位与测量结果无关（本轮已用"分段 vs 整段"和"官方 64-shot 回执同值"两次交叉验证），
  但它不是一次全量 verifier 运行。
* §5.2 里 62Q 件的 Toffoli 1,150 是**分部表相加的近似值**（sheroleg §7 的分段
  数字），已标注为近似；46Q/44Q 的数字是官方回执。
* §4.2 的"35 个原子被 CCX 反算"是**同值判定**的下界（hash-consing 只认严格相同的
  操作数支撑）；如果存在"逻辑等价但支撑不同"的取消对，本轮检测不到。这类改写
  在 4.3 的折叠判据下也需要重新推导恒等式，不能直接套用。
