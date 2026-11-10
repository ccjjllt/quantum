# 新字形状 J/装配扫描（P1）+ R4 形状重评估（2026-11-10）— closed

分支 `codex/dfthcsos-research`，工作区 `.worktree/dfthcsos/`。
本轮不重复 refit/KKT/折点/联合/longloss/ubasis/angles 工作（见 `CLOSED_RESEARCH.md`
11-09 节：固定 (8,143,44) 已死、训练盆地 85.31 渐近 63.3）；是零训练的结构扫描。
P0（`20261110_p0_gauge/`）已 PASS（299,497,670.48，T=14958/Q=427）为当前最优，
本轮所有比较以 `b9eced3e`（T/Q=14966/427，T×Q=6390482）为分母、与 P0 并列记录。

结论先行（两项全 closed，无候选，无验证器运行）：

1. **J/装配扫描：T×Q 最小者在 J=5/brot=6（tensor，−18.61%），成本侧触发 >2%，
   但字表门侧失败（e1=9640 mHa、e2=2325 mHa），conjunction 不成立 → closed。**
   brot=8 下 J=5 仍最优（−0.39%，复现 angles_r5 的 −0.41%），J=4/6 均为正收益耗散。
2. **R4 翻转：signed 规范下 U-符号翻转空间为空（150 行翻转 → 0 字变化，
   精确算术证明）；unsigned 下翻转改变字表但 metrics 有 ~50 uHa 量化抖动，
   且 R4 无过门字表（最优连续 180.11 mHa）→ closed。**

## 1. J/装配扫描（固定 R5/B135/C70 字表，零训练）

字表：`seed_5x135x70_cluster_chol.npz` 的 U/W（`train_r5_500.npz` 已按清理记录删除，
见 CLOSED_RESEARCH.md；用现存种子，同字表跨组对比公平），signed 规范按 brot
重编码（无训练，纯量化）。树沿用 `b9eced3e` log-depth 树。方法 = `build_measure_r5.py`
思路（快照 165d6e7）：朴素 QROM 对照 + `tensorqrom.build_family`（trials=6，jobs=4，
与 angles_r5 同参数）+ kickmix `recover_words_from_circuits`（shots=2，seed=20261110）
成本计量 + `SpinFreeData_V1` 精确 heuristic。12 组全部 `words_match=True`，
sim 恒为 static 的 2 倍（无条件修正门触发）。

heuristic 精确值（只与 (R,B,C,N,chi,beta) 有关，与字/装配无关）：
brot=8：outer 317 + inner 4060 + Givens 2250 = 6627；
brot=6：outer 317 + inner 4060 + Givens 1650 = 6027（−600T 全来自 Givens）。
persist 84 / temp_max 303（inner）两种宽度一致；Q 一律被 heuristic temp 303 钉死
（angles_temp 实测恒为 51，见下）。

tensor 共享 planner（决策用表，加粗为每宽度最优）：

| J | brot | K | angles 实测 | heuristic | T | Q (=84+J·brot+303) | T×Q | vs 基线 |
|---|---|---:|---:|---:|---:|---:|---:|
| 4 | 6 | 19 | 6948 | 6027 | 12975 | 411 | 5332725 | −16.55% |
| **5** | **6** | **15** | **6446** | **6027** | **12473** | **417** | **5201241** | **−18.61%** |
| 6 | 6 | 13 | 6392 | 6027 | 12419 | 423 | 5253237 | −17.80% |
| 4 | 8 | 19 | 8814 | 6627 | 15441 | 419 | 6469779 | +1.24% |
| **5** | **8** | **15** | **8280** | **6627** | **14907** | **427** | **6365289** | **−0.39%** |
| 6 | 8 | 13 | 8418 | 6627 | 15045 | 435 | 6544575 | +2.41% |

- J=5 在两种宽度下都是 T×Q 最小（J=6 angles 多省 ~50T 但 Q+6 吃掉收益；
  J=4 共享不足 angles 贵 400–500T）。**J 扫描不产生新方向：当前 J=5 已是最优装配。**
- J=5/brot=8 得 8280（−24 vs 8304），与 angles_r5 在 500 步探针字上的 8278（−26）
  差 2T——不同字表同方法复现，planner 侧结论稳定。
- 朴素 QROM 对照（排除用）：brot=6 时 +68∼+122%，brot=8 时 +78∼+130%；
  brot=6/8 在 J=5/6 下 static 完全相同（11235/9737），地址树主导，字宽不敏感。
- angles_temp 恒为 51（qubits_max − sel − J·brot：85−10−24、91−10−30、…、109−10−48
  全得 51）：planner workspace 随装配线性伸缩，从不触及 303 上界；Q 公式退化为
  `Q = 387 + J·brot`（brot=8 时 84+303=387；brot=6 同）。
- brot=6 的 −16∼−19% 全由三项叠加：Givens −600T、angles −1800∼−2400T（6-bit 字便宜）、
  Q −10∼−16（J·brot 常驻减小）。代价是字精度（见 §3）。

## 2. R4 重评估：heuristic + 等价翻转静态分析

heuristic 精确值（R4/B131/C83，`SpinFreeData_V1`）：
brot=8：outer 311 + inner 3881 + Givens 2250 = **6442**（−220T vs 当前 6662，即
compact_multikink 保守 −1.70% 的来源）；brot=6：311 + 3881 + 1650 = **5842**（−820T）。
persist 83 / temp 303。Q_cons=426（83 + J·brot + 303 上界内）。

翻转机制演示（R5 种子 U，150/675 two-body 行变号 → 重编码 → 官方 `evaluate_words`
精确数；代码路径与形状无关，P0 已在 (8,143,44) 实表证明逐位不变）：

- **signed 规范：150 行翻转 → 字表 0 项变化，metrics 逐位一致。**
  signed 编码按构造是行符号不变的（pivot 符号被除掉），故对 `tensorqrom`
  signed 管线而言，U-符号翻转搜索空间是**空集**—— provably 无降 T 空间，
  不是"没测到"，是"不存在"。P0 的 −8T 来自 unsigned 规范表 + gengsr 自带 loader
  复用（P0 §3：tensorqrom 在 unsigned 表上直接断言失败），两条管线不要混淆。
- unsigned 规范对照：同批翻转改变 11,250 字项（= 150×75，恰为翻转行全列），
  Λ/E_gap/λeff 逐位一致，但 error_2 有 48.6 uHa 抖动（20.8896 → 20.9382 mHa）：
  naive 翻转+重编码经 8-bit 舍入不对称，不是精确等价（P0 的表是精确构造的）。
  即使用 unsigned+gengsr 式 loader 路线，R4 也需先有**过门**字表——而 R4
  最优连续值是 180.11 mHa（ubasis R4-eigrr 500 步，`20261109_ubasis_retrain`），
  按 R5 类比（连续 182 → 量化 461 mHa）量化后只会更差；翻转保持 metrics
  （精确等价时），过不了门的表翻转后依然过不了门。
- 附带观测（不行动）：同一种子 unsigned 编码 e2=20.89 mHa 而 signed 编码
  e2=924 mHa——Lera 系精细抵消住在 unsigned 舍入里，naive signed 重编码破坏它
  （与 P0 §3 的 signed 重编码失败 e2=318.5 mHa 同机理）。只记录，不展开：
  unsigned 管线无 tensorqrom 可用，需 gengsr 式 loader campaign，前提仍是过门表。

## 3. 门判定（conjunction，两半如实记录）

任务触发条件：某组 T×Q 确降 >2% **且** 字表满足 20 mHa → 才进入 refit/验证讨论。

| 字表 | error_1 | error_2 | 门 |
|---|---|---|---|
| 本扫描 brot=8 signed 字（J 全组共用） | 2.310 Ha（2310 mHa） | 0.924 Ha（924 mHa） | ✗（差 ~2 量级） |
| 本扫描 brot=6 signed 字（J 全组共用） | 9.640 Ha（9640 mHa） | 2.326 Ha（2326 mHa） | ✗（差 ~2–3 量级） |
| 现有最优 R5 探针（500 步，连续值，非本轮字） | — | 182.0 mHa（连续）→ 量化 461 mHa | ✗（差 23×，见 angles_r5 §2） |

成本侧：brot=6 三组确降 >2%（−16.55%/−18.61%/−17.80%）✓ 触发；
门侧：全部失败 ✗。**conjunction 不成立 → 不进入 refit/验证讨论，closed。**
另：brot=6 的省钱是"便宜地加载一张废字"——切空间 refit 要求门附近起点
（joint_budget：门内裕度仅值 0.05 分），Ha 级差距无定义，与 angles_r5 §3 同理。

## 4. 交付物

- `experiments/dfthcsos/20261110_shapes/scan_j_brot.py`（本轮扫描脚本）
- `experiments/dfthcsos/20261110_shapes/r4_flip_static.py`（R4 heuristic + 翻转机制静态分析）
- `artifacts/20261110_shapes/j_brot_scan.json`（6 组 ×（ref+tensor）逐电路 static/qubit、
  heuristic 明细、字 metrics、T/Q/T×Q）
- `artifacts/20261110_shapes/r4_flip_static.json`（R4 heuristic brot6/8、翻转演示精确数）
- `artifacts/20261110_shapes/scan.log`（逐组实测行 + EXIT=0）

## 验证范围声明

- **无官方 78,080-shot 运行，无 `verify.py`/`manual_verify.py` 调用，无训练，
  无新候选 NPZ。**本轮新增计算只有：`SpinFreeData_V1` 精确 heuristic（纯算术）、
  signed/unsigned 字编码 + 官方 `evaluate_words` 精确 metrics（无 shots）、
  kickmix `recover_words_from_circuits`（shots=2/地址，固定种子；纯成本计量，
  非 PASS；12 组 words_match=True，sim 恒为 static 2 倍）。
- R4 翻转演示中 `evaluate_words` 的 e1/e2/Λ/E_gap/λeff 为精确数；"2^600 空间"、
  "P0 量级 ~8T"为机制外推，非实测。
- 现有探针值引用：R5 500 步 182.0 mHa（`20261109_angles_r5` §2）、R4-eigrr 500 步
  180.11 mHa（`20261109_ubasis_retrain`）、R5/R4 保守数（`compact_costs.json`）。
- 未提交 Kaggle，未推送，未改官方验证器/数据与共享环境。
