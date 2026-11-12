# DQI 下一代解码器族判决（`20261112_next_decoder`）

日期：2026-11-12；分支 `codex/dqi-research`；工作区 `.worktree/dqi/`。
性质：**判决性分析 + 本机实测标定**（官方参考电路全量构建、kickmix 原生 gadget T 计数、
正规基秩穷举）。未构建候选 `.kmb`，未跑 102,400-shot 验证器，未提交 Kaggle。
判决见 §0；时间盒内没有找到 ≥20% 的新族，理由与硬数字见 §1–§4。

---

## 0. 结论先行

**没有 ≥20% 的结构性新族。当前最优仍是 `eae396ba`（373.53e9）。**
其中最关键的一条是本轮新标定的：**Berlekamp–Massey 路线被封死，而且它不是“错过的机会”，
是比在役族更差的族**——差一个量级。

### 0.1 BM 线索判决（用户 2026-10-16 Anthropic 文章 / arXiv:2610.22367）

本机实测官方参考电路（`data/competition/verifiers/dqi/dqi_reference_circuit.py`，
`ProosAndZalkaDecoder` + `gf2_idiv`，即“Google EEA 参考”）：

| 量 | 实测值 |
|---|---:|
| static T（`num_toffoli_like`） | **5,725,461** |
| Q | **1,893** |
| 复算 cost = R·Q²·T（R=1.19126046） | **2.444097e13** |
| 官方参考 cost | 2.443946e13（**比 1.00006**，差值即 R 取舍） |

所以文章说的“12×”换算成电路量就是 `5,725,461 / 12 = 477,122 T`。对照：

| 情形 | static/mean T | Q | cost | 相对 eae |
|---|---:|---:|---:|---:|
| 当前 eae396ba（实测） | 401,313 / 394,089 | 892 | **3.7353e11** | — |
| 论文 BM 量级，搬到我方 Q=892 | 477,122（static） | 892 | 4.52e11 | **+21.1%** |
| 同上，按 mean/static=0.982 | 468,534（mean） | 892 | 4.44e11 | **+18.9%** |
| 论文 BM 版自报 Q（1,837） | 477,122 | 1,837 | 1.92e12 | +414% |

**结论：BM 的 12× 收益是相对 Proos–Zalka 朴素 EEA（5.725M）而言；我方 `convert`
（密钥方程/定位多项式那一步）只要 60,663 T，比论文的 BM locator 便宜 7.87×**
（两方向 123,197 T，便宜 3.87×）。按 42 T/乘折算，论文 BM locator ≈ **11,360 次
GF(2^12) 乘**，而 eae 的 convert 前向只有 **≈1,148 次**。原因不是实现优劣，而是族不同：
eae 的密钥方程用的是 `exp/convert_short_hankel/phase34.py` + `final_decoder/conversion.py::convert_safe`
（short-Hankel 变体），既不是朴素 EEA，也不是 BM。

### 0.2 “公开 889Q / ~470k 是否已经是 BM 设计”——否

三条独立证据：

1. **源码词表**：整个公开生成器树（`team-1028-narrow240/source/`，含 `playbook/`、
   `final_decoder/`、`exp/`）里 `grep -rli "berlekamp|massey|discrepan"` **零命中**。
   被 `final_decoder/decode.py` 导入的求解器是 `convert_safe`（EEA/short-Hankel）与
   `exp/jet24/pro_jet.py`；`exp/r-main/narrow240/` 在这份公开树里**不存在**
   （eae 的 tag 词表来自那份未公开的树）。
2. **实测 T 不是 470k**：公开 889Q 重建件（SHA `6349d2bc…95a8`，与公开件逐字节一致）
   static = **456,456**，mean = **437,947**（`20261112_low_ancilla` §3 实测）。
3. **结构上放不下**：BM 的 σ/τ 各 36 words = 864 qubits，而 eae 的 52 个 ancilla 已
   全部记账（48 = 两个 24-bit external jet word，4 个 flag，slack=0）；892 Q 内不存在
   “σ/τ + 历史重构”以外的 BM 形态，而论文自报 1,837 Q 恰说明它没有把 BM 压进 892。

### 0.3 BM 侧“还没用上的优化”为何也无效

| 用户列出的 BM 优化 | 在本族的状态 |
|---|---|
| 只保存 1 个 19-qubit 例外值 | 本族没有 σ/τ，也没有历史栈；ancilla 只有 48+4 且全是贯穿数据 |
| 减少 Chien/Forney 每位置求逆 | scan 已是 **11 T/点 = n−1 下界**（4025×11 = 44,275），且 **0 次乘法**；每点 34 个 CX 做 parity + 11 级 AND ladder，无需求逆 |
| 共享乘法 | `20261112_external_share` 已证链步两乘积的逻辑值被 gauge 分开，上限 15 T/步且需 +24 Q（净 +4.1%）；同乘积两目标的情形在整件电路里不存在 |

---

## 1. 目标算术（把 20% / 37.8% 落到 T 上）

`score = R·Q²·meanT`，mean/static = 0.98200（eae 实测）。
`-20%` ⇔ cost ≤ 2.9883e11；`-37.8%` ⇔ ≤ 2.3230e11。

| 目标 | cost | GM | Q=892 允许 static | Q=870 | Q=850 | Q=840 |
|---|---|---:|---:|---:|---:|---:|
| eae（现在） | 3.7353e11 | 25.405 | 401,313 | 421,866 | 441,952 | 452,537 |
| −10%（最低线） | 3.3618e11 | 26.313 | 361,182 | 379,679 | 397,757 | 407,284 |
| −16.7%（GM 27.0） | 3.1115e11 | 27.000 | 334,294 | 351,414 | 368,146 | 376,964 |
| **−20%（结构性线）** | **2.9883e11** | **27.367** | **321,050** | 337,493 | 353,562 | 362,030 |
| −29.2%（GM 28.5） | 2.6446e11 | 28.504 | 284,130 | 298,681 | 312,902 | 320,396 |
| −37.8%（榜首） | 2.3230e11 | 29.761 | 249,565 | 262,334 | 274,879 | 281,442 |

乘法的必要性（eae 的 static 拆分，`frontier.py` 复算）：

| stage | static | 其中乘法 | 非乘 |
|---|---:|---:|---:|
| extract | 58,742 | 42,482 | 16,260 |
| synthesis | 31,635 | 30,984 | 651 |
| convert | 60,663 | 50,239 | 10,424 |
| scan | 44,275 | 0 | 44,275 |
| unconvert | 62,534 | 52,754 | 9,780 |
| unsynthesis | 40,429 | 38,687 | 1,742 |
| unextract | 103,035 | 73,717 | 29,318 |
| **合计** | **401,313** | **288,863 (72.0%)** | **112,450** |

- **−20% 在 Q=892 要求乘法 T ≤ 208,600 = 现在的 72.2%**（等效 12-bit 秩 ≤ 30.3）。
  即使把**全部非乘 T 归零**（含 scan 的 44,275，那已在 n−1 下界）也只到
  268.9e9（−28%）——所以 −20% 必须动乘法本身，不能靠“省控制逻辑”。
- **−37.8% 在 Q=892 只剩 249,565 static**，即乘法 T ≤ 137,115 = 现在的 **47.5%**
  （等效 12-bit 秩 ≤ 20，低于 Winograd 下界 23）。**在 Q=892 内不可达（数学下界）**；
  必须同时把 Q 压到 ≤840 且乘法砍到 86.4%（秩 ≤36.3），或 Q 更低。

## 2. 本轮新增的硬下界（都是本机实测/穷举，不是估计）

### 2.1 正规基（含 optimal normal basis）乘法族：严格更差

`nb_rank.py` 对每个 β 构造 {β^{2^i}}，判满秩后数 `n²` 个有序秩项里非零的个数
（正规基的乘法表在 Frobenius 对角移位下不变，所以这个计数就是该基下的项数上界；
非对称项 `u_t ≠ v_t` 与对称项同样只花 1 个 CCX，`mul_xor0` 只是恰好用了对称项）。

| 域 | 正规 β 数 | 最好项数 | 现役 tower | 结论 |
|---|---:|---:|---:|---|
| GF(2^4) | 8（=2 个基） | **16** | 9 | 更差 1.78× |
| GF(2^6) | 24 | **36** | 15 | 更差 2.40× |
| GF(2^12) | **1,536（全枚举）** | **144（全部都 144）** | **42** | 更差 3.43× |

ONB 的“2n−1”是*每行非零项*（硬件 AND 计数），不是双线性秩；换算到本模型反而最差。
每个最佳基都做了构造性复核（`verify=True`：全部 `n²` 个基对 + 5,000 组随机值，
在标准多项式基里按掩码逐项重算乘积），因此 144 / 36 / 16 是**可实现的项数上界**，
不是启发式计数。**正规基/ONB 这条线封闭。**

### 2.2 kickmix 原生 gadget 比手写组合更贵（实测 T）

| gadget | 实测 T | 现役手写实现 | 结论 |
|---|---:|---:|---|
| `ixor_gf2_mul` 12-bit | 63 | 42（`mul_xor0`） | 更差 1.50× |
| `init_gf2_mul` 24-bit | 189 | 99（`mul24_xor99`） | 更差 1.91× |
| `init_gf2_inverse` 12-bit | 315 | 66（`field.inverse`） | 更差 4.77× |
| `init_gf2_inverse` 24-bit | 1,323 | 192 | 更差 6.89× |
| `init_lookup` 4096×12 | 4,094 | — | 一元迭代，不可用 |
| `gf2_phase_by_product` 12-bit | **0** | 42（`phase_product`，CCZ） | 唯一更优项，但见下 |

`gf2_phase_by_product` 确实是 0 T（相位二次型只花 CZ）。但全件 CCZ 只有
6,752（v21 实测，占 1.5%），**把所有 CCZ 换成 0-T CZ 也只省 1.5%**；eae 的
unextract 里 CCZ 2,912，同量级。不构成结构性收益。

### 2.3 验证器只允许 X-basis 测量 ⇒ “测量+经典解码+相位”捷径不存在

`km.CircuitBuilder.hmr` 文档原文：“Measures each target qubit in the **X basis**
(storing the measurement outcome) and **resets** the qubit to |0>”。没有 Z 测量。
于是：

- 计算基里的 syndrome 值**无法**被读出成经典值（X 测量对基态给均匀随机位并复位），
  所以“CNOT 复制 → 测量 → 经典 RS 解码 → feedforward 相位”这条 0-T 捷径在门集层面
  就被封死；
- 反过来，正因为只有 X 测量，“测量擦除 + 相位修正”（`erase_*`）才只能用于**相位可写成
  活量子比特二次型**的场合——这正是 `gf2_phase_by_product` 的 0 T 用途，也是
  `20261111_unextract_hmr` 当年 no-go 的同一原因。

这条是**结构性**结论：DQI 不可能靠 verifier 语义取巧，只能靠算术。

## 3. 在役族的天花板：镜像界 −13.7%

eae 是“前向计算 + 反向 uncompute”结构。把反向段与纯镜像比：

| 量 | 值 |
|---|---:|
| 前向（extract+synthesis+convert，不含 scan） | 151,040 |
| 反向实际（unextract+unconvert+unsynthesis） | 205,998（**比纯镜像多 54,958 = +36.4%**） |
| 若反向就是纯镜像：static | **346,355（−13.69%）** |
| 对应 cost | 3.2238e11（**−13.7%**，GM ≈26.6） |

即：**在役族内部，把 uncompute 做到完美（零额外 Q）也只有 −13.7%**，达不到 −20%，
更达不到 −37.8%。而实现它需要把前向中间量全部留下——ancilla slack = 0（48+4 全 live），
所以连这 −13.7% 也拿不到。这与 `20261112_low_ancilla`、`20261112_decoder_family` 一致，
但给出了新的定量口径：**−13.7% 是本族结构上限，−20% 只能换算术**。

## 4. 判决与建议

1. **−20% / −37.8% 都不可达（在现有资产与已探明族内）**。硬门槛：
   Q=892 时乘法 T 必须 ≤72.2%（秩 ≤30.3）；−37.8% 甚至要求秩 ≤20 < Winograd 下界 23。
2. **BM 线索关闭**，且是“更差的族”而非机会：论文 12× 后的 477,122 T 仍比 eae 的
   密钥方程步（60,663 T）贵 7.87×；搬到 Q=892 后成本 +18.9%。
3. **唯一还剩的 ≥20% 方向**（诚实标注为研究方向，不是候选）：
   - (i) `rank(GF(2^12)) ≤ 30` 的非 tower 显式分解（下界 23，现役 42，tower 族已证 42 最小；
     `rank(GF(2^3))=6`、`rank_sym(GF(2^4))=9` 已严格证明）；
   - (ii) 每方向 ≤650 次乘的密钥方程求解器（short-Hankel 现役 ≈1,148，EEA 下界 920）；
   - (iii) 一个不需要 48 个 24-bit 外部字的解码器族（Q→840 单独给 −11.3%，与 (i)/(ii)
     任一项 10% 叠加即 −20%）。
   三者都需要新构造 + 全量验证；本时间盒内没有可构建的候选。
4. **可立即拿到的量级只有 −1.5% 级微优化**（CCZ→CZ 0-T 相位、Q−4 flags），
   远低于最低线 −10%，不建议投入。

## 5. 验证范围（严格区分）

- **本机实测**：官方参考电路全量构建（`reference.kmb`，5,725,461 T / 1,893 Q，
  `operation_statistics()`）；6 个 kickmix 原生 gadget 的 T/Q（微电路）；
  GF(2^4/2^6/2^12) 全部正规基的项数（数学穷举：1,536 个 β 全覆盖，n² 项逐一判定）。
- **数学论证**：正规基项数 = 双线性秩的上界（Frobenius 对角不变 ⇒ 计数即项数）；
  非对称项 1 CCX 与对称项同价（`mul_xor0` 的 pivot 结构，源码 L486-500）。
- **未做**：没有构建任何新整件候选；未跑 `verify_submission_dqi.py`（102,400 shot）；
  没有 PASS/FAIL；未提交 Kaggle；未 push。
- 引用的 eae/v21 数字来自本仓库既有实测记录（`20261112_mulrank`、`20261112_decoder_family`、
  `20261112_low_ancilla`、`20261112_external_share`），本实验未重测。

## 6. 复现

```bash
cd /Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dqi

# 1) 参考电路（Google EEA / Proos–Zalka）全量 T/Q：5,725,461 T / 1,893 Q，~3 s
.venv/bin/python data/competition/verifiers/dqi/dqi_reference_circuit.py \
    artifacts/20261112_next_decoder/reference.kmb

# 2) 正规基秩穷举（n=12 全 1,536 个正规 β，~40 s）
.venv/bin/python experiments/dqi/20261112_next_decoder/nb_rank.py 4 6 --out artifacts/20261112_next_decoder/nb_rank_small.json

# 3) kickmix 原生 gadget T 计数（秒级；inline 脚本，见本文件 §2.2 的表）
#    init_gf2_mul / ixor_gf2_mul / init_gf2_inverse / init_lookup / gf2_phase_by_product

# 4) 目标算术与镜像界
.venv/bin/python experiments/dqi/20261112_next_decoder/frontier.py
```

产物：`artifacts/20261112_next_decoder/{frontier.json, reference.kmb, nb_rank_small.json}`（gitignored）；
入 Git 副本：`experiments/dqi/20261112_next_decoder/results/frontier.json`。

## 7. 文件

| 文件 | 作用 |
|---|---|
| `frontier.py` | 目标算术：允许 static、乘法 T 上限、等效秩、镜像界 |
| `nb_rank.py` | 正规基乘法项数穷举（含双线性验证） |
| `results/frontier.json` | 入 Git 的数字汇总 |
