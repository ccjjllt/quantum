# 20261115 公开前沿升级

> **2026-11-16 结局**：本目录记录的自研升级（27.31 系列）已被公开 **28.059 组合**取代，
> 当前最佳 ref **58392219**，public **28.05896**（rank 91/3114），见
> [stack_28059/REPORT.md](stack_28059/REPORT.md)。三条自研线（invsqrt Q45/T 轴、
> DQI Q888、化学 B/C/Adam/from-scratch）均已实测关闭；本目录的候选件、二进制产物与
> 历史提交 ZIP 已删除，清单见 [docs/abandoned-research.md §7](../../../docs/abandoned-research.md)。
> 当前最佳的组装/复核脚本保留在 [stack_28059/kernels/](stack_28059/kernels/)。

## 当前状态（2026-11-15，历史记录）

- 本账号上一版：ref 58299045，public **27.00209**（46Q invsqrt `321aff83` + 889Q DQI
  `7cbe8ecf` cutoff17 + 4074T chem `6418ec8e`）。
- 2026-11-15 已用新的公开方案提交：ref **58349843**，来源
  `maoxin123/qcc-v27-4033-toffoli-coded-word-chemistry` v2（Apache-2.0）。
  该 notebook 最近一次 Kaggle 运行输出：
  - invsqrt `e46d90c3`，46Q，cost **78,719.529147**
  - DQI `821bf8d1`，889Q，0 errors，cost **360,209,905,486.02**
  - chemistry 4,033 loader + refit，cost **294,991,455.82**
  - 本机/Kaggle 运行 GM **27.30661**；目标 public 约 27.3066–27.3068。
- 公开排行榜当前顶部：29.90871（Entangled Team），公开可复现平台约
  **27.3068–27.3077**（排行榜第 147–166 名附近）。

## 执行记录

- 2026-11-14T16:54Z：创建代码提交 ref **58349843**，直接使用
  `maoxin123/qcc-v27-4033-toffoli-coded-word-chemistry` v2 的 Kaggle 输出。
  该输出 49,292,293 B，18 文件；三项均在 Kaggle 运行内 PASS：
  invsqrt 78,719.529147、DQI 360,209,905,486.02（0 errors）、
  chemistry 294,991,455.82，GM 27.30661。提交时状态 pending，等待排行榜回执。
- 2026-11-15T17:15Z：自建 Kaggle 脚本（`qcc-27-312-frontier-assembler`）组装
  HW-26 invsqrt `1ba197b02771` + DQI `821bf8d1` + maoxin 4,033 chemistry，
  submission.zip SHA-256 `46d53bde0a8b3e6e6aed2693df3a12f540eeb258da75588cbfb99c21f369c933`，
  18 文件，预期 GM **27.31193**（公开件最高拼装为 27.31214，差异仅 chemistry
  npz `e52b7cdd` 的 0.0024%）。
- 公开前沿复扫结论见 `frontier_scan.md`：公开可复现上限 27.31214；
  第 31–146 名（27.40–27.61）使用未公开组件。当前主攻 DQI retention hops
  与 invsqrt 进一步缩宽/旋转压缩。

## 提交回执

- **ref 58349843**（2026-11-14T16:54:52Z）：`maoxin123/qcc-v27-4033-toffoli-coded-word-chemistry` v2
  的 Kaggle 输出，49,292,293 B，18 文件。MCP 回执：**COMPLETE，public_score 27.30661**。
  这是本账号从 27.00209 的第一次升级（+0.30452）。
- **ref 58350759**（2026-11-14T17:34:42Z）：自建 Kaggle 组装包，invsqrt HW-26
  `1ba197b02771` + DQI `821bf8d1` + maoxin 4,033 chemistry，49,292,319 B，
  SHA-256 `46d53bde0a8b3e6e6aed2693df3a12f540eeb258da75588cbfb99c21f369c933`。
  预期 GM **27.31193**（+0.00532）。提交时 pending。
- **HW-26 独立验证**：自建 Kaggle notebook `qcc-hw-26-invsqrt-verify` 使用未修改官方
  invsqrt verifier，200,540,928 shots，**PASS**，score **78,673.56921101942**，
  worst/tol **0.9986660009**，Q=46，circuit SHA-256 与 `1ba197b02771` 一致。
- **DQI retention hops**：自建 Kaggle notebook `qcc-dqi-retention-hops` 重建 cutoff-18
  原始件（383,655 static），用 `retain.py` 在 `max_hops=0/1/2` 下重跑：均只宿主
  241 个乘积，static 383,414，输出逐字节等于 `821bf8d1`，官方 verifier **PASS**
  360,209,905,486.02。结论：retention 已饱和，无新增收益。

- 第一目标：稳定超过 27.31。
- 第二目标：27.5+。
- 第三目标：向 28+ 推进，优先寻找结构性杠杆（Q 下降、DQI 解码器、46Q invsqrt
  进一步缩宽、化学 loader/表重构），而不是只做 0.01% 级 refit。

## 研究约束

- 不在本机跑官方全量 verifier / 大电路模拟；所有候选验证和提交在 Kaggle notebook
  或 Kaggle 代码提交中完成。
- 公开方案保留 Apache-2.0 归属和 NOTICE；记录来源、版本、SHA-256。
- 不自动提交 Kaggle，除非已有明确的候选和验证结果；提交前记录 ref。
- 研究记录写在 `experiments/frontier/20261115_upgrade/`；候选 zip 最终放
  `submissions/`。

## 关键文件/来源

- `experiments/frontier/20261115_upgrade/chem_plan.md`：化学块升级计划（2026-11-15）。
  结论：公开无 < 294.98M 的化学件；唯一 ≥1% GM 的杠杆是 `B=143→129`（GM +1.1%…+1.4%），
  闸门是 8-bit 量化误差；建议实验 `20261115_chem_b129`。
- `submissions/20261113_27_078/README.md`：上一版 27.00209 回执。
- `docs/research-map.md`：比赛契约、历史研究和计分口径。
- `.worktree/dqi/experiments/dqi/ABANDONED.md`：DQI 已关闭方向（cutoff/retention/
  decoder family 的下界）。
- `.worktree/invsqrt/experiments/invsqrt/ABANDONED.md`：invsqrt 62Q 时代结论。
- `.worktree/dfthcsos/experiments/dfthcsos/ABANDONED.md`：化学 loader/训练历史。
- `references/frontier-20261112/`：27.078 公开源清单。
- Kaggle 关键来源：
  - `maoxin123/qcc-v27-4033-toffoli-coded-word-chemistry` v2
  - `asteriospanoras/qcc-27-307-frontier-finer-chemistry-refit` v4
  - `manwithacat/vqcc-hedge-wizardry` v27（HW-26 等小 tweak）
  - `manwithacat/vqcc-apache-public-circuits` v125（497 个公开电路）
  - `areebbb/qai-fewer-toffolis-same-qubits-lb-27-29708` v8（DQI 821bf8d1）
  - `syed3000/vqcc-own-circuit-portfolio` v12（46Q invsqrt builder）
  - `ahoirg/qcc-submit-verify-and-package` v25（64-row invsqrt）
