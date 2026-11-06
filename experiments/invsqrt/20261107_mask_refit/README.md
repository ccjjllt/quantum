# invsqrt：41 旋转的掩码替换与全角度重拟合

日期：2026-11-07。工作区 `.worktree/invsqrt`，分支 `codex/invsqrt-research`。
基线只读：`artifacts/20261106_syed_v9/invsqrt/syed_v9_nofallback.kmb`
（62Q，官方本地 PASS，score 97,700.776777236，C=1,575.818980278）。

本轮问题：保持恰好 41 个 fine rotation，把其中某些 rotation 的控制掩码
`f_i` 换成同一检查点上可廉价得到的函数（`f_i XOR 线性型`、`f_i XOR 两线性型之积`、
`f_i AND 线性型` 等），再重拟合全部 41 个角度。
公开的 guard-bit 修正
`F15 -> F15 XOR [Y1 AND (e1 XOR e2)]`（1 个 CCX，margin 47,884,702 -> 58,597,850）
是这类替换的已知单例，且已包含在基线中。

## 0. 结论

**没有找到正的净收益；没有正的候选 KMB，没有官方全量验证，没有 Kaggle 成绩，基线文件未修改。**

1. 基线相位模型与官方逐位一致（margin 58,597,850 units，最坏比 0.9993237694056958 @x=161，
   C/score 完全一致）。用最大绝对 margin 的 LP 重拟合 41 个角度仍得到 **58,597,850**：
   基线角度已经是这 41 个掩码下的最优解，角度层面没有免费余量。
2. 每个旋转检查点上 62 根线的值在 3 个随机 HMR 分支、全部 3,133,452 个 x 上
   **逐位相同**（分支无关）。但**只有目标线自己**等于该旋转的掩码；其他掩码在各自
   `Z_POW` 后已被 HMR 清零。因此“同时可用的既有掩码的两两乘积”这一族是**空集**。
3. 用全域切割平面 LP 对单掩码替换做精确求值：LP 上界 = 达到的全域 margin 时即为精确最优，
   否则可靠早停（上界低于基线 => 该候选可证明不可能更好）。
   实际搜索 **10,787** 个候选：**0 个严格改善**；667 个“中性”候选的全域最优 margin
   **恰好等于 58,597,850**（LP 上界与达到值相等，即精确最优）；其余 10,120 个被证明
   不可能优于基线。**最好改善 = 0 units = 0C。**（`search_summary.json`）
4. 阻塞点是经济性的：在基线最优点，**额外增加**一个掩码方向（系数自由、不损失任何
   现有掩码）实测最多只值 **+6.87% margin = 0.55C**（24 个随机 pair 的最大值；
   中位数 1.40% = 0.08C；guard 方向 +1.05% = 0.086C）。
   而任何两线性型之积的实现成本是 **1 个无条件 CCX = 1C**。替换比“免费新增”更弱，
   所以 1-CCX 单掩码替换在结构上不可能回本；只有 0 门的线性替换有机会，而它们
   全部实测为严格不变或更差。
5. **电路级机制已验证**（不是只停留在相位模型）：掩码改变需要在目标线 HMR 后追加
   匹配的 Clifford 反冲修正。按此实现的真实 KMB
   （`cand_rot15_lin21.kmb` 0 门、`cand_rot15_pair0_21.kmb` 1 CCX）在
   **部分官方本地验证**（x ≤ 1,048,576，1 shot/x）**PASS**，`rotation_eps`
   与基线逐位相同（2.434041480874084e-13），最坏比同为 0.9993237694 @161；
   1-CCX 版本的 `toffoli_count` 约 +1.0（抽样噪声内）。这些是负结果/机制验证，**不是**成绩提升：
   全量 200,540,928-shot 官方验证没有运行。

## 1. 相位模型与基线精确复现

沿用 `20261106_rot33` 的相位模型：每条固定 HMR 分支上电路是计算基态置换 +
对角相位，`Z_POW q θ` 在 q=1 时贡献 `θ/2` turns。`masks_full.json` 给出 41 个
fine rotation 在全部 `x=1..3,133,452` 上的控制真值表，`T_units.npy` 是去掉
精确 Clifford/T 部分后的理想 fine 相位（单位 `2^-64` turns），`tol_units.npy`
是逐 x 容差。复核结果与官方逐位一致（`repro.py`）：

| 指标 | 本模型 | 官方日志 |
|---|---:|---:|
| 最小 margin `tol-\|err\|` | 58,597,850 units @ x=52,229 | 58,597,850（由 eps 反推） |
| 最小 margin（turns） | 3.176595813648986e-12 | 3.17659581365e-12 |
| 最坏 `\|err\|/tol` | 0.9993237694056958 @ x=161 | 0.9993237694056958 @ x=161 |
| rotation eps | 2.434041480874084e-13 | 2.434041480874084e-13 |
| C | 1,575.818980278 | 1,575.818980278 |
| score | 97,700.776777236 | 97,700.776777236 |

margin 的最小值在 x=52,229，最坏比值在 x=161；验证器用前者（`min_margin`）。

用最大绝对 margin 的 LP 重拟合全部 41 个角度（22,132 个约束起步，切割平面加到收敛）
得到**同样的 58,597,850**（`repro.json`）。基线角度已是这组掩码的最优解。

## 2. 检查点上的可用线

`trace_wires.py` 在全部 3,133,452 个 x 上按位并行追踪，在每个 rotation 的
`Z_POW` 之前保存 62 根线的值（`wires/cp_XX.npz`，950 MB）。
`branch_wires.py` 用 3 个随机 HMR 分支（全部 867 个 HMR 的独立随机结果）
重跑全域并逐线比较：**41 个检查点 × 62 根线全部与全零分支逐位相同**
（XOR 距离 0）。检查点上的线值都是 x 的函数，与测量分支无关。

关键结构（`checkpoint_stats.json`）：

- 每个检查点只有**目标线**等于该 rotation 的掩码 `f_i`；其他掩码线都在各自
  `Z_POW` 之后被 HMR 清零。因此“同时可用的既有掩码的两两乘积”这一族**为空**。
- 常数 0 的自由辅助线：rot 15/16/17/18 有 q28,q40,q41；rot 19 有 q28,q40；
  rot 20 有 q28；rot 35-40 有 3 条。其余检查点 62 根线全部是活线（GF(2) 秩 62）。
- 归一化之后 x 寄存器保存的是尾数，检查点上没有原始 x 位。

## 3. 替换字典、计费口径与 HMR 反冲修正

对 rotation `i`（目标线 t，掩码 `f_i`）：

| 族 | 新掩码 g | 门数 | 实现（Z_POW 前） | HMR 后 Clifford 修正 |
|---|---|---:|---|---|
| `lin` | `f_i XOR w_j` | 0 | `CX qj t` | `Z qj if b` |
| `lin2` | `f_i XOR w_a XOR w_b` | 0 | 两条 `CX` | `Z qa if b; Z qb if b` |
| `pair` | `f_i XOR (w_a AND w_b)` | 1 CCX | `CCX qa qb t` | `CZ qa qb if b` |
| `trunc` | `f_i AND w_j` | 1 CCX + 1 辅助线 | `X wj; CCX t wj a; CX a t; X wj; HMR a` | 视情况 |
| `guard54` | `f_i XOR (q54 AND (w_b XOR w_c))` | 1 CCX | 暂时 `CX qc qb`，`CCX q54 qb t`，再还原 | `CZ q54 qb if b; CZ q54 qc if b` |

**为什么必须修正**：目标线在 `Z_POW` 后被 `HMR q b` 测量，`HMR` 会留下
`(-1)^{m·g(x)}` 的反冲相位（m 为测量结果）。基线为既有掩码准备的
classically-controlled `Z/CZ` 正好抵消它。若掩码改变 `h(x)`，就必须追加
`(-1)^{m·h(x)}` 的 Clifford 修正；对本表所有族，这只需要 `Z`/`CZ`（Clifford，免费），
与公开 guard 修正完全同型：基线 ops 25405-25411 就是
`CX q27 q18; CCX q54 q18 q50; CX q27 q18; Z_POW q50; HMR q50 b350;
CZ q54 q18 if b350; CZ q54 q27 if b350`，
后两条 CZ 正好实现 `(-1)^{m·(q54 AND (q18 XOR q27))}`。

实测验证（`pre_guard_v2.kmb`）：

- 只删 guard 的 CCX、保留两条 CZ：x=258 在随机种子下出现 **2 个不同相位**
  （0.0622573 与 0.5622573 turns，恰好相差 0.5 turn）——分支相关，电路无效。
- 同时删 CCX 和两条 CZ：所有测试 x 上 4 个种子只有 **1 个相位**（分支无关），
  与基线的相位差恰好是 `-θ_15`（在 guard=1 的 x 上），即相位模型精确。

成本口径与验证器一致：每个无条件 `CCX` 记 1 Toffoli-like = 1C；`CX`/`X`/`Z`/`CZ`
免费；`HMR` 与其 Clifford 纠相免费。收益：

```
ΔC = 41 * 0.56/4 * log2(M'/M0) - cost = 5.74 * log2(M'/M0) - cost,  M0 = 58,597,850
```

1 个 CCX 需要 `M'/M0 > 2^(1/5.74) = 1.1283`（+12.83%）才刚好回本。

## 4. 精确替换求值器（切割平面 LP）

单次替换后要重拟合 41 个角度。问题有 41 个自由度而注入样本必须覆盖整个 x 域
（小样本 LP 会给出完全错误的角度：实测 3,229 点 LP 上界 59.2M、全域 margin
-10.2B）。这里用**全域切割平面**（`fast_eval.py`）：

1. 由候选的原始扰动（基线角度下 `f_i -> g`）在全部 x 上找最紧点；
2. 在“基线最紧点 + 原始扰动最紧点 + 稀疏掩码支撑 + 随机点”上解
   `max m s.t. |E-A d| <= tol - m`（变量是角度增量，替换列用新掩码）；
3. 用返回的角度更新全域相位（只更新真正变化的角度），检查全域 margin；
4. 把全域最紧的点加入约束集，重复到 `LP margin == 全域 margin`（差 < 4 units）。

因为约束集是真问题的子集，LP margin 是全域最优值的**上界**；一旦上界低于基线
即可**证明**该候选不可能更好（可靠早停）。收敛时二者相等，返回的是该替换下的
**精确全域最优 margin**。

标定：

- 用 `M.refit`（独立实现、不同约束集）对中性候选 `rot15 lin 21` 重拟合三次，
  全部收敛到**恰好 58,597,850**。
- 对去 guard 的掩码重拟合，得到公开的 **47,884,702 units / 最坏比 0.9994474**
  （与公开 “47,884,702 / 0.99945” 一致）；这是相位模型层的数值对齐，
  电路层必须同时删掉 §3 的两条 CZ 才有效（`pre_guard_v2.kmb`）。

## 5. 搜索结果

全部结果在 `artifacts/20261107_mask_refit/search_*.json`，汇总在
`search_summary.json`。有效求值 **10,787** 个候选。

| 文件 | 族 / 旋转 | 求值 | 拒绝（已证不可能） | 中性（=58,597,850） | >基线 |
|---|---|---:|---:|---:|---:|
| `search_lin_all.json` | lin / 0-14,16-40 | 2,440 | 2,393 | 47 | 0 |
| `search_lin_rot15.json` | lin / 15 | 61 | 56 | 5 | 0 |
| `search_lin2_15_16.json` | lin2 / 15,16 | 3,660 | 3,635 | 25 | 0 |
| `search_pair_15_16.json` | pair / 15,16 | 3,660 | 3,070 | 590 | 0 |
| `search_trunc_15_20.json` | trunc / 15-20 | 366 | 366 | 0 | 0 |
| `search_guard54_15_16.json` | guard54 / 15（部分，已中止） | 600 | 600 | 0 | 0 |
| **合计** | | **10,787** | **10,120** | **667** | **0** |

观察：

- **没有任何候选的 margin 超过 58,597,850。** 最好的候选是“恰好中性”。
- 中性候选集中在 rot 15/16 和小支撑线的线性/异或改变（如 `lin 21` 只翻 63 个 x，
  `pair 0,21` 只翻 ≤63 个 x）；改变发生在余量很大的点上，LP 又能用其他角度
  精确补偿，所以最优值不变。
- 大角度旋转（rot 0-14）和所有 `trunc`（把掩码清零一半）都被立即证明不可能：
  一次翻转让相位改变 `θ_i`，在 rot 0 是 7.0e13 units，远大于任何容差。
- `guard54` 族（公开修正的同型推广，a=q54，所有 (b,c)）在 rot 15 上前 600 个
  全部被证明不可能。

## 6. 成本账与阻塞点

### 6.1 只有两个旋转能吸收掩码翻转

`θ_i`（units `2^-64` turns）与全域最小容差 `tol_max_x = 621,138,291`：

| rot | θ_i | θ_i / tol_max |
|---|---:|---:|
| 15 | 266,193,503 | 0.43 |
| 16 | 541,668,472 | 0.87 |
| 17 | 1,068,829,837 | 1.72 |
| 18 | 2,145,998,496 | 3.45 |
| 24 | 137,440,338,989 | 221 |
| 40 | 9,007,168,114,498 | 14,501 |

rot 0-14、17-40 的掩码翻转在最大 x 处就已超出容差本身，必须靠其他 40 个掩码
在那些点上同时补偿；实测全部失败。真正可搜索的只有 rot 15/16，它们已被
`lin/lin2/pair/trunc/guard54` 覆盖。

### 6.2 一个额外掩码方向最多值 0.55C

在基线最优点用 LP 对偶：`Σλ = 0`，`Σ max(λ,0) = 0.5` units `2^-40`
`= 2^23 = 8,388,608` units `2^-64`，即一阶上界 **+14.32% margin = 1.108C**。
但一阶估计过于乐观；实测**新增**一个自由系数方向（保留全部 41 个掩码）的真实收益：

| 新增方向 | margin 增益 | ΔC |
|---|---:|---:|
| pair 3&38（24 个随机 pair 中最好） | +6.87% | 0.551 |
| pair 5&46 | +4.43% | 0.359 |
| pair 10&24 | +2.27% | 0.186 |
| guard `Y1 AND (e1 XOR e2)` | +1.05% | 0.086 |
| 24 个随机 pair 中位数 | +1.40% | 0.08 |
| `lin2 21^23`、`q23` | 0.00% | 0 |

**即使免费新增一个方向、且不损失任何现有掩码，最好也只有 0.55C**；而实现它需要
1 个 CCX = 1C。替换还要放弃 `f_i` 的贡献，严格更差。所以
**任何 1-CCX 单掩码替换都不可能净正**；只有 0 门的线性替换有机会，而 2,501 个
`lin` 和 3,660 个 `lin2` 全部是 0 改善或被证明不可能。

### 6.3 为什么 guard 修正是可遇不可求的

guard 修正在**去 guard 态**上把 margin 从 47.88M 提到 58.60M（+22%，1.67C，
净 +0.67C），远大于在当前最优点“新增一个方向”的 0.1-0.2C。原因是它置换的
是 `f_15` 本身（`f15 XOR guard` 含 `-2*f15*guard` 交叉项），把基从较差局部解
移到另一个基，而不是在当前基上增加一维。这种“换基”收益依赖原来的基恰好留了
这个缺口；本轮对 rot 15/16 的 7,000+ 个精确替换求值没有找到第二个这样的缺口。

### 6.4 电路级成本确认（部分官方本地验证）

| 电路 | 新门 / 修正 | nops | toffoli_count* | rotation_eps | 最坏比 | 状态 |
|---|---|---:|---:|---:|---:|---|
| 基线 | — | 49,051 | 1280.7311 | 2.434041480874084e-13 | 0.9993237694056958 @161 | PASS |
| `cand_rot15_lin21` | `CX q21 q50` + `Z q21 if b350` | 49,053 | 1280.7340 | 2.434041480874084e-13 | 0.999323769417236 @161 | PASS |
| `cand_rot15_pair0_21` | `CCX q0 q21 q50` + `CZ q0 q21 if b350` | 49,053 | 1281.7200 | 2.434041480874084e-13 | 0.999323769417236 @161 | PASS |

\* 三者都用 `--max-x 1048576 --shots-per-x 1`（1,048,576 shots）跑的**部分官方本地
验证**，`toffoli_count` 有约 ±0.003 的抽样噪声（基线在同设置下为 1280.7311，
官方 200M-shot 为 1280.7282）。1-CCX 候选比同设置的基线多 **+0.989 ≈ +1.0**，
与计费口径一致；0 门候选与基线在噪声内相同。**没有运行全量 200,540,928-shot
官方验证，也没有提交 Kaggle。** 这两个候选的 margin 与基线相同，score 不可能
低于基线（1-CCX 版本反而约 +62）。

## 7. 复现命令

在 `.worktree/invsqrt` 下，使用 `.venv/bin/python`：

```sh
# 1) 基线复现 + 角度 LP 重拟合（~3s）
.venv/bin/python experiments/invsqrt/20261107_mask_refit/repro.py
# 2) 41 个检查点的 62 线全量追踪（~6s，写 950MB wires/）
.venv/bin/python experiments/invsqrt/20261107_mask_refit/trace_wires.py
.venv/bin/python experiments/invsqrt/20261107_mask_refit/checkpoint_stats.py
# 3) 3 个随机 HMR 分支的分支无关性（~25s）
.venv/bin/python experiments/invsqrt/20261107_mask_refit/branch_wires.py
# 4) 公开 guard 修正的相位标定（~10s）
.venv/bin/python experiments/invsqrt/20261107_mask_refit/validate_guard.py
# 5) 固定角度“理想翻转”诊断（~2s）
.venv/bin/python experiments/invsqrt/20261107_mask_refit/ideal_flip.py
# 6) 单掩码替换搜索（每次求值 0.5-2s）
.venv/bin/python experiments/invsqrt/20261107_mask_refit/run_search.py \
  --rots 15,16 --families pair --out search_pair_15_16.json
.venv/bin/python experiments/invsqrt/20261107_mask_refit/run_search.py \
  --rots 15,16 --families lin2 --out search_lin2_15_16.json
.venv/bin/python experiments/invsqrt/20261107_mask_refit/run_search.py \
  --rots 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40 \
  --families lin --out search_lin_all.json
.venv/bin/python experiments/invsqrt/20261107_mask_refit/run_search.py \
  --rots 15 --families lin --out search_lin_rot15.json
.venv/bin/python experiments/invsqrt/20261107_mask_refit/run_search.py \
  --rots 15,16,17,18,19,20 --families trunc --out search_trunc_15_20.json
# 7) 汇总
.venv/bin/python experiments/invsqrt/20261107_mask_refit/summarize_search.py
# 7b) 额外方向的边际价值 + HMR 反冲修正的电路级检查
.venv/bin/python experiments/invsqrt/20261107_mask_refit/additive_value.py
.venv/bin/python experiments/invsqrt/20261107_mask_refit/pre_guard_check.py
# 8) 电路级机制验证（真实 KMB + 部分官方验证）
.venv/bin/python experiments/invsqrt/20261107_mask_refit/build_candidate.py
.venv/bin/python data/competition/verifiers/invsqrt/verify_submission_invsqrt.py \
  artifacts/20261107_mask_refit/cand_rot15_lin21.kmb --max-x 1048576 --shots-per-x 1
.venv/bin/python data/competition/verifiers/invsqrt/verify_submission_invsqrt.py \
  artifacts/20261107_mask_refit/cand_rot15_pair0_21.kmb --max-x 1048576 --shots-per-x 1
```

产物：`repro.json`、`checkpoint_meta.json`、`checkpoint_stats.json`、
`branch_wires.json`、`validate_guard.json`、`ideal_flip.json`、
`search_*.json`、`search_summary.json`、`additive_value.json`、
`pre_guard_branch_check.json`、`wires/cp_XX.npz`、
`theta_pre_guard.npy`、`pre_guard_v2.kmb`、`cand_rot15_lin21.{kmb,json}`、
`cand_rot15_pair0_21.{kmb,json}`。

## 8. 范围与未完成

- **没有正的候选 KMB，没有全量官方 PASS，没有 Kaggle 提交**；基线文件未被修改。
  两个真实 KMB 只用于机制验证，margin 与基线相同或更差。
- 搜索族是任务列出的廉价函数族：线性型、两线性型之积、`f_i AND 线性型`、
  `f_i XOR (一个线 AND 两线异或)`（guard 同型）。**“既有掩码的两两乘积”不可实现**
  （§2），不是被跳过。
- 没有穷举全部 `(a, (b,c))` 的 11 万级 guard 同型族：只跑了 rot 15 的 a=q54
  前 600 个（全部拒绝）。理由是 §6.2 的经济上界与 §6.1 的容差限制。
- 没有做双/三掩码联合替换：单替换全部 ≤0，且每个额外方向实测 ≤0.55C < 1C，
  联合替换按单调性只会更差。
- 所有“中性/拒绝”结论在相位模型 + 全域切割平面 LP 内成立；模型已用官方 PASS、
  公开 guard 数值和两个真实 KMB 的部分官方验证三重标定。
- 部分官方验证只覆盖 x ≤ 1,048,576（包含全域 binding 点 52,229 和 851,985，
  所以 `rotation_eps` 与基线逐位相同），不是 200,540,928-shot 全量。
- 若未来出现以下情况，结论需要重算：
  1. 找到 0 门或 <0.55C 的方式产生一个与当前 41 个掩码线性无关、且在 binding 点上
     对齐 residual 的方向；
  2. 改变旋转数/算术表示，使一个方向的边际价值明显高于 1C；
  3. 发现另一个像 guard 那样“换基”的缺口（需要在去该缺口的电路上做同类搜索）。
