# DQI 无收益方向总表（截至 2026-11-06，分支 `codex/dqi-research`）

**同日后续修正：** 第1.18节属于当时不完整的来源调查，q26完整列表实际有25个Python文件，另已找到旧C1源bundle和独立BM生成器。
详见[最新来源与高收益研究](../20261106_high_return_research/README.md)。不能再据本表判定所有生成器级方向都被阻断；原有局部搜索结论仍限于所述旧基线和搜索方式。

本文件是 DQI 二进制层面研究的**唯一保留记录**：所有已关闭方向的结论、
关键证据数字与重开条件都在这里。对应的脚本、中间产物与实验目录已删除
（可按 git 历史回溯）。

**唯一有收益的方向见** `experiments/dqi/20261106_leo_merge/`：
fd0ef + Leo Tang 编辑合并 → **−42 mean Toffoli**（官方验证器全量
102400 shots PASS，等价错误剖面）。本文件不重复其内容。

---

## 0. 基线事实与验证规范

- 基线 `fd0ef09e`：891 qubit，58,390,266 ops，静态 T **397,177**
  （CCX 382,636 + CSWAP 13,064 + CCZ 1,477）；CX 52.17M 不计费。
- 成本 = R(k)·Q²·meanT；R(0)=1.191260，R(1)=1.196731（+0.459%）。
- **验证噪声标尺（null-patch 实测）**：交换两条不相交 CX 的 kmx 副本，
  meanT 差 0.026，但两次跑出 0v0p / 0v1p，score 比 1.0045927 完全由 R 解释。
  ⇒ **单次官方验证的 DQI 评分噪声量级 ±0.5%，任何 <0.3% GM 的声称
  必须 ≥3 seed 全量复验**；比较必须看 meanT，不看单次 score。
- `R` 语义实测：值上是 **reset-to-0**（`X;R→0`、`R|0>→0`），
  另有随机 phase outcome（只影响 `read_phase_flipped`，不影响值逻辑）。
  `HMR` 同构：值 reset + 随机测量位。
- 投递电路的失败性质（上游公开声明）：Syed 的 891-qubit **C1/Schur**
  解码器（jday96314 的连分数 Schur 算法）对**一个稀有错误类做了近似处理**，
  作者原文见 Alex Chilton 24-80 notebook 的 provenance：
  "one rare error class is handled approximately, so the cost can rise a
  little under another salt (0 errors at the default salt here; 1 error in
  1 of 3 more salts we tried)"。我们在 shot 30178（k=35）复现的确定性失败
  与之一致。**修复需重写 Schur 解码器；生成器不可得**（5 份公开 notebook
  源码均无，jday96314/QuantumAI 仓库已不可访问）。

---

## 1. 已关闭方向（结论 / 证据 / 重开条件）

### 1.1 QQ-51T standalone 替换 — 无 drop-in 目标
kickmix 默认 `init_gf2_mul(m=12)` = 63T；Zenodo `gf2_mul_12` 可 51 CCX 发射
（2000 例 0 失配、m=4 量子级验证通过）。但 fd0ef 的乘法块是
15/25/42/70/99/126 CCX 的**分布式 tower / 标量乘**，`gf2_mul` 标记 0 个，
全电路无 63-CCX 核；25T products 块已在 Winograd 下界附近。
**重开**：生成器级重建或 EEA 块整体重综合。

### 1.2 strict 乘积复用 — 全尺度死亡
58M 行扫描：复用对 16,513；2 次、跨度 [133k,367k] 的 111 候选 **111/111 DIRTY**；
短跨度 [100,133k) 抽 300 → **0 CLEAN**。

### 1.3 跨时间乘积证明 / 后向锥枚举 — 结构性不可行
K12 窗后向切片仅 27 AND/25 线，但全锥爆炸：`q861 q847` → 885 线 /
21.5 万 AND；16M 浅候选同样 885 线 / 14.5 万 AND。解码器全程 ~885 线存活。
**重开**：R43 式单链 + CP-SAT（需上游管线）。

### 1.4 死门删除 — 相位否决
liveness 找到 156 死 CCX + 48 死 CSWAP。naive 删 12 站：value 0/0 但
**phase 130/256 + 112/256**（m=1 kickback 丢失）。CZ 纠正版 156 个中
taint 干净仅 7 个，但 a/b 在纠正前均被自身 HMR 销毁，无干净 ancilla 可借
→ **0/156 可提交**。附：全电路无 H 门，初态 |0> 下恒为基矢态。

### 1.5 fhp / multiply v / inverse / aligned / head 剖解 — 生成器级已极小
`full_head_product` 126/168/210 × 镜像对：块内仅 6 不同控制对（如
`(q792,q804)×72`），控制全程 churn，常量假设与扇出假设均否；
`multiply v` 99 CCX / 27 线；`inverse12` products 25 / norm 15 / scalar 18
（×169，全同构）；`inverse24` 70/42/58（×29）；`aligned_route` ×52 单稳定
控制 + 192 distinct 对（CSWAP 已紧）；`head_phase` ×3（42 CCX + 1452 条件 CZ）。
**重开**：生成器。

### 1.6 peephole 自逆对消 — 零命中
全文件 CCX 382,636 / CSWAP 13,064 / CCZ 1,477 扫描，**可消对 0**。
（假阳性教训：初版 214 对实为读控制线的合法对易。）

### 1.7 模板级公共子表达式 — 精确最小
`inverse12 products` 经重命名全同构（860 ops，25 CCX + 835 CX）；
ANF 精确（非采样）删除 ladder：删1 **25/25 必需**、删2 (300) **0**、
删3 (2300) **0**、删4 (12650) **0**。`norm` 15/105 全 0。
`multiply v` 删1/2/3 全 0；`fhp126/168/210` 删1（全）、删2（7875/14028/21945）
全 0，fhp126 删3（325,500）全 0。有界 2→1（2460 组）**真实 0**
（14 个原始命中全是平凡自替换，实验设计 bug 已修正）。
**重开**：3→2 或更大联合重综合（非删除型）。

### 1.8 镜像对消 — 非同构
convert/unconvert、synthesis/unsynthesis、extract/unextract 的 CCX
multiset 单向差异 13k~76k 门（如 syntax 31,497 vs unsynthesis 38,161），
**不是镜像程序**，无对消空间。

### 1.9 恒零门（R47 式） — 全是稀有分支
2000-shot 三分布（稠密/稀疏/零综合症）一致掩码下 4495 个候选；
SAT 判 `P==0`（断 AND==1 求 INFEASIBLE）抽查 12 个（含 scan 的
(q11,q882)×1050 簇首例、51180484 起的 unsynthesis 连续簇）**全 FIRES**。
即它们在极稀有输入下会触发，属近似剪枝范畴（见 1.15）。

### 1.10 MBU（uncompute-form）— 真例 0
`CCX a b t` 且 `t == a&b` 的 flag 有 10,693 个，但加上 `product != 0`
过滤后 **真 uncompute 为 0**——全部是 `R t` 清零 + 乘积稀有不触发的假象。

### 1.11 clean-control / 首触控制 — 全文件 0
HMR/R-clean（含 SWAP 传播）控制的 CCX/CSWAP/CCZ：**0**。
ancilla 首触即作控制（初态 |0> 恒等可删）：**0**。
「常 1 控制」：675 个终点快照无恒 1 线，全 1 乘积 0。

### 1.12 活线替换（`CCX c d u` → `CX w u`）— 0/116
全文件流式掩码匹配得 4833 个「某活线值等于该乘积」候选 + 25 个终点候选；
SAT 逐一验证 **116 个全 DIFF，0 WIREQ**（含全文件仅存的 3 个
「非控制 + 唯一掩码 + 非 scan」、synthesis q887 族、跨阶段 diverse 集、
R41 活跃期载体线 0 候选）。机制：循环行进使不同线值在样本上高度相关
但函数不等，唯一掩码亦为稀有相关模式。

### 1.13 载体不可能性（逐项实证）
- 全 51 ancilla × 731 cross 跨度：**仅 7 个**有单线 clean 覆盖
  （46.5M 簇，q854+q879），这 7 个 SAT **全 REFUTED**（等式为假）；
  其余 724 个无 1-phase 载体。
- 2-phase / N-phase handoff：同样仅这 7 个；L1 覆盖 550/735 但到 L2 不连通。
- 死线（L1 后零读）：**0**；51M+ untouched 区间平均长度 ~1 行（电路极密）。
- t1 自载体（L1 目标本身干净）：318 个 cross 对满足，但跨度内**全部**被重写
  （t1-clean 但非 write-free）。
- 同 target 对消：5 对，目标在跨度内均被读写数千次。
- R41 形状复刻验证：carrier_enum v3 精确复现 14/14 compute+SWAP+endpoint，
  额外 9 个 SWAP 均为数据搬运（新家 0 control-read 即被杀）。
- 结论：载体与等式空间**零交集**。

### 1.14 宽度 891 → 890 — 无死线
条件化 USE 的 liveness：`true_peak_live = 891`、`n_ever_live = 891`、
`never_live_wires = []`；首末触及区间中位数 ~全电路，born-late / die-early 均 0。
891 线全被使用，峰值 = 分配。**重开**：算法级改动（不同分解/编码）或重综合。

### 1.15 分支稀有度 / R50 式近似剪枝 — 无对象
56 个 `PUSH_CONDITION` guarded 区在稀疏输入下触发率 **947~985 / 2000（≈50%）**，
无一稀有；每个区含 7~22 个计费门。R50 的「稀疏分支删除」在本文件
期望为负。**重开**：需换输入分布假设（会破坏正确性，不可取）。

### 1.16 scan 尾剪枝 — 无收敛
scan 段（17.77M–41.26M）44,275 个 CCX 恰为 **22 的精确周期**
（44275 = 2012×22 + 11，0 处 break）；每个 22-CCX 体含 124 个 X 翻转 +
R/HMR/CZ/SWAP，状态恒变且周期振荡，**无冻结尾**可剪。

### 1.17 六个 SAT-PROVEN 乘积等式（已 banked，未货币化）
全锥 CP-SAT（unfrozen，INFEASIBLE）证明的跨线语义等式：

| L1 | product@L1 | L2 | product@L2 | span | 阶段 |
|---|---|---|---|---|---|
| 45443495 | q849&q852 | 45546777 | q15&q859 | 103,282 | unconvert |
| 45443474 | q846&q852 | 45546756 | q850&q859 | 103,282 | unconvert |
| 45443430 | q846&q849 | 45546712 | q850&q15 | 103,282 | unconvert |
| 50917113 | q841&q885 | 51027504 | q884&q886 | 110,391 | unsynthesis |
| 50227238 | q882&q840 | 50387364 | q846&q851 | 160,126 | unsynthesis |
| 46945987 | q853&q855 | 47313278 | q863&q875 | 367,291 | unsynthesis |

证明管线：bitwise 多 shot 仿真（三分布掩码过滤）→ OR-Tools CP-SAT 全锥
（精确 `AddAllowedAssignments` 门编码，HMR/R 按 reset 建模），
单例 6~233 秒；REFUTED 对照证明器具区分度。
**全部 6 个都因 1.13 而无载体**，无法在二进制层面变现。
**重开**：生成器级载体分配。

### 1.18 上游管线 / 生成器取证 — 不可得
- `somejoint/qcc-dqi-892-q26` 仅 3 个 `.py` 片段（audit/companion/blocked），无构建驱动。
- 5 份公开 notebook 源码（SomeJoint chem-refit V34、yoyobar V28、syed3000×2、
  Alex Chilton 24-80）只有打包代码，无 DQI 解码器生成器。
- jday96314/QuantumAI GitHub 仓库 "Repository not found"。
- 892Q 变体（Atakan `0cb57ff2`、Dmitrii `039ee660`）Q 更差，不可与 891Q 合并。

---

## 2. 方法学结论（可复用）

1. **验证协议**：任何 DQI 候选必须 ≥3 seed × 全量 102400 验证，比较
   `meanT`（seed 无关）；单次 score 受 k 抽签影响 ±0.5%。
2. **掩码相关 ≠ 语义相等**：2000-shot 掩码一致性会给出 99% 假阳性；
   必须 SAT/CP-SAT 证明。
3. **同源近邻电路可直接 diff 合并**：不同作者的编辑若区域不重叠，
   按 hunk 取边即可叠加（见 `20261106_leo_merge/merge_public.py`）。
4. **R 必须按 reset 建模**：忽略 `R` 会让仿真/证明产生系统性错误。
