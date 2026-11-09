# R5/B135/C70 新 ANGLES 共享 planner 电路 + 500 步短训探针（2026-11-09）

分支 `codex/dfthcsos-research`，工作区 `.worktree/dfthcsos/`。
起点 `b9eced3e`（λeff `46.891275349493`，T/Q=`14966/427`，`T×Q=6390482`）。
本轮不重复 W-only/LSB/预算工作（结论见 `20261109_joint_budget/README.md`）；
只做三件事：① 给 R5/B135/C70（A=751，10 位地址）发**新** ANGLES 共享 planner
电路并实测 heur_T/angles_T/Q（不是预算）；② 用新 planner 的 U 结构做 500 步
短训探针 + 1 个变体；③ 若 T×Q 确降 >2% 则做切空间 refit（本轮未触发）。

结论先行（三项全 null，但数字完整）：

1. **新电路实测 angles=8278（-26 vs 当前 8304），T=14905/Q=427，
   T×Q=6364435（-0.41%）。** 预算 T=14177（-5.27%）的缺口 728 T 没有补上；
   新形状 heuristic 只省 35 T（6627 vs 6662），tensor 共享 planner 在原始
   舍入字上与当前持平（static 4139/遍 vs 当前 4152/遍），没有拿到预算假设的
   754 T。
2. **500 步短训：182.0 mHa（复现 joint_budget），扰动重启变体 181.3 mHa。**
   量化后字误差 e1/e2 = 2.31 Ha/461 mHa——未收敛 U 的舍入字离门差 5–7 个量级，
   不是候选。
3. **切空间 refit 未触发。** 触发条件是 T×Q 确降 >2%，实测 -0.41%（trials16
   复建同为 -0.41%，和数饱和）；且新字误差在 Ha 量级，20 mHa 门附近的切空间 refit 无定义。

## 1. 新 ANGLES 共享 planner 电路（实测，非预算）

方法：沿用仓库内 Lera V7 `tensorqrom.build_family`（缓存低/高地址单项式 +
配对仿射乘积 + 测量擦除，signed 规范；`dfthc_refit/tensorqrom.py`），在
R5/B135/C70 签名规范舍入字（A=751，`(751,75)`，J=5，brot=8，固定 b9eced3e
log-depth 树）上重建 15 批全。signed 规范在 XOR 下封闭
（bit7⊕bit6=0 是线性的），故全部 batch delta 满足其断言。
对照组为官方 `angle_k_reference_circuit` 朴素 QROM（同字、同 J）。
成本口径与验证器一致：angles = kickmix 实测 fwd+rev 均值
（`recover_words_from_circuits`，shots=2，固定种子；实测恰为 static 2 倍，
无条件修正门触发），heuristic = `SpinFreeData_V1` 精确值，
Q = persist + J·brot + max(temp)。

| 电路 | angles 实测 | static/遍 | qubits_max | T | Q | T×Q | vs 基线 |
|---|---|---:|---:|---:|---:|---:|---:|
| 当前 b9eced3e（15 批，J5） | 8304 | 4152 | 128 | 14966 | 427 | 6390482 | — |
| R5 朴素 QROM（同字 J5） | 22470 | 11235 | 59 | 29097 | 427 | 12424419 | +94.42% |
| **R5 tensor 共享 planner（新，trials=6）** | **8278** | **4139** | **101** | **14905** | **427** | **6364435** | **-0.41%** |
| 预算（旧，需新电路，`compact_costs.json`） | 7550 | — | — | 14177 | 427 | 6053579 | -5.27% |

- 新电路 words_match=True（15 批全功能正确），Q=84+40+max(303,51)=427，
  与当前一致（temp 仍被 heuristic inner 303 支配）。
- 缺口算术：实测 T=14905 vs 预算 14177，差 **728 T**；heuristic 省 35 T，
  angles 省 26 T，合计 61 T，只有预算 754 T 的 8%。
- 逐批 flat：15 批 static 全为 275–276（batch0 225 terms→276T），说明成本由
  乘积项主导而非地址数；当前 V9 字 batch0 为 195 products——我们的原始舍入字
  未经 `quantize.py --coded` + refine，复杂度反而更高，吃掉了地址数红利。
- trials=16 复建：angles=8278（static 合计 4139/遍，与 trials=6 总和一致；
  仅 1T 在 batch1→batch6 间挪动，搜索已饱和）；结论不变。复建输出在
  `artifacts/20261109_angles_r5_trials16/`（`angles_r5_costs.json` 同值）。

证据：`artifacts/20261109_angles_r5/angles_r5_costs.json`（逐批 static/qubit、
heuristic 明细、words_match），
`artifacts/20261109_angles_r5/angles_tensor/*.kmb`（15 个新电路），
`artifacts/20261109_angles_r5/angle_words_r5.npy`（`(751,75)` 签名字）。
脚本：`experiments/dfthcsos/20261109_angles_r5/build_measure_r5.py`。

## 2. 500 步短训探针 + 变体

复用 `20261106_train_r5/fit_probe.py`（连续 packed-pair L-BFGS）与种子
`seed_5x135x70_cluster_chol.npz`，500 步、chunk 100：

| iter | e2 (mHa) | 当段下降 |
|---:|---:|---:|
| 0 | 793.56 | — |
| 100 | 411.29 | −382.3 |
| 200 | 314.32 | −97.0 |
| 300 | 248.56 | −65.8 |
| 400 | 208.05 | −40.5 |
| 500 | 182.00 | −26.0 |

与 `20261109_joint_budget` 的 182.0 mHa 逐位一致（确定性复现）。
距 20 mHa 门还差 **162 mHa**。

变体（扰动重启：同种子 U+0.01 高斯/行归一、W+1% 噪声，rng=7，
`|dU|_F=2.2355`）：起点 2085.93 mHa（扰动把初始误差放大 2.6 倍）→
100 步 420.26 → 200 步 319.87 → 300 步 248.23 → 400 步 207.43 →
500 步 **181.28 mHa**，距门 **161.3 mHa**。
起点差 1292 mHa，终点差仅 0.7 mHa——同一盆地/同一 stall 点，
不是种子运气问题；与 joint_budget“优化器/盆地为主”的判断一致。
按任务“>100mHa 试 1 个变体”的要求，本轮只做这一个变体，不再展开
R4/B131/C83（其 PSD 9.69 mHa 更紧而预算更大，留给有 GPU 时）。

舍入字质量（500 步最优 U/W 经 signed 8-bit 编码，固定树）：
e1=2.310 Ha、e2=461.0 mHa、Lambda=1595.5、E_gap=957.4 Ha——
连续 182 mHa 的 U 经量化后离门差 5–7 个量级（one-body 本征结构未成形），
故新电路的字**不是候选**，只用于成本测量。

证据：`artifacts/20261109_angles_r5/train_r5_500.npz`、
`train_r5_500_perturbed.npz`（500 步最优 U/W，连续探针产物，非候选）、
`seed_r5_perturbed.npz`（变体起点）。

## 3. 切空间 refit（未触发）

触发条件（任务 §3）：新电路 T×Q 确降 >2%。
实测 -0.41%（trials=16 复建同为 -0.41%，和数饱和），**未触发，不执行**。
另：即使触发，新字 e1/e2 在 Ha 量级，`nullspace_refit.py` 所要求的
20 mHa 门附近切空间（uHa 裕度 Newton）无定义——该工具只适用于近门字
（如 b9eced3e 的 ±uHa 回缩），不能把 162 mHa 差距炼掉。
此处无 λeff/score 精确算术数可报告（舍入字 metrics 见 §2；score 按门为 inf）。

## 4. 验证范围声明

- **无官方 78,080-shot PASS。** 本轮无候选（新字 e1/e2 出门 5–7 个量级），
  没有运行任何 78k-shot 验证。
- **成本实测**：新电路 `words_match=True` + kickmix Toffoli 均值
 （shots=2/地址，固定种子 `20261109`；纯成本计量，非 PASS）。
  sim 恰为 static 2 倍，shot 数不影响结论。
- **精确算术**：heuristic `SpinFreeData_V1` 精确值；字 metrics 为官方
  `evaluate_words` 精确数。
- 未提交 Kaggle，未推送，未改官方验证器与共享环境。

## 5. 复现

```bash
uv run --no-project --with jax --with optax --with numpy --with scipy --with h5py \
  python experiments/dfthcsos/20261106_train_r5/fit_probe.py \
  artifacts/20261106_high_yield/train_r5/seed_5x135x70_cluster_chol.npz \
  artifacts/20261109_angles_r5/train_r5_500.npz --iters 500 --chunk 100
.venv/bin/python experiments/dfthcsos/20261109_angles_r5/variant_init.py \
  artifacts/20261106_high_yield/train_r5/seed_5x135x70_cluster_chol.npz \
  artifacts/20261109_angles_r5/seed_r5_perturbed.npz 0.01 7
PYTHONPATH="$PWD/artifacts/20261106_high_yield/lera_data/dfthc_refit:$PYTHONPATH" \
.venv/bin/python experiments/dfthcsos/20261109_angles_r5/build_measure_r5.py \
  artifacts/20261109_angles_r5/train_r5_500.npz \
  artifacts/20261108_public_frontier/dfthcsos_refit/submission.npz \
  artifacts/20261109_angles_r5 --trials 6 --jobs 4 --shots 2
# 仅在有候选时才手动运行（本轮无）：
# .venv/bin/python scripts/manual_verify.py dfthcsos <family_dir> --salt <local-salt>
```
