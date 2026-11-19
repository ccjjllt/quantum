# Quantum Circuit Compilation：公开前沿治理与提交记录

本仓库用于 [Google Quantum AI — Verifiable Quantum Circuit Compilation](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation)。`main` 分支负责公开方案筛选、独立官方验证、打包与提交回执治理。

## 当前状态（2026-11-19）

| 职责 | 分支 / 目录 | 当前状态 |
|---|---|---|
| 公开方案治理与提交 | `main`（仓库根目录） | 最佳 COMPLETE **`28.23162`**（ref `58522779`，rank **183 / 3,355**，本地 GM `28.231630`） |
| invsqrt | `codex/invsqrt-research`（已停） | 44Q `d0227f3c` 局部优化、43Q 重写/按需标志、`Z_POW` 与查表融合均 no-go（[详情](docs/abandoned-research.md)） |
| DQI | `codex/dqi-research`（已停） | 890Q 局部/rewrite/sweep/掩码插值、2 数组/x-adic/BM/Gao/WB 均 no-go（[详情](docs/abandoned-research.md)） |
| 化学 / dfthcsos | `codex/dfthcsos-research`（已停） | 形状/重训/BLISS-THC/`Lambda` 重拟合与列规范、loader H-A/B/C 均 no-go（[详情](docs/abandoned-research.md)） |

- **现役最佳三件套（`58522779`）**：invsqrt `d0227f3c`（44Q，74,405.672，200,540,928 shots PASS）+ DQI `15a4b740`（890Q，345,256,821,433.98，mean T 365,894.20，102,400 shots 0/0 PASS）+ 化学 `4d63be3d`（427Q，T=14,706，294,642,170.57，78,080 shots PASS）。
- **清理说明**：三条自研线已停止，已关闭的实验文档、脚本、`.worktree/`、旧候选 `artifacts/` 与本地环境缓存均已清理以释放磁盘空间（详见 [abandoned-research.md](docs/abandoned-research.md)）。

## 近期与关键提交记录

全部 25 份历史回执保留在 `submissions/*/README.md`；下表列近期关键节点（线上成绩来自 Kaggle 回执，与作者自报和本地 GM 分别口径）：

| 日期（UTC） | 方案摘要 | 提交 ID | Kaggle Public Score |
|---|---|---:|---|
| 2026-11-18 | [公开 SOTA `15a4b740` DQI + `d0227f3c` + `4d63be3d`](submissions/20261118_sota2823/README.md) | `58522779` | **28.23162，COMPLETE**（rank 183） |
| 2026-11-18 | [公开 HW-30 `35fa5ef9` DQI 替换](submissions/20261119_hw30/README.md) | `58517010` | 28.20311，COMPLETE |
| 2026-11-18 | [公开 invsqrt `d0227f3c` 替换](submissions/20261118_2820/README.md) | `58514074` | 28.20041，COMPLETE |
| 2026-11-18 | [公开组合 W（`864f81cd` + `5f901c55` + `4d63be3d`）](submissions/20261118_2819/README.md) | `58496528` | 28.18965，COMPLETE |
| 2026-11-18 | [28.18067 组合（`563d0583` + `575b043f` + `a73b25d2`）](submissions/20261118_281806/README.md) | `58487952` | 28.18067，COMPLETE |
| 2026-11-17 | [DQI `575b043f` 替换](submissions/20261117_deep_575b043f/README.md) | `58464076` | 28.15094，COMPLETE |
| 2026-11-16 | 公开组合迭代（4030 loader / 28.059 / Atakan v15 / Ozertuu 28.091 / sub1） | `58382097`–`58424363` | 27.31541 → 28.09486，COMPLETE |
| 2026-11-15 | [公开 27.31 组合（`1ba197b0` + `821bf8d1` + maoxin 4033）](submissions/20261115_public_2731/README.md) | `58350759` | 27.31193，COMPLETE |
| 2026-11-13 | [27.078 公开三件套](submissions/20261113_27_078/README.md) | `58299045` | 27.00209，COMPLETE |
| 2026-10-30..11-13 | 早期公开组合与自研基线 | `57808271`–`58290992` | 23.00037 → 25.44039，COMPLETE |

## 文档、目录与环境

- [研究现状与公开前沿](docs/public-frontier.md) · [停研总览与清理记录](docs/abandoned-research.md) · [比赛契约与约束](docs/research-map.md) · [官方文档清单](references/competition-manifest.json)
- `data/competition/`：官方原始数据与未改动验证器（不入 Git）。
- `submissions/`：各次提交回执 `README.md`（本地不留 ZIP）。
- `scripts/`：静态检查（`inspect_circuit.py`）、手动验证（`manual_verify.py`）、评分计算（`gm.py`）与打包（`package_submission.py`）。

本地 `.venv` 与 `.uv-cache` 已清理；需运行电路脚本时先 `uv sync`（Python 3.12 + PyPI 原生 `kickmix`，不导入比赛包 Linux `.so`）。不自动提交 Kaggle 或推送代码。
