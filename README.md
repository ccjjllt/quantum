# Quantum circuit compilation：公开方案与 submission 治理

本仓库用于 [Google Quantum AI — Verifiable Quantum Circuit Compilation](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation)。
根工作区使用 **main**，负责公开优秀方案的来源与版本管理、比较选择、组合装配、submission 和提交回执。
三个研究分支保留了 11 月 13 日收尾的旧实验，11 月 18 日重新检出，用于研究冲击 29 至 31.5 分的新算法。[公开方案比较与本轮研究入口](docs/public-comparison-20261118.md)

## 分支与本地工作区

| 职责 | 分支 | 本地目录 | 当前状态 |
|---|---|---|---|
| 公开方案治理与 submission | `main` | 仓库根目录 | 最佳 COMPLETE **28.20311**（58517010）；28.23163 已提交（58522779，PENDING） |
| invsqrt | `codex/invsqrt-research` | `.worktree/invsqrt` | 2026-11-18：43Q 退休/相位扇出重写、旋转余量、查表-相位融合均 no-go；Q≥44 结构下界 |
| 化学 / dfthcsos | `codex/dfthcsos-research` | `.worktree/dfthcsos` | 2026-11-18：6T、8-bit、Q<427、(8,129,44) 重训、`Lambda` 一范数均 no-go；`Lambda` 283.144 已是可行下限（误差预算仅 0.114 mHa） |
| DQI | `codex/dqi-research` | `.worktree/dqi` | 2026-11-18：抽稀/889Q/divstep/retained/2 数组/quotient sweep/ancilla/x-adic/BM-Gao-WB 全 no-go（BM 下界 3t+6=111 字）；tape floor 367,110.166 |

三个旧研究工作区在 2026-11-18 清理后已从原分支恢复。三条旧研究线于 2026-11-13 停止，
2026-11-17/18 的 frontier push 在 14 条轴全部实测关闭后收尾
（见 [已停止研究总览 §9](docs/abandoned-research.md)）。已关闭实验的详细文档、脚本与
大型 artifacts 已清理。官方数据与公开源清单保留；环境可用 `uv sync` 重建。
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
| 2026-11-10 | [自研三件套组合（全本机验证，P0 化学）](submissions/20261110_trio_candidate/README.md) | 58190972 | 已创建，未持续监控分数 |
| 2026-11-11 | [Ozer 25.296 原包](submissions/20261111_ozer296/README.md) | 58222873 | 25.29661，COMPLETE |
| 2026-11-11 | [三验证件三件套（a15b0d73 + 9fcda0c1 + Maoxin303）](submissions/20261111_trio25303/README.md) | 58228252 | 25.30340，COMPLETE |
| 2026-11-11 | [Grimoire 33 公开前沿组合（三件全本机验证）](submissions/20261111_grimoire33/README.md) | 58235797 | 25.33133，COMPLETE |
| 2026-11-11 | [Maoxin v22 4,097T 化学 loader（只换 loader）](submissions/20261111_maoxin4097/README.md) | 58239559 | 25.36085，COMPLETE |
| 2026-11-12 | [25.367 前沿安全组合（新 invsqrt + 化学 refit，DQI 不换）](submissions/20261112_public_25367/README.md) | 58256166 | 25.38868，COMPLETE |
| 2026-11-12 | [eae396ba DQI 替换（公开前沿 25.39570）](submissions/20261112_eae_253957/README.md) | 58265561 | 25.39570，COMPLETE |
| 2026-11-13 | [392k DQI swap（公开 392k 解码器）](submissions/20261113_392k_swap/README.md) | 58290992 | 25.44039，COMPLETE |
| 2026-11-13 | [27.078 public-frontier trio（46Q invsqrt + 889Q DQI + 4,074T chem）](submissions/20261113_27_078/README.md) | 58299045 | **27.00209，COMPLETE** |
| 2026-11-15 | [公开 27.30661 包（maoxin v27 4033 chem + 821bf8d1 DQI + 46Q invsqrt）](submissions/20261115_public_2731/README.md) | 58349843 | **27.30661，COMPLETE** |
| 2026-11-15 | [HW-26 invsqrt + 4033 chem 升级包](submissions/20261115_public_2731/README.md) | 58350759 | 27.31193，COMPLETE |
| 2026-11-15 | [化学换件：4030 loader + 新权重 refit](experiments/ARCHIVE_closed_lines.md) | 58382097 | 27.31541，COMPLETE |
| 2026-11-16 | [换栈：28.059 公开组合（44Q invsqrt + 890Q DQI + marculera v6 化学）](experiments/ARCHIVE_closed_lines.md) | 58392219 | 28.05896，COMPLETE（当时 rank 91/3114） |
| 2026-11-16 | [换件：最高的真实公开包（Atakan v15，GM 28.07503）](experiments/ARCHIVE_closed_lines.md) | 58410043 | 28.07502，COMPLETE |
| 2026-11-16 | [换件：公开最高真实包（Ozertuu 28.091）](experiments/ARCHIVE_closed_lines.md) | 58420406 | **28.09090，COMPLETE（rank 255/3152）** |
| 2026-11-16 | [换件：28.09486 sub1（f2cdab0b + ccc2ab84 + sub1，三件官方 verifier 全 PASS）](experiments/ARCHIVE_closed_lines.md) | 58424363 | **28.09486，COMPLETE（rank 188/3160）** |
| 2026-11-17 | [换 DQI：61c8348d → 575b043f（+4 个已证明 product-retention closings，mean T 367,116.06）](submissions/20261117_deep_575b043f/README.md) | 58464076 | **28.15094，COMPLETE（rank 156，silver 线内）** |
| 2026-11-18 | [28.1807 包：invsqrt 563d0583 + DQI 575b043f + chem a73b25d2](submissions/20261118_281806/README.md) | 58487952 | **28.18067，COMPLETE**（本地 GM 28.180659） |
| 2026-11-18 | [公开 28.19 组合 W：invsqrt 864f81cd + DQI 5f901c55 + chem 4d63be3d](submissions/20261118_2819/README.md) | 58496528 | **28.18965，COMPLETE**（本地 GM 28.189660；独立复核三腿 PASS） |
| 2026-11-18 | [公开 28.20042 包：invsqrt d0227f3c + 同 DQI/chem](submissions/20261118_2820/README.md) | 58514074 | **28.20041，COMPLETE**，rank 120/3327（本地 GM 28.200418，只换 invsqrt −85.22） |
| 2026-11-19 | [公开 HW-30 DQI `35fa5ef9`：−105.01 mean T](submissions/20261119_hw30/README.md) | 58517010 | **28.20311，COMPLETE**，rank 134/3332（本地 GM 28.203115） |
| 2026-11-18 | [公开 SOTA 28.23163：DQI `15a4b740` −1,110.95 mean T](submissions/20261118_sota2823/README.md) | 58522779 | 已创建，PENDING（本地 GM 28.231630；DQI 365,894.20 已独立复核 PASS） |

当前最佳 COMPLETE 为 **28.18965 包（本账号 `58496528`）**：
`864f81cd` invsqrt（44Q，74,490.94707587373）+ `5f901c55` DQI（890Q，346,404,203,610.11，
mean T 367,110.166，0/0）+ `4d63be3d` 化学（427Q，T=14,706，294,642,170.565）。
18 成员 SHA-256 固定，未改动官方 verifier 三腿全量 PASS（invsqrt 200,540,928 shots、
DQI 102,400 shots、chem 78,080 shots），本地 GM **28.189660448**。
榜单返回 **28.18965，COMPLETE**；2026-11-18T06:40Z 快照为 rank 149/3300，**12:46Z 为 rank 184/3314
（跌破银线：28.18965 并列块已扩到 288 队，前 5% = 165）**。榜面只显示 5 位小数，
GM +0.00001 即可越过整个并列块。本轮找到的新杠杆：化学 `Lambda` 一范数（`lambda_eff = sqrt(E_gap(2Lambda-E_gap))`，
`Lambda` = 270.1148 npz 权重项 + 13.0291 角度字项 = 283.1440）——`Lambda` 每降 1，GM +0.0167，
且不花 T/Q；见 [next-generation-20261118](docs/next-generation-20261118.md)。
上一版 **28.18067**（`58487952`）为 `563d0583` invsqrt + `575b043f` DQI + `a73b25d2` chem。
2026-11-18 公开前沿复查：**没有 >28.19 的公开包**；榜首 31.50701 无公开电路。
详见 [公开前沿 2026-11-18b](docs/public-frontier-20261118b.md) 与 [总览 §9.9](docs/abandoned-research.md)。
（更早的 28.15083 包为 `58454232`）：
`f2cdab0b` invsqrt（44Q，75,006.38）+ `ccc2ab84` DQI（890Q，347,375,470,571.73）+
`sub1` 化学（427Q，T=14,712，294,762,697.44）。三件由官方 verifier 在本账号复核 PASS
（chem 78,080 shots、invsqrt 200,540,928 shots / worst-tol 0.99956、DQI 102,400 shots，0 value / 0 phase）。
28.09486 已扩成 185+ 队并列，银线 rank 156 在并列内部；本账号 rank 188，尚未拿银。
上一版 **28.09090**（`58420406`）为：`8b410e77` invsqrt + `ccc2ab84` DQI + `f6e12f02` 化学。
再上一版 **28.07502**（`58410043`）为：`2c125b39` invsqrt + `4b350932` DQI + `881d9dae` 化学。
历史：`58382097` 27.31541 → `58350759` 27.31193 → `58349843` 27.30661。
invsqrt `1ba197b02771`（46Q，78,673.569211；未修改官方 verifier 200,540,928 shots PASS，
worst/tol 0.9986660009）、DQI `821bf8d1`（889Q，360,209,905,486.02，0 errors）、
化学 maoxin 4,033 loader（427Q，294,991,455.82，T=14,728）。
上一版 `58349843` 已 COMPLETE、public **27.30661**，是第一次公开 27+ 升级（+0.30452）。
两版均以公开 Apache-2.0 件为源，归属和来源记录在
[20261115_public_2731](submissions/20261115_public_2731/README.md)。
MCP 名次：提交时 **159 / 3053**，2026-11-15 复核为 **175 / 3055**（其他队伍前进所致）。

历史组合与证据保留在 `submissions/*/README.md`；原始大产物已按
[已停止研究总览](docs/abandoned-research.md) 清理。
作者公开提交 `58121501`（及 Hosen42 `58120775`）得分 **25.14222**，不是本账号 `58123354` 的实时成绩。
gengsr 25.2268、Syed V9、Public Frontier、Grimoire 33、Maoxin 4,097 等旧组合均保留为历史对照，
不得将其旧增量直接累加到新基线上。

历史组合与证据：

- 每个历史提交的机器回执、来源、SHA-256 和验证范围保留在 `submissions/<日期_方案>/README.md`。
- 2026-11-13 清理了原始候选、公开源解包和中间产物；**2026-11-16 又删除了全部 18 个历史
  `submission.zip`（872.5 MB）与已关闭研究的二进制产物（合计回收约 1.10 GB）**。本地不再保存
  提交 ZIP；当前 28.180659 包由 `qingyu1232/qcc-integrator-281806` v1 重建，
  历史组装脚本已随 2026-11-18 清理删除，可用 `git checkout b754ef5 -- <path>` 取回。
- 官方公开源清单保留在 `references/frontier-20261112/`；被删除目录的概况、大小和放弃原因
  见 [已停止研究总览](docs/abandoned-research.md)（§7 为 11-16、§9 为 11-18 清理清单）。

## 公开前沿升级（2026-11-15）

公开前沿已从 27.078 升到 27.3066：2026-11-15 提交 `58349843`（maoxin v27
4,033 chemistry + `821bf8d1` DQI + 46Q invsqrt），MCP 回执 **COMPLETE，27.30661**。
随后提交 `58350759`（HW-26 invsqrt `1ba197b02771` + 同 DQI/化学），**COMPLETE 27.31193**。
HW-26 已在 Kaggle 用未修改官方 verifier 独立 PASS（200,540,928 shots）。
研究记录、公开前沿扫描和逐项判据已随 2026-11-18 清理删除；结论见
[逐轮归档](experiments/ARCHIVE_closed_lines.md) 与
[已停止研究总览 §9](docs/abandoned-research.md)。

## 自研线停止（2026-11-13）

三条研究线（invsqrt、DQI、dfthcsos/化学）已停止推进：最后一版均被公开前沿超过，
最近的判决实验全部 no-go，剩余收益需要换算法族/新训练范式。各研究分支只保留入口 README、
`ABANDONED.md`、系统性复盘和可复用载体；已关闭实验的详细文档、脚本与大型 artifacts 已删除。

- invsqrt：自研 `9c708f7b` 62Q/93,555.26 → 公开 46Q/80,162.73（低 14.3%）。
- DQI：本线最后采用 `eae396ba` 892Q/373.53e9 → 公开 889Q/360.73e9（低 3.4%）。
- 化学：自研 4,097 loader/297.56M → 公开 4,074 loader/296.64M（低 0.31%）。

完整概况、关键数字、放弃原因、删除清单与恢复口径见
[已停止研究总览](docs/abandoned-research.md)。

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
本地 `.venv` 已在 2026-11-18 清理，运行任何脚本前先 `uv sync`；安装完成不代表全量验证通过。

```text
.worktree/            三个独立研究工作区；新实验和证据在对应分支目录
data/competition/     官方原始数据和未修改的验证器（不入 Git）
docs/research-map.md  比赛契约与公开资料的带日期快照
docs/abandoned-research.md  已停止研究总览、放弃原因与四次清理记录
references/          来源清单；frontier-20261112/ 保留当前最佳公开源清单
experiments/          仅保留 README.md 与 ARCHIVE_closed_lines.md；研究目录已清理
artifacts/            已清空（仅 .gitkeep，不入 Git）
submissions/          提交回执与 README；本地不保存 ZIP（不入 Git）
scripts/             静态查看、手动验证、GM 复核和打包入口（kgpu.py 已删除）
```

已有官方34个文件的来源清单见 [competition-manifest.json](references/competition-manifest.json)。
比赛契约、评分口径和历史讨论见 [研究地图](docs/research-map.md)；它注明快照日期，不代表实时公开前沿。

main 可手动装配已经选定的三任务组合：

```sh
uv run python scripts/package_submission.py artifacts/candidate --output submissions/selected_release/submission.zip
```

候选目录需含 `invsqrt.kmb`、`dqi.kmb` 和完整 `dfthcsos/`；每个电路也可用唯一的 `.kmx` 格式。
比赛上传文件名必须为 `submission.zip`。该命令只打包，不运行官方验证器，也不向 Kaggle 提交。
