# Fix4: 成本校准更新（invsqrt §2-4）

范围：更新 `approxB62.billing_hypothesis` 的基线静态校准切点，
明确 256 项完整地址表，一般旋转 / T / Clifford 分开计数；
旧纸面成本全部保留为历史记录，新候选排名只用 Q×C 实测。
不重跑 billing 网格（假设项不变，只换切点口径），不跑官方验证。

复现（2026-11-02 实测）：

```
uv run python -c "<Fix4-calibration 段：新旧两套切点的 CCX 分段计数 + F；Z_POW 68 分类>"
uv run python -c "<Fix4-table 段：trackB_fit S=7 nseg=256 vs S=6 nseg=128；两候选 full/margin>"
```

机器可读切点表：`artifacts/20261102_generator_v2/invsqrt/fix4_calibration.json`。

## 1. 新切点表（新基线 47258 ops；`stage_align.json` 权威边界）

`baseline_calibration()` 仍用 ahmed 旧坐标（`ccx(16127,25630)` /
`ccx(28726,43870)`）切新 KMB：一刀切在 B 区中部（新 B 止于 25687）、
一刀切在 inverse 区中部（新 inverse_B 起于 28783、inverse_A 止于 43927）。
实测：

| 切点 | 口径 | CCX 数 |
|---|---|---|
| compute `16127:25630`（旧，B 被腰斩） | 旧 | 375 |
| compute `16127:25687`（新，A+B 完整） | 新 | 384（A 37 + B 347） |
| uncompute `28726:43870`（旧，两头各差一段） | 旧 | 483 |
| uncompute `28783:43927`（新，inverse_B 282 + inverse_A 196） | 新 | 478 |
| F = uncompute/compute | 旧 1.288 | 新 **1.2448** |
| Lphase `25687:28783`（参考，非校准项） | — | 171 |

旧 `F=1.288`（`trackB_approx.md` §5 “校准”行）是切点错位产物，
`billing_hypothesis` 的 `qrom_meas=(1+F)·N` 须换 `F=1.2448`。
`compute_ccx=375 / uncompute_ccx=483` 数字保留为历史（旧切点），
不再用于任何新候选排名。

## 2. 256 项完整地址表

`fit_config` 的 `nseg_total = 2·2^S`：S=7 → **256**（2 parity × 128），
S=6 → 128。实测 `trackB_fit_7_8_16_5_trunc.json`（`nseg=256`，rect 通过，
0.431×TOL）与 `trackB_fit_6_8_16_5_trunc.json`（`nseg=128`，rect 不通过，
3.934×TOL）。旧 billing 取 `N=2^S`（S=7 计 128 项），漏掉 parity 维：
QROM 地址扇出 `qrom_meas=(1+F)·N` / `qrom_rev=2·N` 应按完整 256 项重表
（或书面声明 parity 共享解码假设并量化）；在声明补齐前，
`trackB_billing_*.json` 的 `datapath_exec`/`Q62xC` 全部冻结为历史假设。

## 3. 一般旋转 / T / Clifford 分开计数（新基线实测）

| | Clifford | T | 一般旋转 | 小计 |
|---|---|---|---|---|
| 无条件 Z_POW | 6 | 1 | 41（实测：41 条条件栈全空，创始行 `(15253, q28, [])`） | 48 |
| 条件 Z_POW（b414/b308，行内 if，depth 0） | 8 | 12 | 0 | 20 |
| 合计 68 | 14 | 13 | 41 | 68 |

旧 billing 的 `T_base=7` 硬编码假设（`cmd_billing` 打印的
`baseline_official {score 100568.4992, C 1622.07, toffoli_exec 1325.48,
t_base ~7, n_rot 41}` 同为硬编码）与此表的关系：条件 T 实测 12
（非 7），无条件 T 还有 1。`T_base` 改记“待实测”，旧纸面 billing
（91231 / 95007 / 96553 及 reversible 变体）冻结为历史。
另：`w_keep=24`、`Ws_sum=40` 硬编码假设不变（仍非实测宽度），一并冻结。

## 4. 历史记录封存与新排名规则

封存为历史、不再用于候选排名：README 的 62Q/81.10、63Q/105.56、
64Q/129.26 回本线（切点与口径双重过时）；`retain_chain62/chain2` 的
dscore 行（旧 F、旧切片口径）；`trackB_approx.md` §5 billing 表与余量
叙述（旧切点、128 项表、`T_base=7`）；`approx_boundary.log` 108 行
rect 网格（搜索 bug 见 evidence_fix5，rect 数字本身是 bug 版搜索产物，
有效性仅由各自独立全域检查背书）。
新规则：候选排名只用 **Q×C 实测**（verifier 单位，执行口径；
条件执行部分按版本化结果计，见 evidence_fix2——当前 0 电路、
0 verifier 运行，无候选可排）。

实际命令输出（粘贴）：

```
total ops 47258
OLD compute ccx(16127,25630)= 375
OLD uncomp  ccx(28726,43870)= 483
NEW compute ccx(16127,25687)= 384
NEW uncomp  ccx(28783,43927)= 478
A-only ccx(16127,20738)= 37
B-only ccx(20738,25687)= 347
Lphase ccx(25687,28783)= 171
invB ccx(28783,32283)= 282
invA ccx(32283,43927)= 196
F_old= 1.288
F_new= 1.2447916666666667
Z_POW classes (ALL): {'clifford': 14, 'rotation': 41, 't': 13}
uncond Z_POW: {'clifford': 6, 'rotation': 41, 't': 1} cond Z_POW: {'clifford': 8, 't': 12}
```

官方验证：0 shots（未运行）。Kaggle 提交：无。
