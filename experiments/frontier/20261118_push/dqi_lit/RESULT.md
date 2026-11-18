# DQI 解码器前沿文献扫描（2026-11-18）

范围：找比现役 tape `575b043f`（Q=890，static 367,989，mean T 367,116）更便宜的
量子 Reed–Solomon 综合症解码电路，或可移植的算法/线路技术。
**纯文献 + 折算**：没有重测 tape、没有写生成器、没有提交、没有跑 Kaggle。

结论先说：**公开前沿没有 ≤300k T 的构造**（在我们这组参数、且 Q 不涨的约束下）。
唯一在完全相同参数 `(m,n,b,t)=(4095,70,12,35)` 上给出显式 `(T,Q)` 的论文是
arXiv:2610.22367，其 BM 解码器 **440,000 T / 1,837 Q**，`Q²T` 比我们差 **2.47×**；
官方参考实现 **5,725,461 T / 1,893 Q**，差 **33×**。
但有三条技术可移植，其中一条（history decoding）是唯一被公开数据证明能吃掉
「一整趟 Bennett 反算」的机制。技术排序在 §4，查询清单在 §5。

---

## 0. 折算口径（所有「我们折算」列都用这一节）

官方 DQI cost（`BRIEF.md`，已实测）：

```
cost = rep_factor * Q^2 * mean_toffoli ,  rep_factor = 1.1912605
ref_dqi = 24,439,463,583,672.93
GM = ( ref_inv/cost_inv * ref_dqi/cost_dqi * ref_chem/cost_chem ) ** (1/3)
```

现役：`Q=890, T=367,116.057` → `cost=3.464098e11` → `GM 28.180659`。
**DQI 腿成本降 10% ⇒ GM × 1.0357 = +1.01 GM**（比 BRIEF 的 +0.9 略乐观，用精确公式）。

`Q` 与 `T` 的等价交换（保持 cost 不变，即不掉分）：

| Q | 允许的 mean T 上限 |
|---:|---:|
| 840 | 412,121 |
| 866 | 387,746 |
| 890（现役） | 367,116 |
| 1,000 | 290,793 |
| 1,200 | 201,939 |
| 1,680（`2nb`） | 103,030 |
| 1,837（公开 BM） | 86,172 |

这张表是本次扫描最重要的一把尺：**任何把 Q 涨到 2nb=1,680 的构造，必须把 T 压到
103k 以下才不打脸**。公开 BM 在 1,837 Q 下只有 440k T，缺口 5.1×。

每单位归一化（用于跨论文折算）：

| 电路 | T | Q | T/综合症 | T/位置 | T/错误(t=35) | Q·T |
|---|---:|---:|---:|---:|---:|---:|
| **我们 575b043f** | 367,989 | 890 | 5,257 | 89.9 | 10,514 | 3.27e8 |
| 2610.22367 BM | 440,000 | 1,837 | 6,286 | 107.4 | 12,571 | 8.08e8 |
| 2510.10967 / 2610.23832 参考 | 5,725,461 | 1,893 | 81,792 | 1,398 | 163,585 | 1.08e10 |

「≤300k T」等价于 **≤4,286 T/综合症 = 73.3 T/位置 = 8,571 T/错误**。

---

## 1. （方向 3 的核心）唯一同参数、有显式门数的论文

### 1.1 Gu et al. 2026 — LLM 发现的 BM Reed–Solomon DQI 解码器
- 作者/年份：Andi Gu 等，2026-10
- arXiv：**2610.22367**，*Discovering state-of-the-art quantum circuits with large language models*
- 链接：https://arxiv.org/abs/2610.22367

**它给的是什么电路**（论文原文，SI I.1）：Berlekamp–Massey 关键方程（70 轮）
+ 条件路由（conditional routing，把「分支算术」换成「受控交换 + 单条算术路径」）
+ 分支历史解码（uncompute 时从当前状态反推每轮决策，而不是存历史）
+ 就地构造 evaluator（用 `σ;S₁..S₃₅` 覆写成 `σ;ω<35`，省掉 420-qubit 的 ω 寄存器）
+ 预算倒数 `Ψ ≡ 1/σ' (mod σ)`，把每位置的除法换成 **12 个双线性 AND**；
+ 掩码的线性部分离线对消掉 71 个位置。

**论文声称的显式数字**：

| 项 | T | 备注 |
|---|---:|---|
| BM 关键方程（正向，70 轮） | 140,000 | Fig. S1(a) 逐轮实测；同步 Euclid 对照 1.9M |
| 4,024 位置相位扫描 | 93,000 | 23 T/位置 = 11（σ(β)=0 零测试）+ 12（双线性 trace） |
| Ψ 的半次数 EEA（deg 17，E²+zO² 分解） | 44,000 **每方向** | 两次 = 88,000 |
| **总计** | **440,000** | **1,837 Q**，`Q·T=8.1e8`，10 万次测试 7 次错号 |
| 参考基线（2510.10967） | 5.1e6 | 1,938 Q |

**我们折算到 (4095,70,12,35)**：T/位置 107.4（我们 89.9）、T/错误 12,571（我们
10,514）、`Q²T` 8.08e8（我们 3.27e8，**我们好 2.47×**）。
即使把这片电路硬压进 890 Q 而保持 440k（不可能，但作为上界），cost = 4.15e11 →
**GM 26.53，仍比我们低 1.65**；按它实际的 1,837 Q 算是 **GM 16.37（−11.8）**。
⇒ 这篇论文的电路整机拿来是退步，只能拆零件。

**能否落地**：作为整机不能（Q 1,837）。作为零件能，见 §4 的技术 2/3。
工作量：若只抄「in-place evaluator + precomputed reciprocal」到我们 tape 的 Chien 段，
1–2 周可评估；若抄 BM 关键方程，3–6 周。

### 1.2 Khattar et al. 2025/2026 — 参考实现（我们 benchmark 的定义者）
- 作者/年份：Tanuj Khattar, Noah Shutty, Craig Gidney, Adam Zalcman, Nour Yosri,
  Dmitri Maslov, Ryan Babbush, Stephen P. Jordan（Google Quantum AI），2025-10
- arXiv：**2510.10967**，*Verifiable Quantum Advantage via Optimized DQI Circuits*
- 链接：https://arxiv.org/abs/2510.10967
- 同组 benchmark 论文：**2610.23832**（*Leveraging verifiable structure…*，2026-10）

**论文声称的显式数字**：

| 项 | 数字 | 出处 |
|---|---|---|
| (4095,70,12,2016) 全算法 | **5.72e6 T，1,885 Q** | 2510.10967 Table VI |
| 参考 RS 解码器（竞赛基线） | **5,725,461 T，1,893 Q** | 2610.23832 §III.B.2 |
| EEA 空间 | **2nb + O(log²n)** = 两个数组，`n+3` 个 b-bit 字 | 同上 |
| 显式 Bézout EEA | 6n 次迭代，**6n²** 次域乘 | Table III |
| 隐式 Bézout（Dialog） | **2nb**，**2n²** 次域乘 | Table III |
| 半 PEEA（RS 只需 deg<35） | 迭代上界 **6⌊n/2⌋+5 = 215**（参考用 222） | 附录 D Thm D.6 |
| GF(2¹²) 乘法 | **51 Toffoli / 1,506 CNOT**（Karatsuba+PCTOF） | Table VII |
| 每位置 | **351 T**（一次 Itoh–Tsujii 求逆 + 就地更新 σ,σ',Ω） | 2610.23832 |

**我们折算**：参考的 EEA **单趟 ≈ 1.9M T**（2610.22367 Fig. S1(a) 标注为 *forward* 的
读数；与 215 cycles × 70 域乘 × 63 T ≈ 0.95M 同量级），**两趟 ≈ 3.8M**；即使按最保守的
「两趟合计 1.9M」读，也仍是我们 322k 的 5.9×。每位置扫描 351×4,095 ≈ **1.44M T**
（2610.22367 原文「1.3 million」，与我按 315 T 求逆 + 36 T 更新复算一致）。
**关键推论（我们的）**：参考实现是**两数组**，EEA 仍要 ≥1.9M —— 我们 3 数组的
322k 便宜 **5.9–11.8×**。**这就是「3→2 数组 = −33%」是幻觉的直接反证**：
2 数组构造存在，代价是 6n 次迭代。同理扫描级我们便宜 31–62×（46k vs 1.44M）。
所以文献对我们唯一的真实威胁不是空间换法，而是 **BM 的正向关键方程只要 140k**
（我们正向 ≈153k，打平）**且它的反算几乎免费**（见 §1.1 的 440k 总账）。

**能否落地**：整机已被我们超越；其 `2nb` 论证与 MBUC-for-GF2Mul（附录 C.3，
X 基测量 + 纯 CZ 相位修正，精确）是我们 tape 已在用的东西。

### 1.3 方向 1 的直接答案：divstep / safegcd / Montgomery 的可逆量子版本
| 论文 | 构造 | 显式数字 | 数组数 | 对我们 |
|---|---|---|---|---|
| **2610.22367 §II.1 + App. A**（2026） | 素数域 divstep + **精确分支恢复**（从更新后的 `f_v,g_v` 的 2-adic 尾零反推 swap/sub 位；只对 excursion 深度 ≥5 的歧义位存历史） | 4.0e6 T / **935 Q**（512-bit 模逆） | ~1.8n | 机制可移植（见技术 1），算术不可移植 |
| **Banegas et al. 2020**（TCHES，经 2510.10967 Table III） | GF(2^m) 上 binary/Bernstein–Yang GCD 求逆 | **4nb + n** 量子位，**4n²** 次域乘 | **4** | 直接淘汰：4×1680=3,360 Q，域乘 4n²=19,600 |
| **Luo et al. 2026**，arXiv:**2604.02311** / **2607.13816** | EEA 的寄存器共享 + **长度寄存器 + 位置受控算术**（紧凑变宽存储） | 3n+6⌊log₂n⌋+O(1) 量子位；1056n³/log₂n T；256-bit ECDLP **835 Q** | **3** | 空间换法与我们 tape 同族、但仍是 3 数组 → Q 2,520，淘汰 |
| **Long et al. 2026**，arXiv:**2609.28882** | record-and-replay dialog-GCD（Jump-2 / ping-pong），safegcd 参考实现 | safegcd **741 轮，3,300 Q，7,501,932 static T**（256-bit 求逆）；ping-pong 1,338 Q / 1.128M T；阶段占比：值更新 58.1%、**replay 37.3%**、transcript 1.6% | 2 + transcript | replay 仍是「第二趟」，只省 ~18%，见技术 3 |
| **Al-Qasimi & James 2026**，arXiv:**2611.15387** | 「Quantum Euclid Algorithm」用于分解 | **无 Toffoli/qubit 表**，作者自述「does not scale in a favourable manner」 | — | 按规则**不进结论** |

**方向 1 的结论**：2 数组的可逆 EEA **是存在的**（就是 §1.2 的参考实现），但它「每步
只碰 2 个数组」的代价是 **6n 次迭代 / 6n² 次域乘**，实测单趟 **1.9M T** —— 比我们
3 数组的 322k **贵 5.9–11.8×**。所以方向 1 的前提（「2 数组 ⇒ −33% T」）在文献里不成立：
数组数与 T 不是单调关系，**迭代数 × 每步乘法数**才是。文献里的 2 数组构造只有两族：
(a) 2510.10967 的同步 EEA —— 6n 次迭代 / 6n² 次域乘（我们 1.5n²，它 6n²）；
(b) 同文的 Dialog/implicit —— 2n 次迭代、2n² 次域乘，但 dialog 本身占满另外 nb 位
（2nb=1,680 Q > 890）。两者都不划算。

### 1.4 方向 2：in-place / garbage-free 可逆 EEA
唯一给出「不产生需要 Bennett 反算的 ancilla」的严格构造是 **2610.22367 §II.1 +
Appendix A（Exact branch recovery for divstep inversion）**，但它针对**整数** divstep：

- 每步标签 `(s,b)`（swap / 被减数为奇），uncompute 时从**更新后的状态**反推：
  swap 后 `f'_v = 2g_v` 恰有一个尾零，非 swap 后 `f'_v = 2f_v` 被 4 整除 → swap 位可零成本恢复；
  非 swap 的 `b` 用 `z'` 的符号与 `g'=0` 边界恢复；**约 2/3 的决策免费**，其余按
  excursion 深度 ≥5 存历史（**1 个栈项 = 19 qubits**，溢出概率 1.0e-4）。
- 量化收益：这一机制让 4.0e6 T 的 divstep 求逆**不需要第二趟算术**（对比我们 extract
  的 170,528 T 反算）。

**能否移植到 GF(2)[x]**：结构可移植，具体判据要重推。特征 2 下 `f'_v = x·g_v` 与
`x·f_v` 都带一个 x 因子，尾零判据退化；可用「系数最低非零位的位置 / 次数差 δ」做
同类判据（Bernstein–Yang 的 δ 本身就是为了这个）。**这是公开文献里唯一一条
「吃掉一整趟反算」的路线**，但没有 GF(2^m)[x] 上的实例，属于研究级工作（2–4 周）。

### 1.5 方向 4：只算相位的解码器
**已经有，而且就是我们的 benchmark 定义**。2610.23832 Eq.(38) 明确：
`U_c|s⟩|0⟩_W = (−1)^{c·bin(e(s))}|s⟩|0⟩_W`，`c` 是经典测量记录（= 我们的 mask `M_j`）。
2610.22367 SI I.1 把它做到「不materialize e_j」：

- `⟨c_j,e_j⟩₂ = Tr(μ_j e_j)`（把 12-bit mask 折成一个域元素 μ_j）；
- 掩码的**线性部分离线对消 71 个位置**（纯 Clifford Z）；
- 余下 4,024 位置的相位 = `Tr(ν_j ω(β_j) Ψ(β_j))`，**12 个 AND**（每个 trace 项一个），
  加 11 个 AND 的零测试（σ(β)=0 谓词）⇒ **23 T/位置**。

**我们折算**：我们的 Chien 是 4,025 位置 ×(10 CCX + 1 CCZ) ≈ **11.5 T/位置**
（40,240 CCX + 5,977 CCZ = 46,217）。**我们已经是这条路的 2× 优解**，
所以「相位只需要的场景」没有可导入的增益；反过来说，这条文献证实我们的
`gf2_phase_by_product(mask=M_j)` idiom 不是浪费，公开最好构造还要多花一倍。

### 1.6 方向 5：MBUC 能否省掉 extract 的 uncompute（170,528 T）
| 论文 | 结论 | 量化 |
|---|---|---|
| **2609.31605**（Jeon, Huang, Cai, 2026-09）MBU 的纠错视角 | 后选择 MBU（只接受 zero-syndrome）可**完全去掉 uncompute oracle**，成功率 = `2^{-affine rank(garbage support)}`；确定性 MBU 的**结构条件是「原 uncompute oracle 可复用做相位修正」** | 我们的 extract 活状态 816–840 bit，支撑秩 ≥816 ⇒ 成功率 ≤2⁻⁸¹⁶ ≈ 10⁻²⁴⁶，需要 10²⁴⁶ 次重复；确定性分支 ⇒ 0 节省 |
| **2611.02345**（Yang & Yuan, 2026-11）MBUndo | 第一个「任意电路 → MBU」的**可靠自动编译 pass**：逐 ancilla 静态分析「哪些位置测量是 sound」+ 通用相位修正改写 | 只到 gadget 级（Toffoli/AND、QROM、加法器）；对 840-bit 解码器状态没有构造，也没有资源数字 |
| **2407.20167**（Luongo et al., 2024/2025 DAC） | 单 qubit 寄存器的 MBU 形式化；加法/比较/模加的形式化定理 | gadget 级；我们 tape 的 `init_and + HMR + CZ` 已在用 |

**方向 5 结论**：公开文献**没有**「测量 + 经典后处理」的严格构造能省掉 extract 的反算。
两个定理级结果都指向同一个障碍：相位修正需要「被测量寄存器的值」，而那个值就是我
们要算的 `e(s)`。后选择版本的概率代价是 `2^{-rank}`，在我们的 840-bit 上等于不可能。
这与我们已有的论证一致，现在有引用和定量形式。

---

## 2. 已查但按规则不进结论（无显式门数 / 不适用）
- **2411.12553**（Chailloux et al. 2024）*Quantum advantage from soft decoders*、
  **2511.22691** *OPI x Soft Decoders*（2025-11）：改进 OPI 的**经典可解性/硬度**，无电路门数。
- **2609.31484** COFI-DQI（2026-09）、**2510.06603** Hermitian codes（2025-10）：
  换码族（Hermitian/Suzuki/norm-trace），我们的 `(4095,70,12)` 是固定 RS，参数不可换。
  仅一条可用定性结论：Hermitian 码「每个域元素少约 1/3 量子位」——对 Q 有意义的只有换码，
  不在本任务契约内。
- **2605.00312**（DQI 综述）、**2605.16955**（DQI-Kit 软件框架）、**2611.12718**、
  **2604.15025**：复杂度/软件/界，无电路表。
- **2603.18110** *Improved quantum circuits for division*（2026-03）：整数除法
  `O(n²)→O(nm)`，但我们的 EEA 是无除法的（商由 Galois 乘加得到），无直接接口。
- **2412.12558** Jacobi factoring circuit（STOC 2025）：近线性门数的 gcd/Jacobi，
  但那是**整数**平方自由分解，规模/结构都不同，无可折算的 `(T,Q)`。
- Semantic Scholar / Google Scholar：前者 429 限流，后者不可抓取；arXiv + OpenAlex
  已覆盖其预印本与 DOI 记录（见 §5）。

---

## 3. 判定

1. **公开前沿没有 ≤300k T 的构造**（同参数、Q≤890）。
   - 同参数唯一显式 `(T,Q)`：440k/1,837（2610.22367）、5.73M/1,893（2510.10967+2610.23832）。
   - 我们在 `Q²T` 上是这两者的 2.47× / 33× 优解。
2. **我们的 EEA（322k，两趟）比文献参考 EEA（≥1.9M，两数组）便宜 5.9–11.8×**，
   扫描级便宜 31–62×（46k vs 1.44M）。真正与我们打平的是 **BM 的正向关键方程**
   （140k vs 我们正向 ≈153k），差距在**反算**：BM 整机 440k 里留给反算+清理的
   只有 ~119k，我们单反算就 170,528。⇒ 想再降 T，杠杆是**反算**，不是数组数、
   也不是正向算术。
3. **方向 5（MBUC 省反算）在文献层面是负结果**，且现在有两个定理级引用
   （2609.31605 的 `2^{-rank}`；2611.02345 的 sound 条件）。
4. **方向 4（phase-only）没有增益**：公开最好 23 T/位置，我们 11.5 T/位置。

---

## 4. 排序：3 条最有希望的技术（「若成立」的 ΔT / ΔQ / GM）

> 全部是**条件收益**，不是已验证结果。基线 `cost=3.4641e11, GM=28.180659`。

### 技术 1 — EEA 分支历史解码（吃掉反算趟）
来源：**2610.22367 §II.1 + App. A**（整数 divstep 的 exact branch recovery），
移植目标：我们 extract 的 170,528 T 反算趟。

- 若成立：反算趟从 170,528 T 降到「决策重放」量级（论文里 19 qubits 历史 + 纯控制），
  保守取 −150k；**ΔT = −150k → T≈217k，ΔQ = +0（19–70 bit 历史可放进 50-word pool），
  GM 33.58**（cost 2.05e11，+5.40）。
- 风险/工作量：GF(2)[x] 判据要重推（尾零判据退化），且反算趟里还有真实算术（商、乘加），
  能省的是**决策部分**不是全部算术。**2–4 周**，成功率我估 25–35%。

### 技术 2 — BM 关键方程 + 就地 evaluator + 预算倒数 Ψ（压到 890 Q）
来源：**2610.22367 SI I.1**（BM 140k 正向 / Ψ 44k×2 / 扫描 93k / 就地 ω）。

- 若成立（Q 保持 890，T = 140k + 50k 反算 + 46k 我们自己的 Chien = 236k）：
  **ΔT = −131k，ΔQ = 0，GM 32.65**（cost 2.227e11）。
- 若 Q 涨到公开的 1,837：**GM 16.37（−11.8）**，这是硬约束（见 §0 表：1,837 Q 只允许 86k T）。
- 风险/工作量：BM 需要 σ 与 τ **同时活**，`2nb=1,680 Q`；我们的 890 Q 是「840 综合症
  +50 pool」，综合症必须留活（每轮重读），所以必须做**窗口化 σ/τ**才有 890 Q，而这会
  把 140k 推高。**3–6 周**，成功率 20–30%。这是内部 `RECORD.md §4y` 已判「结构上不可能」
  的那条，本次扫描确认公开实现也停在 1,837 Q。

### 技术 3 — transcript 压缩的第二趟（record-and-replay）
来源：**2609.28882**（Jump-2 / base-5 编码；261 步 → **609 qubits**，2.3 bit/步；
阶段占比 replay 37.3% vs 值更新 58.1%）。

- 若成立：把「完整 Bennett 反算 = 1.0×正向」换成「replay = 0.62×正向」，
  EEA 两趟 322k → ≈ 247k（反算 170,528 → ≈95k）；**ΔT = −75k → T≈292k，
  ΔQ = +0（35 步 × ~13 bit ≈ 455 bit，需从 50-word pool 借），GM 30.42**（cost 2.84e11，+2.24）。
- 风险：我们 tape 的反算**已经是重算式 replay**（不存商），所以真实增益可能 ≈0。
  **1–2 周**，成功率 15%。

### 为什么不是「3 数组 → 2 数组」
因为唯一的 2 数组可逆 EEA（2510.10967 Table III）要 **6n 次迭代 / 6n² 次域乘**，
它自己的参考实现实测单趟 **1.9M T**（两趟 ≈3.8M），是我们 3 数组 322k 的 **5.9–11.8×**。
**换成 2 数组会把 T 推到 1.9M 以上**。这条杠杆在文献层面关闭，而且是被「2 数组构造的
实测成本」关闭的，不是被理论论证关闭的。

---

## 5. 查过的数据库与查询（可复现）

脚本：`experiments/frontier/20261118_push/dqi_lit/scan.py`（arXiv API + OpenAlex），
输出 `scan_out/scan_raw.json`、`scan_out/index_arxiv.md`、`scan_out/index_openalex.md`。
PDF 抓取与检索：`pdfgrep.py`（pypdf 文本抽取 + 正则上下文）。

**arXiv API**（19 条查询，按 `submittedDate` 降序，全部过滤 ≥2024-01-01）：
`abs:"Reed-Solomon" AND abs:decod*` · `abs:"BCH" AND abs:"decoding"` ·
`abs:"algebraic decoding" AND abs:"quantum"` · `all:divstep` · `all:safegcd` ·
`abs:"extended Euclidean" AND abs:quantum` · `abs:"greatest common divisor" AND abs:quantum` ·
`abs:"modular inversion" AND abs:quantum` · `all:"half-gcd"` ·
`all:"measurement-based uncomputation"` · `abs:uncomputation AND abs:measurement` ·
`abs:"Berlekamp-Massey"` · `abs:"syndrome" AND abs:"quantum circuit" AND abs:decod*` ·
`abs:"polynomial arithmetic" AND abs:reversible` · `abs:Forney AND abs:quantum` ·
`abs:Chien AND abs:quantum` · `abs:"Reed-Solomon" AND abs:"quantum algorithm"` ·
`abs:Toffoli AND abs:"Reed-Solomon"` · `abs:"quantum" AND abs:"decoder" AND abs:"Toffoli" AND abs:"code"`
补充 6 条：`all:"Reed-Solomon" AND all:"qubit" AND all:"decoder"` ·
`all:"decoded quantum interferometry"` · `all:"T-count" AND all:"decoder"` ·
`all:"Peterson-Gorenstein-Zierler"`（0 命中）· `all:"BCH" AND all:"quantum circuit"` ·
`all:"Reed-Solomon" AND all:"gate count"`。

**OpenAlex**（7 条，`from_publication_date:2024-01-01`）：
`quantum Reed-Solomon decoding circuit` · `quantum BCH decoder circuit` ·
`divstep quantum circuit` · `quantum circuit greatest common divisor reversible` ·
`measurement based uncomputation` · `algebraic soft-decision decoding Reed-Solomon` ·
`syndrome decoding phase oracle quantum`。

**直接读 PDF（全文）**：2510.10967、2610.23832、2610.22367、2609.28882、2607.11713、
2611.15387、2611.02345、2609.31605。
**未查/查不到**：Google Scholar（反爬，未用）；Semantic Scholar API（429 限流，未重试成功）；
IEEE Xplore 全文（只有 DOI 元数据，无门数表）；Kaggle discussion 753185（已在
`/tmp/negledger` NR-0112 内，本轮未重读）。

**未覆盖的时间窗/类型**：2024 年以前的经典（Kaye–Zalka、Proos–Zalka、Sugiyama）只通过
2510.10967 的 Table III/IV 间接引用，未逐篇核原数；BCH/Hermitian 解码器的专文（若有）
未做专门检索，因为我们在 RS 上的参数已由 2610.22367 覆盖。
