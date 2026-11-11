# 2026-11-11：公开最高分 Ozer 25.296 组合提交

用户明确批准后提交一次。采用公开最高分方案原样提交。

## 提交
- 本账号 `ccjjllt` 提交 **58222873**（`2026-11-11T03:03:25Z` / 北京时间 11:03:25），
  `submitted_by ccjjllt`，`submission.zip` 28,089,106 bytes。
- 方式：MCP `create_code_competition_submission`（kernel `ozertuu/25-296-quantum-ai-starter-notebook` v11，
  file `submission.zip`）。提交前 MCP 身份已换回 ccjjllt（配额 GPU 已用 88188s 验证）。
- 未持续监控分数；作者自报 Public 25.29661，非本账号实时成绩。
- 线上回填（2026-11-11）：**COMPLETE，public_score 25.29661**，与作者自报完全一致。

## 包内容（原样，未修改）
- 外层 `submission.zip` SHA-256 `0309dde866dd6749…`（见 `artifacts/20261111_ozer296/README.md`）。
- `invsqrt.kmb` `a15b0d73…`（新 family，静态 1381，作者称 93925.35，未本地验证）。
- `dqi.kmb` `9fcda0c1…`（892Q，静态 395584；本地全量 PASS 374685006335.94，作者 371.44e9 不复现）。
- `dfthcsos/submission.npz` `ff5e05ee…` + 15 loaders（refit 版，本地全量 PASS 298961236.04）。

## 验证范围
- chem/DQI 本地全量 PASS（见 `artifacts/20261111_ozer296/README.md` §4）；
  invsqrt 200M 全量未跑。GM 本地拼 25.388（含作者 invsqrt 数）。
- 比较基线仍为 gengsr 25.2268（`references/public-baseline.json`），不更新；
  本包 chem（298961236）弱于已验证 Lera（298942334），后续组合候选见 dfthcsos 线。
