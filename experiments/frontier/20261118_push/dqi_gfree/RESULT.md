# DQI「用 qubit 换 uncompute」三级拆解与定价

日期 2026-11-18。研究线：`dqi_gfree`（DQI，tape `575b043f`）。
账号 `zhuating`。本文件只做研究、统计与定价：**没有改 tape、没有跑官方 verifier、没有提交、没有动 `submissions/`**。
所有数字来自已经实测并落盘的 region / block 表（`dqi_algo`、`dqi_surgery`、`dqi_normeea`、`dqi_block`、`dqi_fastshift`），
本文件用 `analyze.py` 重新聚合，不重新读 479 MB tape。

---

## 0. 结论先行

**这条轴对 `575b043f` 关闭，而且不是「差一点」：**

1. **tape 里只有一个大的 uncompute**：反向 EEA = **168,577 CCX + 1,951 CCZ = 170,528 T**（把最后一个 Chien cell 归回 Chien 后）。
   它不是 NR-0265 所说的「三个 36.8k 的对」，而是**一个 170.5k 的对**。
2. **另外两级已经没有 Toffoli uncompute**：
   * synthesis（Chien）：每位置 10 CCX 是纯 compute；AND 链的 uncompute 用 **10 HMR + 10 CZ_IF**（MBUC，0 T），
     不是 10 个逆 CCX。**synthesis 的 uncompute 已经是 0**。
   * convert：本 tape 只剩 **1,856 T** 的窄口径 unconvert（宽松口径 62,675 T）；它不是公开件的 129k convert 对。
3. **任何切反向 EEA 的方案都要持有 816–840 bit 的活状态**（68–70 个 12-bit word）；
   最小的「可持有摘要」是 35 个错误值 = **420 qubit**（还要加一次 Chien 重扫或 103k T 的 syndrome 重算）。
4. 打平账（`cost ∝ Q²T`，T=367,116.057）：
   * 整个反向 EEA 170,528 T（CCX+CCZ）的打平上限是 **+326 qubit**；只算 168,577 CCX 的静态口径是 **+319 qubit**；
   * 31.42723 在 Q=890 需要 ΔT=102,425 T，打平上限 **+158 qubit**；Q=902 需要 ΔT=109,421 T，上限 **+172 qubit**。
   * 420 > 326；420 > 172。**最好的「持有」方案也差 2.4–2.7 倍**。
5. 即使把 50 个 pool qubit 全部算成免费、并假设 syndrome 重算免费，**+370 qubit 仍需 ΔT ≥ 183,951 T**，
   而整个反向 EEA 只有 170,528 T，**短 13,423 T**；对应的 GM 是 **27.52 < 28.18**。
   最乐观的理论方案（420 q + 免费重算）是 **26.82**；可构造的 840-q 拷贝是 **22.28**。**全是净亏**。
6. 因此：**31.4 不可能来自「对 `575b043f` 做 qubit-for-uncompute」这条轴**。
   要重开，需要新一代解码器把 uncompute 的活状态从 816–840 bit 降到 **≤158 bit**（Q=890）或 **≤172 bit**（Q=902），
   即 5.2 倍的空间压缩；这是生成器级工作（估 20–40 天），不是 tape 手术。

---

## 1. 实测三段与块统计

### 1.1 region 表（静态，官方 verifier 口径）

tape `575b043f`：Q=890，ops 57,520,821，静态 T 367,989 = CCX 362,012 + CCZ 5,977，
mean T 367,116.057，`cost = 1.1912605·Q²·meanT = 346,409,762,292.72`，GM **28.180659**。

| region | op 区间 | ops | CCX | CCZ | T_static | T_mean |
|---|---|---:|---:|---:|---:|---:|
| preamble（纯经典） | 0 – 17,576,206 | 17,576,206 | 0 | 0 | 0 | 0 |
| **fwd EEA** | 17,576,206 – 30,335,416 | 12,759,210 | 153,185 | 1 | 153,186 | 153,180.12 |
| **Chien / Forney**（4,024 cells） | 30,335,416 – 35,627,262 | 5,291,846 | 40,240 | 4,024 | 44,264 | 44,216.96 |
| **rev EEA**（含最后 1 个 Chien cell） | 35,627,262 – 52,910,631 | 17,283,369 | 168,587 | 1,952 | 170,539 | 169,719.23 |
| epilogue（纯经典/reset） | 52,910,631 – 57,520,821 | 4,610,190 | 0 | 0 | 0 | 0 |
| **合计** | | 57,520,821 | **362,012** | **5,977** | **367,989** | **367,116.06** |

mean/static = **0.99763**；下面所有 ΔT 用静态块和，作为 mean ΔT 是 **0.24% 的乐观高估**（结论只会更强）。

**一个边界修正（实测，不是模型）**：`chien_trace.json` 有 4,025 行，最后一行 `n=4024` 在 op **35,627,287**，
是 10 CCX + 1 CCZ（CCZ 在 35,627,428）。它落在 `dqi_surgery` 的 rev 边界里，但按算法它是第 4,025 个 Chien cell。
所以本文件同时给两套口径：

* **region 口径**（与既有记录一致）：Chien 4,024 cells = 40,240 CCX + 4,024 CCZ；rev = 168,587 CCX + 1,952 CCZ。
* **算法口径**（本文件 §2 用）：Chien 4,025 cells = **40,250 CCX + 4,025 CCZ = 44,275 T**；
  rev = **168,577 CCX + 1,951 CCZ = 170,528 T**。总数不变。

### 1.2 块统计（CCX block：同 `(wa,wb,wt)`、CCX 间隔 ≤80 的极大段）

来源：`artifacts/20261118_push_dqi_normeea/out_sched/sched.json`，48,771 个 fwd 块 + 61,542 个 rev 块，逐块 `[size,wa,wb,wt,op]`。

| 块大小（CCX） | fwd 块 / T | rev 块 / T | 读数 |
|---:|---:|---:|---|
| 99 | 6 / 594 | 0 / 0 | 6 个 24-bit 型乘积（fwd 独有） |
| 82 | 16 / 1,312 | 2 / 164 | gap 规则合并的两个乘积 |
| **42** | **1,542 / 64,764** | **1,526 / 64,092** | GF(2¹²) 域乘法（Toom-4 = 7×6） |
| 36 | 210 / 7,560 | 212 / 7,632 | 短窗乘法 |
| 34 | 105 / 3,570 | 105 / 3,570 | 短窗乘法 |
| 24–35 | 128 / 3,184 | 113 / 2,953 | 短窗乘法（fwd 24:111, 30:11, 31:4, 33:2；rev 24:109, 25:1, 30:6, 31:2, 35:2） |
| **<24** | **46,764 / 72,201** | **59,577 / 90,176** | 控制/部分积/scratch，非满宽乘法 |
| **合计** | **48,771 / 153,185** | **61,542 / 168,587** | |

读数：

* fwd 的满宽（≥24）T = **80,984（52.9%）**，控制/小块的 T = **72,201（47.1%）**。
* rev 的满宽 T = **78,411（46.5%）**，控制/小块 T = **90,176（53.5%）**（含最后 Chien cell 的 10 CCX）。
* **两趟的乘法几乎镜像**：42-块 1,542 vs 1,526（−1.0%），36-块 210 vs 212，34-块 105 vs 105；
  但 rev 的控制/小块多 **17,975 T**，这就是 rev 比 fwd 贵 10.1% 的原因。
* 42-块的 `wa` 直方图也几乎相同（fwd: word69 328、word70 309、…；rev: 328、308、…），
  所以 rev 不是另一套算法，而是同一 EEA 的反向/重算。**rev 不是 fwd 的逐门镜像**（见 §2.2），
  但它的乘法内容和 fwd 是同一分布的。

### 1.3 一个乘法块的解剖（实测，已复核）

来源：`dqi_block/k_dump/main.py`（c132_0，op `[21,385,877, 21,387,169)`）与
`dqi_fastshift/k_run/main.py`（6 个块的 ANF + bit-slice，6/6 一致）。

```
3 个 word = 36 qubit；不碰任何其它 qubit
42 个无条件 CCX + ~1,250–1,460 个 CX（全部 Clifford，0 T）
scratch = 累加 word 的 5 个 bit（CCX 的 target）
结构：CCX(a_i,b_i → 5 个 scratch bit 之一) → CX fan-out 到 ~2–10 个输出 bit
      → 下一个 CCX 用新的线性组合 toggles 掉上一个积
张量（rev0）：GF(2¹²) 域乘法，模 0x1053 = x¹²+x⁶+x⁴+x+1，363 个 1，逐位一致
```

**关键：42 个 CCX = 42 个 rank-1 项，不是 84 个（没有 2× compute/uncompute）。**
所以「乘法块内部」没有可买的 uncompute；uncompute 只在**整趟 EEA** 的层面。

---

## 2. 三级拆解：compute / uncompute / synthesis

### 2.1 判据

三级不是按 region 硬切的，而是按**算法对象**：

| 级 | 对象 | 判据 | 位置 |
|---|---|---|---|
| **E extract（EEA）** | σ, ω（关键方程的解） | 除法梯的满宽乘法 + 商项/余因子更新；最后一个是 EEA 除法块 | fwd 主体；rev 尾部 |
| **C convert** | Forney 形式（σ′、ω/σ′ 的预因子/导数打包） | fwd 末尾的 **scaling + 两组 convolution**：`(69,5,71)…(8,5,9)` 16 块、`(0,71,69)…(0,5,4)` 16 块、`(71,67,3)…(5,2,3)` 16 块；rev 头部是它们的逆序镜像 | fwd `[29.60M, 30.335M)`；rev `[36.29M, 36.45M)` |
| **S synthesis（Chien/Forney 相位）** | 每个位置的 12-bit 零判定 + CCZ 相位 | 4,025 个 cell × (10 CCX + 1 CCZ)；AND 链由 **10 HMR + 10 CZ_IF** uncompute | Chien `[30.335M, 35.627M)` + 最后 1 cell |

**窄口径**（块模式）：convert = fwd `[29.60M, 30.335M)` 的 5,005 T；unconvert = rev `[36.29M, 36.45M)` 的 1,856 T。
**窄+控制口径**：把 rev 头部 `[35.627M, 36.45M)` 的经典/控制也算给 unconvert，7,280 T。
**宽口径**（故意放宽的上界）：fwd 最后 10/34 段 = 56,535 T；rev 最前 10/34 段 = 62,675 T。

### 2.2 实测 T

**窄口径（块模式，本文件的主口径）：**

| 级 | compute（CCX） | uncompute（CCX） | synthesis |
|---|---:|---:|---:|
| E extract | **148,180** | **166,721** | — |
| C convert | **5,005** | **1,856** | — |
| S synthesis | 40,250 CCX | **0** | **4,025 CCZ**（44,275 T 总计） |
| 合计 | 193,435 CCX | 168,577 CCX | 4,025 CCZ |

（另有 fwd 的 1 CCZ + rev 的 1,951 CCZ，都是相位修正；加上 Chien 的 4,025 CCZ = 5,977，才是静态总 T 367,989 的全部 CCZ。
表中 synthesis 列只列 Chien 的 CCZ。）

**窄+控制口径：** extract 148,180 / **161,297**；convert 5,005 / **7,280**；synthesis 同上。

**宽口径（10/34 段，故意高估 convert）：**

| 级 | compute（CCX） | uncompute（CCX） | synthesis |
|---|---:|---:|---:|
| E extract | 96,650 | 105,902 | — |
| C convert | 56,535 | 62,675 | — |
| S synthesis | 40,250 CCX | **0** | 4,025 CCZ |

两套口径的结论完全一致（§3）。**窄口径的物理依据更强**：fwd 的最后 42-块在 29.804M，
之后到 30.151M 只剩小块/经典；29.655–29.804M 的三组 42-块是固定的线性变换（scaling + convolution），
不是 EEA 的除法。rev 的 36.295–36.44M 是这三组在逆序下的镜像：
`(71,67,3)…` 先出现、`(0,71,69)…` 后出现，正好是 fwd 的逆序。这就是 convert/unconvert。

### 2.3 为什么 synthesis 的 uncompute 是 0（实测）

一个 Chien cell 的完整结构（`win2_chien_block1.txt`，op 30,335,009–30,335,416）：

```
X 12 个 σ 位（补码）                          # 0 T
10 × ( R 一个 ancilla; CCX 链一步 )           # 10 CCX compute；10 R 是 free reset
CCZ(Q888, σ[11], e_j[0])                     # 1 CCZ = 相位
12 × 条件 CX（Forney 预因子）                 # 0 T
10 × ( HMR 一个 ancilla; CZ_IF )              # MBUC uncompute，0 T
X 12 个 σ 位（还原）                          # 0 T
```

region census 的精确对应：

| 量 | Chien region | 每 cell |
|---|---:|---:|
| CCX | 40,240 | **10** |
| CCZ | 4,024 | **1** |
| HMR | 40,240 | **10** |
| CZ（全部 `_IF`） | 40,240 | **10** |
| R | 40,240 | **10** |

**10 个 CCX 是 compute，10 个 HMR + 10 个 CZ_IF 是 uncompute，Toffoli 成本 0。**
如果作者用 10 个逆 CCX 来 uncompute，Chien 会多 **40,250 T（+11% T，约 −0.95 GM）**。
tape 已经把这个「最便宜的 pair」用 MBUC 拿掉了。**synthesis 级没有可买的 uncompute。**

### 2.4 为什么 EEA 的 uncompute 不能用 MBUC 拿掉

MBUC 的 HMR 是 **X 基测量 + reset**，测量结果是公平随机位（NR-0084 实测：replay HMR 记录可用 0 T；
`bit_store` 的 control 必须是 classical，不能相干读 qubit；没有 qubit→classical 的相干拷贝）。
MBUC 能消掉的是**乘积/相位的 uncompute**（Chien 的 AND 链），
不能消掉**数据置换的 uncompute**（EEA 要把 840-bit 的 syndrome 原样还回去）。
反向 EEA 是数据置换，不是相位 gadget；这是它能被 MBUC 替代与否的分界线。

### 2.5 公开件「三对」的对照（只作价格参考，不当作本 tape 的结构）

NR-0265（Syed v12，384,003 T / 889 Q）：81% T 是域乘法，**三个 compute/uncompute 对占其中 86%**，
即 0.86×0.81×384,003 ≈ **267,500 T**，平均每对 ~89k（compute+uncompute），uncompute 半边 ~44.6k。
本 tape 的 **全部** uncompute 是 170,528 T；差额 ~97k，正好对应：
synthesis 的逆链（~40.3k，已用 MBUC 拿掉）+ convert 的公开件 unconvert 65.7k 与本 tape 1.9–7.3k 的差（~58–63k）。
也就是说：**本 tape 不是「少了三对」，而是已经把便宜的两对（synthesis、convert）拿掉了，只剩最贵的一对（extract）。**
这个 accounting 与 NR-0083（convert 63,336 + unconvert 65,674）和 NR-0188（Chien 4,025×11 T）一致，
但它是**一致性检查**，不是逐条证明；本文件的决定性论证仍在 §3 的 tape 自身测量。

**任务书阶梯与本 tape 的对应（关键）：**

| 任务书行 | ΔT | 任务书 k | 本 tape 上最接近的对象 | 实测 ΔT | 状态 |
|---|---:|---:|---|---:|---|
| 1 对 | 36,800 | +48 | synthesis 的逆 AND 链（若用 10 逆 CCX/cell） | 40,250 | **已经是 0**（10 HMR + 10 CZ_IF） |
| 2 对 | 73,600 | +100 | synthesis + convert（40,250 + 7,280） | 47,530 | **synthesis 0；convert 7.3k** |
| 3 对 | 110,400 | +159 | ≈ 31.4 目标（102.4k） | 102,425 | **需要砍 extract 的 62%** |
| convert 整对 | 129,000 | +214 | 公开件 888q 的 convert 对；本 tape | 6,861 | **已压到 1/19** |

所以任务书的阶梯本身没有算错；错的是**它在本 tape 上的映射**：本 tape 不是「三对都还在」，
而是「便宜的两对已经拿掉，只剩最贵的一对」。31.4 落在「3 对」那一行，但本 tape 的 extract 一对就有 161–167k，
比「3 对」的总和还大。**这就是 31.4 与 28.18 之间的真实缺口。**

---

## 3. 逐级可行性：为什么 420 qubit 也不够

### 3.1 打平公式与实测上限

`score ∝ Q²·meanT`。去掉 ΔT 的 uncompute、加 k qubit，打平条件：

```
(890+k)²/890² = T/(T−ΔT),   T = 367,116.057
k_max(ΔT) = 890·(sqrt(T/(T−ΔT)) − 1)
```

| ΔT | 来源 | k_max（mean 口径） | k_max（静态口径） |
|---:|---|---:|---:|
| 1,856 | convert 窄 | 2.3 | 2.3 |
| 7,280 | convert 窄+控制 | 9.0 | 8.9 |
| 62,675 | convert 宽 | 87.3 | 87.1 |
| 105,902 | extract 宽 | 165.1 | 164.6 |
| 161,297 | extract 窄+控制 | 298.6 | 297.5 |
| 166,721 | extract 窄 | 314.6 | 313.4 |
| 168,577 | 反向 EEA（只算 CCX） | 320.2 | **319.0** |
| **170,528** | **整个反向 EEA（CCX+CCZ）** | **326.2** | **325.0** |
| 102,425 | 31.42723 在 Q=890 所需 | 158.1 | 157.7 |
| 109,421 | 31.42723 在 Q=902 所需 | 172.3 | 171.7 |

（用户任务书里的 319 是「只算 168,577 CCX、静态 T」的口径；把 1,951 CCZ 算进去是 325，
mean 口径是 326。三者都远小于下面的持有下限，结论不依赖口径。）

### 3.2 可持有的最小摘要（实测/信息量）

| 摘要 | bit 数 | qubit | 说明 |
|---|---:|---:|---|
| syndrome S0..S69 | 70×12 | **840** | verifier 逐个检查；精确、无需重算 |
| EEA 实际写过的 syndrome word | 68×12 | **816** | word 0/1 从不做 CCX target（只做 control/source）；816 是 CCX 写入的下界，CX 还可能写 word 0/1 |
| σ + ω | 35+35 words | 840–852 | σ 次数 ≤35；ω 次数 ≤34 |
| σ 单独 | 35 words | **420–432** | 首项归一后可 35 word |
| 35 个错误值 | 35×12 | **420** | 位置需 Chien 重扫；值域 1..4095 需 12 bit |
| 错误值 + 位置 | 35×24 | 840 | 一遍式 |
| Chien 活跃窗口 | 32×12 | **384** | `x_word_distinct` 实测 32 个 word（下界，不是完整 EEA 输出）；需重跑 Chien + 重算 S |

**为什么 420 是「最小摘要」而不是「足够摘要」：**

* 打平整个反向 EEA 需要 **≤326 qubit**（mean；CCX-only 静态 319）。420 > 326。
* 在 +420 时，打平要求 ΔT ≥ **197,666 T**；整个反向 EEA 只有 **170,528 T**，**短 27,138 T**。
* 即使把 tape 已有的 **50 个 pool qubit** 全部算成免费（实际 Chien 期间只有约 40 个可用），+370 仍要求
  ΔT ≥ **183,951 T**，**短 13,423 T**。
* 420 已经是**乐观**估计：只存值不存位置，还要一次 Chien 重扫（44,275 T）或 103k T 的 syndrome 重算。
  一遍式（值+位置，或 70-word 累加器）是 **840 qubit**，更差。

**为什么不能更小：**

* σ 是 35 个系数 ×12 bit = 420；ω 也是 420；σ+ω = 840。这是答案的信息量，不是实现浪费。
* 错误值最多 35 个（`n=70`, `l=35`；测试分布 mean 31.05，k=35 仍占 2.77%，102,400 shot 里约 2,833 次）。
  35×12 = 420 是硬下限；值域 4,095 个非零元素，12 bit 不可压。
* 84 个 syndrome bit 的「哈希/摘要」不能用于反向 EEA：反向 EEA 需要精确的 840-bit 状态，不是校验和。
* classical bit 不能帮忙：`bit_store` 的 control 必须是 classical（kickmix 文档原文），
  HMR 是 X 基测量 + reset、结果是公平随机位；没有 qubit→classical 的相干拷贝。NR-0084 已实测 replay 0 T 可用。

### 3.3 方案 A（持有输出）

| 级 | 最便宜的可行持有 | ΔQ | ΔT | 新 GM | 判定 |
|---|---|---:|---:|---:|---|
| S synthesis | 不需要（已经 0） | 0 | 0 | 28.180659 | **已经免费** |
| C convert（窄） | Chien 输入窗口 384 q | +384 | 1,856 | **22.22** | 净亏 |
| C convert（宽） | 384 q | +384 | 62,675 | **23.62** | 净亏 |
| E extract（窄） | 错误值 420 q + Chien 重扫 + syndrome 重算 | +420 | 19,546（净） | **22.18** | 净亏 |
| E extract（窄） | 错误值 420 q + 免费重算 | +420 | 166,721 | **26.65** | 净亏 |
| E extract（窄） | syndrome 拷贝 816 q | +816 | 166,721 | **22.35** | 净亏 |
| **整个反向 EEA** | 840 q 拷贝 | +840 | 170,528 | **22.28** | 净亏 |
| **整个反向 EEA（理论最优）** | 420 q + 免费重算 | +420 | 170,528 | **26.82** | 仍净亏 |
| **整个反向 EEA（最乐观）** | 370 q（信用 50 pool）+ 免费重算 | +370 | 170,528 | **27.52** | 仍净亏 |

**净 ΔT 的算法**（extract 窄口径 166,721）：
166,721 − 44,275（Chien 重扫）− 约 102,900（70×35 个常数 GF(2¹²) 乘法 ×42 T）≈ **19,546 T**。
即使把重算完全当免费，也只有 166,721 T；两者都小于 +420 所需的 **197,666 T**。
对「整个反向 EEA」170,528 做同样扣除是 170,528 − 147,175 ≈ **23,353 T**，同样远小于 197,666。

### 3.4 方案 B（融合进下一级）

* **convert → Chien**：本 tape 的 convert 只剩 5,005 T compute + 1,856 T unconvert（窄）。
  要「EEA 直接产 Forney 形式」，替代链必须 **< 5,005 T**；NR-0199 的实测替代链是
  Bezoutian 190.7k、half-degree Ψ 180.6k、skip-unconvert 180.7k、Forney per position ~455k（每方向），
  比本 tape 的整个 convert 对（6,861 T）贵 **26–66 倍**。**关闭。**
* **extract → Chien**：Chien 需要完整的 σ/ω；EEA 的系数在最后一次迭代之前一直在变，
  没有「边算边扫」的流式形式。要融合就得把 σ/ω 物化，物化就是当前的 fwd；没有省掉反向 EEA。**关闭。**
* **整对 convert 省掉**（任务书 129k 那一行）：本 tape 的 convert 对只有 **6,861 T（窄）**，不是 129k。
  129k 是公开件 888q 的 convert 对（NR-0083），本 tape 已经把它压到 1/19。**这一行的收益在本 tape 上不存在。**

### 3.5 方案 C（原地可逆，Bernstein–Yang / Montgomery / in-place BM）

* EEA 本身已经是 **1nb 原地**（70 word = 840 q + 50 pool），不是 2nb out-of-place。
  反向 pass 不是「实现浪费」，而是 in-place 可逆计算的 Bennett 价格：要还原 840-bit 输入，必须把 840-bit 中间状态
  逆着走一遍。**「原地」不等于「无 uncompute」**；只有「自逆」或「相位 oracle」才无 uncompute。
* Bernstein–Yang divstep / Montgomery 是**前向**算法，不是自逆的；它们的逆向仍然要一步步还原因子。
  公开件 NR-0234 实测：in-place BM 1.44×（最好 1.13×）、time-multiplexing 1.85×、narrower layout 1.03×，
  替代架构全部更贵。**关闭。**
* 直接相位 oracle：decoder 的相位 f(S) 是高度非线性的（根查找），没有已知的低次相位多项式；
  通用对角酉的合成仍是 compute–uncompute。**没有已知构造。**

---

## 4. 最小可行组合

**没有可行组合。** 当前 `Q²T` 就是最优：

| 方案 | Q | T | Q²T / 当前 | GM |
|---|---:|---:|---:|---:|
| **现役 575b043f** | **890** | **367,116** | **1.000** | **28.180659** |
| 反向 EEA，840 q 拷贝 | 1730 | 196,588 | 2.023 | 22.28 |
| 反向 EEA，816 q syndrome | 1706 | 196,588 | 1.968 | 22.49 |
| 反向 EEA，420 q + 免费重算 | 1310 | 196,588 | 1.160 | 26.82 |
| 反向 EEA，370 q（信用 pool）+ 免费重算 | 1260 | 196,588 | 1.073 | 27.52 |
| **31.4 目标（Q=890，ΔT=102,425）** | 890 | 264,691 | 0.721 | **31.43** |
| **31.4 目标（Q=902，ΔT=109,421）** | 902 | 257,695 | 0.721 | **31.43** |

`Q²T/当前 = (Q/890)² × (T/367,116)`；例如 840 q 行 = 3.778 × 0.536 = 2.023。

最后两行是**目标反解**，不是可构造方案：在 Q=890 时，102,425 T 的打平上限是 **+158 qubit**；
任务书的例子是 Q=902（+12）配 T≈257,900。两者都要求 uncompute 的活状态 ≤158–172 bit。
而最小的可持有摘要是 420 bit，**比目标预算大 2.4–2.7 倍**。

**「最不坏」的组合**是「420 q + 免费重算」的 26.82，仍比现役低 **1.36 GM**；
可构造的 840-q 拷贝是 22.28，低 **5.9 GM**。所以这条轴上的任何组合都不应进入候选队列。

---

## 5. 证伪门：关闭

### 5.1 每级的量化理由

| 级 | uncompute ΔT | 打平 k_max | 最小精确持有 | 差 | 判定 |
|---|---:|---:|---:|---:|---|
| **S synthesis** | **0**（MBUC HMR+CZ） | 0 | 0 | 0 | **已免费；无可动** |
| **C convert（窄）** | 1,856 | 2.3 | 384 | 167× | **关闭** |
| **C convert（窄+控制）** | 7,280 | 9.0 | 384 | 43× | **关闭** |
| **C convert（宽）** | 62,675 | 87.3 | 384 | 4.4× | **关闭** |
| **E extract（宽）** | 105,902 | 165.1 | 420 | 2.5× | **关闭** |
| **E extract（窄）** | 161,297–166,721 | 298.6–314.6 | 420 | 1.3–1.4× | **关闭** |
| **整个反向 EEA** | **170,528** | **326.2** | **420**（乐观 370） | **1.29×**（乐观 1.13×） | **关闭** |
| **31.42723 所需** | 102,425（Q=890）/ 109,421（Q=902） | 158.1 / 172.3 | 420 | **2.4–2.7×** | **关闭** |

（「整个反向 EEA」的 k_max 用 mean 口径 326.2；只算 168,577 CCX 的静态口径是 319。
两种口径都小于 420，结论不变。convert 的「差」= 384 / k_max。）

### 5.2 结论句

**「31.4 不可能来自对 `575b043f` 做 qubit-for-uncompute」——这是本轮的证伪结论。**

更精确地说：

* 31.4 需要的 ΔT 是 102–109k，恰好是任务书「3 对 = 110.4k」那一行；
* 但本 tape 只剩 **一对 170.5k**，不是三对 36.8k；便宜的两对已经被作者用
  **MBUC（synthesis）** 和 **convert 融合（convert）** 拿掉了；
* 这一对的活状态是 816–840 bit，最小摘要 420 bit；打平上限 326 bit；
* 即使把已有 pool 全部信用、把重算当免费，最乐观的 370 q 方案仍差 13.4k T（GM 27.52 < 28.18）。

### 5.3 什么能重开（下一代解码器，不是 tape 补丁）

1. **把 uncompute 活状态压到 ≤158 bit（Q=890）或 ≤172 bit（Q=902）**：
   相对现在的 816–840 bit 是 **5.2 倍**压缩。这不是「少存几个 word」，而是换算法：
   例如把 Chien 流式嵌入 EEA 的最后几轮，使 σ/ω 从未完整物化；或找到一种只留 ~13 word 垃圾的 in-place EEA。
2. **或找到直接的相位 oracle**：把 decoder 的相位写成 ≤158 ancilla 的相位多项式/代数 gadget，
   不需要还原 840-bit 中间状态。
3. **或把省下的 T 转到别的腿**：31.4 只需三腿乘积改善 1.387×；如果 invsqrt 或 chem 能各自再降 28%，
   DQI 可以不动。但 `WORKPLAN_31.md` 已把这两条腿的 tape 级杠杆实测关闭，所以这同样不是本轮能做的。

### 5.4 工作量估计

| 路线 | 估计 | 风险 |
|---|---:|---|
| 本条轴（对现 tape） | **0 天**（关闭） | — |
| 新一代「≤158 bit 垃圾」解码器 | **20–40 天** | 高；需要重写 EEA/BM + Chien 流式 + 新的 uncompute 剖面 |
| 直接相位 oracle | 数月/研究级 | 极高；没有已知构造 |
| 公开件小项打磨（NR-0065/NR-0081 等） | 1–2 天 | 低；但只有 −0.13% 级，GM +0.01 左右 |

---

## 6. 与公开负结果台账的对照（引用条目号）

台账：`manwithacat/vqcc-chemistry-negative-results`（295 条；本文件引用 `ledger.csv` 的卡片号）。

| 条目 | 实测事实 | 对本问题的含义 |
|---|---|---|
| **NR-0265** | Syed v12 384,003 T / 889 Q；81% T 是域乘法（1,376×GF(2²⁴)×99 + 2,853×GF(2¹²)×42）；三个 compute/uncompute 对占 86% | 「三对」假设的来源；但那是 384k 的公开件，不是本 tape 的 368k 结构 |
| **NR-0083** | convert 63,336 + scan 44,275 + unconvert 65,674 = 173,285 T，888 q；每方向 1,285 products + 49 inverses | 本 tape 的 convert 对只有 6.9k T，已压到 1/19；129k 那一行不适用 |
| **NR-0199** | Bezoutian 190.7k、half-degree Ψ 180.6k、skip-unconvert 180.7k、Forney/位置 ~455k；需要 <1,000 products/方向 | 方案 B 的每条替代链都比本 tape 的整个 convert 对贵 26–66× |
| **NR-0084** | replay HMR 记录可用 0 T；genuine reverse arithmetic 71,362 T；holding +25 q/epoch 约 +24.1k T-eq vs ≤6,280 省；9 epochs +225 q 约 +217k T-eq vs 42,065 省；HMR 随机 | 方案 A 在公开件上也亏；「持有」的价格与本文一致 |
| **NR-0234** | narrower 1.03×（最好 0.949×）、in-place BM 1.44×（最好 1.13×）、time-mux 1.85×、Gu 4.91×、Khattar 5.5–9.4× | 方案 C 的替代架构全部更贵 |
| **NR-0001** | 单阶段删除在算术上到不了榜首；phase-only DQI 投影 9.975、840Q 地板 10.690、angle 全免 15.980 | 需要换架构/分解，不是删一个阶段；与本轮结论同向 |

**注意**：NR-0265 的「三对」没有逐对命名；本文用它做**价格量级**对照，不把它当作本 tape 的结构证明。
本 tape 的结构证明是 §1–§3 的 region/block/cell 实测。

---

## 7. 证据与复现

### 7.1 本文件用到的已落盘测量

| 文件 | 内容 | 本文件用法 |
|---|---|---|
| `artifacts/20261118_push_dqi_normeea/out_sched/sched.json` | fwd 48,771 / rev 61,542 个 CCX 块的 `[size,wa,wb,wt,op]` | 全部块统计、level 边界、T 求和 |
| `experiments/frontier/20261118_push/dqi_algo/region_split.json` | region 边界、opcode census、mean T、CCX 块 census | region 表、mean/static、Chien 10 CCX/cell |
| `experiments/frontier/20261118_push/dqi_surgery/out/chien_trace.json` | 4,025 个 Chien cell 的 `j, ccx, ccz, x_word, n_swap` | 最后 1 cell 的边界修正、32-word 窗口 |
| `experiments/frontier/20261118_push/dqi_surgery/out/win2_chien_block1.txt` | 3 个 Chien cell 的逐 op 清单 | 10×(R,CCX)+CCZ+10×(HMR,CZ_IF) 的结构 |
| `experiments/frontier/20261118_push/dqi_block/RESULT.md` + `k_dump/main.py` | c132_0 的 1,292 op 清单（41 CCX + 1,251 CX） | 乘法块单 scratch、无 2× uncompute |
| `experiments/frontier/20261118_push/dqi_fastshift/RESULT.md` + `k_run/main.py` | 6 个块的 ANF/bit-slice，rev0 = GF(2¹²) mul | 张量确认 |
| `experiments/frontier/20261118_push/dqi/RESULT.md` + `evidence/pool_census_575b043f.json` | 50 pool wire 的 census（26 EEA + 24 product） | 持有下限与 pool 信用 |
| `/tmp/negledger/ledger.csv`（公开数据） | NR-0265/0083/0199/0084/0234/0001 | §6 对照 |

### 7.2 本地复现（小算术，不读 tape）

```bash
cd /Users/zhaohuaxiang/ccjjllt/quantum
python3 experiments/frontier/20261118_push/dqi_gfree/analyze.py
# 输出 experiments/frontier/20261118_push/dqi_gfree/summary.json
```

`analyze.py` 只读上面两个 JSON（3.4 MB + 12 KB），做块求和与 GM 算术；不导入 kickmix、不模拟、不跑 verifier。

### 7.3 关键数字的一行复核

```
fwd 153,185 CCX + 1 CCZ
Chien 40,250 CCX + 4,025 CCZ      (4,025 cells)
rev 168,577 CCX + 1,951 CCZ
sum 362,012 CCX + 5,977 CCZ = 367,989 static
mean 367,116.057; Q=890; cost 346,409,762,292.72; GM 28.180659
reverse uncompute 170,528 T; k_max(mean)=326.2, k_max(static, CCX-only 168,577)=319.0
31.42723 at Q=890 -> ΔT 102,425; k_max 158.1
smallest exact hold 420 q (35 error values); 420 > 326
best optimistic scheme +370 q -> needs ΔT 183,951 > 170,528; GM 27.52
```

---

## 8. 未决项（明确写出，不当作已解决）

1. **convert 的精确边界**：窄口径 5,005/1,856 与宽口径 56,535/62,675 之间还有约 5,400 T 的 rev-head 控制
   （`[35.627M, 36.29M)`）归属不清。它不影响结论（两种口径都关闭），但影响「convert 对」的精确报价。
   需要一次逐 op 的 ANF/线性映射提取才能钉死（约 1 个 Kaggle CPU kernel，1–2 小时）。
2. **「三对」与本 tape 的逐对映射**：NR-0265 没有逐对命名；本文的「synthesis + convert 已拿掉」是
   价格一致性检查，不是逐条证明。若要做成论文级对照，需要拿到 Syed v12 的生成器或逐对 region dump。
3. **≤158 bit 垃圾的新算法是否存在**：本文只证明「持有摘要」路线的最小值是 420；
   没有证明「流式 EEA + Chien」不能把活状态降到 158。这是下一代生成器的开放问题。
4. **其他腿**：31.4 也可能来自 invsqrt/chem；本轮按任务书只做 DQI gfree，没有重测其他腿。

---

## 9. 一句话给协调者

**这条轴已经用尽：tape 作者把能免的 uncompute 都用 MBUC/融合免掉了（synthesis 0 T、convert 6.9k T），
剩下 170.5k T 的 EEA 反向 pass 需要 816–840 bit 的活状态；最小摘要 420 bit，打平上限 326 bit。
31.4 需要 158 bit。差 2.7 倍。关闭。**
