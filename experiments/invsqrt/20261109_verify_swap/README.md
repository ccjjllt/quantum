# [7506:8860] 邻位对易重排序候选（零差分 PASS）

日期：2026-11-09；分支 `codex/invsqrt-research`；工作区 `.worktree/invsqrt/`。
基线：Public Frontier `7c10edba`（62Q / 53,686 ops / 1403 Toffoli-like，报告成本 95430.78）。

## 改动
- 交换 `ops[7520]=CX q61 q14` 与 `ops[7521]=CX q19 q16`（皆 depth 0、无 `if`、线集 `{q61,q14}∩{q19,q16}=∅`，对易）。
- 静态统计不变：53686 ops / 1403 Toffoli-like / num_t_like 1。

## 验证
- 官方验证器完整运行 1 次：**PASS**（`verified_shots 200540928`）。
  `score 95430.941580313`（基线 95430.78，差 +0.16 salt/硬币流噪声带），
  `toffoli_equivalent 1539.2087`，`worst_error_over_tolerance 0.9993@x161`，
  `circuit_sha256 bd960f19…`（新哈希，Private LB 独立抽样）。
- 候选：`artifacts/20261109_verify_swap/candidate_swap_7520_7521.kmb`。
- 复现：`experiments/invsqrt/20261109_xreg_resynth/scripts/build_candidates.py` 方法
  （`km.Circuit.from_file(StringIO(hdr+ops), format="kmx")`），交换两行后写 kmb；
  验证：`.venv/bin/python data/competition/verifiers/invsqrt/verify_submission_invsqrt.py <kmb>`。

## 结论
零差分对称候选，证明新窗重排序机械链条有效；Δscore 实质为 0，无正收益。
未打包/提交/推送；基线未重验（eps 沿用实测值）。
