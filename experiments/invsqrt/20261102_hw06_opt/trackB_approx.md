# Track B 近似线首轮结论（invsqrt / 20261102_hw06_opt）

状态：首轮 108 配置网格完成（模型级），3 个候选完成 angles + 全域模型检查 + billing 假设。
**无电路、无官方 verifier 运行、无 gain claimed。**所有计费数字均为假设。

## 1. 模型（见 `approxB62.py` 头 docstring）

- shift-14 坐标：`(m>>14, delta 14位)`，bit20 保留在段地址内；`S∈{6,7}`，分 parity 拟合。
- S=6：bit14 折入 dprime（精确），bit0 成为 domain-doubling 约束（特征 bit0-blind）。
- 特征：`u` 全精度，`w=ut²`（ut 为 r0 起点截断/舍入量化，`r0∈{5,6,7}`）；模型 `vhat=B0+M·u+R·w`。
- **“精度”= CSD 非零 digit 数预算**（位置自由）：M 占 `Pm∈{7,8,9}`，B0/R 占 `Pr∈{16,17,18}`。
  `quantize_cap` 按 cap 截 LSB digit，`fit_segment` 坐标 digit 搜索全程强制 `len ≤ cap`。
- **相位角每配置重拟合**：`cmd_angles` 从本配置自己的 `coef_store` 整数模型位出发构造角度，
  不读取、不截短任何旧角度表。`cmd_full` 只用同配置 `drop0` 角度。无沿用旧表行为。
- 拟合：相对残差 scale-normalized IRLS minimax 初始化 → CSD 量化 → tread 代表域坐标搜索。

## 2. 本轮发现的两个代码 bug（均已修复，结果无效项已重跑）

### Bug A：B0 重缩放漏 `+1`（`irls_minimax`，已修，~line 220）

`R = V/C − 1`，故 `V = C·(1+c0) + (c1·C)·U + (c2·C)·W`。旧代码 `B0 = coef[:,0]*C` 漏了 `+1`，
初值 `B0r ≈ −7e−8`（应 ≈1.05），预测 `pred ≈ −2.7e−7` vs 真值 `≈1.05`。

- 证据（S=6,Pm=7,Pr=16,r0=5,trunc,seg=51,p=0）：float 初值（未量化）已 `maxrel=1.002`；
  修复后同配置 float 初值 S=6 为 2.6e−7、S=7 为 2.8e−8。
- 独立 `--cfg 7_9_18_5_trunc` 与 boundary 日志行 `maxrel` 逐位一致
  （`2.5517425182888425e-08`），确定性可复现。

### Bug B：角度 minimax LP 数值 invalid（`fit_angles`，已移除，改精确二进制权重）

- 现象：最优 rect 配置（maxrel 2.55e−8）经 LP 后 boundary `maxrel=136.7`、`lp_t=8.4e6`、
  `max_abs_dev_weight=0.32`。
- 根因：LP 约束矩阵混入 O(1) 位列与 `tol~1e−11` 缩放的 t 列，低于求解器可行容差；
  而平凡可行点（二进制权重）本可达到 `t≈0.43`。“最优” 8.4e6 ≫ 可行 0.43 ⇒ 求解器/scaling 失败。
- 修复：角度取**精确二进制权重 + 全局 const 余量居中**（`max_abs_dev_weight=0.0`），
  同配置同集合验证 `maxrel=0.579` 通过（16s，原 LP 96s）。
  LP 被删除而非重缩放：精确权重已对模型相位字 bit-exact，37 自由度对 786k 约束本无实质增益。

## 3. 中断的 12 行旧日志解读（已归档 `approx_boundary_preB0fix.log`，全部作废）

1. `maxrel_rect≈1.0000002~5` 是**真超差**，不是口径问题：容差是 `2⁻²⁴≈5.96e−8`，
   `maxrel≈1.0` = 100% 相对误差（超容差约 1.68e7 倍），源头是 Bug A（预测≈0）。
   佐证：同 `(r0,variant)` 下 Pr=16→17 的 `maxrel` 逐位相同——真正拟合误差不可能对 digit cap
   完全不敏感；且坐标搜索被困（单步加 digit 够不到 B0≈1.05，加 digit 候选还有 pick-one 缺陷）。
2. `synth_share_left = 1 − worst/TOL` 是“容差预算剩余份额”（留给旋转合成的份额），
   `≈−1.68e7` 即拟合已花掉容差的 1.68e7 倍、合成为零预算。它量的是**拟合余量**，不是综合余量。
3. `worst_loc` 聚集 `(p=0,seg=51,dprime≈中心,sub=1)` 说明**系统性偏差**而非局 Dom 建模困难：
   `pred≈0` 处处成立时 argmax 确定性地落在最大 V 点，与配置无关。修复后 worst_loc 即散开
   （seg 0/2/3/9/24/53，d 取边沿 0/31/127/16319/16352/16383 等真实困难区）。

## 4. 首轮网格结论（108 配置，修复后全量重跑，`approx_boundary.log` 108 行 + `trackB_grid.json`）

下表为 `maxrel_rect / 2⁻²⁴`（`<1*` = 通过；Pr 三列逐位相同，B0/R cap 从不在最坏点起作用）：

```
S=6（0/54 通过；最好 3.93×超差）
Pm=7 : r5tr:4.77 r5ro:6.16 r6tr:8.86 r6ro:7.53 r7tr:10.06 r7ro:10.84
Pm=8 : r5tr:3.93 r5ro:4.06 r6tr:6.03 r6ro:6.35 r7tr:8.08 r7ro:10.76
Pm=9 : r5tr:3.93 r5ro:4.06 r6tr:5.44 r6ro:6.18 r7tr:8.08 r7ro:10.84
S=7（18/54 通过 = Pm{8,9} × Pr{16,17,18} × {r5tr,r5ro,r6tr}）
Pm=7 : r5tr:1.04 r5ro:1.25 r6tr:1.49 r6ro:1.42 r7tr:2.08 r7ro:2.45
Pm=8 : r5tr:0.43* r5ro:0.58* r6tr:0.82* r6ro:1.09 r7tr:1.53 r7ro:2.25
Pm=9 : r5tr:0.43* r5ro:0.58* r6tr:0.82* r6ro:1.09 r7tr:1.49 r7ro:2.25
```

- **S=6 死**：Pm=7→8 只从 4.77×降到 3.93×，Pm=8→9 在 r0=5 零增益（3.93 逐位不变）→
  残差地板是结构性的（bit0-blind + tread 量化），非 digit 预算问题。M bind 88~99/128 段。
- **S=7 活一半**：r0=5 trunc 最好（0.43×）；r0=6 trunc 可过（0.82×）；r0=7 全死；
  round 处处劣于 trunc；Pm=7 全死（最好 1.04×，仅超 4%）；Pr∈{16,17,18} 对最坏点零影响。

## 5. 候选 angles + 全域模型检查 + billing（≤3 个）

boundary 集：S=7/r0=5 为 786052 点（含 tread 边 `t,t+1,t+step/2,t+step−1`、
`dp∈{0,1,8191,8192,8193,16382,16383}`、x=1..63、161、888、2^k±1 进位点、dprime=2^j 边界；
r0=6 为 459462 点）。全域：x=1..3133452 逐个，batch-256  framing，
尾 batch 12 真输入 + 244 padding（padding 永不求值），seeds 101/202/303 哈希一致。

| cfg | rect maxrel | boundary maxrel/margin(2⁻⁶⁴ turns) | 全域 pass/maxrel/余量 | 检查点(1..63,161,888)maxrel |
|---|---|---|---|---|
| 7_9_18_5_trunc | 2.55e−8 (0.43×) | 0.579 / 3.15e8 (1.71e−11 turns)，最坏 x=2162624 | true / 0.579 / 3.15e8 | 0.384 (x=32)；161:0.231；888:0.117 |
| 7_8_16_5_trunc | 2.57e−8 (0.43×) | 0.610 / 2.71e8 (1.47e−11 turns) | true / 0.610 / 2.71e8 | 0.404 (x=9)；161:0.231；888:0.117 |
| 7_9_18_6_trunc | 4.90e−8 (0.82×) | 0.994 / 4.38e6 (2.37e−13 turns)，最坏 x=2097152=2²¹ | true / 0.994 / 4.38e6 | 0.823 (x=32)；161:0.454；888:0.248 |

全域 maxrel 与 boundary maxrel 逐位一致（最坏点已被 boundary 集覆盖）。
`7_9_18_6_trunc` 余量仅 0.6%——datapath 定点误差未建模，实际判死，仅留作 r0 方向证据。

Q×Toffoli-equivalent 估算（**假设**：n_rot=37 实际；datapath 执行数=静态公式值；
余量取全域值；Q=62 借用；无电路无验证。括号为 reversible-x2 变体）：

| cfg | meas Q62xC | vs 基线 100568.5 | vs 阈值 95540.1 | eps/rot | 说明 |
|---|---|---|---|---|---|
| 7_8_16_5_trunc | 91231 (143692) | −9337 | −4309 | 1.25e−12 | 纸面最优，仍依赖共享 QROM 解码等乐观假设 |
| 7_9_18_5_trunc | 95007 (151311) | −5562 | −534 | 1.45e−12 | 纸面低于阈值 0.6%，无意义余量 |
| 7_9_18_6_trunc | 96553 (152424) | −4015 | +1013 | 2.01e−14 | 纸面即超阈值 |

校准：基线静态 `compute_ccx=375, uncompute_ccx=483, F=1.288`（kickmix 实测）。
公式：`qrom=(1+F)·2^S`（meas）|`2·2^S`（rev）；`sq=(14−r0)·14/2`；`M=nM·14+20`；
`R=nR·w_keep+20`；`adds=3·Ws_sum`；`align=4·36+20`；`rot_synth=n·(0.56·log2(1/eps)+5.3)`。
**硬编码假设**：`w_keep=24, Ws_sum=40`（非实测宽度），`T_base=7`，执行≈静态。
`--billing` 输出 `trackB_billing_*.json`。

## 6. 口径说明（重要）

官方容差是**绝对相位口径** `tol(x) = 2⁻²⁴/sqrt(x)` turns（x=1 处 5.96e−8，max_x 处 3.37e−11）。
rect 阶段用的是 mantissa **相对口径**。两者逐点等价：`1/sqrt(x) = 2^e·v` 精确成立，
故 `|vhat−v|·2^e < tol(x) ⟺ |vhat−v|/v < 2⁻²⁴`。rect 门限不是放错的口径——
旧 12 行的失败是 Bug A 的真超差，不归咎于口径。
但 rect `synth_share_left` 只是拟合余量；综合余量以全域 `min_abs_margin_units` 为准；
datapath 定点舍入误差尚未建模，会吃掉这部分余量（cfg1/2 剩 ~40%，cfg3 剩 0.6%）。

## 7. 结论与下一步

- **放弃 S=6**（结构地板，Pm 加到 9 无增益）。**放弃 r0=7、round 变体**（全死）。
- **收窄到 S=7 / r0=5 / trunc**：`7_8_16_5_trunc`（便宜）与 `7_9_18_5_trunc`（余量最大）
  全域模型通过、余量 ~40%。`7_9_18_6_trunc` 形式通过但实际无余量，不再跟。
- 下一步（二选一）：(a) 在 S=7/r0=5/trunc 下探 Pm=8/Pr<16 降本（低于当前网格下限，
  需扩网格；Pr 目前零影响，降 Pr 有望不丢余量）；(b) 以绝对相位误差加权 refit 提余量
 （当前 IRLS 是相对准则，绝对最坏点 x=2162624/2097152 恰在归一化边界附近）。
- 建电路之前不 claim 任何 gain：billing 假设项（共享 QROM 解码、w_keep/Ws_sum 硬编码、
  执行≈静态、Q=62）任一落空即可吞掉纸面 −4.5%。

## 8. 产物与验证范围

- 实验目录：`approxB62.py`（修 Bug A/B）、本文件。
- `artifacts/20261102_hw06_opt/invsqrt/`：`approx_boundary.log`（108 行，修复后全量重跑；
  旧 12 行 bug 输出归档 `approx_boundary_preB0fix.log`）、`trackB_grid.json`、
  `trackB_fit_*.json`（108）、`trackB_angles_{3cfg}.json`、`trackB_full_{3cfg}.json`、
  `trackB_billing_{3cfg}.json`。
- 验证范围：**模型级**官方容差表（`reference_values`）全域检查（3 配置通过，3.13M 真输入、
  padding 分开、3 seeds 确定性哈希一致）+ 检查点抽查；**非官方 verifier 电路验证**
  （无 .kmb 电路，verifier 未运行；verifier 本体未改动）。
- 未建测试目录/CI，未提交 Kaggle，未推送代码。
