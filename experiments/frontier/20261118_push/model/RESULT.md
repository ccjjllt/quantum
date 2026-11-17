# 2026-11-18 「提交可控量 × 官方计分」审计（invsqrt / dqi / dfthcsos）

审计对象：`data/competition/verifiers/` 内**未修改**的三个官方 verifier（行号均指该目录下的文件）。
审计目标：列出「提交侧能控制、且会改变分数」的每一个量，给出 `d(score)/d(参数)` 或离散增量，
并指出哪些量被 verifier 钉死、哪些拒绝条件留下合法更便宜的替代、以及哪些是**合法但意外的漏洞**。

GM 换算口径沿用 `docs/ceiling-20261117.md` / `SUMMARY2.md`：`ΔGM = (GM/3)·Δln(1/cost)`，GM=28.18
→ **每 1 单位相对成本 = 9.393 GM**。本文所有 ΔGM 都按此换算。

证据等级（按 AGENTS.md 要求区分）：

* **[算]** 纯算术复算（`model/audit_math.py`，只调用 verifier 自带的成本模型）。
  其中 chem 的模型对 shipped 提交**逐位复现**官方回执（`T=14706, Q=427, score=294643137.73357135`）。
* **[测]** Kaggle CPU kernel 跑**未修改**的官方 verifier 代码（两个 kernel，见 §8）。
  另有少量**本地静态**结论（只解析电路、只数门，不做任何 `Simulator` 演化），单独标注。
* **[读]** 只读源码得出的结论（引用行号）。
* 未执行的验证一律不写成通过。

---

## 0. 结论摘要（按价值排序）

| # | 支线 | 结论 | 量级 | 状态 |
|---:|---|---|---|---|
| 1 | chem | **loader Toffoli 是唯一还没打满的大轴**：8,044 / 14,706 = 55 %；参考 QROM 同表要 36,540 | 1,000 T = **+0.64 GM** | 开放（另一线） |
| 2 | chem | **brot 8→7 已关闭**：重量化到 7 bit 后 `error_1` 涨 102×、`error_2` 涨 21×，且 `lambda_eff` 从 46.92 涨到 74.94 | 原估 +0.30 GM → **实测不可得** | **[测] 关闭** |
| 3 | chem | `Q_total = 387 + brot·J` 精确成立，`J` 对 metric **零影响**、对成本是纯旋钮，最优点 J=5 | 1 J = 1.87 % | **[测] 关闭** |
| 4 | chem | **行序（地址分配）是新的免费自由度**：ρ 块内 `(w,u)` 联合置换、单体行置换都把全部 metric 保持到 1e-14 | 可重排 loader 基 | **[测] 新增，待 planner 试** |
| 5 | chem | **ANGLE 电路的工作比特完全免费**（61→128 qubit，`Q_total` 不变、score 逐位不变） | 与 #1 配合 | **[测] 已确认** |
| 6 | invsqrt | 33 个 rotation 已是「二进制相位阶梯」的下界（32 是理论极限） | 1 rotation = +0.041 GM | [算] 关闭 |
| 7 | invsqrt | `min_margin` 最大只能再抬 19.5×，收益上限 +1.16 % | +0.037 GM | [算] 关闭 |
| 8 | dqi | 失误容限是**有价**的：第 1 个错拍 = −0.043 GM（等价 1,678 T） | 交换率 | [算] 新增 |
| 9 | 全部 | `reaction_depth`、`num_ops`、`num_bits`、静态 `max_toffoli_count` **不计分** | — | [读] |
| 10 | 全部 | seed = 提交哈希（官方回执显示 grader **未加盐**）→ 哈希/盐研磨、稀有分支漏检 | 0.1 %+ | **[测] 漏洞，只记录不建议使用** |

---

## 1. 三个成本公式（逐行源码）

### invsqrt — `invsqrt/verify_submission_invsqrt.py`

```
score = Q · C,     Q = circuit.num_qubits,     C = toffoli_count + t_count/4      (L324, L327)
t_count = t_base + n_rot · (0.56·log2(1/eps) + 5.3)                               (L148-149, L323)
eps     = π · min_margin / 2^64 / n_rot        # 「能容下的最大 eps」,均分        (L320)
min_margin = min over all 200,540,928 shots of ( tol(x) − |θ̂(x) − target(x)| )     (L286-295, L313)
toffoli_count = mean executed CCX+CCZ+CSWAP     t_base = mean executed T 类 Z_POW
n_rot         = mean executed level≥4 Z_POW                                       (L302-304)
tol(x) = floor(2^40/√x)  (单位 2^-64 圈 = 2^-24/√x 圈)，target = round(2^64/√x) mod 1  (L117-131)
```
固定常数：`T_PER_TOFFOLI=4, ETA=218, N_P=10, shots_per_x=64, batch=256`（L65-71），
`width=2n_p+2=22, max_x=3(2^10−2)^2=3133452, beta=1, precision_bits=24`（L99-106）。
`num_shots = 64·3133452 = 200,540,928` 全部逐拍检查，**没有抽样容限**（L289-293）。

### dqi — `dqi/verify_submission_dqi.py`

```
score = rep_factor · Q² · T                                                       (L420)
rep_factor = R(eps_plus) = ln2 / −ln(1/2 + 2√eps_plus)                             (L130-136, L415)
eps_plus   = Clopper–Pearson upper(k = value+phase errors, n = num_shots, δ=2^log2_delta) (L139-171, L408)
T          = mean executed CCX+CCZ+CSWAP,  Q = circuit.num_qubits                  (L416-417)
```
固定常数：`m=4095, n=70, degree=12, r=2016, num_shots=102400, batch=256, log2_delta=−128`
（L52-59 + CLI L453-466）。`rep_factor` 在 k=0 时 = **1.1912595**（算得，与 brief 一致）。

### dfthcsos — `dfthcsos/verify.py`

```
score      = lambda_eff · T_total · Q_total                                       (L555)
lambda_eff = sqrt(E_gap·(2Λ − E_gap))                                             (dfthc_math L360-364)
T_total    = angles_toffoli + outer + inner + givens                              (L490)
givens     = 2(N−1)(2·beta−1),  beta = brot                                       (costs_prepare L147)
Q_total    = heur_persistent + J·brot + max(heur_temp, angles_temp)               (L491-493)
angles_temp= max_k num_qubits(ANGLE_k) − |selection| − J·brot                     (L405-408)
```
`chi = KEEP_BITS = 10` 写死（L139, L441）；`R,B,C` 取自 `w.shape`（L487）；
`N = 76` 来自打包 FCIDUMP；`S, beta_1` 强制用 baseline 的（`reference.load_fixed_shifts`）。

---

## 2. 提交可控量总表

### 2.1 invsqrt

| 量 | 提交能否控制 | 允许值 / 被谁钉死 | 是否进分数 | 灵敏度 |
|---|---|---|---|---|
| `width`/`x` 寄存器长度 | ✗ | 必须恰 22，且必须全是 `km.q`、互不相同（L182-192） | Q 的一部分 | — |
| 寄存器集合 | ✗ | 必须**恰好** `['x']` 一个寄存器（L182） | — | — |
| scratch 量子比特 | ✓ | 任意 id `<num_qubits`、末态必须 \|0>（L193, L277-281） | **进 Q** | 1 qubit = +0.213 GM |
| `num_qubits` | ✓（间接） | `circuit.num_qubits = max(qid)+1`（本地静态解析：`X q5` → 6，无仿真） | **Q** | 见上 |
| Toffoli 类门 | ✓ | CCX/CCZ/CSWAP 各记 1；CX/X/SWAP/Z/CZ/NEG/HMR/R 记 0 | **C** | 1 T-eq = +0.0055 GM |
| T 类 Z_POW | ✓ | 指数 ≡ 奇×1/4 圈（mod 1/2）→ 每门 1 T | **C/4** | 1 T = +0.00138 GM |
| rotation 类 Z_POW | ✓ | 其余任何指数 → 每门 `0.56log2(1/eps)+5.3` T | **C/4**，且抬高分母 eps | 1 rotation ≈ 29.9 T（边际）= **+0.041 GM** |
| Clifford Z_POW | ✓ | 指数 ≡ 0 (mod 1/2) → 0 T | 免费 | — |
| min_margin（相位余量） | ✓（间接） | `tol(x)−|err|` 的最小值；上限 `tol(max_x)=621138291`（2^-64 圈） | 通过 eps 进价 | 19.5× → 每 rotation −2.4 T |
| 条件执行 | ✓ | `if b` 的门只在 b=1 的拍计数 | 降 T | 已用掉 100.6/1560（6.4 %） |
| 经典 bit | ✓ | 任意条数（`num_bits` 不计分） | 免费 | — |

> **本地静态确认**：`X q5` 的 `num_qubits = 6` ⇒ **空号也计费**。所以 invsqrt 里不能「声明但不用」，
> 也不能用高 id 摆放寄存器；这也解释了为什么 44 就是本设计的 Q（liveness 峰值 44）。

### 2.2 dqi

| 量 | 提交能否控制 | 允许值 / 被谁钉死 | 是否进分数 | 灵敏度 |
|---|---|---|---|---|
| `num_shots` | **✗** | CLI，默认 400·256 = 102,400（L56, L459-461） | 进 `eps_plus` | 提交无权改 |
| `log2_delta` | **✗** | CLI，默认 −128（L58, L464-466） | 进 `eps_plus` | 提交无权改 |
| `(m,n,degree,r)` | **✗** | CLI，默认 4095/70/12/2016（L52-55, L453-458） | 进 `eps_plus`, 寄存器表 | 提交无权改 |
| S0..S69 | 必须 | 每个 12 个 `km.q`，两两不交，**量子**（L212-224） | **Q²** | 1 wire = +0.0211 GM |
| E0..E4094 | 必须 | 每个 12 个 `km.b`，**经典**（L212-224） | **完全不进 Q** | — |
| E 的取值 | ✓ | **verifier 从不回读**（只写不读，L378, L382） | 免费草稿纸 49,140 bit | — |
| 未声明的经典 bit | ✓ | 任意（现提交 `num_bits=66,722`） | 免费 | — |
| ancilla 量子比特 | ✓ | `num_qubits` 内所有非 S 的 q，末态必须 \|0>（L229, L384-389） | **Q²** | 1 wire = +0.0211 GM |
| Toffoli 类门 | ✓ | CCX/CCZ/CSWAP，按拍计 | **T** | 1,000 T = +0.0256 GM |
| 条件执行 | ✓ | `if b` 只在 b=1 计 | 降 T | 现提交省 873（0.24 %） |
| 失败拍数 k | ✓（间接） | `eps_plus<1/16` 才算过；k 抬高 `rep_factor` | **乘性** | 见 §5 |
| Z_POW（含 T！） | ✗ | 静态检查 `'Z_POW' in stats` → 直接 FAIL（L349-350） | 全部相位只能 Z/CZ/CCZ/NEG | — |

> **dqi 的关键否定结论**：kickmix **没有 Z 基测量指令**。可用的只有
> `HMR`（X 基拆测量 + 复位，`kickmix_instructions.md`）和 `R`（复位）。
> HMR 的结果按 `scoreinfra/circuits.py:387-398` 的模型是**均匀随机**、与比特值无关：
> 它只能做「拆测量式反计算」（把本该用 CCX 反算的 ancilla 换成 0 Toffoli 的 HMR + 免费
> conditioned CZ/CCZ），**不能用来读出 syndrome 再重装**。所以「测 syndrome→重装」这条路
> 在本指令集里不存在；随机结果还会破坏「同一地址 64 拍词表必须一致」的检查
> （chem `circuits.py:509-520`）和 dqi 的零错拍要求。`R` 作用在 \|1> 上会随机化相位
> （同文档），所以只能对已确定 \|0> 的比特用。

### 2.3 dfthcsos

| 量 | 提交能否控制 | 允许值 / 被谁钉死 | 是否进分数 | 灵敏度（见 §3 精确式） |
|---|---|---|---|---|
| `N` | ✗ | 76，来自打包 FCIDUMP（`reference.ORBITALS`） | 处处 | — |
| `R,B,C` | ✓ | `W.shape=(R,B,C)`，要求 `U.shape[:2]==W.shape[:2]`、`U.shape[-1]=76`、`H2_I=(R,C)`、`Hsym_lower=(2926,)` | heur T 与 Q | 见 §3.3 悬崖 |
| `chi` | **✗** | `KEEP_BITS=10` 写死（verify.py L139, L441） | b1,b2 → QR/QI | 提交无权改 |
| `brot` | ✓ | = `len(word_j)`，1..63（dfthc_math L411），所有 word 寄存器同宽（circuits L338-342） | givens、J·brot、inner k2 | **3.21 %/bit，但 [测] 8 bit 已是最低** |
| `J` | ✓ | word 寄存器个数，必须 `0..J-1` 连续（circuits L330-333） | J·brot，且 K=⌈75/J⌉ | **1.87 %/步，最优 J=5** |
| `K`（电路数） | ✗（被 J 决定） | 必须 `= ceil(num_angles/J) = ceil(75/J)`（circuits L465-470） | 通过 T | — |
| `selection` 宽度 | ✗ | 必须 `= (num_vectors−1).bit_length()` = 11（circuits L472-477） | **免费**（见 §3.2） | — |
| ANGLE 电路工作比特 | ✓ | 只要 `num_qubits ≤ 128`（L134, L516） | **免费** | **[测] 61→128 分数逐位不变** |
| `tree_edges` | ✓ | 任意 `(75,2)`、父先于子、根 0（dfthc_math L419-428） | 只影响精度 | 成本 0 |
| 75 个角度词 | ✓ | 整数 `<2^brot`，第 75 列以后的 padding 必须 0（circuits L541-542） | 精度 + 行序 | 见 §4 |
| `(ρ,b)` 行序 | ✓ | 与 `w` 同步置换即完全自由 | **免费** | **[测] 不变到 1e-14** |
| 单体（one-body）行序 0..75 | ✓ | 任意置换（按 \|overlap\| 一对一配 eigenvalue，dfthc_math L185-188） | **免费** | **[测] 不变到 7e-16** |
| `U` 的数值 | ✓ 但无用 | 只用形状；但仍进哈希 | — | 哈希研磨面 |
| `H1_I`,`Hsym_lower` | ✓ 但被忽略 | `load_inputs` 用 baseline 覆盖（verify.py L218） | — | 哈希研磨面 |
| 电路实现（门级） | ✓ | 任意，只要 simul 出的词表正确、相位不翻、工作区回 0 | 只影响 angles_toffoli | **1,000 T = +0.64 GM** |

被 verifier 钉死、提交无法触碰：`KEEP_BITS=10`、`QUBIT_CAP=128`、`LAMBDA_FLOOR=49.0`、
`E_GAP_FLOOR=3.914898`、`ERROR_{1,2}_THRESHOLD=0.020`、`SHOTS_PER_ADDRESS=64`、
`UPPER_ENERGY=−22140.27335`、baseline 的 `(S,β₁)`、FCIDUMP 及其 SHA-256。

---

## 3. chem 的精确算术（[算]，逐位复现官方回执）

### 3.1 复现

`model/audit_math.py` 用 verifier 自带的 `SpinFreeData_V1(R=8,B=143,C=44,N=76,chi=10,beta=8)`
得到 `outer=317, inner=4095, givens=2250, outer_p=40, inner_p=44, inner_t=303`，
于是

```
T = 8044 + 317 + 4095 + 2250 = 14706        Q = (40+44) + 5·8 + max(90,303,77) = 427
score = 46.92171681802857 · 14706 · 427 = 294643137.73357135
```

与回执 `receipt_2815083_v14.json` 的 `toffoli_count/num_qubits/score` **逐位相同**（**算**＝**测**）。

### 3.2 Q_total 的两个结构性事实

* `selection` 的 11 个比特被 `angles_temp` 减掉后**再也没有加回来**（L405-408 + L491-493），
  即地址寄存器免费。这是设计而不是 bug，但意味着「地址越宽越贵」在 chem 不成立。
* `angles_temp ≤ 128 − 11 − J·brot ≤ 117 < inner_t = 303`，所以对 (8,143,44) 这个形状
  **任何合法提交都取 `max` 的 303 分支**：

```
Q_total = 84 + 303 + J·brot = 387 + J·brot          (8,143,44) 精确、无条件成立
```

### 3.3 brot 轴：非单调悬崖（[算]）

| brot | givens | inner T | inner temp | T_total | Q_total | score / 现价 |
|---:|---:|---:|---:|---:|---:|---:|
| 4 | 1050 | 4095 | 303 | 13506 | 407 | −12.46 % |
| 5 | 1350 | 4095 | 303 | 13806 | 412 | −9.42 % |
| 6 | 1650 | 4095 | 303 | 14106 | 417 | −6.33 % |
| **7** | 1950 | 4095 | 303 | 14406 | 422 | −3.19 % |
| **8** | 2250 | 4095 | 303 | 14706 | **427** | 0 |
| 9 | 2550 | 2991 | **606** | 13902 | **735** | **+62.7 %** |
| 10 | 2850 | 2991 | 606 | 14202 | 740 | +67.4 % |
| 12 | 3450 | 2991 | 606 | 14802 | 750 | +76.8 % |

原因：`find_qroam_size_to_minimize_global_temp_ancilla`（costs_prepare L84-99）用
`ceil(log2(RC·ceil(B/2^k2))) + (2^k2−1)·b2 < beta·(N−1)` 选 `k2_opt`。
本形状 `beta·75 = 600`，而 `k2=5` 需要 `600 < 600`（差 1，刚好不成立）→ 停在 `k2=4`（temp 303）。
`brot ≥ 9` 时约束放宽到 `>600`，`k2` 跳到 5，temp 变 606。**所以 brot 只能往下走**
（想靠加大 brot 换精度是灾难性的）。同理 `B ≤ 128` 会让 `b2 = 18`，`31·b2 = 558 < 600`
→ `k2=5` → Q 约 +270；这就是 (8,143,44) 里 B=143 的来源。

### 3.4 J 轴：metric 完全无关，只有成本

**[测]** 同一份词表重切成 J=5/8/13/14 后，`error_1 = 19.999993360335144 mHa`、
`error_2 = 19.999999648293347 mHa`、`Λ = 283.14581063582807`、`E_gap = 3.9148981125363207`、
`λ_eff = 46.92171748806728` **四次逐位相同**；`Q_total` 依次为 427 / 451 / 491 / 499。

```
J=5  : selection=11, J·brot=40,  angles_temp=10, heur_temp=303 → Q=427
J=8  : 11 / 64 / 10 / 303 → 451        J=13: 11 / 104 / 10 / 303 → 491
```

三个推论：
1. `Q_total = 387 + 8J`（与 §3.2 的公式一致，实测三点）；
2. **J 对精度零影响** ⇒ 换 J 无需重拟合，是纯成本旋钮；
3. `QUBIT_CAP` 与 J 交互：`11 + 8J + 工作比特 ≤ 128`。参考 QROM 用 10 个工作比特，
   J=14 就 133 qubit → **实测被拒**：`"an ANGLE_k circuit uses 133 qubits > 128"`。
   现役 cut-based loader 用 69 个 cache qubit，所以 **J ≤ 6**。

J 的成本模型（按 15 条 plan 实测的 `264 ≈ 189 product + 69 high_cache + 6 low_computes`，
product ∝ J、fixed ≈ 75/circuit；k≥8 的 7 条是 189+69+6=264）：

| J | K | 估 angles T | Q | score / J=5 |
|---:|---:|---:|---:|---:|
| 3 | 25 | 9420 | 411 | +6.2 % |
| 4 | 19 | 8596 | 419 | +2.7 % |
| **5** | **15** | **7920** | **427** | **0** |
| 6 | 13 | 7847 | 435 | +1.4 % |
| 8 | 10 | 7548 | 451 | +2.9 % |
| 13 | 6 | 6796 | 491 | +6.1 % |
| 25 | 3 | 6120 | 587 | +20.5 % |

注：仅当 loader 成本由「地址数」而非「product 数」主导时 J 才该往上走（[测] 参考 QROM 正是
这种：J=5 → T=43,202/score 8.66e8；J=13 → T=21,278/score 4.90e8，−43 %）。现役 product 型
loader 的 product ∝ J，所以 J=5 最优。**结论：J 轴在 J=5、brot=8 处最优，且只值 ±1.4 %。**

---

## 4. chem：三个「合法但意外」的自由度（全部 [测]）

### 4.1 ANGLE 电路的工作比特免费

把参考 QROM 的 15 条电路从 61 qubit 用空闲 `X q;X q` 补到 128 qubit：

```
max_circuit_qubits 61 → 128,  angles_temp 10 → 77,  Q_total 427 → 427,
T_total 43202 → 43202,  score 865576840.6186191 → 865576840.6186191 (逐位相同)
```

⇒ **loader 可以把 128−11−J·brot 个工作比特全部用来做 product cache，Q 一分不涨。**
现役 77 个工作比特已经被用满（`high_cache=69` + `low_cache_peak=8`），所以这条不是新收益，
但它是「允许把 loader 写得更凶」的许可：任何「多花工作比特换 Toffoli」的重写都免费。

### 4.2 行序（地址分配）是免费自由度

**[测]** 在 8 个 ρ 块内把 `(w 的第 b 行, 词表第 b 行)` **同步**做字典序重排（动了 1211/1220 行）：

```
error_1 Δ = +4.5e-16   error_2 Δ = +3.5e-18   Λ Δ = 0.0   E_gap Δ = 0.0   λ_eff Δ = 0.0
```

只重排 76 个单体行也完全不变（最大相对差 7e-16）。而**只重排词表不动 w** 会立刻爆掉
（error_1 27,133 mHa、error_2 7,718 mHa）——这是一个必须记住的约束：地址重排**必须**同步置换 `w`。

价值：loader 的 product 数是「地址比特的函数」的 cube（立方体）覆盖数，**换行序等价于换一整套 cube 基**。
这是唯一一个能在 91,500 个角度值**完全不变**（因此精度、Λ、E_gap 零风险）的前提下
重打 loader 的自由度。见 §7 的实验 E1。

### 4.3 「空寄存器」也要钱

`persistent_qubits = layout.batch_size · layout.brot`（L407）只看 `word_0..word_{J-1}` 的**宽度和个数**，
所以多声明一个 word 寄存器就多付 `brot` 个 qubit（同时 K 变小）。没有「声明但不用」的免费午餐。

---

## 5. dqi：`rep_factor` 的精确价格表（[算]，用 verifier 自带的 CP 与 R 函数）

`num_shots`、`log2_delta`、`(m,n,degree,r)` 全部由 CLI 决定，提交无法控制，
所以 `rep_factor` 只随「失败拍数 k」变：

| 失败拍 k | eps_plus | rep_factor | 相对 0 错 | 打平所需的 T 节省 |
|---:|---:|---:|---:|---:|
| 0 | 8.6606e-4 | **1.191260** | 0 | 0 |
| 1 | 9.1042e-4 | 1.196731 | +0.459 % | **1,678** |
| 2 | 9.4882e-4 | 1.201388 | +0.850 % | 3,095 |
| 3 | 9.8391e-4 | 1.205584 | +1.202 % | 4,362 |
| 10 | 1.1880e-3 | 1.229011 | +3.169 % | 11,276 |
| 100 | 2.8648e-3 | 1.388657 | +16.6 % | 52,185 |

即：**第 1 个错拍值 1,678 个 Toffoli（0.043 GM）**。这条把「要不要为了省 686 T 而容忍
1 个错拍」变成一个明确的比较：686 < 1,678，所以现役 0 错拍是对的；但若将来有一个
>1,678 T 的重写带来恰好 1 个错拍，**按官方 verifier 它是净赚的**。

另外两个被钉死的点（源码级）：`score` 只用 mean executed Toffoli（L416），
`max_toffoli_count`（静态）只打印不进分（L434）；`reaction_depth`、`num_ops` 同理。

---

## 6. invsqrt：为什么 33 个 rotation 已经是下界（[算] + 用回执校准）

* `tol(max_x) = floor(2^40/√3133452) = 621,138,291`（2^-64 圈）= `2^-34.82` 圈 ⇒ 二进制相位阶梯
  的 LSB 必须到 `2^-34`（四舍五入，误差 ≤2^-35）→ 阶梯 34 级，其中 `2^-1`（Clifford）与
  `2^-2`（T=1）免费/廉价 → **理论下界 32 个 rotation**；现役 33 个，`worst_error_over_tolerance
  = 0.99956`（把余量用掉了 99.96 %），即已在 1 个 rotation 之内。
  ⇒ 「更便宜的 rotation 块」在这套代数里不可得；只有换一种非格点相位编码才可能，
  而那是一个 22 参数 / 313 万约束的逼近问题，没有已知构造。
* 每个 rotation 的**边际**价格：`d/dn[n·0.56·log2(2^64·n/(π·margin))]`
  = `0.56·(log2(1/eps) + 1/ln2) + 5.3` = `29.08 + 0.81` = **29.9 T**（加/删一个 rotation）。
* `min_margin` 的杠杆：现役 `3.179e7`，上限 `6.211e8`（19.5×）。把余量全部拿回来
  只降 2.4 T/rotation → **79 T = 19.8 T-eq = 1.16 % = +0.037 GM**，而且拿回余量本身需要更多
  rotation（自相矛盾）。所以 `margin` 轴 = 关闭。
* 已用条件执行：`max_toffoli_count=1560` vs `toffoli_count=1459.37` → **100.6 个静态 Toffoli 已被
  HMR 条件化省掉**（6.4 %）。剩下的 1459 是「必须算」的部分。
* `t_base = 2.4999`：整个 T 预算几乎全是 rotation（33×29.08 = 959.6 T）。

⇒ invsqrt 只剩 **Q** 一条路：1 qubit = +0.213 GM；44→42 = +0.43 GM（brief 已判定需重综合）。

---

## 7. 拒绝条件 × 是否留下合法更便宜的替代

| 支线 | 条件（源码） | 严格/含等号 | 合法更便宜的替代？ |
|---|---|---|---|
| invsqrt | `x` 未复原（L275） | — | 无（必须精确复原） |
| invsqrt | scratch 未回 \|0>（L277-281） | — | 可用 HMR+修正「拆测量」清位（0 Toffoli），**必须**配套 CZ/CCZ/NEG 修正 |
| invsqrt | 任一拍 `|err|>tol(x)`（L289-293） | 200M 拍逐拍 | **无抽样容限**，任何概率性设计必然失败 |
| invsqrt | `min_margin=0` 且有 rotation（L321-322） | — | 无 |
| invsqrt | 没有 Depth/门数限制 | — | 深度**不计分**（`reaction_depth` 只打印） |
| dqi | 有 `Z_POW`（L349-350） | 静态 | 无：T 也是 `Z_POW`，所以 dqi 里没有任何 T 门可用 |
| dqi | 寄存器表不符（L212-224） | 精确集合 | 无 |
| dqi | `eps_plus ≥ 1/16`（L409） | 含等号 → 拒 | **有**：k 最多可到 ~5,000（4.9 %）仍算过，只是 `rep_factor` 涨；见 §5 价格表 |
| dqi | E0..E4094 的末态 | **完全不检查** | E 是免费草稿纸（49,140 bit），合法 |
| chem | `error_1,error_2 > 0.020`（L528-535） | **含等号（=0.02 通过）** | 现役 `error_1=0.01999999336`、`error_2=0.01999999965`：**精度预算 100 % 用尽** |
| chem | `Lambda ≤ 49.0`（L366-370） | 严格 | 现役 Λ=283.1，5.8× 余量 → 该闸不 binding |
| chem | `E_gap ≤ 3.914898`（L366-370） | 严格 | 现役 `3.91489800026`（回执）/ `3.9148981125`（npz 词表）：**2.6e-10 余量** |
| chem | `angles_qubits > 128`（L539-542） | 含等号 → 128 通过 | **有**：≤128 的工作比特全部免费（§4.1） |
| chem | 寄存器契约（circuits L319-360） | 精确 | 无（`selection` 宽度、word 数/宽度都被钉死） |
| chem | 词表一致/相位不翻/工作区回 0（circuits L402-416, L509-520） | 64 拍/地址 | **有**：只按 64 拍采样，稀有失败分支可漏（见 §9 漏洞） |

**危险提示**：chem 的 `E_gap` 只在严格下限上方 **2.6e-10**，`error_1/error_2` 在含等号阈值下方
`6.6e-9 / 3.5e-10`。任何**改动词表或 w 的数值**的操作都必须重跑拟合；只有「同词表重切 J」
（§3.4）和「(w,u) 同步行置换」（§4.2，实测 Λ/E_gap 逐位不变）是零风险的。

---

## 8. 实测确认（Kaggle CPU，未修改的官方 verifier）

两个 kernel，都是 `enable_gpu=false / enable_tpu=false`，只在 `/kaggle/input` 的
competition 数据上跑官方代码；本地只做纯 numpy 算术。两个 kernel 均已 `COMPLETE`，
没有占用中的 CPU 会话（zhuating 账号已交回给 DQI 线）。

### kernel 1 — `zhuating/qcc-chem-param-audit-brot-j`

载荷：shipped `a73b25d2` 的词表/W/H2_I/tree（zlib+base64 内嵌，`U` 用同形状零阵；
`angle_k_*.kmb` 与回执 `staged_sha256` **逐字节相同**已验证）。
入口：`dfthcsos.verify.load_inputs / evaluate_words / evaluate_circuits / rejection_reason`
与 `dfthcsos.example_submission.angle_k_reference_circuit.build_angle_k_family`（官方原文件，importlib 载入）。

```
brot=8 (shipped)   err1=19.999993  mHa  err2=19.999999648 mHa  Λ=283.14581064  E_gap=3.9148981125  λ=46.921717488  PASS
brot=7 (重量化)     err1=2047.303   mHa  err2=419.519775   mHa  Λ=289.11275892  E_gap=9.8818463937  λ=74.941876545  FAIL
brot=6 (重量化)     err1=4493.303   mHa  err2=823.768037   mHa  Λ=298.56821865  E_gap=19.337306124  λ=105.70278463  FAIL
float 交叉核对      与 brot=8 逐位相同  → 重算的 8-bit 表就是电路实际装的表
                     (λ=46.921717488 vs 回执 46.921716818：相对差 1.4e-8，来自 npz 里
                      那份额外 angle_words 与电路恢复词表的末位差异；误差闸余量 3.5e-10 不受影响)
J=5  : Q=427 T=43202 score=8.655768e8   (参考 QROM，非现役 cut loader)
J=8  : Q=451 T=31022 score=6.564781e8
J=13 : Q=491 T=21278 score=4.902145e8
J=14 : angles_qubits=133 → REJECT "uses 133 qubits > 128"
brot=7 端到端 (J=5): REJECT "error_1 = 2047.3032 mHa > 20 mHa; error_2 = 419.5198 mHa > 20 mHa"
词表单独重排 (J=5): REJECT "error_1 = 27133.16 mHa" → 行序必须与 w 同步
```

### kernel 2 — `zhuating/qcc-chem-free-dof-check`

```
joint (w,u) within rho  : PASS, Δerror_1=+4.5e-16, Δerror_2=+3.5e-18, ΔΛ=0.0, ΔE_gap=0.0, λ 不变
one-body rows only      : PASS, 最大相对差 6.9e-16
words only, w untouched : FAIL, λ 46.92 → 381.43
61 qubit  → Q=427, score 865576840.6186191
128 qubit → Q=427, score 865576840.6186191   (angles_temp 10→77, 其余逐位不变)
```

### 结论性判定

1. **brot=8 是这个拟合的下限**，不是可以往下压的旋钮：`error_2` 对 brot 的弹性是
   **每比特 ×21**（8→7）和 **×2**（7→6），而下限只有 20 mHa。7 bit 需要新建一套
   能把 21× 量化偏差吸收掉的拟合（换 rank/树/权重），不是「重新量化 75 个词」能做到的。
   同时 7-bit 表连 `Λ`/`E_gap` 都会恶化到 `λ_eff=74.94`（+60 %），所以即使精度过关，
   λ 也会吃掉全部收益。⇒ **brief 里 +0.30 GM 的 brot 路线按现表实测为负，应当关闭。**
2. `Q_total = 387 + J·brot` 与 `QUBIT_CAP` 交互已实测（J=13 通过、J=14 拒）。
3. ANGLE 工作比特免费、行序免费（须与 w 同步）——两条都已实测。

---

## 9. 合法但意外的漏洞（按官方 verifier 判「过」，但违反 README 声明的契约）

### 9.1 词表可以「不精确」，因为只按 64 拍采样

`SHOTS_PER_ADDRESS=64`（circuits L399），且**同一地址的 64 拍必须一致**（L509-520）。
官方 README 明说这是「sampled evidence, not a proof」（L283-315）。所以一个
「只在 1/(2^64) 概率下失败」的构造是**合法通过**的。这条本身被文档承认，风险由 grader 的
私有 salt 承担。

### 9.2 官方回执显示 grader **没有加盐**，哈希可研磨

`receipt_2815083_v14.json` 里三个 verifier 的命令行都没有 `--salt`，而
`initial_seed(digest, salt='')  = int(digest,16)`（circuits L272-276, dqi L300-304、
invsqrt L159-163 同构）。所以 seed 完全由提交字节决定。可控的「免费哈希面」：
化学的 `U` 数值（86,944 个 float，只用形状）、`H1_I`、`Hsym_lower`（都被 baseline 覆盖但**都进哈希**，
`HASHED_NPZ_KEYS`，circuits L197）。dqi/invsqrt 可以插入成对的 `NEG`/`X q;X q`（免费、语义不变）
改 `.kmb` 哈希。

可研磨出来的东西有**两类**，量级不同：
* 计分量的种子抖动：dqi 的 `T` 是「每拍实际执行」的均值，其中 **873 T（0.24 %）来自
  条件化折扣**（静态 367,993 → 实测 367,120）；这部分随 seed 的抖动本次**没有测**，
  但上界就是这 873 T（0.24 %），研磨的期望收益远小于此。化学的 mean executed angles T
  同理（静态 4,074/次 vs 实测 4,022/次 = 1.3 % 的条件化折扣）。
* 稀有失败分支的规避（§9.1）→ 可以把一个「99.99 % 正确」的构造挑到通过，这是**真正的**
  收益来源（它允许使用带稀有失败分支的便宜构造）。

**按 README 的契约（"the grader must supply a private, unpredictable salt"）这属于违规利用**，
所以本报告只登记面，不建议使用；如果确实要用，必须先确认 grader 端的 salt 策略。

### 9.3 `E` 寄存器不检查（dqi）

`E0..E4094` 只被写、从不被读（L378 写、L382/L384-389 只读 syndrome 与 ancilla）。
契约文字（L11-12）也只要求 S 复原 + 其余量子比特回 \|0> + 相位正确。
⇒ **49,140 个经典比特是合法的免费草稿纸**（现役已经多用了 17,582 个未命名 bit）。
这不改变 T/Q，只是「经典工作区无限」这一事实。

### 9.4 `selection` 不计入 Q（chem）

见 §3.2：11 个地址比特在 `angles_temp` 里被减掉后没加回来。合法，量级 = 11 个 qubit
（按 1/Q 计约 2.6 %），但它同时是「地址宽度必须精确」的补偿，没有进一步榨取空间。

---

## 10. 排序后的杠杆表 / 需要的实验

| 排名 | 支线 | 杠杆 | Δ 公式 | ΔGM | 可行性 | 需要的实验 |
|---:|---|---|---|---:|---|---|
| 1 | chem | loader Toffoli（现 8,044/14,706） | 1,000 T | **+0.64** | 高（门级重写无 metric 风险） | 已有产品线；我的审计补充：工作比特免费(§4.1)、行序免费(§4.2) |
| 2 | invsqrt | Q 44→42 | 1 qubit = +0.213 | **+0.43** | 低（需重综合） | 已关闭（liveness 满 44） |
| 3 | chem | 行序重排后的 product 基 | 未知，product 189→? | 0.64/千 T | **新**，零 metric 风险 | **E1**：把 1211 行重排后喂给 `planner.py/climb_cuts.py`，比 `product_count` |
| 4 | chem | brot 8→7 | −3.19 % | +0.30（原估） | **实测不可得** | 若要尝试：必须重跑 7-bit 拟合（不是重量化），并接受 λ 恶化 |
| 5 | dqi | 失误容限 | 第 1 错拍 = −0.043 | 交换率 | 已量化 | 若将来有 >1,678 T 的重写，可容忍 1 错拍 |
| 6 | invsqrt | rotation 数 | 1 rot = 29.9 T（边际） | +0.041 | 33 = 阶梯下界（32 是极限） | 只有非格点相位编码能破（无构造） |
| 7 | invsqrt | min_margin | 19.5× → −79 T | +0.037 | 与 rotation 数耦合，自相矛盾 | 不建议 |
| 8 | chem | J | 1.87 %/步 | − | J=5 已最优 | 已实测关闭 |
| 9 | chem | λ_eff | 1 单位 = +0.200 | ≤+0.027（46.9216→46.786） | 已测下限 46.786 | 关闭 |
| 10 | dqi | Q | 1 wire | +0.021 | 890 = 840+50 | 关闭（需 ≤864 新一版） |
| 11 | dqi | T | 1,000 T | +0.026 | 静态 367,989 → 367,116 | 关闭（剩 873 已条件化） |
| — | 全部 | 哈希/盐研磨 | §9.2 | ≤0.1 % + 分支规避 | **不建议**（违反契约） | 需先确认 grader salt |

### 建议立刻做的唯一新实验（E1）

把 §4.2 的 1211 行置换（或任意 76! × (143!)^8 中的样本）**同步应用到 `w` 和词表**，
然后用现成的 `experiments/frontier/20261117_deep/chem/work/ds/code2/planner.py` +
`climb_cuts.py` 重跑 15 条 loader 的 product 搜索，比较 `product_count` 总和。
判据：**product 总数每降 1 就 ≈ 2 个 Toffoli（fwd+rev）≈ +0.0013 GM**。
现役 15 条电路的静态分解是 `2945 product + 1034 high_cache + 95 low_computes = 4074/pass`，
实测 4022/pass（条件化省 52）→ 8,044 T。
metric 完全不变（已实测），所以这是一个纯赚/纯亏的赌注，风险只在 planner 的搜索时间。

---

## 11. 本次未做 / 不要误读

* 没有在本地跑任何电路仿真（`km.Simulator` 只在 Kaggle 上、经官方 verifier 调用）。
* 没有提交 Kaggle、没有 push、没有发布数据集。
* brot=7 的负结论是针对「现表重量化」+「同形状 7-bit 拟合下界」的实测；**没有**排除
  「换 rank/换树/换权重后 7 bit 可行」——但那已经不是 brot 轴，而是重新做 Task 1/2。
* `Λ = 283.1` 距 `LAMBDA_FLOOR = 49` 有 5.8× 余量，所以 §5/§7 里「λ 轴 ≤ 0.29 %」沿用
  brief 的实测下限 46.786，本次没有重跑 λ 优化。

## 附：文件

* `model/MEASURED.json` — 两个 kernel 实测 JSON（本文所有 [测] 数字的原始值）
* `model/audit_math.py` + `model/AUDIT_MATH_OUTPUT.txt` — 纯算术复算（复现回执；
  brot/J/dqi/invsqrt 全部敏感度表）
* `model/make_payload.py` — kernel 载荷生成（shipped 词表 → zlib+base64）
* `model/kernel/` `model/kernel2/` — 两个 Kaggle kernel 的 `main.py` 与元数据
* `model/row_perm_proxy.py` — 行序对「break-early 段树」成本的影响（结论：参考 QROM 的
  早停条件比较的是 `delta[lo,0]` 标量，永远不触发，所以该代理无分辨力；拿到 planner 才能测，见 E1）
