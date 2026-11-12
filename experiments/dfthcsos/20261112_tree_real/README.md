# Givens 树用真实 loader T + refit λeff 重评（2026-11-12）

用**真实 loader**（`tensorqrom8.py` 生成的 15 个 ANGLE 电路，官方模拟器复核
`toffoli_per_pass`）重测 Givens 树，而不是 `tensorqrom.per_output` 代理。

结论：**no-go**。没有任何树能在真实 loader + 官方 `resource_costs` 下把成本压到
292M 以下；甚至没有一棵树的成本低于当前 297.237M。阻断点不是树：
(a) 我们自己的 loader 生成器在**同一张表**上就比公开 loader 贵 32%；
(b) 换树会破坏 U 的 8-bit 精确可表示性，误差门直接崩；
(c) 换树让 `E_gap` 离开地板、λeff 从 46.91 涨到 53–69。

## 1. 对照：复现当前最优

| 项 | 公开件（当前最优） | 用 `tensorqrom8` 重建同表 |
|---|---:|---:|
| 目录 | `artifacts/20261112_frontier/chem14840` | `artifacts/20261112_tree_real/work/tree_current` |
| ANGLE T / pass | **4,089** | **5,414** |
| T_total | **14,840** | 17,490 |
| Q_total | **427** | 427 |
| λeff | **46.907378146** | 46.907378146 |
| error_1 / error_2 | 19.99998 / 19.999997 mHa | 17.545 / 19.999997 mHa |
| 成本 | **297,237,044.95** | 350,315,088.69（+17.9%） |
| 官方验证 | **全量 78,080 shots PASS**（本次复跑，salt `tree-real-control`，`score=297,237,044.9509761`） | 未跑全量；官方模拟器 1 shot/address 结构校验：`words_equal=true, toffoli_per_pass=5,414.0` |

=> 公开 loader 的 4,089/pass 是**别人生成器的成绩**；`tensorqrom8` 在同一张表、同一
J=5 / lowbits=4 / 8-bit 设置下是 5,414/pass。任何树路线都要先还掉这 32% 的差距，而任务
目标只需要 1.7%。

## 2. 每棵树（同一编码器、同一 loader 设置）

编码器（所有树一致）：两体行 = 精确 `U` 在该树上的最近 8-bit 取整
(`encode.tree_angles` → `to_words`)；单体行 = `h1'` 特征向量在**该树**上做 signed-gauge
取整 + `onebody.polish`（`common.onebody_words`，无 jax）。权重 `(W, H2_I)` 沿用当前件，
未 refit（除 §2.1 的单点对照）。

| 树 | 形状 | T/pass | T_total | Q | error_1 (mHa) | error_2 (mHa) | Λ | E_gap | λeff | cost | 误差门 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **current**（log-depth 二叉树） | 深 6，44 叶 | 5,414 | 17,490 | 427 | 17.54 | 20.00 | 282.974 | 3.914898 | 46.9074 | **350.32M** | 过 |
| **heap**（二叉堆标号） | 深 6，38 叶 | 5,422 | 17,506 | 427 | 18.35 | 172.25 | 284.084 | 5.024685 | 53.1941 | 397.63M | **失败** |
| **star**（深度 1） | 深 1，75 叶 | 5,105 | 16,872 | 427 | 63.23 | 363.09 | 287.404 | 8.344921 | 68.7538 | 495.33M | **失败** |
| **path**（链） | 深 75，1 叶 | 5,428 | 17,518 | 427 | 95.60 | 362.99 | 287.336 | 8.277069 | 68.4696 | 512.17M | **失败** |
| greedy（振幅贪心合并） | 深 7，37 叶 | 未完成 | | | | | | | | | |
| twostar（深度 3） | 深 3，66 叶 | 未完成 | | | | | | | | | |

`cost` 用官方 `resource_costs(evaluate_words)`：`λeff × T_total × Q_total`，
`T_total = 6,662 + 2 × T_pass`，`Q_total = 427`。树只改 ANGLE 的 T 和 λeff，不改 Q
（重建的 ANGLE 电路 124 qubits < heuristic 的 303 临时工作区 + 124 persistent）。

关键：错误门失败的树，`E_gap` 从 3.914898（地板）抬到 5.02–8.34，λeff 从 46.91 涨到
53.2–68.8。**换树同时惩罚 T 和 λeff**，即使 T 便宜（star 5,105，比 current 少 309），
成本反而 +41%。

### 2.1 换树直接击穿误差门，短 refit 救不回来

`path`、`star` 的 error_2 = 363 mHa（门限 20 mHa，超 18 倍），`heap` 也有 172 mHa。
原因：当前 U 是**为当前树量化过的**——该表在当前树上的 8-bit 角度全部落在 1/128 栅格上
（重编码-解码角度误差 2e-8 度），所以 error_2 恰好等于 DF-THC 模型本身的 19.999997 mHa。
换树后角度不再落在栅格上，76 维向量经 75 次旋转累积量化误差；深链（path）和宽星
（star，根部振幅被 75 个 cos 连乘压到极小 → 角度贴 ±π/2）最严重。

**短 refit 也救不回来**（预算 ≤ 现有 refit）：对 `star` 跑
`artifacts/20261112_tree_real/refit_local.py`（300 次 L-BFGS + 1 轮 refine 移动，
objective/梯度与 `refit_weights.WeightProblem` 相同）：

| star + refit | error_1 | error_2 | Λ | E_gap | λeff |
|---|---:|---:|---:|---:|---:|
| 起始 | 63.2 mHa | 363.1 mHa | 287.4 | 8.345 | 68.75 |
| refit 后 | 80.8 mHa | **283.6 mHa** | 424.7 | 15.042 | **112.03** |

误差仍超门 14 倍，λeff 反而涨 63%。refit 只能调 `(w, W)`，改不了已经量化坏的 `u u^T`；
要让新树可用必须**在新树上重训整个 factorization**（`quantize.py` 那一整套 jax 流水线，
小时级），不在本次预算内。

## 3. signed-gauge（7-bit 装载）不是出路

`onebody.signed_gauge`（纯整数、精确）把任意表变成 bit7 == bit6 的规范形，loader 可以
只装 7 bit（35 输出）并借用最高位。指标**逐位不变**：

- 对当前表做 gauge 变换后：e1 19.99998 mHa、e2 19.999997 mHa、Λ 282.97398、
  E_gap 3.914898003、λeff 46.907378146 —— 与当前件完全一致；解码向量只差每行整体符号。
- 真实 loader：**T = 4,872/pass**，T_total 16,406，Q 427，成本 **328,603,164.38**
  （比 8-bit 的 5,414 便宜 10%，但仍是当前最优 297.2M 的 1.106 倍）。
- 官方模拟器结构校验：`words_equal=true, toffoli_per_pass=4,872.0`。

即：省 5 个输出位确实划算（−542/pass），但不足以抵消生成器差距，也没到 292M。

## 4. proxy 与实际 T：代理测不准，且排序会反

`tensorqrom.per_output` 代理（`cost(per_output(anf_tensor(...)), L, H)`）与实际 loader T，
都在同一批表上算：

| 树 | 代理 / pass | 实际 T / pass | 实际/代理 | 代理排名 | 实际排名 |
|---|---:|---:|---:|---:|---:|
| star | 6,000 | 5,105 | 0.851 | 4 | 1 |
| current | 5,738 | 5,414 | 0.943 | 2 | 2 |
| heap | 5,833 | 5,422 | 0.929 | 3 | 3 |
| path | 5,640 | 5,428 | 0.962 | 1 | 4 |

- 绝对误差 4–15%；**Spearman ρ = −0.8（四棵树上完全反序的两个极端）**：代理认为 path 最
  便宜、star 最贵，实际正好反过来。
- 原因：`per_output` 对每个输出位单独做秩分解，真实 `shared` 在每组 6 个输出位之间共享
  乘积项，共享程度依赖 ANF 张量结构，代理看不到。

**结论：`tensorqrom.per_output` 代理不能用来判定换树收益。**
`experiments/dfthcsos/20261112_tree_search/` 的旧结论"换树无收益"方向对，但依据不成立；
真实原因是换树会击穿误差门并抬高 λeff，而不是"T 不降"。

## 5. 其余树

`greedy` 在 25 分钟里没跑完 15 个电路（`shared` 分解在部分 delta 上明显更慢，机器同时
被其他 subagent 占满），已停止；`twostar / balanced / random` 未启动。它们不会改变结论：
heap（同样是深度 6 的平衡二叉树）已经把 error_2 打到 172 mHa，greedy 是深度 7 的合并树，
误差只会同量级或更差；而 T 的树间差最多 ±6%（current 5,414、heap 5,422、path 5,428、
star 5,105），远不足以从 350M 压到 292M。要补齐直接重跑：

```bash
cd .worktree/dfthcsos/artifacts/20261112_tree_real
../../../../.venv/bin/python sweep.py current path star heap greedy twostar balanced random:1
```

## 5b. 本地改动与复现边界

`artifacts/20261112_tree_real/` 是**自包含副本**，不改动 main、`20261112_jbatch/`、
`20261112_group_search/`：

- `pipeline/`：`dfthc_refit` 的 `paths.py / encode.py / refine.py / refit_weights.py /
  onebody.py / onebody_quant.py / fastfit.py / structure.py / polish_words.py` 只读副本。
  `onebody_quant.py` 依赖 jax（本环境没有），所以 `common.onebody_words` 实现了
  `onebody.refresh` 去掉 jax 渐进取整那一支的版本（其余 candidates/polish/kicks 相同）。
- `generator/tensorqrom8.py`：`20261112_jbatch/tensorqrom8.py` 的只读副本 + **一处本地
  patch**：`build_family` 里 grouped 分支原来固定 `scratch=True`，而 `full=True` 时字的
  最高位也是真实输出，`take()` 会把它当缓存 ancilla 借走，随后 fan-out 产生
  `CX q q`（`ValueError: qubit collision`）。改为 `scratch=not full` 后正常
  （e.g. `work/tree_current` 每电路 124 qubits）。原文件对某些表（本实验的
  重编码表、甚至当前表本身）会随机触发该崩溃。
- 编码用 `encode.encode(..., signed=False)`（`to_words(tree_angles(...))`，全 8 bit），
  与当前表的 unsigned 表示一致；`onebody` 用 signed gauge（只用低 7 位并不影响，
  因为 8-bit 模式会把 8 位全装载）。

## 6. 验证范围

- **官方全量 78,080 shots PASS**：只对公开对照件
  `artifacts/20261112_frontier/chem14840` 执行（salt `tree-real-control`），
  `score = 297,237,044.9509761`，逐项 e1/e2/Λ/E_gap/λeff 与主仓记录一致。
- **重建候选未跑官方全量**：它们的成本（≥328.6M）都高于当前件，按任务约定只有
  cost < 292M 才建完整候选并全量验证。
- **loader T 的可信度**：`tensorqrom8` 的静态 Toffoli 计数在 `work/tree_current` 和
  `work/base_signed` 上都由官方 `recover_words_from_circuits`（1 shot/address）复核，
  静态 == 模拟执行（5,414.0 / 4,872.0），且恢复出的 1,220×75 字表与提交 npz 逐位相同。
- 所有 λeff 都由官方 `evaluate_words` 算出。

## 7. 结论与下一步

- 树这一轴**不足以**达到 <292M：真实 T 的树间差 ≤6%，需要 −3.2%，且生成器本身落后
  公开 loader 32%；再叠加误差门与 λeff 惩罚。
- 还想在化学件上压成本，优先级是**换 loader 生成器/参数**（J、lowbits、7-bit 装载、
  coded 位），不是换树；这些是 `20261112_jbatch` / `20261112_coded2` 的在研方向。
- 换树的前提是**在新树上重训 factorization**（让 8-bit 角度落在栅格上），否则误差门必崩。
