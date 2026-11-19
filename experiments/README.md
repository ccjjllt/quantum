# 实验记录约定

三条自研线（`invsqrt`、`dqi`、`dfthcsos`）均已停止，`.worktree/` 下的本地研究工作区已清理，分支 `codex/{invsqrt,dqi,dfthcsos}-research` 保留在 Git 中。停研概况、已否证方向与清理清单见 [docs/abandoned-research.md](../docs/abandoned-research.md)。

若未来重开某条研究线，需在对应分支的 `experiments/<task>/YYYYMMDD_short-name/` 中记录：

1. **假设与改动**：要降哪项官方指标、代码/参数/固定上游版本。
2. **观察与验证范围**：严格区分静态计数、小尺度检查、默认 salt 官方 verifier 全量 PASS 与线上提交成绩；未跑过的验证不写成通过。
3. **存储约束**：大电路、权重与日志放 `artifacts/`（不入 Git），最终提交包放 `submissions/`（ZIP 不入 Git），禁止将 Kaggle token 或签名 URL 写入仓库。
