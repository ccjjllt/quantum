# 2026-11-11：三验证件三件套提交（~25.303，Maoxin 内核通道）

用户明确批准后提交。三件均为本地官方验证 PASS。

## 提交
- 本账号 `ccjjllt` 提交 **58228252**（`2026-11-11T06:35:50Z` / 北京时间 14:35:50），
  `submission.zip` 28,037,130 bytes，MCP `create_code_competition_submission`
 （kernel `maoxin123/lb-25-303-combined-invsqrt-refit-chem` v6）返回成功。
- 通道说明：直传文件（CLI `competitions submit`）两次 400（包 100% 传完、
  建提交被拒，线上无落袋）；改走 code 提交（58222873 同款，无需上传）一次成功。
- 线上分数待回填（COMPLETE 后查）。

## 三件（全部本地验证）
- invsqrt `a15b0d73`：全量 200,540,928 shots **PASS 93925.34907144618**（102s），
  vs gengsr −612.24（`codex/invsqrt-research:20261111_a15b0d73`）。
- DQI `9fcda0c1`：102,400 shots **PASS 374685006335.94**（0/0；72-salt 15/72，R 关闭）。
- chem Maoxin303：main 独立复核 **PASS 298720881.30016786**（78080 shots，
  sha `a9385b97…`；Lera 回退，P0 再退一级）。

## 预期
本地 GM ≈25.303（Maoxin 笔记本自报 25.30339；Ozer296 包 25.29661 已线上兑现 58222873）。
