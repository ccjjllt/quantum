# Quantum circuit compilation：公开方案与 submission 治理

本仓库用于 [Google Quantum AI — Verifiable Quantum Circuit Compilation](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation)。
根工作区使用 **main**，负责公开优秀方案的来源与版本管理、比较选择、组合装配、submission 和提交回执。
三个研究分支分别推进算法、电路与资源成本研究。

## 分支与本地工作区

| 职责 | 分支 | 本地目录 | 当前研究入口 |
|---|---|---|---|
| 公开方案治理与 submission | `main` | 仓库根目录 | 本页及 `submissions/` |
| invsqrt | `codex/invsqrt-research` | `.worktree/invsqrt/` | [Syed V9 研究](.worktree/invsqrt/experiments/invsqrt/20261106_syed_v9/README.md) |
| 化学 / dfthcsos | `codex/dfthcsos-research` | `.worktree/dfthcsos/` | [Syed V9 研究](.worktree/dfthcsos/experiments/dfthcsos/20261106_syed_v9/README.md) |
| DQI | `codex/dqi-research` | `.worktree/dqi/` | [Syed V9 研究](.worktree/dqi/experiments/dqi/20261106_syed_v9/README.md) |

工作区链接用于本机浏览，`.worktree/` 不进入 Git。三条研究线保留共同历史，新增研究只写入各自工作区。
官方数据、原始公开包和已有 Python 环境可只读共用；每条研究线的候选和日志写入自己的 `artifacts/`。
采用研究成果时，main 记录实际选定的产物、来源、参数和验证范围，不整支混入研究过程。

## 已有提交记录

以下来自本地保存的回执，不是实时状态查询。作者成绩、本地验证结果和本账号成绩分别记录。

| 日期（北京时间） | 采用方案 | 本账号提交 ID | 已记录的本账号 Public Score |
|---|---|---:|---|
| 2026-10-30 | Heliosli v26 / dataset v24 / v45_oz | 57808271 | 23.00037，COMPLETE |
| 2026-11-01 | Hedge Wizardry notebook v5 / HW-06 | 57876561 | 23.83790，后续回执已确认 |
| 2026-11-04 | [Heliosli V5 原始组合](submissions/20261104_heliosli_v5/README.md) | 57980157 | 24.54651，COMPLETE |
| 2026-11-05 | [Maoxin V2 原始组合](submissions/20261105_maoxin_v2/README.md) | 58014726 | 24.78590，创建新提交前的去重读取确认COMPLETE |
| 2026-11-06 | [Syed V9 固定数据集组合](submissions/20261106_syed_v9/README.md) | 58041132 | 24.94081，2026-11-08提交前去重读取确认COMPLETE |
| 2026-11-08 | [Public Frontier 25.14222 原始组合](submissions/20261108_public_frontier/README.md) | 58123354 | 已创建，未持续监控分数 |
| 2026-11-10 | [gengsr 25.2268 组合](submissions/20261110_gengsr_252268/README.md) | 58181743 | 已创建，未持续监控分数 |

当前公开比较基线为 **[gengsr 25.2268（shifter 46 + own chemistry loaders）](https://www.kaggle.com/code/gengsr/lb-25-2268-shifter-46-own-chemistry-loaders)**；机器可读来源和口径见 [public-baseline.json](references/public-baseline.json)。
作者公开提交 `58121501`（及 Hosen42 `58120775`）得分 **25.14222**，不是本账号 `58123354` 的实时成绩。
2026-11-10 起比较基线已更新为 gengsr 25.2268（本账号提交 `58181743`，invsqrt 本机重验 PASS 94537.59），
Syed V9 与 Public Frontier 组合均保留为历史对照，不得将其旧增量直接累加到新基线上。
共享原始电路在 `artifacts/20261108_public_frontier/release/`，来源快照在相邻 `source/`。
本次直接提交未修改的原始 `submission.zip`（18 个文件 SHA-256 已核对），没有混入本地研究补丁，提交前未在本机重跑全量官方验证。
上一版 Syed V9（`artifacts/20261106_syed_v9/release/`）保留为历史对照，不能把基于 Syed V9 的旧增量直接累加到新公开前沿上。

历史组合与证据：

- `artifacts/20261030_public_best/`：v45_oz 公开输入、归属、首次提交记录；化学在本机完成默认规模官方验证，成本337,991,954.0482345。
- `experiments/20261030_public_best/`：该历史公开组合的来源清单与装配代码，保留原路径便于复现。
- `artifacts/20261101_public_hw06/`：HW-06 来源及提交记录，本机未全量复跑。
- `artifacts/20261104_submission_refresh/`：Heliosli V5 固定版本、作者日志和平台回执。
- `artifacts/20261105_submission_maoxin_v2/`：Maoxin V2 本次提交的机器可读回执。

## main 的治理约定

1. 对公开方案记录作者、固定版本、生成/组合方法和原始产物。公开成绩是带日期的比较依据，不是不可突破的上限。
2. 明确区分来源文件可用、静态资源、局部诊断、完整官方本地验证和实际 Kaggle 分数。未执行的检查不写成通过。
3. 原始提交 ZIP 与回执一起放在 `submissions/<日期_方案>/`；README 可进入 Git，ZIP、大文件、凭据和签名 URL 不进入 Git。
4. 研究候选的采用是单独的组合决定；在 main 记录选定版本与证据，不覆盖原始公开文件。
5. 不自动提交 Kaggle、发布数据或推送代码。打包不触发验证或上传；验证和提交均按明确任务手动发起。

历史哈希记录保留其原有验证范围，不意味着以后每次提交必须重复匹配哈希。
本次 Maoxin 提交按用户要求跳过该步骤，详细范围见回执。

## 环境与目录

使用 Python 3.12 和 `uv`，依赖由 `pyproject.toml`、`uv.lock` 管理：

```sh
uv sync
```

macOS 使用 PyPI 原生 kickmix，不导入比赛数据包面向 Kaggle Linux 的 `kickmix.so`。
已有本地环境为 Python 3.12.13 / kickmix1.0.0；安装完成不代表全量验证通过。

```text
.worktree/            三个独立研究工作区（不入 Git）
data/competition/     官方原始数据和未修改的验证器（不入 Git）
docs/research-map.md  比赛契约与公开资料的带日期快照
references/          来源清单
experiments/          main 的历史记录与公开组合装配；新算法研究在研究分支
artifacts/            main 的公开输入、来源快照与提交证据（不入 Git）
submissions/          最终 ZIP（不入 Git）及 README 回执
scripts/             静态查看、手动验证和打包入口
```

已有官方34个文件的来源清单见 [competition-manifest.json](references/competition-manifest.json)。
比赛契约、评分口径和历史讨论见 [研究地图](docs/research-map.md)；它注明快照日期，不代表实时公开前沿。

main 可手动装配已经选定的三任务组合：

```sh
uv run python scripts/package_submission.py artifacts/candidate --output submissions/selected_release/submission.zip
```

候选目录需含 `invsqrt.kmb`、`dqi.kmb` 和完整 `dfthcsos/`；每个电路也可用唯一的 `.kmx` 格式。
比赛上传文件名必须为 `submission.zip`。该命令只打包，不运行官方验证器，也不向 Kaggle 提交。
