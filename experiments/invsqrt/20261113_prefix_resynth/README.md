# `9c708f7b` prefix 重综合：成本归因纠正 + 167-CCX 算术块的结构性 no-go（`20261113_prefix_resynth`）

日期：2026-11-13；分支 `codex/invsqrt-research`；工作区 `.worktree/invsqrt/`。
对象：`9c708f7b9abc7c7e6719f6e258a3881945e9ee1fd4fd7009fe37367ca1ef20d1`（62Q，C=1,508.9567，score 93,555.2627）。
本实验**没有产出可提交候选**：没有生成新 `.kmb`，没有跑官方全量验证。未提交 Kaggle、未 push、无残留进程。

## 0. 结论

| 项 | 结果 |
|---|---|
| 任务里给的 prefix 拆分 | **实测完全正确**：63 T + 167 T + 7 T = 237 T，见 §1 |
| 上一轮 “193 CCX / 22 bit = 8.8 AND/bit，可省 83 C” | **撤回**。193 里只有 19 个属于 normaliser（加 44 CSWAP 共 63 T = 2.86 T/bit，已低于“5/bit≈110”的朴素下界）；167 个是算术块，7 个是收尾。**−83 C 不再是目标** |
| op 650–7030 是什么 | 纯可逆置换（无 HMR / 无相位门 / 无条件），作用在 47 个比特上（q0–q13、q23 各自只影响自己）。不是 compute/uncompute 对。未能归约到单一论文原语（见 §4.4） |
| 167 T 是否已高度优化 | **是**。块内 2 次 ANF 部分就有 1,081 个不同单项式 / 21,904 个 (i,j,out) 关联，而电路只用 167 个 AND 实现同一置换（6.5× 复用）；论文 reference 最便宜的原语（22-bit squaring）是 442 T，是它的 2.6 倍。见 §4.3 |
| 局部冗余 | **0**。全定义域上 237/237 个 Toffoli 的 fire 集合非空（无死门，最稀有者仅 1 个 x 触发）；逐一删除在 2,800 点 × 2 HMR 分支上都改变 cut 状态；19 对精确抵消全是 X/CX，省 0 T。见 §5 |
| 最好 T/Q/score | **无候选**，仍是基线 237 T(prefix)/1,508.9567/62Q/93,555.2627 |
| 官方验证 | 未运行（无候选）。本机换用**新写的精确定点模拟器**，对官方 200M 口径的全定义域 3,133,452 个 x 逐点比对相位，0 差异（§3） |

**一句话**：prefix 已经没有“normaliser 太贵”这个问题；剩下的 167 T 是一个 AND 密度已经只有“直接二次型合成”1/6.5 的算术块，本次 3 小时盒内没有找到 sound 的替代形态。

## 1. 拆分验证（实测，先纠正成本归因）

`scripts/prefix_dump.py`（只读）按 500-op 窗口统计 + 精确切点：

| 区间 | CCX | CSWAP | T | 结构（实测） |
|---|---:|---:|---:|---|
| `[0:649)` | 19 | 44 | **63** | 前导位检测（18 级 `CCX` AND 链 `q23…q41` + 1 个 `CCX q41 q1 q47`）+ 可变量移位网络：44 个 `CSWAP q48 q_a q_b`（交换距离 1,3,5,…,19 混排，不是 2 的幂分层的标准 barrel），每步前后用 `CX … q48` 的奇偶和算出/消掉移位量的一位（q48 复用为 scratch） |
| `[650:7031)` | 167 | 0 | **167** | 纯可逆置换，**无 HMR、无 Z/CZ、无条件门**；6,381 op 里 ~6,000 是 CX |
| `[7031:8546)` | 7 | 0 | **7** | 收尾（`8516,8518,8521,8522,8527,8530,8537`） |
| 合计 | 193 | 44 | **237** | 与报告一致 |

所以：

- 真正的 “leading-zero 检测 + 44-CSWAP normaliser” 只有 **63 T**，**每 bit 2.86 T**，已经**低于**上一轮用来立项目的 `5 AND/bit ≈ 110 T` 朴素下界。这条线上不存在 −83 C。
- 上一轮的 8.8 AND/bit 是把 167 个算术 CCX 混进了 normaliser 的分母。**报告里的 −83 C（→88,410）撤回，不再作为已证目标。**
- 167 T 占 C 的 11.1%；即使整块免费，C=1,341.96、score≈83,201（−11%）。这是这条路的**毛上限**，不是可期收益。
- 按 +1Q ≈ 24 C 的换算，任何要加 ancilla 的替代方案必须净省 >24 T 才打平。

复现：`uv run python experiments/invsqrt/20261113_prefix_resynth/scripts/prefix_dump.py artifacts/20261112_newfamily_census/invsqrt.kmb 8600`（输出存 `artifacts/20261113_prefix_resynth/prefix_split.log`）。

## 2. 来源归属：实际是 `94b29cc5`，不是 ThomasG 的 prefix

`scripts/splice_map.py` + `scripts/anchor_diff.py`（24-op 锚点 diff）显示：

- 三条电路共享**完全相同的前 70 op**（前导位检测的 `CX q21 q23` + `X q2..q21` + 18 级 CCX 链）。
- `9c708f7b` 的 `[0:8546)` 基本上是 **`94b29cc5` 的逐字拷贝**，只有 4 处本地改写：`[70:92)`（22 op）、`[453:643)`（190 op，即 HMR 块）、`[7448:7989)`（541 op）、`[8519:8664)`（145 op）。
- `5ec4f516` 只在 `8664+` 之后以 5–8 op 的小片段出现（ladder 区），**没有提供 prefix**。

因此本轮的任务前提“`5ec4f516`（ThomasG early prefix）提供前缀”与字节不符：prefix 是 WCao24(`94b29cc5`) 的。这一点只影响归因，不影响 §1 的成本拆分。

## 3. 工具：精确定点模拟器（本轮唯一的正资产）

`scripts/qsim.py`：把整条电路当“定点置换 + 相位”精确模拟——`X/CX/CCX/SWAP/CSWAP` 是基态置换，`Z/CZ/CCZ/Z_POW/NEG` 是相位，`HMR` 是 X 基测量（结果按分支给定）+ 复位 + 相位回踢。相位用 `uint64` 记 2⁻⁶⁴ 圈（mod 1 圈），与官方 verifier 的定点比较**逐位一致**。

两个必须踩对的语义（都实测确认过，写下来避免后人再踩）：

1. **条件门有两种写法**：行内 `Z q3 if b9` 和 `PUSH_CONDITION` 块。只解析栈会漏掉行内条件，把 `Z q if b` 当成无条件 Z —— 因为所有相位都是半圈，错误只会表现为“整体差半圈”，不会炸得很明显（这正是我第一次对不上的原因）。`PUSH_CONDITION` 还必须**快照**压栈时的位值（文档明确：之后写该位不影响栈）。
2. **HMR 回踢 = 结果 AND 被测比特当时的值**（`v & q`），且 **v 是每次 shot 的伪随机位**（同 x 不同 shot 不同、同 shot 不同 salt 不同）。`X q0; HMR q0 b0` 单独用时相位就是随机的；只有配上 `NEG if b0` 之类的精确修正才确定。`NEG` = 半圈（全局 −1），不是整圈。

验证范围（明确区分）：

| 检查 | 范围 | 结果 |
|---|---|---|
| 微电路逐指令对照 `km.Simulator` | 10 个手写**合法**电路，覆盖 X/CX/CCX/SWAP/CSWAP/Z/CZ/CCZ/Z_POW/NEG/HMR/BIT_*/栈条件 | 10/10 值与相位全等 |
| 全电路 vs 官方口径 tabulation | `base_full.npz` 的 6,500 个 x（5,000 稠密 + 1,500 随机），**三种 HMR 分支**（value/zero/hash） | 三种分支各自 **0** 差异，且三分支互相 0 差异 |
| **全电路全定义域** | **x = 1…3,133,452（3,133,452 点）** | **相位 0 差异**；x 复原 3,133,452/3,133,452；scratch 全 0 |

即：这个模拟器现在可以在**全定义域**上给出“候选 = 基线”的精确等价证明（比官方 verifier 的 64 shot/x 抽样更强），不必上 Kaggle。日志见 `artifacts/20261113_prefix_resynth/qsim_full_domain.log`。

## 4. `[650:7031)` 的 167 CCX：结构分析

### 4.1 它是纯置换，不是 compute/uncompute 对

- 6,381 op 内没有 `HMR`、没有 `Z/CZ/CCZ/Z_POW/NEG`、没有条件门 → 纯 `{X,CX,CCX,SWAP}` 置换。
- `scripts/inverse_copy.py`：把该块逐门取逆、逆序，在整条 36,965 op 里做 24-op 锚点搜索，**0 个匹配窗口** → 电路里没有它的逆拷贝，它**不是**可被“测+对角修正”替掉的 compute/uncompute 对（这与 `20261112_newfamily_census` 的 0 对普查一致，但那条结论只覆盖小片段，这里覆盖整块）。

### 4.2 影响矩阵：47 个比特上的置换

`scripts/influence.py`（每个输入位在 8 个随机基点上翻转，看哪些输出位变）：

- `q0–q13` 和 `q23`：每个只影响**自己那一位**（不进算术）。
- `q14–q22`（9 位）和 `q24–q61`（38 位）：互相高度混合，几乎影响 `q14–q61` 的全部输出。

即块是 **47-bit 置换**，其中 9 位（q14–q22）是“乘数/被乘数”性质的高扇出控制位。

### 4.3 AND 结构：167 个 AND 已经是 6.5× 复用后的结果

`scripts/and_census.py`：

```
block [650:7031) CCX = 167
distinct control pairs = 38   (repeats: (14,17)×34, (15,14)×25, (14,16)×24, …)
distinct targets = 39
每个 AND 的即时扇出: median 1, max 4
逐一删除: 在可达定义域上改变块输出的 = 167/167（全部 load-bearing）
```

`scripts/degree_probe.py`：2 阶导沿 (14,15) 随基点变化 → 次数 ≥3；3 阶导沿 (14,15,16) 仍变化 → **次数 ≥4**。

ANF（对 62 个输入变量做 1 + 62 + 1,891 次求值，取 0/1/2 次项）：

```
不同 2 次单项式 = 1,081 个
(i,j,out) 关联 = 21,904 个（单个单项式最多进 30 个输出）
1 次项 62 列全部非零
```

**这张表是本次最硬的一条**：如果按“每个 2 次单项式一个 AND”的常规二次型/乘法器形状合成，至少需要 **1,081** 个 AND；该块用 **167** 个 AND 实现同一置换，说明它靠“AND 非线性中间量再复合”（次数 ≥4 的来源）把 1,081 个单项式折叠成了 167 次乘法。也就是说这块**不是**朴素展开，已经把 AND 复用到 6.5×。

### 4.4 它算的是哪一段（诚实结论：没有归约到单一原语）

- 用了 6,381 op、167 AND、39 个目标比特、控制对高度复用（同一对控制出现 24/25/34 次），CX 段是“同一个目标连收十几个 CX 再 SWAP”的消元形态 → 这是**位串行（shift-and-add 型）算术循环展开**，靠复用工作比特把规模压到 47 位。
- 但它**不是**论文里的 Horner（1,071 T）、22-bit squaring（442 T）、Newton（1,043/867 T）中的任何一个的朴素形态：167 T 比其中**最便宜**的 442 T 还低 2.6 倍。9 位高扇出控制位 + 39 个目标 + 3–4 次复合，最接近的解释是“9×k 位串行乘加 + 余数更新”的混合块，但**我没有在本轮把它归约成一个可命名的闭式**，因此不写“它是 X”。
- 这对结论没有影响：**能证明的是成本侧**（1,081 → 167 的复用已经发生；整块只有 167 T，毛上限 −11%），而不是“它一定最优”。要证最优需要 3 次型张量秩下界，本轮没做。

## 5. 局部冗余：0（定义域精确）

| 检查 | 方法 | 结果 |
|---|---|---|
| prefix 里有没有“死门” | 全定义域（x=1…3,133,452）单遍统计每个 Toffoli 的 fire 集合（量子控制全 1 的 x 集合） | **237/237 fire 集合非空**，0 个结构性 no-op；**最稀有的那个只对 1 个 x 触发**（所以采样检查会漏） |
| 逐一删除 prefix 全部 237 个 Toffoli-class 门 | `scripts/dead_toffoli.py`：删一个门，比较 `op 8546` 处的**全部 62 个比特值 + 全部经典位 + 相位**，2,800 个 x（800 稠密 + 2,000 随机）× 2 个 HMR 分支 | **0 个**删除后 cut 状态不变 |
| 精确门对抵消（含交换律） | `scripts/cancel_scan.py`：同一门、同一组比特、中间无任何门碰这些比特 → 句法恒等，必然 sound | 19 对，**全部是 X 或 CX**，Toffoli-class 省 **0** |
| 常量控制（CCX→CX / CSWAP→SWAP） | 上一轮 `const_sweep.py` 的 {0,1,unknown} 精确跟踪 | 0（本轮第一行是它的加强版：连“控制恒 0 因而成为 no-op”都不可能） |

第 1 行是**全定义域精确**结论；第 2 行是 2,800 点采样（删门改变的是状态本身，2,800 点足以排除结构性 no-op，但不等于全定义域证明，这里如实区分）。

顺带一个有诊断价值的数：prefix 的 237 个 Toffoli 都是**无条件**门，计分固定记 237；但全定义域平均只有 **55.97** 个门的量子控制同时为 1（其余 181 个在当次 shot 上对经典值什么都不做，却照样计费）。也就是说这条 prefix 的“有效算术密度”只有 56/237 ≈ 24%——这是静态计数口径的固有代价，不是可删的冗余（删任何一个都会改函数，见第 2 行）。

## 6. no-go 论证（三条独立证据）

1. **成本归因**：normaliser 只有 63 T（2.86 T/bit），已经低于当初立项的朴素下界 110；`−83 C` 的前提不存在（§1）。
2. **算术块没有可拆的冗余**：167 个 AND 全部 load-bearing（删除即改函数）；无逆拷贝（不是 compute/uncompute）；19 对精确抵消全是 Clifford（0 T）；237 个 Toffoli 在全定义域上无一死门（最稀有者只对 1 个 x 触发）；块内 AND 相对“二次型直接合成”已经复用 6.5×（1,081→167）（§4、§5）。
3. **量级**：替代必须净省 >24 T 才抵得上 +1Q，而整块的毛上限是 167 T（−11%）；要在 3 小时内重写一个 47-bit、次数 ≥4、在 3,133,452 个点上有 0.9993 结构裕度的置换并保持精确等价，不现实。任何新形态（Estrin/Karatsuba/截断）改的是这块的**函数**，会动下游 42 步 digit recurrence 的 b_k(x) 列，直接吃掉那 0.9993 的裕度。

**未做（明确声明）**：没有生成候选 `.kmb`/`.kmx`；没有跑 `verify_submission_invsqrt.py`（快检和全量都没跑）；没有 Kaggle 提交。

## 7. 下一步（按性价比）

1. **不要**再对 prefix 做“删门/换门/去 normaliser”：本节已把这三类在定义域上关死（237/237 load-bearing、0 T 抵消）。
2. 若要继续 prefix，唯一有量级依据的问题是“167 T 的**下界**”：需要 3 次齐次部分的张量秩（本块次数 ≥4，2 次部分已被复合折叠，单看 2 次秩给不出 >47 的界）。这是一个纯理论任务，收益是“知道能不能省”，不是“省下来”。
3. 真正的分差在 **tail（476.96 mean）与 mid（372.99 mean）**，占 70%；但那两块是 859 次 HMR 的“值计算 + 三体修正”，前序实验已把单门/门对/条件化三类关死。
4. 复现本轮结论只需 §8 的前两条命令（秒级）；`qsim.py` 可作为后续任何段落的**全定义域精确等价检查器**复用。

## 8. 复现

```bash
cd .worktree/invsqrt
# 拆分（§1）
uv run python experiments/invsqrt/20261113_prefix_resynth/scripts/prefix_dump.py \
    artifacts/20261112_newfamily_census/invsqrt.kmb 8600
# 来源归属（§2）
uv run python experiments/invsqrt/20261113_prefix_resynth/scripts/anchor_diff.py \
    artifacts/20261112_newfamily_census/invsqrt.kmb \
    artifacts/20261113_prefix_resynth/sources/5ec4f516.kmb \
    artifacts/20261113_prefix_resynth/sources/94b29cc5.kmb
# 算术块结构（§4）
uv run python experiments/invsqrt/20261113_prefix_resynth/scripts/and_census.py \
    artifacts/20261112_newfamily_census/invsqrt.kmb 650 7031
uv run python experiments/invsqrt/20261113_prefix_resynth/scripts/degree_probe.py \
    artifacts/20261112_newfamily_census/invsqrt.kmb 650 7031
# 局部冗余（§5）
uv run python experiments/invsqrt/20261113_prefix_resynth/scripts/dead_toffoli.py \
    artifacts/20261112_newfamily_census/invsqrt.kmb 8546 800
uv run python experiments/invsqrt/20261113_prefix_resynth/scripts/cancel_scan.py \
    artifacts/20261112_newfamily_census/invsqrt.kmb
# 精确模拟器自检（§3；全定义域那条约 2.5 min）
uv run python experiments/invsqrt/20261113_prefix_resynth/scripts/micro_validate.py
uv run python experiments/invsqrt/20261113_prefix_resynth/scripts/validate_modes.py \
    artifacts/20261112_newfamily_census/invsqrt.kmb 1500 5000
```

产物（均只读证据，无候选）：`artifacts/20261113_prefix_resynth/{prefix_split,and_census,dead_toffoli,qsim_full_domain}.log`；
来源 `.kmb` 在 `artifacts/20261113_prefix_resynth/sources/`（`5ec4f516…`、`94b29cc5…`）。
