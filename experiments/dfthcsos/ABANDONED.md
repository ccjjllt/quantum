# dfthcsos 已放弃方向总览（2026-11-11）

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
  303,854,940.78。基线 8afd4c67 仍最优。见 `20261111_public_survey/`。
- **MBU 反向装载**：公开 loader 已经是 forward+MBU（prefix/setup 的相位 gadget）；
  15 个 loader 共 4,123 CCX/pass、1,142 HMR+CZ，最后一个 CCX 之后 0 CCX。
  相干反算本会多 2,284 T（15.32%），已省下；剩余 215 loads 是 oracle 输出，
  verifier 同电路跑两遍，2× 是结构性的。对 word 寄存器做 MBU 的变体
  （k0 + `HMR q11..q50`）官方 `recover_words_from_circuits` 直接报
  `InvalidCircuits: ANGLE_0: uncorrected phase (measurement kickback)`；
  即使补相位修复，HMR reset 也会把 word 清零，前向 word 检查失败。
  见 `20261111_mbu_probe/`。
- **形状 (5,129,68)**：精确 heuristic T 6,516、Q_total 427（387 是 heuristic qubits，
  不是计分 Q）；现 loader 下仅 −0.98%，线性 loader 缩放投影 −23.6%（228.12e6，
  未合成 721 地址 loader）。5k 连续 e2 67.82 mHa，自由幂律外推 50k 38.3 mHa；
  R5/B135/C70 50k 40.24 mHa 对照；U 参数 49,020 vs 当前 86,944，20 mHa 不可信。
  见 `20261111_shape_probe/`。
- **7-bit 字**：直接重量化 e1 2.04 Ha / e2 0.45 Ha（门 0.02 Ha 的 100×/22×），
  λeff 78.15；T 估计 −7.45%（−810 loader T −300 Givens T），但精度地板 ~40 mHa，
  8-bit 已在量化地板。见 `20261111_7bit_probe/`。

## 已落实（保留，不属放弃）
- `20261110_p0_gauge`：P0（299497670.48，T−8）已随三件套提交，留作回退。
- `20261111_lera11x`：Lera (8,143,44) PASS 298942333.64（−555K），新基线候选。
- `20261106_train_r5`：种子生成脚本（`seed_numpy.py`）保留。
- `20261110_gputrain` / `20261110_gpu_newshape/`：盆地证据 + 可复用载体。

## 删除清单
- `experiments/dfthcsos/` 下除本文件、`20261110_arch_review/`、`CLOSED_RESEARCH.md`、
  `20261106_train_r5/`、`20261110_gputrain/`、`20261110_gpu_newshape/`、
  `20261110_p0_gauge/`、`20261111_lera11x/`、`README.md` 外全部目录。
- `artifacts/` 下删除 `20261106_high_yield/`（570M）、`20261106_syed_v9/`、
  `20261108_public_frontier/`、`20261109_*`、`20261110_brot6/`、`20261110_shapes/`。
