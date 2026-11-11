# 2026-11-11：化学基线更新为 Maoxin303（main 独立验证通过）

## 决定
化学基线候选从 Lera 11.2x（298942333.64）更新为 **Maoxin303（298720881.30）**，
P0（299497670.48）再退一级，Lera 为回退。

## Main 独立验证（本记录依据，未改验证器/数据）
- `uv run --project . scripts/manual_verify.py dfthcsos .worktree/dfthcsos/artifacts/20261111_maoxin303 --salt maoxin303-main-20261111`
- 结果：**PASS**，78080 shots，score **298720881.30016786**，
  `submission_sha256 a9385b97…`，T=14914 / Q=427 / λeff=46.907638344332305，
  与工作区验证（`20261111_lera_deep/README.md` §4.2，同分数同 SHA）逐数一致。
- 来源：`maoxin123/lb-25-303-combined-invsqrt-refit-chem` v6（ozertuu 表 + 自研 k1–k3；
  字表与 Lera 逐字节一致，W/H2 微调；rank-86 重综合无公开代码，不复现）。

## 组合现状（已验证件）
- invsqrt：gengsr `26ebf39d` 94537.59（已验证）；`a15b0d73`（称 93925.35）验证中，
  出结果前不采用。
- DQI：`e9f54be3` 系 374.685e9 量级（72-salt 实测均值 375045278747.2；`9fcda0c1`
  本地 374685006335.94 一致）。
- 化学：Maoxin303 298720881.30（本记录）。
- 三项全齐后可组新三件套（预期本地 GM ≈25.303，即 Maoxin 笔记本自报口径）；
  组包与提交需用户另行批准。

## 依据
- 工作区解剖：`.worktree/dfthcsos/experiments/dfthcsos/20261111_lera_deep/README.md`
- 放弃记录：`.worktree/dfthcsos/experiments/dfthcsos/ABANDONED.md`
