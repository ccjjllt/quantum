# dfthcsos 已放弃方向总览（2026-11-12）

分支 `codex/dfthcsos-research`。本文件是所有已关闭/不再做方向的唯一保留记录。
旧关闭记录见 `CLOSED_RESEARCH.md`（保留）；形状扫描结论见 `20261110_shapes/README.md`（已删，数字下收）。

## L-BFGS 训练路线：盆地关闭（_gpu 实证）
- R5/B135/C70：2000 步 85.31 → 10k 49.85（CPU 807s）→ **50k 40.24**（GPU 467s）；
  15k 步后每 2500 步仅降 ~0.4，渐近 ≈38–40，距 20 mHa 仍 ~20。
- R4/B131/C83：20k **73.07**（GPU 194s），远未到门。
- 新形状 R4/B143/C83 30k：**50.46**（GPU 283s；相对旧 R4 好，但渐近 ~48–50）。
  新种子 R5-eigrr 30k：**53.29**（GPU 295s；差于 R5 基线 40.24）。
- 结论：算力≠解。20 mHa 需要新形状/新 loss/新优化器，不再烧卡。
  载体（`slim_train.py` + `fastfit.py` + `prob_r5.npz`）保留在 `20261110_gputrain/`。

## 字宽/结构死线（零训练可判）：关闭
- brot=6：T×Q −18.61% 但 e1 字宽地板（9620 mHa 缺口，训练梯度恒零）不可兑现。
- B≤128 小形状：temp 悬崖（B=128→130 处 temp 303→574，Q 427→~697，T×Q +45%∼+51%），
  R6 小 B 全灭；R6/B143/C59（+0.13%）、B160/C59、C70、B180/C59 均负收益。
- 固定 (8,143,44)：KKT 切空间、第二折点、联合 Newton、LSB、预算再分配全 closed。
- Huber（更差）/ joint e2+αL1（同盆地）/ U-only 分阶段（+115.65 mHa）：全 null。
- 换基 rand/dft（500 步 373/593 mHa，更差）；J 扫描 J=5 已最优；R4 翻转 signed 空间为空。

## 旧基线系（历史）
- `20261106_gain_search`（λ 微增益 + R4/R5 预算）、`20261108_frontier_refit`
 （W-only refit −15,251.61，c1321df2）、`20261109_angles/joint/longloss/ubasis`
 （新 planner −0.41%、短训 182、长训 2000 步 null）。
- `20261106_high_yield`（570M 训练中间产物，盆地数字已入本文件/GPU 记录）：删除。

## 2026-11-11 recon probes（新增，全部关闭）
- **公开集扫描**：截至 2026-11-11 11:34 UTC 无低于 298,600,061.56 的公开化学集；
  heliosli v95 `8d4c99a2` 298,600,262.29、junmiaotiao `e627ac4d` 298,859,435.63、
  catalog best `8d4c99a2` 298,600,262.29、T01 best 299,454,243.65、T03 best
  303,854,940.78。基线 8afd4c67 仍最优。见 `20261111_public_survey/`（已删）。
- **MBU 反向装载**：公开 loader 已经是 forward+MBU（prefix/setup 的相位 gadget）；
  15 个 loader 共 4,123 CCX/pass、1,142 HMR+CZ，最后一个 CCX 之后 0 CCX。
  相干反算本会多 2,284 T（15.32%），已省下；剩余 215 loads 是 oracle 输出，
  verifier 同电路跑两遍，2× 是结构性的。对 word 寄存器做 MBU 的变体
  （k0 + `HMR q11..q50`）官方 `recover_words_from_circuits` 直接报
  `InvalidCircuits: ANGLE_0: uncorrected phase (measurement kickback)`；
  即使补相位修复，HMR reset 也会把 word 清零，前向 word 检查失败。
  见 `20261111_mbu_probe/`（已删）。
- **形状 (5,129,68)**：精确 heuristic T 6,516、Q_total 427（387 是 heuristic qubits，
  不是计分 Q）；现 loader 下仅 −0.98%，线性 loader 缩放投影 −23.6%（228.12e6，
  未合成 721 地址 loader）。5k 连续 e2 67.82 mHa，自由幂律外推 50k 38.3 mHa；
  R5/B135/C70 50k 40.24 mHa 对照；U 参数 49,020 vs 当前 86,944，20 mHa 不可信。
  见 `20261111_shape_probe/`（已删）。
- **7-bit 字**：直接重量化 e1 2.04 Ha / e2 0.45 Ha（门 0.02 Ha 的 100×/22×），
  λeff 78.15；T 估计 −7.45%（−810 loader T −300 Givens T），但精度地板 ~40 mHa，
  8-bit 已在量化地板。见 `20261111_7bit_probe/`（已删）。

- **R3/B129**：GPU 50k（qingyu1232/qcc-r3-gpu-train，1,751.2 s）连续 e2
  (3,129,114) 87.53 / (3,129,120) 95.92 / (3,129,150) 96.35 mHa；远离 20，
  未量化，关闭。见 `20261111_r3_probe/`（已删）。
- **R8 基组 B 143→129/131/135**：连续 B135 5k 18.51 / 20k 16.71 mHa，
  B131 5k 20.42 / 10k 19.12，B129 5k 21.55；但 8-bit Lera quantize 全配方
  （GPU 1,479.1 s）后 B135 e2 33.1236 mHa（e1 11.204，λeff 49.8628），
  `build.py` 拒绝；且公共 `tensorqrom` 1,156 行实测 4,528–4,530/pass
  = 9,056–9,060 T（fourqrom J=3 16,800 T），B135 打平线 8,262 T；
  投影 score 334.3M（+11.96%）。连续精度不够 + loader 成本否决，关闭。
  见 `20261111_r8_basis/`（已删） 与 `20261111_r3_probe/`（已删）。

## 历史已落实（数字存档，文件删除）
- P0 `20261110_p0_gauge`：299,497,670.48（T−8），曾随三件套提交；已被 Lera/Maoxin 取代。
- Lera `20261111_lera11x`：298,942,333.64（−555K），曾被 Maoxin303 取代。
- Maoxin303 `20261111_lera_deep`：298,720,881.30；已被 Maoxin v22 4,097 loader 取代。
- 当前采用见 `README.md`：`f21b8a87` + Maoxin v22 4,097 loader，297,557,548.71。

## 可复用载体（保留，不属放弃）
- `20261106_train_r5`：`seed_numpy.py`（种子生成）。
- `20261110_gputrain`：`slim_train.py` + `fastfit.py` + `prob_r5.npz`（训练/拟合栈）。

## 2026-11-12/13 追加关闭（详细目录已删除，数字保留）
- **coded2**（`20261112_coded2`，387M artifacts）：e1 22.65 / e2 34.60 mHa（门 20.0）；
  本仓库 loader 对同表复现 4,612/pass，最好 ~307.6M。精度与 loader 差距双否。
- **R=4 C 截断联合**（`20261112_ctrunc_joint`）：C=110 连续原子 18.89 mHa 过门，
  但 rows=1,096 需 11-bit loader，成本 325–337M（+9.5–13.4%）；B=255 下成本无解。
- **R=7 / (R,C) 重分区**（`20261112_r7`、`20261112_rc_shape`）：R=7 loader
  4,672–4,677 T/pass，成本 311.9–327.1M；门内形状 basis 1,020–1,287，R=7 不足。
- **loader 结构搜索**（tree/row/batch/gauge/lowbits/J）：
  当前树/行序/gauge 已最优；J=5 最优但比当前 +14.07%；lowbits=3 总账仅 −0.9%
  且 λeff 更差；tree_real 用自己的构造器重建同表 5,414 T/pass（公开 4,089）。
- **loader product-set/full-support/ESOP**（`20261112_loader_productset` 等）：
  “4089→3881 T/pass、288.90M” 是 z=0 假象，官方 `evaluate_circuits` 以
  `uncorrected phase` REJECTED；full-support 需 8 product/bit（不是 1）；
  输出基变换是严格零收益；gate-level 可删 T 实测 0。
- **loader-aware 训练**（`20261112_loader_aware_train`）：真 loader = 80 缓存 AND +
  214 product CCX = 4,097；结构化 1% loader T 要付 ~10× 误差门代价；表字 rank 15/15
  已是当前构造器最泛型。no-go。
- **其余形状/训练**（`20261112_table_survey`、`group_search`、`j6`、`jbatch`、
  `loader_re`、`loader_opt`、`kaggle_r4_gate`、`kaggle_r4_ctrunc_gate`）：
  均无 ≥2.5% 收益或成本/误差否决；关键数字已在本文件与 main
  `docs/abandoned-research.md`。
- **未完成项**（`20261113_cfix`）：只有 `run.py`，无 README/结果/候选，未纳入研究结论；
  随本目录删除。

## 2026-11-13 停止研究
公开 4,074 T/pass + 296.64M 化学件已略优于自研 `f21b8a87` + 4,097 loader
（297.56M，+0.31%）。`(8,143,44)` 的 T/Q/λeff 已接近局部最优；训练盆地 38–40 mHa
距 20 mHa 约 2×；loader 4,089 已被逆向到机制层，本仓库构造器无法在 ≤4,089 落地。
继续需要新 factorization/新训练范式，停止推进。总览见 main `docs/abandoned-research.md`。

## 删除清单
- `experiments/dfthcsos/` 下除本文件、`README.md`、`CLOSED_RESEARCH.md`、
  `20261110_arch_review/`、`20261106_train_r5/`、`20261110_gputrain/` 外全部目录
  （含 20261112 的 loader/shape/tree/group/j6/jbatch/coded2/rc_shape/r7 等全部
  以及未完成的 20261113_cfix）。
- `artifacts/` 下删除 `20261112_coded2/`（387M）、`20261112_rc_shape/`（405M）、
  `20261112_ctrunc_joint/`（71M）、`20261112_tree_real/`（54M）、`20261112_jbatch/`（47M）、
  `20261112_r7/`、`20261112_loader_re/`、`20261112_loader_aware_train/`、
  `20261112_group_search/`、`20261112_j6/`、`20261112_lowbits/`、
  `20261112_loader_productset/`、`20261112_loader_esop/`、`20261112_gauge_search/`、
  `20261112_tree_search/`、`20261112_table_survey/`、`20261112_row_order/`、
  `20261112_batch_group/`、`20261112_kaggle_r4_gate/`、`20261112_kaggle_r4_ctrunc_gate/`；
  `20261110_gputrain/` 保留训练栈。
