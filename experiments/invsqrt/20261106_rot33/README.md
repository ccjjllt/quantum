# invsqrt：33 旋转表示与廉价控制可行性（Syed V9 基线）

日期：2026-11-06。工作区 `.worktree/invsqrt`，分支 `codex/invsqrt-research`。
基线只读：`artifacts/20261106_syed_v9/invsqrt/syed_v9_nofallback.kmb`。
官方本地读数：62Q，PASS，`score=97,700.776777236`，`C=1,575.818980278`，
41 个一般旋转合成 `294.8408238889C`，最坏误差/容差 `0.9993237694056958 @ x=161`。

**结论：没有证明正的净收益。**
33 项数值拟合本身存在（33-bit 截断，全域最差比 `0.863738`），
但它的 33 个理想控制位在现有电路的任何检查点都不是活线的线性形式，
在 41 个旋转检查点也不是二次型，单个 cubic monomial 也不匹配；
只用原 41 个掩码删 8 个的 33 子集，LP 重调角后最差比仍为 `110.53`。
合并字所需的新算术下界已超过回本预算 `89.428C`：
34-bit shift ladder 约 `136C`，再加 34-bit adder 约 `66C`。
本记录没有生成候选 KMB，没有运行官方全量验证，也没有 Kaggle 成绩。

## 1. 相位模型与 41 个旋转掩码

电路是 phase-polynomial 电路：`X/CX/CCX/SWAP/CSWAP` 是基态置换，
`Z/CZ/CCZ/NEG/Z_POW` 是对角相位，`HMR/R` 是测量清零。
在固定 HMR 分支上每根线都是计算基态，`Z_POW q θ` 在 q=1 时贡献 `θ/2` turns
（文件参数 θ 是 half-turns）。HMR 的 kickback 与后续条件 Z 纠相在每条分支上相消；
全零分支上两者都为 0。因此总相位可写成

```
总相位 = Σ_i (θ_i/2) f_i(x) + (Clifford/T 部分, 2^-3 turns 的整数倍)
```

脚本 `extract_masks.py` 用 bit-parallel Python 整数在全部
`x=1..3,133,452` 上追踪，记录每个 fine `Z_POW` 的控制线真值表 `f_i`。
41 个旋转的 `f_i` **互不相同，GF(2) 秩 41**，因此实数域秩也是 41。
`branch_check.py` 在 4 个随机 HMR 分支、4096 个随机 x 上比较，
41 个掩码与全零分支逐位相同（XOR 距离全 0）。

把 `target - Σ θ_i f_i` 归到最近的 `2^-61` 单位（`1/8 turn`）整数倍，
得到精确的 Clifford/T 部分，剩余的理想 fine 相位记为 `T`。
用这个模型复算基线，全域最差误差/容差为
`0.9993237694056958 @ x=161`，与官方日志逐位一致（`validate_phase.py`）。
这验证了掩码、角度和相位约定。

完整真值表在 `artifacts/20261106_rot33/masks_full.json`（base64 位串），
前 64 个 x 的可读表在 `masks_truth_sample.json` / `masks_first64.csv`。
所有关键数值的汇总在 `summary.json`（`summarize.py` 生成）。

### 角度与支撑

| rot | op | wire | θ (half-turns) | popcount |
|---:|---:|---:|---:|---:|
| 0 | 15287 | q28 | 2^-17 (7.6294e-6) | 995,341 |
| 1 | 15295 | q28 | 2^-16 (1.5259e-5) | 1,464,333 |
| 2 | 15303 | q28 | 2^-15 (3.0518e-5) | 1,597,952 |
| 3 | 15311 | q28 | 2^-14 (6.1035e-5) | 1,550,464 |
| 4 | 15318 | q28 | 2^-13 (1.2207e-4) | 1,653,293 |
| 5 | 15327 | q28 | 2^-12 (2.4414e-4) | 1,587,848 |
| 6 | 15336 | q28 | 2^-11 (4.8828e-4) | 1,207,970 |
| 7 | 15345 | q28 | 2^-10 (9.7656e-4) | 2,386,871 |
| 8 | 15394 | q28 | 2^-9 (1.9531e-3) | 861,935 |
| 9 | 15448 | q28 | 2^-8 (3.9063e-3) | 215,484 |
| 10 | 15502 | q28 | 2^-7 (7.8125e-3) | 53,872 |
| 11 | 15550 | q28 | 2^-6 (1.5625e-2) | 13,469 |
| 12 | 15597 | q28 | 2^-5 (3.1250e-2) | 3,368 |
| 13 | 15602 | q28 | 2^-4 (6.2500e-2) | 841 |
| 14 | 15607 | q28 | 2^-3 (1.2500e-1) | 213 |
| 15 | 25408 | q50 | 2^-35 (2.8861e-11) | 1,535,051 |
| 16 | 25418 | q50 | 2^-34 (5.8728e-11) | 1,437,062 |
| 17 | 25426 | q50 | 2^-33 (1.1588e-10) | 1,534,103 |
| 18 | 25434 | q50 | 2^-32 (2.3267e-10) | 1,558,145 |
| 19 | 25445 | q50 | 2^-31 (4.6545e-10) | 1,563,852 |
| 20 | 25456 | q50 | 2^-30 (9.3234e-10) | 1,566,985 |
| 21 | 25467 | q50 | 2^-29 (1.8633e-9) | 1,566,209 |
| 22 | 25476 | q50 | 2^-28 (3.7253e-9) | 1,566,089 |
| 23 | 25487 | q50 | 2^-27 (7.4497e-9) | 1,566,646 |
| 24 | 25498 | q50 | 2^-26 (1.4901e-8) | 1,566,901 |
| 25 | 25509 | q50 | 2^-25 (2.9801e-8) | 1,566,734 |
| 26 | 25520 | q50 | 2^-24 (5.9605e-8) | 1,566,752 |
| 27 | 25533 | q50 | 2^-23 (1.1921e-7) | 1,566,679 |
| 28 | 25546 | q50 | 2^-22 (2.3842e-7) | 1,566,868 |
| 29 | 25559 | q50 | 2^-21 (4.7684e-7) | 1,566,818 |
| 30 | 25570 | q50 | 2^-20 (9.5367e-7) | 1,567,227 |
| 31 | 25581 | q50 | 2^-19 (1.9074e-6) | 1,565,855 |
| 32 | 25592 | q50 | 2^-18 (3.8147e-6) | 1,563,250 |
| 33 | 25603 | q50 | 2^-17 (7.6294e-6) | 1,129,688 |
| 34 | 25609 | q50 | 2^-16 (1.5259e-5) | 314,061 |
| 35 | 25617 | q50 | 2^-15 (3.0518e-5) | 78,594 |
| 36 | 25625 | q41 | 2^-14 (6.1035e-5) | 19,683 |
| 37 | 25633 | q40 | 2^-13 (1.2207e-4) | 4,977 |
| 38 | 25638 | q28 | 2^-12 (2.4414e-4) | 1,294 |
| 39 | 25643 | q28 | 2^-11 (4.8828e-4) | 373 |
| 40 | 25648 | q28 | 2^-10 (9.7656e-4) | 114 |

角度不是精确的 2 的幂，而是拟合值；表中的指数是主导权重。
41 项覆盖 33 个不同权重：`2^-3..2^-17`（15 个，block A）、
`2^-15..2^-35`（21 个，block B）、`2^-10..2^-14`（5 个，block C）。
8 个权重有两项：`2^-10..2^-17`。`pairs.py` 的实际交集不是空集，
例如 `2^-17` 两项交集 283,499 个 x，`2^-15` 交集 22,649 个 x；
因此不能把同权重的两项简单合成一个 Boolean 项。

## 2. 33 项数值拟合确实存在

理想 fine 相位 `T` 是 34-bit 定点数：`N = floor(T_half * 2^35)`，
`N ≤ 2^33`（bit length 34），权重 `2^-2..2^-35`。取权重 `2^-2..2^-34` 的 33 位、
丢掉最低位 `2^-35`，得到 33 项表示。全域检查（`truncation.py`）：

| 指标 | 值 |
|---|---:|
| 最差误差/容差 | **0.8637381700291318** |
| 最差 x | 3,132,865 |
| 最小绝对余量 | **4.588634648e-12 turns** |
| 33 旋转的合成 eps | 4.368369970e-13 |
| 33 旋转合成成本 | **233.412822260C** |
| 基线 41 旋转合成 | 294.840823889C |
| 合成节省 | **61.428001629C** |

这是**数值拟合**，不是电路：它假定 33 个理想位 `g_w` 可以免费计算。
这 33 个位就是需要的新 Boolean 控制；下面检验它们是否便宜。

## 3. 廉价控制检验

### 3.1 线性（免费 CX）不可行

在 41 个旋转检查点，取当前全部 62 根量子线和已定义经典位，
在全部 3,133,452 个 x 上做 GF(2) 线性张成检验：
**33 个理想位没有一个属于任何检查点的线性张成（0/33）**。
`linear_span.json`。

再把扫描扩展到全部 49,051 个操作（每个 op 都检查，2048 个 x 的样本），
**没有任何一个 op 上任何一个理想位是活线的线性形式（0/33）**。
`scan_checkpoints.py`；样本上的否定是全域否定的有效证据。
也就是说，合并字从未以 33 根（或更少）独立线性的形式存在于电路中。

### 3.2 二次（1 CCX）不可行

在 41 个旋转检查点，取活线的 GF(2) 基，构造
`{1, p_i, p_i p_j}` 的二次张成（秩约 1,200–1,770），
在 8,192 个 x 的样本上检验：
**33 个理想位没有一个属于任何检查点的二次张成（0/33）**。
`quadratic_span.py`。因此 pairwise product 不能在这些检查点直接生成理想控制。

原 41 个掩码在别的检查点的二次可用性也很有限：
只有相邻旋转出现（checkpoint 15295: 掩码 0,1；15303: 0,1,2；
15311: 0,3；25418: 15,16），没有跨阶段的合并。
`quadratic_orig_sample.json`。这等价于公开作者说的
“needed Boolean controls not in the checked quadratic span”。

更便宜的 cubic 单项也做了 support-aware 检查（`cubic_monomial_probe.py`）：
样本 32,457 个 x，包含稀疏目标 f_36..f_40 的全部 24,339 个支撑点加 8,192 个随机 x。
在 block A 末尾（checkpoint 14）对 f_33..f_40、在 block C 末尾（checkpoint 40）
对 f_0..f_7，**没有任何一个目标是实际活线的单个 linear/quadratic/cubic monomial**
（0 hit）。单个 cubic product 的成本是 2 CCX；连这个最便宜的三次项都不能直接匹配，
需要多项之和，成本更高。第一次用 4,096 个随机 x 的版本出现了 951 个“命中”
（示例全部是 popcount=114 的 f_40），那是稀疏目标在样本上全零导致的假阳性；
换成包含全部支撑点的样本后为 0。这里只穷举了实际活线的单个 monomial；
任意三个线性形式之积的完整 cubic 张成没有穷举（需要 >41k 个约束的 GF(2) 求解，
且即使属于该张成也可能需要很多 CCX）。

### 3.3 纯 33 子集（只删 8 个 Z_POW + 重调角）不可行

删除一个 `Z_POW` 在电路语义上是精确的：该旋转的 HMR 仍发生，
kickback 与后续条件 Z 纠相仍相消，所以只去掉该相位项，其他线不变。
如果存在 33 子集 + 角度微调能过容差，那会是最便宜的方案。

实测（`fit_subset.py`，不重调角）：

| 方案 | 最差误差/容差 |
|---|---:|
| 删最小的单个 rot15 | 1.330447 @ x=3,063,147 |
| 删最小的 8 个 rot15–22 | 110.528803 @ x=3,127,843 |
| 保留 33 个最大角（贪心） | 110.528803 |

再用公开 `fit_phase.py` 的 constraint-generation LP 重调 33 个保留角
（`subset_lp_iter.py`，初始 19,141 个约束，逐轮加入最差 2,000 个 x）：

| 删除集 | 全域最差比 | 最小绝对余量 | LP margin |
|---|---:|---:|---:|
| 15–22（8 个最小角） | **110.528803136** | -4.387915e-9 turns @ x=161 | 3.176596e-12 turns |
| 15–21,23（避开 x=161 的 8 个最小角） | **165.846762** | -6.512002e-9 turns @ x=50 | 3.176596e-12 turns |

LP margin 恰好停在基线的 `3.1766e-12 turns`，说明角度微调不能补偿被删项；
全域最小余量为负，且最差比在 100 倍以上。

更根本地：41 个掩码 GF(2) 秩 41，因此实数域线性无关。
删掉任意 8 个后，被删相位的非零组合不可能落在保留 33 个的实张成里；
纯子集不可能精确表示。以上测量给出自然子集的实际差距。
没有跑完 95,548,245 个 33 子集的穷举 LP；但两个自然/避开最坏 x 的集合都远离容差。

一个独立的计数下界：低字节 `W = Σ_{k=0}^7 2^k f_{15+k}` 在 `pairs.py` 中
取 0..255 全部 256 个值且近似均匀。最大 x 的容差对应 W 的绝对误差 < 2.31，
即每个 W 值要被误差 ≤2 的相位值覆盖。k 个 Boolean 项最多产生 `2^k` 个不同相位值，
覆盖 256 个值至少需要 `2^k ≥ 256/5 ≈ 52`，即 `k ≥ 6`。
所以低字节最多省 2 项；要从 41 项省到 33 项，还必须在高/中位再省 6 项，
而高/中位的合并需要 carry（非线性），不是简单的同权重项相加。

## 4. 代价账

回本预算（`economics33.py`）：

```
33 旋转合成                    233.412822C
基线 41 旋转合成               294.840824C
合成节省                        61.428002C
8 个旋转的 gadget 逻辑参考      8 × 3.5 = 28.0C
总回本预算                      89.428002C
```

新算术必须 **< 89.428C** 才能有正收益。下界：

| 新算术 | 下界 |
|---|---:|
| `phase_fused` 式两级 shift ladder，34-bit 字，正反两遍 | `4 × 34 = 136C` |
| Gidney `gadd` 34-bit，正反两遍 | `2 × (34-1) = 66C` |
| shift + adder | **202C** |
| 净收益（仅 shift） | **-46.57C** |
| 净收益（shift + adder） | **-112.57C** |

这些是下界，不含 33 个旋转自身的 CCX/CSWAP loading、HMR 纠相
和 high-word 搬移；实际新 C 只会更大。

换成总账（62Q，score = 62 × 新 C）：

| 方案 | 新 C | 62Q score |
|---|---:|---:|
| 基线 | 1,575.819 | 97,700.78 |
| 仅 shift ladder 136C | 1,622.391 | 100,588.24 |
| shift + adder 202C | 1,688.391 | 104,680.24 |

shift ladder 下界本身已超过 89.428C 的回本预算。公开
`merge_build.py` 的 merged 路径正是这个结构：加 7 个 high qubit，
`gadd` 正反两遍，`phase_fused` 在 25-bit 字上做两级 shift；
25-bit 的 shift ladder 已是约 `4×25=100C`，而它只换 8 个旋转的节省。
公开作者“cost more arithmetic than it saved”的结论与这里的下界一致。

宽度账：`census.json` 的保守活跃区间显示第一个旋转块
（约 `[15283,15347)`）已经在 62Q 峰值；若在早期加入 8 个重叠位，
需要 70Q。70Q 下要维持当前 score，C 必须降到
`97,700.776777236/70 = 1,395.725C`，即净省 **180.094C**，
远大于 89.428C 的旋转节省。第二个旋转块（25408–25649）只有 41 根活跃线，
有 21 根余量，但 block A 的 15 位不在该点；把它们保留到后期要穿过
`[15617,25408)` 的 61–62Q 区域（会到 76–77Q），重算则至少是
`[0,15278)` 的 247C 或 `[15617,25408)` 的约 377C，均远超预算。

## 5. 公开 fit1..fit8 的检查

没有使用任何凭据。Kaggle 公共数据集的**文件列表和单文件下载**可以匿名访问；
当前版本 `mrmeows/qcc-1375-open-circuits`（version 8）列出的是
`sources/invsqrt_20p032_verified_source/...` 解包目录，
没有 `research/results/merged/fit1.json..fit8.json`；
README 中引用的 `sources/invsqrt_20p056_verified_source.zip`、
`sources/invsqrt_20p032_verified_source.zip` 等在本版本单文件下载均返回 404。
因此没有直接读到 fit1..fit8 的 33-rotation basis。

可读到的 20.0321x 源码包给了同一套方法的实现
（关键文件已复制到 `artifacts/20261106_rot33/public/`，来源与匿名下载方式见同目录 `SOURCE.txt`）：

- `compiler/fit_phase.py`：LP + 逐轮把最差 x 加入约束，删除旋转用固定
  `delta=-old`；这是公开的数值拟合器。
- `source/baseline/round3_phase/merge_fit.py`：把 17 个 high bit 和 29 个 low bit
  合成 36-bit merged word，再对 bit 0..35 做 33 个 free fine rotation 的拟合。
- `source/baseline/round3_phase/merge_build.py`：加 7 个 high qubit `H`，
  `gadd` 正反两遍，`phase_fused` 作用于 18 low + 7 high 的 25-bit 字，
  最后 33 个旋转。
- `data/partial_merge3_fit.json`：tail 3（索引 41,42,43）的 partial merge，
  全域最差比 0.999447，`synth_C=296.51`；它已经需要“new high word”。

这与公开 research README 的记录一致：33-rotation 拟合的数值余量
（`35,960,695` units of `2^-64` turns，最差比 0.999585）不是瓶颈，
瓶颈是 merged word 的控制算术。公开作者没有发布实现该控制的电路。

## 6. 复现命令

在 `.worktree/invsqrt` 下，使用 `.venv/bin/python`：

```sh
.venv/bin/python experiments/invsqrt/20261106_rot33/extract_masks.py
.venv/bin/python experiments/invsqrt/20261106_rot33/analyze_masks.py
.venv/bin/python experiments/invsqrt/20261106_rot33/validate_phase.py
.venv/bin/python experiments/invsqrt/20261106_rot33/truncation.py
.venv/bin/python experiments/invsqrt/20261106_rot33/linear_span.py
.venv/bin/python experiments/invsqrt/20261106_rot33/quadratic_span.py
.venv/bin/python experiments/invsqrt/20261106_rot33/quadratic_orig.py
.venv/bin/python experiments/invsqrt/20261106_rot33/cubic_monomial_probe.py
.venv/bin/python experiments/invsqrt/20261106_rot33/scan_checkpoints.py
.venv/bin/python experiments/invsqrt/20261106_rot33/fit_subset.py
.venv/bin/python experiments/invsqrt/20261106_rot33/pairs.py
.venv/bin/python experiments/invsqrt/20261106_rot33/gadget_cost.py
.venv/bin/python experiments/invsqrt/20261106_rot33/economics33.py
.venv/bin/python experiments/invsqrt/20261106_rot33/subset_lp_iter.py 15 16 17 18 19 20 21 22
.venv/bin/python experiments/invsqrt/20261106_rot33/subset_lp_iter.py 15 16 17 18 19 20 21 23
.venv/bin/python experiments/invsqrt/20261106_rot33/branch_check.py
.venv/bin/python experiments/invsqrt/20261106_rot33/summarize.py
```

实际耗时（本机）：full mask trace 2.2s；linear span 1.8s；
quadratic span 2.5s；all-op scan 14.2s；每个 subset LP 约 40s；
`fit_subset.py` 约 90s。`cheap_fit.py` 的 greedy OMP 也跑过，
在 6,178 个候选上最差比 1.4e7，是失败的启发式，不作为定量结论。

## 7. 范围与未完成

- 本记录只有数值拟合、掩码/张成检验和成本下界；
  **没有生成 33-rotation 候选 KMB**，没有官方全量验证，没有 Kaggle 提交。
- 线性/二次张成检验的否定来自样本；若函数在全域属于张成，它在样本上也必须属于，
  所以样本否定是全域否定的有效证据。反过来，样本上的通过不构成全域名。
- 没有穷举 95,548,245 个 33 子集的 LP；两个自然/避开最坏 x 的集合实测均 >100。
- 公开 fit1..fit8 的 JSON 未在当前公共数据集列表中；只读到同方法的
  `fit_phase.py`、`merge_fit.py`、`merge_build.py` 和 `partial_merge3_fit.json`。
- 若未来出现以下任一情况，结论需要重算：
  1. 在 62Q 下用 <89.428C 的新算术直接得到 33 个理想位（或等价 33 函数）；
  2. 61Q/60Q 调度改变了宽度/回本预算，或释放出足够线做 merged word；
  3. 找到一个不同于理想位的 33 项表示，其控制可在现有检查点用
     <89.428C 的线性/二次/少量三次逻辑生成。
