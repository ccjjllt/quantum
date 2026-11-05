# Quantum circuit compilation research

[Google Quantum AI — Verifiable Quantum Circuit Compilation](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation) 的研究工作区。围绕电路表示、可逆算法、精度分配和资源复用迭代方案。

当前分支 `codex/invsqrt-research` 的新增研究集中于 **invsqrt**；Maoxin V2 方法、局部候选与后续方向见[本轮研究](experiments/invsqrt/20261105_maoxin_v2/README.md)。化学与 DQI 的新研究分别放在独立分支 `codex/dfthcsos-research`、`codex/dqi-research`，共同历史记录保留作参考。

本工作区位于主仓库的 `.worktree/invsqrt/`。根目录 `main` 负责公开方案治理与 submission；本分支继续推进本方向研究。共享输入只读使用，新增产物写入本工作区。

工作约定：先做能回答研究问题的最小实验；不写测试文件，不配置 CI、自动测试或合并门控。需要检查时手动执行命令，记录结果即可。官方 verifier 是测量正确性与成本的研究工具，保留原版；初始化仓库不代表已经完成全量验证。

## 环境

使用 Python 3.12 和 [uv](https://docs.astral.sh/uv/)。在仓库根目录执行：

```bash
uv sync
```

需要 Jupyter 时再安装可选依赖：`uv sync --extra notebooks`。

本地使用适配当前系统的 `kickmix` 包。比赛附带的 `kickmix.so` 面向 Kaggle 镜像，不能直接当作 macOS 动态库使用。固定依赖版本见 `uv.lock`；与线上评测比较时，同时记录所用 kickmix 和官方 verifier 版本。

2026-10-30 初始化已完成 Python 3.12.13 环境与依赖安装，当前使用 `kickmix 1.0.0`。官方参考基线尚未运行三项全量本地验证。

同日已引入 Heliosli notebook v26 / dataset v24 的公开组合 `v45_oz`，18 个候选文件和 ZIP 成员均与公开清单的 SHA-256 一致。化学任务已通过默认规模官方本地验证（78,080 shots，salt `notebook-verification`），成本 `337,991,954.0482345`；提交前 invsqrt、DQI 本机仅检查文件完整性，后续完成了局部诊断。作者保存的三项完整验证日志给出本地 GM `23.0355`，与我们的线上分数分开记录。组件来源保存在 `artifacts/20261030_public_best/release/CREDITS.md`，实验结果分别保存在各子任务目录。

按本次明确提交指令，已于北京时间 2026-10-30 22:29 向 Kaggle 提交一次，编号 `57808271`；平台状态为 `COMPLETE`，Public Score 为 **23.00037**。提交包为 `submissions/20261030_public_best/submission.zip`，平台返回记录保存在 `artifacts/20261030_public_best/kaggle_submission.json`。

该组合的后续审计记录了 DQI 的低权重错误、化学的结构与成本阶梯、invsqrt 的恢复成本。
[invsqrt有效研究入口](experiments/invsqrt/README.md)现已整理为当前62Q生成/证明链及有效历史方法；
其余审计见[dqi](experiments/dqi/20261030_public_audit/)和[dfthcsos](experiments/dfthcsos/20261030_public_audit/)。

2026-11-04最新已完成公开组合提交为[Heliosli V5](submissions/20261104_heliosli_v5/README.md)，
提交57980157，实际Public Score **24.54651**。本地另有62Q invsqrt候选，双seed完整官方
成本约**98123.14**，尚未提交；其本地结果与上述组合榜分分别记录。

已手动检查三个脚本及官方 CLI 的帮助入口，读取真实 invsqrt/ANGLE 基线的静态资源，并将完整参考提交打包为 `submissions/baseline.zip`（13 个文件）。这只确认环境、读取与打包可用，不代表全量评分通过。

## 目录

```text
data/competition/     官方数据、参考电路和原版 verifiers（不入 Git）
docs/research-map.md  比赛契约、公开方案与讨论索引
experiments/          研究记录、小型探索脚本和笔记
artifacts/            生成电路、中间产物和手动验证结果（不入 Git）
submissions/          提交ZIP（不入Git）及对应README回执
scripts/             查看电路、手动验证和打包的便利入口
```

官方数据目录应包含 `sample_submission/`、`verifiers/`、`kickmix/` 和比赛论文。数据来源为 [Kaggle Data](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/data)。额外的 [化学 Starter Kit](https://www.kaggle.com/datasets/sohier/verifiable-circuit-compilation-starter-kit) 用于训练分解和生成 ANGLE 电路，按研究需要另行获取。

初始化已获取全部 34 个官方文件（约 1.04 GB）；文件来源和逐文件 SHA-256 见 [competition-manifest.json](references/competition-manifest.json)。

## 开始一次实验

先查看基线电路，再挑一个子任务和一个改动。静态资源统计不等于完整评分。

```bash
uv run python scripts/inspect_circuit.py data/competition/sample_submission/invsqrt.kmb
```

需要官方检查时，手动运行对应命令。三项独立执行，完整验证可能耗时较长；不在安装、导入或打包时自动触发。

```bash
uv run python scripts/manual_verify.py invsqrt data/competition/sample_submission/invsqrt.kmb --salt research-001
uv run python scripts/manual_verify.py dqi data/competition/sample_submission/dqi.kmb --salt research-001
uv run python scripts/manual_verify.py dfthcsos data/competition/sample_submission/dfthcsos --salt research-001
```

把自己的完整候选放到 `artifacts/candidate/`，保留以下结构。只研究一个任务时，其余任务可以沿用基线。

```text
artifacts/candidate/
├── invsqrt.kmb
├── dqi.kmb
└── dfthcsos/
    ├── submission.npz
    ├── angle_k_0.kmb
    └── ...
```

文本 `.kmx` 也可使用，每个电路只保留一种格式。打包由自己触发：

```bash
uv run python scripts/package_submission.py artifacts/candidate --output submissions/submission.zip
```

打包不等于验证通过，也不会向 Kaggle 提交。比赛接口要求上传文件名恰好为 `submission.zip`；区分多个版本时使用不同的父目录。实验结论保存在对应子任务的实验目录，记录约定见 [experiments/README.md](experiments/README.md)。本地 verifier 的结果、作者自报的 LB 和实际线上评分分开记录。

## 研究入口

- `invsqrt`：近似与精度分配、相位融合、寄存器生命周期和反计算。
- `dqi`：解码器算法、有限域算术、流式原位实现，以及 `Q² × 门数 × 失败惩罚` 的权衡。
- `dfthcsos`：量化感知分解、系数重拟合、Givens 树和多字 QROM。

具体任务契约、已有方案和主办方澄清放在 [研究地图](docs/research-map.md)。公开成绩是带日期的研究线索，不视为不可突破的上限。
