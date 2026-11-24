# 研究约定

本仓库用于 Kaggle Google Quantum AI – Verifiable Quantum Circuit Compilation 比赛。优先推进算法、量子电路和资源成本研究。

- 不创建测试文件、测试目录、CI、提交钩子或自动门控。需要检查时手动执行命令，并记录实际结果。
- 官方验证器是评估研究结果的工具。只在明确需要验证候选方案时手动运行；不要在导入、打包或一般编辑时自动触发全量验证。
- 尽量保持脚本简单，避免为实验建立复杂框架或通用基础设施。
- 将实验假设、关键改动、资源成本及验证范围记在 `experiments/<task>/<实验名>/` 的研究记录中。区分局部检查、完整官方本地验证和 Kaggle 排行榜成绩，不把未执行的验证写成通过。
- 按 `invsqrt`、`dqi`、`dfthcsos` 分别开展实验。候选电路、日志和大型中间产物放在 `artifacts/`，最终压缩包放在 `submissions/`。
- 官方原始数据保留在 `data/competition/`，不要修改其中的验证器；实验性修改另存至实验目录并说明差异。
- 引用公开方法时记录来源、版本和生成方法，保留可复现电路的生成代码。
- 凭据、Kaggle token、下载签名链接及大体积数据不得进入 Git。
- 不自动提交 Kaggle、发布数据、推送代码或创建远程仓库。

## 分支与工作区职责

- 主仓库根目录 `main`：公开优秀方案的来源、固定版本、比较与组合治理，以及 submission 打包和提交回执。
- `.worktree/invsqrt/` / `codex/invsqrt-research`：invsqrt 算法、电路和资源研究。
- `.worktree/dfthcsos/` / `codex/dfthcsos-research`：化学 / dfthcsos 研究。
- `.worktree/dqi/` / `codex/dqi-research`：DQI 研究。
- 新实验、候选和验证证据只写入对应研究工作区。共同历史保留作参考；采用研究成果时，在 main 记录选定产物、来源及验证范围，不整支混入研究过程。
- 官方数据、原始公开包与已有环境可从 main 只读复用；研究输出写在各自工作区的 `artifacts/`，最终提交包和回执留在 main 的 `submissions/`。需要变更依赖时使用独立环境，避免修改其他工作区共用的环境。

## 工作区检出与停更记录

2026-11-24 整理：三个研究工作区使用 sparse-checkout，只展开各自的研究目录。

| 工作区 | 展开路径 |
| --- | --- |
| `.worktree/invsqrt/` | `experiments/invsqrt/` |
| `.worktree/dqi/` | `experiments/dqi/` |
| `.worktree/dfthcsos/` | `experiments/dfthcsos/` |

根目录的 `README.md`、`AGENTS.md`、`pyproject.toml`、`uv.lock` 等共享文件仍保留；`data/`、`docs/`、`scripts/`、`references/`、`submissions/`、`artifacts/` 默认不展开。sparse-checkout 只改变工作区可见文件，分支 tip 仍是完整提交快照，不是把分支内容删掉了。

```bash
# 查看当前展开范围
git -C .worktree/invsqrt sparse-checkout list

# 需要共享目录时临时加入
git -C .worktree/dqi sparse-checkout add scripts

# 恢复完整工作区
git -C .worktree/invsqrt sparse-checkout disable
```

三条自研线目前处于停止状态，恢复研究前先确认方向、预算和验证范围。停更经过：

- 2026-11-13 15:32，三个分支各提交一次 `cleanup: stop ... research`，主动停止并清理已关闭实验。
- 11-13 至 11-19，main 转向公开方案打包，成绩从 28.18 推进到 28.23、33.14、33.17。
- 11-19 晚 main 短暂重开三个 worktree；11-20 16:35 再次全部停止（`d552dce`、`9f78308`），结论写入 `docs/abandoned-research.md`，这一轮没有产生新的分支提交。
- 11-20 停止时删除了 worktree 里的研究文件但未提交，三个工作区只剩相同的共享骨架，因此看起来与 main 相同；2026-11-24 已恢复这些文件并用 sparse-checkout 固化。
- 本地三个分支在 2026-11-11 之后没有 push，`origin` 仍停在 11-11；按约定不自动 push。
- DQI 的 `experiments/dqi/hw31/` 是停止时保留的可复用代码，此前为 untracked，2026-11-24 已提交到 `codex/dqi-research`（`6721206`）。

## 环境

使用 Python 3.12 与 `uv`。依赖由 `pyproject.toml` 和 `uv.lock` 管理；环境初始化使用 `uv sync`。
macOS 使用 PyPI 的原生 `kickmix`，不要导入比赛数据包内为 Kaggle Linux 镜像编译的 `kickmix.so`。
