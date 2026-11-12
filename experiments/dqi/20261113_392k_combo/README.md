# DQI `maoxin123/qcc-dqi-392k-toffoli-decoder`：16-salt 官方统计 + product retention + 组合 GM

日期：2026-11-13。工作区 `.worktree/dqi`（`codex/dqi-research`）。未提交 Kaggle、未 push。

## 结论先行

| 问题 | 答案 |
|---|---|
| 392k 是否真的更好 | **是，且是零风险的严格支配**：每一个 draw 上都比 `eae396ba` 便宜 0.5261% |
| 失败率是否更高 | **不。完全相同**：8 个 paired seed 上错误模式逐个一致；16-salt λ 0.4375 vs eae 52-draw λ 0.442 |
| retention 能否再省 | **不能**。392k 的 52 个空闲 ancilla 全被占用，最多省 2 T（需 880 T 才打平 +1 qubit） |
| 组合 GM | zero-failure **25.44954**；expected **25.4329**（eae expected 25.3882） |
| 是否建议提交 | **不值得单独提交**：+0.0447 GM，落在事前判据的 0.02–0.05「不值得」区间 |

一句话：392k 是把 eae 的 T 直接降 0.526%、错误行为一字不改的**免费替换**；
收益真实但太小，不足以单独为它打一个包。

## 1. 文件与来源

- 主仓库 `artifacts/20261112_frontier_rescan/dqi392k/dqi.kmb`（已存在，未重新下载）。
- SHA-256 `4c81b7263c0b4856068a691295d945ae627aa6af4e62e45f2c40411b6d01e5d9`，
  与公开 `circuit_sha256` 逐字节一致。
- Q=892，`max_toffoli_count` 392,346，`num_bits` 101,418，`num_ops` 57,141,458。

## 2. 官方 verifier 多 salt 统计（主要证据）

官方 `data/competition/verifiers/dqi/verify_submission_dqi.py` 原样导入，未改一行。
102,400 shots、`--max-workers 4`、`log2_delta=-128`、m=4095/n=70/b=12/r=2016。
脚本 `run_salts.py`；每次 ~47 s。

16 个不同 salt 全部 **PASS**：

| salt | ve | pe | R | cost |
|---|---:|---:|---:|---:|
| frontier-20261112 | 1 | 0 | 1.196731499 | 373,276,386,859.62 |
| s2 | 0 | 0 | 1.191260465 | 371,569,622,175.35 |
| s3 | 0 | 0 | 1.191260465 | 371,569,742,979.06 |
| s4 | 1 | 0 | 1.196731499 | 373,276,140,711.33 |
| s5 | 1 | 1 | 1.201388060 | 374,728,703,385.59 |
| s6 | 0 | 0 | 1.191260465 | 371,569,633,171.81 |
| s7 | 0 | 0 | 1.191260465 | 371,569,926,207.12 |
| s8 | 0 | 0 | 1.191260465 | 371,570,089,006.57 |
| s9 | 1 | 0 | 1.196731499 | 373,276,301,654.80 |
| s10 | 0 | 0 | 1.191260465 | 371,569,733,991.21 |
| s11 | 0 | 0 | 1.191260465 | 371,569,695,040.78 |
| s12 | 0 | 0 | 1.191260465 | 371,569,615,742.23 |
| s13 | 0 | 0 | 1.191260465 | 371,569,795,943.49 |
| s14 | 0 | 1 | 1.196731499 | 373,276,432,144.73 |
| s15 | 0 | 1 | 1.196731499 | 373,276,160,768.82 |
| s16 | 0 | 0 | 1.191260465 | 371,569,526,372.85 |

- 公开 `salt=frontier-20261112` 结果**逐位复现**（373,276,386,859.6189，1 value error，R=1.1967315）。
- 合计 **7 errors / 1,638,400 shots**（4 value + 3 phase），p = 4.272e-6/shot，
  95% CP CI 1.718e-6 … 8.803e-6。
- λ = **0.4375** errors per 102,400-shot draw；**P(0 失败) = 0.646**。
- 实测 k 直方图 {0:10, 1:5, 2:1}，与 Poisson(0.4375) 预期 {10.3, 4.5, 1.0} 吻合。
- T 的 salt 均值 392,016.117（公开报 392,016.265），全 salt 极差 < 0.7 T：
  T 随 draw 只微动（条件化 CCX 是否执行），R 的变化才是 cost 的主项。

### 2.1 与 eae 的 paired 对照（关键）

`eae396ba` 已有的 52-seed 记录（`artifacts/20261112_dqi96/results.jsonl`）
给出 52 draws 上 {0:34, 1:13, 2:5}，λ = 23/52 = **0.442**，与 392k 的 0.4375 统计上无差别。

再用**同样的 `--seed`** 跑 392k 的 8 个 draw（`paired_seeds/`），与 eae 同 seed 逐一对照：

| seed | eae (ve,pe) | 392k (ve,pe) | cost 比 |
|---:|---|---|---:|
| 4 | (0,1) | (0,1) | 0.994739 |
| 5 | (1,0) | (1,0) | 0.994739 |
| 8 | (1,0) | (1,0) | 0.994739 |
| 11 | (2,0) | (2,0) | 0.994740 |
| 17 | (2,0) | (2,0) | 0.994739 |
| 29 | (0,2) | (0,2) | 0.994738 |
| 38 | (0,1) | (0,1) | 0.994739 |
| 40 | (2,0) | (2,0) | 0.994739 |

**8/8 错误模式完全一致，cost 比 0.9947389 ± 3.9e-7。**

这说明失败由共享解码器核心的算法边界触发（eae 与 `cd71c482` 在 52 seeds 上也是
逐 seed 同模式失败），与两个编译版本的 T 结构无关。于是：

> `cost_392k(seed s) / cost_eae(seed s) = 392,016.12 / 394,089.46 = 0.9947389`，
> 对**每一个 draw** 成立，不是平均意义上的成立。

392k 不引入新的失败模式、不放大方差，只是把同一个 R 乘到更小的 T 上。

## 3. Product retention（公开 `retain.py`）

工具：`.worktree/invsqrt/experiments/invsqrt/20261113_retention/retain.py`
（复制入本目录，SHA-256 `f9a477f5…40bfc`，未改）。脚本 `scan_retention.py`。

**方法自检**：同一脚本跑 `eae396ba` 得到 **133 hosted / 无新增 qubit**，
与公开 notebook 声称的 133 个可保留 product 完全一致 → 工具与我的调用正确。

392k 结果（`retention_stats_392k.json`）：

| 变体 | duplicate pairs 可用 | toffolis_saved | Q | cost 变化 | GM 变化 |
|---|---:|---:|---:|---:|---:|
| 仅用现有 ancilla（hops=0） | 3,525 | **0** | 892 | 0 | 0 |
| 现有 ancilla + 最多 8 跳 | 3,525 | **2** | 892 | −0.001% | +0.000% |
| +1 个 host qubit | 3,525 | **138** | 893 | **+0.189%** | −0.063% |
| +2 个 host qubit | 3,525 | **262** | 894 | **+0.382%** | −0.127% |

原因：392k 有 3,525 个重复 product、52 个未注册 ancilla，但这 52 个的
|0⟩ 窗口在 392k 的调度里全部被占用（eae 的同名 52 个 ancilla 则能覆盖 133 对）。
更本质的是数量级：892→893 使 Q² 涨 **0.224%**，需省 **879.5 T** 才打平，
而最好的变体只省 262 T（29.8%）。**retention 在 DQI 上是纯亏**，
这与 invsqrt（Q 小、Q 线性、省 133 T 即 0.0337% 可观）完全不同。

结论：**392k + retention = 392k**，没有任何组合空间。已关闭。

## 4. 组合 GM（invsqrt `9c708f7b` + chem `5d5007a75784` + DQI）

参考 cost（主仓库，已由 sample submission 独立核对）：
invsqrt 2,076,774.2337；DQI 24,439,463,583,672.93；chem 3,355,599,588.3155。
固定件：invsqrt 93,555.2627，chem 297,237,044.9509761。

| 口径 | DQI cost | GM |
|---|---:|---:|
| eae zero-failure | 373,534,939,340.64 | **25.40482651** |
| eae 52-draw 实测均值 | 374,269,174,492.34 | **25.38820271** |
| eae manifest 96-draw expected | 373,856,548,625.22 | 25.39753961 |
| 392k zero-failure | 371,569,738,063.05 | **25.44953532** |
| **392k expected（16-draw 均值 / Poisson）** | **372,300,469,135 / 372,293,481,316** | **25.4329** |

- 392k 的 16-salt 实测均值 372,300,469,134.71，与「eae 52-draw 均值 × 0.9947389」
  这条完全独立的估计 372,300,106,938.42 相差 3.6e5（0.0001%），互证。
- 期望收益：**+0.0447 GM（+0.176%）**，对照 eae 自身 expected 25.38820；
  若对照 eae zero-failure 25.40483 则是 +0.0280 GM（+0.110%）。
- 因为比值是逐 draw 恒定的，**这个收益的方差为 0**：不存在「抽到坏 salt 就亏」的情形，
  392k 在任何 draw 下都赢 eae 0.0447 GM。

## 5. 判定：不值得提交

事前判据是「若只是 +0.02–0.05 GM，明确说不值得提交」。实测 **+0.0447 GM**
（对照 eae expected）落在该区间内 → **不值得为它单独打包、单独提交**。

- 它不是「有风险的赌注」，而是**零风险严格支配**：若将来因为别的原因（化学/invsqrt
  有新件）需要重新组包，应顺手把 DQI 换成 392k，无需重新评估。
- 单独为 +0.0447 GM 走一次提交流程（组 18 件包、上传、回执）不成比例。
- retention 不提供任何额外理由（见 §3）。

## 6. 验证范围（明确区分）

- **完整官方本地验证**：24 次全量 102,400-shot 跑（16 salts + 8 paired seeds），
  合计 2,457,600 shots，全部 PASS；每次均记录 ve/pe/R/cost/T。
- **public salt 复现**：`frontier-20261112` 与公开数字逐位一致
  （373,276,386,859.6189 / 1 ve / R 1.1967315）。
- **未做**：未构建完整 18 件包；未跑 Kaggle 排行榜；未提交、未 push。
- 化学件 `5d5007a75784` 的 `E_gap` 距门限仅 3e-9 的既有风险与本轮无关（未改动它）。

## 7. 复现

```bash
cd .worktree/dqi
# 16-salt 全量（~13 min，4 workers）
uv run python experiments/dqi/20261113_392k_combo/run_salts.py \
  /path/to/dqi392k.kmb artifacts/20261113_392k_combo/salts \
  frontier-20261112 s2 s3 s4 s5 s6 s7 s8 s9 s10 s11 s12 s13 s14 s15 s16
# 统计与 GM
uv run python experiments/dqi/20261113_392k_combo/analyse_salts.py \
  artifacts/20261113_392k_combo/salts
# paired seeds（与 eae 同 seed 对照）
uv run python experiments/dqi/20261113_392k_combo/run_salts.py \
  /path/to/dqi392k.kmb artifacts/20261113_392k_combo/paired_seeds \
  seed:4 seed:5 seed:8 seed:11 seed:17 seed:29 seed:38 seed:40
# retention（先把 .kmb 转 .kmx，约 3 s）
uv run python experiments/dqi/20261113_392k_combo/scan_retention.py dqi392k.kmx --first-new-bit 101418
```

## 8. 产物

- `run_salts.py` / `scan_retention.py` / `analyse_salts.py` / `retain.py`（公开件副本）
- `artifacts/20261113_392k_combo/salts/*.json`：16 个 salt 的原始 verifier 输出
- `artifacts/20261113_392k_combo/paired_seeds/*.json`：8 个 paired seed 的原始输出
- `salt_stats_summary.json`、`analysis.json`、`retention_stats_{392k,eae}.json`
- `salts_sweep.log`、`paired_seeds.log`、`retention_scan.log`
