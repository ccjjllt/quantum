# DQI 解码器族判决实验（`20261112_decoder_family`）

日期：2026-11-12；分支 `codex/dqi-research`；工作区 `.worktree/dqi/`。
性质：**只读分析 + 经典乘法计数 + kickmix 子块原型**。未构建全解码器候选，
未运行 102,400-shot 官方验证器，未提交 Kaggle。判决见 §0/§9。

---

## 0. 结论先行

**no-go。** 不存在一个已知的、Q≤892 且 static T≤340k 的 RS(4095,4025) 解码器族。
三条可核查的硬数：

1. **目标本身要求 convert+unconvert ≤61,884 T**（401,313−340,000=61,313 必须全部
   从 123,197 里出，等价于该块 −49.8%）。而这两段做的**扩展 Euclid 算术本身**
   （degree-17、两个 Bezout cofactor、两个方向）就需要 **1,840 次 GF(2^12) 乘 =
   77,280 T**（§5.1，`hgcd_count.py`；42 T/乘来自 `20261112_mulrank` 的实测差分）。
   **77,280 > 61,884**：任何 EEA 型 convert 都到不了目标，与实现优劣无关。
2. **half-gcd 在 n=17 不是减法而是加法**：convert 的 EEA 核心实测 ≈939–955 次乘
   （= 1,148 total − 68 setup/reduce − ~141 Hankel；与任务书 955 吻合），而
   half-gcd 是 **1,027 次乘（比核心高 7.5–9.4%）**，plain extended Euclid 是 920
   （核心只比它高 2–4%）。Karatsuba 在 9 系数上也更贵（原型 45→60 乘、Q 324→912）。
   更关键的是**目标只给得起 61,884/42 = 1,473 次乘（两方向合计，即 737/方向）**
   ——比 920 还低 20%。EEA 族在算术上就出局。half-gcd 的 textbook combine 原型
   另外实测 **Q=1,296、T=15,120**（§5.2/§5.3），Q 也不利。
3. **BM 与快速求根在 Q 或 T 上差一个量级以上**：BM 的 σ/τ 两个 36-word 寄存器
   就是 864 qubits，超过全部 52 个 ancillas 的 16.6×；论文自己的 BM 版是
   4.4e5 T / 1,837 Q（比 eae 的 892Q/401k 更差）。Berlekamp trace 的求根
   至少 155k–1.85M T，而它要替代的 scan 只有 44,275 T（§6/§7）。

**最优族 = half-gcd（本题列出的族里唯一还有算术上想象空间的）**，
但其外推是：

| 情形 | static T | Q | 相对 eae | 可行性 |
|---|---:|---:|---:|---|
| 当前 eae396ba | 401,313 | 892 | — | 已测 PASS |
| half-gcd（EEA 核心 1,027，setup/Hankel 原样） | **407.4k–408.7k** | ≥900（textbook 1,296） | +1.5–1.9% | 更差 |
| 理论最优 extended EEA（920，其余原样） | **398.4k–399.7k** | 892 | −0.4 到 −0.7% | 仍差 ≥58.4k |
| 目标 | ≤340,000（−15.3%）或 ≤347,094（−13.5%） | ≤892 | | 未达到 |

即使给“完美 extended EEA（920 次乘）+ 零额外开销”这种不可能的最好情况，也只到
**398.4k**，比 340k 高 **58.4k**；而 half-gcd 本身把 static 推到 **407–409k**
（比 eae 更差）。Q 方面，textbook half-gcd 的矩阵乘实测 1,296 qubits（1.45× 契约）；
最激进的流式改写也许能压到 ~900–960，仍在 892 线上，且不减少乘法数。
故 **no-go，不构建候选、不跑验证器**。

---

## 1. 目标与计分口径

- 计分：`score = R(ε+) · Q² · meanT`，`R(ε)=ln2 / −ln(1/2+2√ε)`。
  eae396ba：Q=892，static 401,313，mean 394,089.27，102,400-shot 0/0 →
  `R=1.19126046`，`cost=3.73535e11`（与任务书 3.7353e11 一致）。
- **任务书的 −13.5% 与 340k 不是同一条线**：mean/static = 0.98200，
  所以
  - static 340,000 → mean 333,880 → cost 3.1647e11（**−15.28%**）；
  - −13.5% → mean 340,846 → static **347,094**。
  本实验两条线都判：**340k（任务书）和 347k（真正的 −13.5%）都达不到**。
- Q 项：Q=892 ↔ `Q²=795,664`；若 Q 能降到 889/880/840，−13.5% 的 T 预算分别是
  343,184 / 350,239 / 384,390。**但 Q=840/889 都被已关闭的 low-ancilla 实验
  证伪**（48 个 24-bit external jet word + 4 flag 全程 live，52 个 ancillas slack=0，
  见 `ABANDONED.md` 与 `20261112_low_ancilla`）。所以 Q 只能取 892。

## 2. 输入与方法

| 资产 | 用途 |
|---|---|
| `artifacts/20261112_eae_candidate/dqi.kmb`（SHA `eae396ba…785bd`） | 待判决基线；`.kmx` 835 MB（临时目录，不入 Git） |
| 公开 v21 生成器 `artifacts/20261112_mulrank/source_copy/`（逐字节公开件） | 可复现的**精确**乘法普查（插桩构建，SHA 仍为 `6349d2bc…`） |
| `experiments/dqi/20261112_decoder_family/stage_mulcensus.py` | 给 `field.mul_xor0` / `mul99` / `noscratch` 插桩，按 top-level `mark()` 分阶段计数 |
| `experiments/dqi/20261112_decoder_family/block_detect.py` | 在 `.kmx` 上识别 `mul_xor0`/`tensor_xor_noscratch` 的 rank-one motif（每 motif = 1 CCX = 1 T），用于 eae 的分阶段乘法普查 |
| `experiments/dqi/20261112_decoder_family/hgcd_count.py` | 经典 GF(2^12) 多项式 EEA / half-gcd 的**精确乘法计数**（schoolbook 与 Karatsuba） |
| `experiments/dqi/20261112_decoder_family/proto_hgcd.py` | kickmix 子块原型：可逆 poly-mul / Karatsuba / matvec / matmat，实测 T/Q |
| `experiments/dqi/20261112_decoder_family/budget.py` | 汇总判决算术（读下列 JSON） |

产物：`artifacts/20261112_decoder_family/{v21_stage_mulcensus.json, v21_blocks.json,
eae_blocks.json, hgcd_count.json, proto_hgcd.json}`（gitignored），以及
**入 Git 的同一份小 JSON** `experiments/dqi/20261112_decoder_family/results/`。
`budget.py` 读后者，所以研究记录本身可离线复算。

**校验**：插桩构建的 SHA 仍是公开 `6349d2bc82eb…95a8`（Q=889、T=456,456），
所以计数不是“另一份电路”的。eae 的 motif 计数在 v21 convert 上校准：
detector 54,771 motifs vs 插桩精确 54,579（+0.35%），故 convert/unconvert 的
乘法估计误差约 ±2%。

## 3. 任务书两个前提的核对

### 3.1 convert 的 955 次乘 = EEA 递归核心，不是可省的冗余

eae convert 的 42-T 乘法实测 ≈1,148（motif 计数，用 v21 插桩校准 ±2%）。
按 `convert_safe` 的代码结构可以精确分解：

| 分量 | 来源 | 42-T 乘 |
|---|---|---:|
| EEA 递归核心 | `look_solve` / `_pre_root` / `_post_root` / `q_post` | **≈939–955** |
| setup + final | `mul(top,O[i],w[i])` ×17 + `mul(E[i+1],w[i],top)` ×17 | 68 |
| reduce | `bez_lookahead` 首尾各 17 | 34 |
| Hankel | `old.hankel` → `tri`（n=34 递归） | ≈141 |
| 合计 | 与插桩 v21 的 1,247 / motif eae 的 ≈1,148 吻合 | **1,148** |

另有 6-bit 乘法 ≈135 次（15 T/次，共 2,025 T）。
**关键：EEA 核心 ≈939–955 只比经典 extended Euclid 的 920 高 2–4%。**
所以 955 不是“低效冗余”，而是 degree-17 extended-Bezout 的算术本身；
half-gcd 的 1,027 比它还高 7.5–9.4%。真正能动的只有 68+34+141+2,025 这些
固定外设，合计 ≈7,900 T（convert 的 13%）——即使全部省掉也远不到 61k。

（`20261112_branch_recovery` 的 tag 普查 3,406 vs 插桩 5,183 的差异仍然存在，
但那是全电路的签名匹配率问题，不影响这里的 955 归属。）

### 3.2 `ABANDONED.md` 的 “decoder2: ≥190k vs extract 59k” 口径

已从 git 取回被删的 `experiments/dqi/20261111_decoder2/README.md` §2 原文核对。
它**不是** full decoder 的下界，也**不是** half-gcd 的下界：

- 覆盖对象：**朴素时域** BM/Euclid + Chien + syndrome 的**乘法次数**：
  Chien 4095×35 = 143,325 次 GF 乘；syndrome 70×4095 = 286,650（或 NTT ≈49k）；
  BM/Euclid ≥1k；合计 ≥190k。
- 定价：**幻想 1 CCX/次乘法**（“低于任何物理实现”），所以得到“≥190k paid”。
- 对照物：frontier 的 **extract 子阶段 59,169 paid**（58,977 CCX + 192 CSWAP），
  不是整颗解码器（整颗 401,313）。
- 因此该论证有两个口径错误：
  1. **整解码器乘法数 vs 单个子阶段的 paid**——extract 的 59k 门实现的是
     频域 syndrome，不是 286k 次乘法；两者不可比。
  2. 它假设 Horner 逐点求值，但真实 scan 用的是**系数预缩放**：每点只需
     34 个 CX（0 T）+ 11 个 CCX 零测试 = **11 T/点**，没有乘法（§4）。
- 它**仍然成立**的部分：朴素时域族按实测 42 T/乘是 ≥190k×42 = **≥8.0M T**，
  确实死透；但这与 half-gcd、与当前频域族都无关。

**结论：不要把 “≥190k vs 59k” 当作 half-gcd 或当前族的关闭证据。** 本实验用
真正的口径重做：§5 的 920/1,027 次乘法是 degree-17 EEA 的算术计数，§4 的
scan 44,275 T 是 11/点下界。`ABANDONED.md` 已加一行指向本节的口径更正。

## 4. eae396ba 的 T 分解（实测）

阶段 T 来自 `20261112_branch_recovery`（`.kmx` 逐行实测）；乘法 T 来自本实验的
motif 计数（每 motif 1 CCX；42 项 = 1 次 GF(2^12) 乘，99 项 = 1 次 GF(2^24) 乘）：

| stage | static T | 乘法 T（motif） | 占比 |
|---|---:|---:|---:|
| extract | 58,742 | 42,482 | 72.3% |
| synthesis | 31,635 | 30,984 | 97.9% |
| **convert** | **60,663** | **50,239** | **82.8%** |
| scan | 44,275 | 0 | 0% |
| **unconvert** | **62,534** | **52,754** | **84.4%** |
| unsynthesis | 40,429 | 38,687 | 95.7% |
| unextract | 103,035 | 73,717 | 71.5% |
| **total** | **401,313** | **288,863** | **72.0%** |

说明：
- 乘法占比是**下界**。detector 只认零 workspace 的 rank-one motif；eae 的
  extract/unextract 若用了带 scratch 的乘法 schedule，会计不到。v21 的同口径
  普查是 79.1%（精确插桩 77.9%，`20261112_mulrank` §3），故 eae 的真实乘法占比可能在 72–79% 之间。
- **scan 是 0 乘法**：`for k in 1..34: cx(A[k],A[0]); cx(B[k],B[0])` 是
  34 个 CX 的 parity，之后 11 级 AND ladder 做 12-bit 零测试。4025×11=44,275 CCX
  恰好用满，已在 n−1 下界。**任何逐点求值/求根族都必须先打败 11 T/点。**
- convert+unconvert = 123,197 T，其中乘法 **102,993 T（83.6%）**，
  非乘只有 20,204 T（CSWAP 10,236 + inverse/AND-ladder ≈10k）。所以
  “改写 convert 的控制逻辑”最多省 20k；要省 61k 必须动乘法。

## 5. 族 A：half-gcd / 分治 EEA（最有希望）

### 5.1 经典乘法计数：n=17 时 half-gcd 比 plain extended Euclid 更贵

`hgcd_count.py` 在 GF(2^12)=GF(2)[x]/(x¹²+x⁶+x⁴+x+1) 上实现并精确计数
（1 次“乘” = 1 次 `mul_xor0` = 42 T；inverse 单独计，因为电路用 65T 专用 gadget）：

| n（多项式次数） | plain Euclid | **extended Euclid（2 cofactor）** | half-gcd（schoolbook） | half-gcd（Karatsuba） |
|---:|---:|---:|---:|---:|
| 8 | 88 | 218 | 205 | 205 |
| 16 | 304 | 818 | 975 | 975 |
| **17（convert 实际）** | **340** | **920** | **1,027（+12%）** | **1,027** |
| 32 | 1,120 | 3,169 | 4,639 | 4,549 |
| 34 | 1,258 | 3,572 | 4,907 | 4,857 |
| 64 | 4,288 | 12,479 | 21,649 | 19,468 |
| 128 | 16,765 | 49,526 | 99,177 | 80,472 |
| 256 | 66,289 | 197,335 | 446,700 | 327,624 |
| 512 | 263,610 | 787,635 | 1,985,717 | 1,324,830 |

读法：
- convert 的 EEA 是 **degree 17 vs 16**（`convert_safe` 把 35-word B 拆成
  `E=B[::2]` 18 words / `O=B[1::2]` 17 words），不是 degree 34。**n=17 正是
  half-gcd 最不划算的尺寸**：矩阵乘法的常数（8 次 n/2 多项式乘）还没被
  次二次乘法摊薄。
- half-gcd 的交叉点在 **n≳1,000**（Karatsuba 到 512 仍输；要 FFT 级乘法才回本）。
  对 t=35 的 RS 解码，这个尺寸永远到不了。
- 即使把 `hgcd_count.py` 的 half-gcd 换成更精巧的实现，也改不了
  “8M(n/2) vs ~1.5n²” 的常数比；n=17 时前者是后者的 1.1×。
- Karatsuba 在 d=8（9 系数）也**实测更贵**（见 §5.2）：45→60 次乘，Q 324→912；
  d=16 也 +10%（153→168 乘），Q 648→2,388。

### 5.2 子块原型（kickmix 实测，真实 `field.mul_xor0`）

`proto_hgcd.py` 用公开件的 `field.mul_xor0`（42 T，零 workspace）搭可逆子块：

| 子块 | 内容 | Q | T | 折合乘法 |
|---|---|---:|---:|---:|
| `pmul_school_d8` | C ^= A·B，9×9 系数（d=8） | 324 | 1,890 | 45 |
| `karatsuba_d8` | 同上，递归 Karatsuba + 临时输出 | 912 | 2,520 | **60（更差）** |
| `karatsuba_d16` | d=16 | 2,388 | 7,056 | 168（schoolbook 153，**+10%**） |
| `matvec_school_d8` | (u,v) ← M·(u,v)，4 次 poly-mul | 864 | 7,560 | 180 |
| **`matmat_school_d8`** | **2×2 矩阵乘（half-gcd combine）** | **1,296** | **15,120** | **360** |

三个子块都在 kickmix 模拟器上用随机输入做了功能校验（`pmul_d4`、`karatsuba_d4`、
`matmat_d2` 全部 True；期望值由独立 GF(2^12) 卷积/矩阵乘计算）。
**这一次 combine 就是 15,120 T = eae 整段 convert（60,663）的 25%**；
它的 Q=1,296 是子块自身（3 个 2×2 矩阵）。真实电路里操作数可复用 840 个
S 寄存器，但**额外的矩阵 scratch 至少还要 432 qubits → 总 Q ≥ 840+432 = 1,272**，
仍超契约 892（§5.3）。
half-gcd 的 EEA 核心 1,027 vs 当前 ≈939–955：**+7.5–9.4%，不是节省**。
convert 的乘法 T 会从 50,239 升到 ≈53,263（+3,024），static 反而增加。

### 5.3 Q 账：half-gcd 的矩阵态放不进 892

- 契约：892 qubits = 840 S（70×12-bit，输入/输出，全程 live）+ **52 ancillas**。
  低 ancilla 实验已证 48 个 ancilla 是 24-bit jet word、4 个 flag，slack=0。
- 当前 convert 的状态：EEA 操作数 E+O = 35 words + payload u,w = 34 words =
  **69 words ≈ 828 qubits**（在 70-word / 840-qubit S 预算内），加 12-bit
  history word 与 flag，正好填满 892。
- half-gcd 的状态：操作数 35 words + 2×2 矩阵（4 个 degree≤9 多项式 =
  4×10 = 40 words）≈ **75 words = 900 qubits**——**比契约高 ~8 qubits**；
  最激进的“矩阵只乘向量、不合成 T*S”的流式写法也只能压到 ~73–75 words。
- textbook 的 `return T*S` 更贵：两个 degree≤9 矩阵（8 多项式 = 72 words）+
  输出矩阵（36 words）= 108 words = **1,296 qubits**；原型
  `matmat_school_d8` 实测 Q=1,296 正好是 3 × 4 × 9 words。
- 结论：**Q 是边际超线（~900 vs 892），textbook 形式是 1.45× 超线**；
  即使把 Q 问题用重算硬压下去（会加 T），也改不了 §5.1 的 1,027 次乘/方向
  与目标 737 次乘/方向（两方向 1,473）的差距。**T 账本身已经关门，Q 是第二道门。**

### 5.4 外推与误差带

把 convert 的 42-T 乘法拆成 EEA 核心（≈939–955）+ 固定部分（setup/reduce 68 +
Hankel ≈141 + 6-bit 2,025 T），只替换核心：

| 核心方案 | convert 42-乘法 | ΔT/方向 | 全电路 static | 相对 eae |
|---|---:|---:|---:|---:|
| 当前 EEA 核心 | 1,148 | — | 401,313 | — |
| **half-gcd（1,027）** | 1,220 | **+3,024** | **407.4k–408.7k** | **+1.5–1.9%** |
| 完美 extended EEA（920） | 1,113 | −1,470 | 398.4k–399.7k | −0.4 到 −0.7% |

- **half-gcd 的现实外推是 407–409k（更差）**，不是“降到 70k”：1,027 只替代
  EEA 核心，setup/Hankel/6-bit 都不动；它比当前核心高 7.5–9.4%。
- **误差带（EEA 族）：398.4k（完美 920，不可达）～408.7k（half-gcd）**；
  340k 在带外 ≥58.4k。任何矩阵拷贝/清理/Q 重算只会把 398.4k 往上推。
- 所以不需要构建全解码器候选；按任务书“子块外推明确 ≤340k 才构建”的规则，
  此族不满足。

## 6. 族 B：Berlekamp–Massey with retain/replace

- **算术量**：BM 迭代 2t=70 次；每次 discrepancy（≤36 乘）+ σ 更新（36）+
  τ 更新（36）≈108 乘 → **7,560 次 GF(2^12) 乘 = 317,520 T**（forward）。
  论文的优化版 locator 实测 **≈140k T**（引用任务书/arXiv:2610.22367），
  即 ~3,300 乘，已是 4.4e5 T 整颗的一部分。
- **Q**：σ、τ 各 (t+1)=36 words = 72 words = **864 qubits**；加上 70 个 syndrome
  word（840）→ **1,704 qubits**。论文自己用 **1,837 Q**。严格说，syndrome 是
  逐个消费的，理论上可用“已消费 word 覆盖”把峰值压到 ~70 words；但 σ/τ 的
  读数与更新顺序要求同时持有两者，流式实现最多把 Q 拉回 ~900–1,000 量级，
  仍不轻松，而且**不改变 T**。用我们的 4T GF(64) phase / 44-CSWAP normalizer
  也压不掉数据态的缺口（这些不是相位 gadget）。
- **与 eae 比较**：BM locator 单项 ≥140k > eae 的 convert+unconvert（123k）；
  再加 syndrome extract（58.7k）、Chien scan（44.3k）、Forney/phase、以及
  uncompute ≥2×，整颗 ≥400k；论文实测 4.4e5 T / 1,837 Q，Q²T 比 eae 差 2.3×。
- **判决：no-go（T 先输，Q 也不利）**。retain/replace 的 σ↔τ 共享只省一些
  乘法，不省“两个 36-word 多项式同时 live”的算术事实；整颗 ≥400k 的 T 账
  与论文 4.4e5 T 的实测一致。

## 7. 族 C：Berlekamp trace / 快速求根

- 目标：替代 scan 的 44,275 T。
- 算法：对 degree≤35 的 locator f，用 Tr(βx) mod f 递归分裂根；每层要算
  gcd(f, trace)（EEA）和 trace 映射。
- **T 估计**：一次 degree-35 gcd ≈ plain Euclid 1,258 乘（§5.1 表）；
  朴素“每个根一次 gcd” = 35×1,258 = **44,030 乘 = 1.85M T**；
  平衡分裂树最优 O(t² log t) ≈ 612×6 ≈ **3,700 乘 = 155k T**，
  再加 trace 计算/多项式乘。**155k–1.85M T，全部 ≫ 44,275 T**。
- **Q**：f（36 words）+ 分裂栈（任意时刻两子因子次数和 = 父次数，≥36 words）
  = **≥72 words = 864 qubits** > 52 ancillas。
- **判决：no-go**。scan 的 11 T/点是频域表示的产物；换成“求根”反而回到
  O(t²) 乘法。即使 scan 免费，static 也只剩 357,038 > 340k——**单改 scan 结构上
  不可能达标**。

## 8. 族 D：其他候选

| 族 | 乘法量（估计） | T（×42） | 备注 |
|---|---:|---:|---|
| Welch–Berlekamp（解 2t×2t 线性系统） | 70³/3 ≈ 114k | 4.8M | 高斯消元，Q 也要 2t words |
| 子积树 + 多点求值（4095 点） | ~n log²n ≈ 590k | 24.8M | 每点仍是多项式乘 |
| Chirp–z / Bluestein | ~2n log n ≈ 98k | 4.1M | 卷积长度 8191 |
| Paterson–Stockmeyer 逐点求值 | ~2√t/点 ×4095 ≈ 48k | 2.0M | 已优于 Horner，但仍 ≫ 当前 0 乘/点 |
| 频域 Chien（当前） | **0** | **44,275** | 11 T/点，n−1 下界 |

这些族连“替代 scan”都不够格，更不用说整颗 340k。**全部 no-go。**

## 9. 总判决：要想到 340k 需要什么

把 401,313 拆成“必须保留的算术”与“可省的实现开销”：

1. **单阶段充分性**（谁能单独把 401k 拉到位）：

| 删除/减半的块 | 结果 static | ≤340k? |
|---|---:|---|
| scan 全免 | 357,038 | 否 |
| convert+unconvert 减半 | 339,715 | 是（但需 −50%） |
| convert+unconvert 全免 | 278,116 | 是（但不现实） |
| synthesis+unsynthesis 全免 | 329,249 | 是（但它们 96% 是乘，且必需） |
| extract+unextract 全免 | 239,536 | 是（但它们承载 syndrome） |

   所以**唯一现实的单块路径是 convert+unconvert 减半**；而这需要每方向
   ≤30,942 T = **≤737 次 42-T 乘**，低于扩展 Euclid 的 920 次算术下界
   （§5.1）。**EEA 族在算术上被排除。**

2. **非 EEA 族**：BM 每个方向 7,560 乘（论文优化版 ~3,300），Welch–Berlekamp
   114k 乘，都 ≥ EEA 的 920；trace 求根 ≥3,700 乘、且只替代 scan（44k T）。
   全部更差；Q 账在 900–1,837（textbook/论文），也不利（§6/§7/§8）。

3. **剩下的唯一算术杠杆是降低单次乘法的 42 T**：`20261112_mulrank` 已严格证明
   `rank(GF(2^3))=6`、`42=7×6` 与 `99=11×9` 在 Chudnovsky/tower 族内最优；
   要再降只能找 rank≤34 的**非组合** GF(2^12) 分解（开放研究问题）。
   即使 rank 42→34，按 v21 的 5,183 个 12-bit 块只省 8×5,183 ≈ 41k T；
   按 eae 的块数（motif 口径约 4 千）约省 30–40k → static 360–370k，
   仍不到 340k，且需要新的显式构造 + 全量验证。

4. **Q 方向**：−1Q ≈ 887 T 等价；Q=892→889 只买 2,661 T，且 889 件已实测
   更差（`ABANDONED.md`）。Q 不能救 61k。

5. **为什么不能把 61k 拆到别的块**：scan 已在 11 T/点下界（全免也只到 357k）；
   synthesis/unsynthesis 分别 97.9%/95.7% 是乘，且没有替代族；extract/unextract
   是 48 个 24-bit jet word 的数据态（low-ancilla 已证 52 个 ancilla slack=0），
   其乘法是 42/99-T 张量（mulrank 已证秩最优）；branch-recovery 已证决策机器
   全部在 n−1 / 1-CSWAP 下界。**不存在一个 ≥10k 的、可替换的非 convert 块。**

**最终判决：no-go。** 不是“没找到实现”，而是**算术下界（主）+ Q 契约/矩阵态（次）**同时挡住：
- 目标要求 convert+unconvert ≤61,884 T；
- 该块的扩展 Euclid 算术下界是 77,280 T；
- half-gcd 的 EEA 核心 1,027 > 当前 ≈939–955（+7.5–9.4%），static 反而升到
  407–409k；完美 extended EEA（920）也只到 398.4k，仍差 58.4k；
- BM/trace/WB 更差且 Q≥864–1,704。

不构建全解码器候选，不跑 102,400-shot 验证器。

## 10. 复现

```bash
cd /Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dqi

# 1) 公开 v21 精确乘法普查（插桩构建，~4 min，SHA 必须仍是 6349d2bc…）
.venv/bin/python experiments/dqi/20261112_decoder_family/stage_mulcensus.py \
    artifacts/20261112_decoder_family

# 2) eae/v21 的 rank-one motif 普查（需先有 .kmx；dump 脚本见
#    20261112_branch_recovery/dump_kmx.py，eae 路径换成 eae 候选）
.venv/bin/python experiments/dqi/20261112_decoder_family/block_detect.py \
    $TMP/eae.kmx artifacts/20261112_decoder_family/eae_blocks.json

# 3) 经典 EEA / half-gcd 乘法计数（~3 min）
.venv/bin/python experiments/dqi/20261112_decoder_family/hgcd_count.py --trials 8
#    输出写到 artifacts/；results/ 是同一份的入 Git 副本

# 4) kickmix 子块原型（秒级）
.venv/bin/python experiments/dqi/20261112_decoder_family/proto_hgcd.py

# 5) 判决算术
.venv/bin/python experiments/dqi/20261112_decoder_family/budget.py
```

`.kmx` 放系统临时目录（eae 835 MB），不入 Git。

## 11. 验证范围

- **已做**：公开 v21 插桩构建（SHA 与公开件逐字节一致）；eae `.kmx` 的
  motif 普查（与 v21 精确值校准）；经典 GF(2^12) EEA/half-gcd 的精确乘法计数；
  kickmix 子块原型的 T/Q 实测（`proto_hgcd.py` 的电路是真实 kickmix 电路，
  T 来自 `operation_statistics().num_toffoli_like`，Q 来自 `num_qubits`）。
- **未做**：没有构建任何全解码器候选 `.kmb`；未运行
  `verify_submission_dqi.py`（102,400-shot）；无 PASS/FAIL；未提交 Kaggle。
- **估计的边界**：convert/unconvert 的 eae 乘法数是 motif 计数 × 校准因子，
  ±2%；extract/unextract 的乘法占比是下界（可能到 v21 的 79–90%）；
  half-gcd 的 1,027 是经典算法计数，不是量子电路实测（因为它 Q 不可行，
  无法构建）；398.4k 是“完美 extended EEA + 零额外开销”的乐观下界，
  不是可实现的候选。
- 计分口径：`R=1.19126046` 来自 eae 的 102,400-shot 0/0 本地 PASS
  （`artifacts/20261112_eae_candidate/verify_dqi_a.log`，main 只读引用）；
  mean/static=0.98200 是 eae 的实测比值，外推时对所有 T 假设同一比值
  （若新族条件门比例不同，mean 会偏移 ±1%，不影响判决）。
