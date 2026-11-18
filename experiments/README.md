# 实验记录

> 2026-11-13：三条自研线（invsqrt、DQI、dfthcsos）已停止推进（当时 main 只保留
> `frontier/20261112_rescan/` 一份公开前沿来源记录，该目录已在 2026-11-17 清理中删除）；
> 概况、放弃原因和删除清单见 [docs/abandoned-research.md](../docs/abandoned-research.md)。
> 各研究分支只保留入口 README、`ABANDONED.md`、系统性复盘和可复用载体。
>
> 2026-11-16：换用公开 28.059 组合（ref 58392219，**28.05896**）后，又删除了
> `artifacts/` 下已关闭研究的候选件、`.worktree/dfthcsos` 的训练权重快照、全部 18 个
> 历史提交 ZIP（872.5 MB）与临时工作区（124 MB），合计约 **1.10 GB**。
> 详细清单见 [docs/abandoned-research.md §7](../docs/abandoned-research.md)。
>
> **2026-11-17：** 再次清理。三条腿都已由实测 + 官方 cost 公式算术判定关闭，
> 删除 `frontier/20261116_push/{invsqrt,dqi,chem}/` 的文档/脚本/构建产物、
> `frontier/20261112_rescan/`、`frontier/20261115_upgrade/`，以及 `artifacts/` 下
> **2.86 GB** 的 Kaggle 内核输出下载镜像（`20261116_intel/{outputs,outputs2,unz,ds}`）
> 与 DQI v15 源码（59 MB）。**合计回收 2.96 GB（4.1 GB → 1.1 GB）。**
> 删除前锚点 `8155189`，受跟踪文件用 `git checkout 8155189 -- <path>` 取回。
> 逐条归档、放弃原因与一次误删说明见
> [experiments/ARCHIVE_closed_lines.md](ARCHIVE_closed_lines.md)
> 和 [docs/abandoned-research.md §8](../docs/abandoned-research.md)。
> 当前只保留：`frontier/20261116_push/{intel,pipeline}/`（侦察 + 提交管线）、
> `frontier/20261116_push/dqi/{RESULT_WIDTH_BUDGET.md,width_budget.py}`、
> 公开源清单 `references/`、提交回执 `submissions/`、官方数据 `data/competition/`。
>
> **2026-11-18：** frontier push 收尾。14 条轴全部实测关闭（Toffoli 已 100% 对账，
> 剩余空间 <1.3%），删除整个 `frontier/`（20261116/17/18 三轮，34 MB）、`artifacts/`
> 全部产物（646 MB，含 479 MB 未提交的 `dqi_cond.kmb`）、`.worktree/` 三个 checkout、
> `.venv` + `.uv-cache`（116 MB）、四份本轮备忘与会话文档、研究用 `scripts/kgpu.py`。
> **合计回收 797 MB。** 删除前锚点 `b754ef5`，受跟踪文件可 `git checkout b754ef5 -- <path>` 取回。
> 研究概况、14 条轴的决定性数字与恢复口径见
> [docs/abandoned-research.md §9](../docs/abandoned-research.md)；逐条清单见
> [ARCHIVE_closed_lines.md §7](ARCHIVE_closed_lines.md)。
> 当前只保留：本文、逐轮归档、`scripts/{gm,inspect_circuit,manual_verify,package_submission}.py`、
> 公开源清单 `references/`、提交回执 `submissions/`、官方数据 `data/competition/`。

main 保留公开前沿来源和 submission 回执。若未来恢复研究，新增 invsqrt、化学、DQI
实验分别写入 `.worktree/invsqrt`、`.worktree/dfthcsos`、`.worktree/dqi` 的对应
`codex/` 分支；三个 worktree 已删除，但分支与提交保留，可用
`git worktree add .worktree/dqi codex/dqi-research` 重建。提交包与回执由 main 管理。

这里按 `invsqrt`、`dqi`、`dfthcsos` 分别保存研究笔记、小型探索脚本和结果。先完成实验，再决定是否值得抽成公共代码；不为一次性探索搭建测试或门控体系。

每次研究只需留下：

- **假设**：想降低什么成本，为什么这个改动可能有效。
- **改动**：代码、参数、输入和参考版本。
- **观察**：资源数字、误差、运行耗时或失败原因。
- **证据**：候选电路与手动运行的日志位置，必要时加 hash、salt 和工具版本。
- **下一步**：保留、放弃，或继续哪个方向。

实验目录使用 `experiments/<task>/YYYYMMDD_short-name/`，例如 `experiments/dqi/20261030_public_audit/`。小型源码和研究记录放在对应目录中，同一次跨任务研究在三个子任务下分别记录，避免额外的重复汇总目录和总表。大电路、权重、运行日志放到 `artifacts/<实验名>/<task>/`，最终 ZIP 放到 `submissions/`。不要将 Kaggle token 写入源码、笔记或结果。

记录日期使用北京时间；资源成本、改善倍数和验证结果未测则明确写明。引用结果时附上对应产物路径、工具版本、salt 或 seed，必要时加 hash 和运行耗时。

所有检查都手动发起。记录应如实区分“生成完成”“静态统计”“本地 verifier PASS”和“线上提交成绩”。只运行一项或缩小规模时，写明范围；不将快速探索结果标成完整验证通过。

总榜 GM 与子任务成本使用不同口径，作者自报 LB 也单独注明。比较不同方案时尽量保持官方 verifier、依赖、参数和 salt 一致；近似 DQI 的最终候选可手动增加不同 salt 的测量。
