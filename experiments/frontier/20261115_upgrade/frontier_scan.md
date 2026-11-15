# 2026-11-15 公开前沿复扫：27.3068 之上还有没有可用件

扫描时间：2026-11-15 01:00–01:20（本地）= 2026-11-14 17:00–17:20 UTC。
范围：**2026-11-14 12:00 UTC 之后**新增/更新的 notebook、dataset、论坛帖；以及
11-14 11:49 UTC 的 497 件公开电路 manifest 作为全量基线。
工具：Kaggle MCP（`search_notebooks`、`search_datasets`、`get_dataset_info`、
`list_dataset_files`、`download_dataset`、`get_notebook_info`、`get_forum_topic`、
`list_competition_topics`、`get_competition_leaderboard`、`get_competition_submission`）
+ `kaggle` CLI 2.2.5 + 本仓库 `scripts/inspect_circuit.py`（只读结构，不模拟）。

## 结论（先行判决）

1. **没有任何公开件或公开件组合超过 27.3122。** 公开可分任务的最佳拼装
   （invsqrt `1ba197b02771` + DQI `821bf8d1` + chem npz `e52b7cdd`）算出
   **27.31214**，比我们 ref 58349843 的 **27.30661** 高 **+0.0203%**。
   其余公开件都不超过 27.3079（多数集中在 27.3066–27.3069）。
2. **唯一有实际价值的公开升级件：`1ba197b02771`（HW-26 invsqrt，46Q，
   78,673.5692）**，比我们现用的 `e46d90c3`（78,719.5291）低 46.0 个 cost，
   正好等于少执行 1 个 Toffoli。它由 `manwithacat/vqcc-hedge-wizardry` v27
   （2026-11-14T16:33Z 更新，在我们 12:00 截止点之后）直接以 198,631 字节
   单文件释出。单独换它：GM **27.31193**，在 2026-11-15 快照里对应**第 147 名**
   （我们现在的 27.30661 是 23 队并列段，221–243 名）。
3. **没有 Q<46 的 invsqrt，没有 Q<889 且更便宜的 DQI，没有 840Q DQI，
   没有 T<14,728 的化学。** 全部为 "none found"，证据见下。
4. 排行榜第 31–146 名（27.40–27.61）**不是公开件**：公开可复现的天花板就是
   27.31193（第 147 名），其上方存在 0.09 分的断层。
5. **27.30774 那 3 个队**已反推出来：HW-26 invsqrt + 4,038 化学（预测 27.30772，
   差 0.00002），也就是"换了 invsqrt 但化学没跟上"的版本——不是新组件。
   11-14 12:00 UTC 之后**没有任何 notebook 或 dataset 声明 >27.3077**；
   最高的自报值是 `asteriospanoras` v4 的 27.3068 与 `junmiaotiao` 的 27.30683。

## 排行榜结构：公开件与私有件的分界（关键证据）

快照：`get_competition_leaderboard`，最新提交时间 2026-11-14T16:02:22Z，
取前 300 名（`pageSize=100` 连续三页，分数单调递减）。

| 分数 | 首次出现排名 | 队伍数 | 解释 |
|---:|---:|---:|---|
| 29.90871 | 1 | 1 | Entangled Team，仍居首，11-12 后未动 |
| 28.00000 | 21 | — | 28+ 共 20 队 |
| 27.50000 | 46 | — | 27.5+ 共 45 队 |
| **27.31193** | **147** | **2** | **= HW-26 invsqrt + 4,033 化学（本文预测 27.311926）** |
| 27.30774 | 151 | 3 | = HW-26 invsqrt + 4,038 化学（预测 27.307717） |
| 27.30687 | 154 | 3 | 微调权重 |
| **27.30683** | **162** | **48** | = `e46d90c3` + npz `e52b7cdd`（预测 27.30683，精确命中） |
| 27.30670 | 210 | 8 | 微调权重 |
| **27.30661** | **221** | **23** | **= 我们的 ref 58349843**（`get_competition_submission` 确认 score 27.30661） |
| 27.30242 | 252 | 22 | = `e46d90c3` + 4,038 化学（预测 27.302402） |

这个分解是从三项几何平均反推的，四个平台都能用三项公开件反推到 1e-5 以内，
说明计分模型没有遗漏项。由此得到两条硬结论：

- 公开件最高只能到 **27.31214**（把最好的 invsqrt、最好的 chem 权重同时用上），
  当前还没有人提交这一组合；已有人到达的是 27.31193（第 147–148 名）。
- 第 31–146 名（27.40–27.61）与公开天花板之间有 **≥0.09 分（≈0.3%）** 的空档，
  这些队在用一个**没有公开**的组件。本轮没有找到它。

参考换算（相对 27.30661）：单项任务 cost 每降 1%，GM 升 0.336%。
到 27.5 需要单任务 −2.09%（invsqrt ≤77,070 / DQI ≤3.5266e11 / chem ≤288.81M），
到 28.0 需要单任务 −7.25%（invsqrt ≤73,015 / DQI ≤3.3411e11 / chem ≤273.61M）。

## 候选公开包

| 公开件 | 释出/更新 (UTC) | 分数 | invsqrt | DQI | chemistry | submission.zip 直接可得？ |
|---|---|---|---|---|---|---|
| `manwithacat/vqcc-hedge-wizardry` v27（HW-26）<br>https://www.kaggle.com/datasets/manwithacat/vqcc-hedge-wizardry | 11-14 16:33 | 单件 +0.039%（其基线 27.27840→27.28902） | **`1ba197b02771` 46Q 78,673.5692** | — | — | 否：只有 `circuits/invsqrt/1ba197b02771.kmb` |
| `junmiaotiao/qcc-frontier-20261114f` v1<br>https://www.kaggle.com/datasets/junmiaotiao/qcc-frontier-20261114f | 11-14 15:25 | **27.30683**（自报） | `e46d90c3` 46Q 78,719.529 | `821bf8d1` 889Q | npz `e52b7cdd` + 15 loaders `71735b23…`，**294,984,413.84**，T 14,728 | 否：18 个文件 + `MANIFEST.json`，需自行 zip |
| `asteriospanoras/qcc-27-307-frontier-finer-chemistry-refit` v4<br>https://www.kaggle.com/code/asteriospanoras/qcc-27-307-frontier-finer-chemistry-refit | 11-14 16:08（搜索索引） | 27.3068（自报 local） | `e46d90c3` | `821bf8d1` | maoxin 表 + 权重再拟合，λeff 46.905894→46.905863 | 否：跑 notebook 并置 `WRITE_SUBMISSION=True`（~15 min CPU） |
| `masonbradleygilhool/qcc-frontier-merge-v119` v1<br>https://www.kaggle.com/datasets/masonbradleygilhool/qcc-frontier-merge-v119 | 11-14 13:38 | 未标 | `e46d90c3`（SHA 已核） | `821bf8d1`（文件 455,584,321 B） | 旧 family：`angle_k_0` 128Q/292 Toffoli（我们 4033 版是 128Q/**291**） | 否：散件 |
| `lucifer19/black-cat-credited-portfolio` v1<br>https://www.kaggle.com/datasets/lucifer19/black-cat-credited-portfolio | 11-14 13:51 | 27.30661（自报 = maoxin v27 字节） | `e46d90c3` | `821bf8d1` | 4033 版 | 否：滚动包 + fallback |
| `maoxin123/qcc-chemistry-4033-toffoli-loaders` v1<br>https://www.kaggle.com/datasets/maoxin123/qcc-chemistry-4033-toffoli-loaders | 11-14 13:02 | — | — | — | 我们现用件：λeff **46.9070139**、T **14,728**、Q 427、**294,991,455.82** | 是（组件级） |
| 我们 ref 58349843（`maoxin123/qcc-v27-…` v2） | 11-14 16:54 | **27.30661** | `e46d90c3` 78,719.529147 | `821bf8d1` 3.602099e11 | 294,991,455.82 | 已提交 |

附带说明（同批，均 ≤27.3066，不构成升级）：
`dmitrybatow/qcc-v27-frontier-live-assembly`（27.29700）、
`xianyu3/vqcc-v52-asterios-invsqrt-20261114`（复现 `e46d90c3`）、
`mizeroluckygall/quantum-circuits-4033-chemistry-refit-guide`（27.30683 的复述）、
`arizalfirdaus123/vqcc-50-688-d-df-thc-valley-refit-audit`（引用 27.30661）、
`thomasgamet/quantum-attempt-new-base-bundle`（27.30661 基线）、
`sheroleg/quantum-circuits-from-zero-2-the-dqi-decoder`（教学）。

论坛：`list_competition_topics` 最新两条为
[759244](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/discussion/759244)
（QVC v0.4.0，11-14 13:22，46Q/889Q，自报 26.97516–27.01640，低于我们）与
[759220](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/discussion/759220)
（RezOps 简报，11-14 11:23，公开前沿 27.27838）。**没有 27.4+ 的公开声明。**

## 分任务证据

### 1) invsqrt：Q<46 或 cost<78,719.5 —— 找到 1 件（cost 维度）

从 `manwithacat/vqcc-apache-public-circuits` **v125（2026-11-14T11:49Z，497 件）**
的 `manifest.csv` 全量筛 87 件 invsqrt：

```
条件 (Q<46) OR (cost<78719.53)  →  0 命中
Q 最小值 = 46（共 6 件 46Q；最低 cost 78,765.51）
```

11-14 12:00 之后新增的唯一更优件：

| 项 | 值 |
|---|---|
| 文件 | `circuits/invsqrt/1ba197b02771.kmb`，198,631 字节 |
| SHA-256 | `1ba197b027713aac164056d12505c87f286c3fcd94f403c522073325763bf2f9`（本地 `shasum` 与数据集 `SHA256SUMS` 一致） |
| Q | 46 |
| 静态 Toffoli-like | **1,550**（CCX 1,412 + CCZ 9 + CSWAP 129） |
| cost | **78,673.56921101942**（−0.1167% vs `dcde70780434`；−0.0584% vs 我们的 `e46d90c3`） |
| 作者 / 方法 | manwithacat，HW-26："measure-first at q21，再把 q10·q11 的一个被抵消乘积经 q21 测出" |
| 验证 | 本机未改官方 verifier，**默认 salt、200,540,928 shots，PASS**，worst error 99.87% of tolerance；另 32/32 本地引擎 salt PASS；**hosted（Kaggle）验证仍标 pending** |

本仓库独立结构核对（`scripts/inspect_circuit.py`，只读、不模拟）：

| 电路 | SHA-256 前 12 | Q | bits | 静态 Toffoli-like | CCX | CZ | HMR | POP/PUSH_CONDITION |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `dcde70780434`（公开基线） | `dcde70780434` | 46 | 387 | 1,552 | 1,414 | 2,224 | 1,278 | 702 / 702 |
| `e46d90c36d1b`（我们现用） | `e46d90c36d1b` | 46 | 387 | **1,551** | 1,413 | 2,225 | 1,278 | 702 / 702 |
| `1ba197b02771`（HW-26） | `1ba197b02771` | 46 | **388** | **1,550** | 1,412 | 2,226 | **1,279** | **709 / 709** |

差值形态（+1 HMR、+1 CZ、+7 条件栈、+1 经典位、−1 CCX）与 HW-26 描述的
"再多测出一个 Toffoli" 完全一致，**不是**同一件的字节改写。

**Q=45 的可行性**：`asteriospanoras/qcc-27-30-what-works-what-fails-and-why`
（v12，11-14 16:24）第 3 节明确：46 wires 上的每个峰值都是 carry 或 AND 临时位，
绕开它们最便宜要 **+196 Toffoli**，而盈亏平衡点是 **+38**，因此 45Q 不可行。
本轮未找到任何反例。

### 2) DQI：Q<889（尤其 840Q）或 cost<3.602e11 —— none found

`manifest.csv` 97 件 DQI 中 cost<360,209,905,486.02 的**只有 `821bf8d1` 本身**。
Q<889 共 17 件，全部更贵：

| Q | 代表 SHA-12 | cost | 相对我们 |
|---:|---|---:|---:|
| 877 | `f3d335c3f693` | 444,151,956,391 | +23.3% |
| 880 | `e8083195cec2` | 842,819,878,126 | +134% |
| 881 | `835414f51eff` | 891,688,391,401 | +148% |
| 882 | `545189b999f4` | 485,193,743,460 | +34.7% |
| 883 | `26369ae8dfaa` | 500,874,373,991 | +39.1% |
| 888 | `fe98677c61ef` | **398,268,953,061**（Q<889 里最便宜） | **+10.56%** |

`asteriospanoras/qcc-circuit-atlas` v2（含非 Apache 件，51 件 DQI）给出同一图景：
Q 分布 = {873, 877, 880, 881, 883, 888, 889, 891, 892, 893, 898, 900, …}，
Q<889 的静态 Toffoli 为 443,898–1,146,775，而 889Q 的解码器约 40 万。
**整个公开集合里没有 840Q 的 DQI**（notebook 搜索 "840"、论坛搜索 "840" 均无相关命中）。

Q<889 的件全部属于**早一代解码器**：`hedge-wizardry` HW-01 在 yoyobar 的 889Q 上
做 release-and-recompute 得到 888Q，代价只需 **+460.4 mean Toffolis**，48 抽签
均值便宜 0.108%，但那一条线的绝对值本身是 **402.7e9**；换成 cutoff-18 的
`821bf8d1` 线后，同 Q 已经降到 **360.2e9**。也就是说"少 1 个 qubit"这件事
早就做得到，值不值取决于解码器代数——在当前这一代上没有任何公开件做到。

### 3) chemistry：T<14,728 或 cost<294.98M —— none found

- `manifest.csv` 313 件化学件的 **T 最小值 = 14,738**（`a742a60010a3` /
  `1575c74b1944` / `0b2e60550a38` 等，均 4,038-loader 家族），公开最低 cost
  **295,127,884.76**。
- 我们与 Atakan 的 4,033-loader 家族把 T 压到 **14,728**（少 10 个 Toffoli），
  这是目前已知的 T 下限；`maoxin123/qcc-chemistry-4033-toffoli-loaders` 自述
  "k0 291, k1–k3 286, k6/k8/k10 261, k12–k14 262，其余 263"，本地
  `inspect_circuit.py` 核到 `angle_k_0` = 128Q/**291**、`angle_k_1` = 125Q/**286**。
- 11-14 12:00 后的最好公开化学是 `junmiaotiao` 的 npz `e52b7cdd` +
  15 个 loader `71735b23…`，**294,984,413.83657354**（T 仍 14,728，Q 427），
  比我们低 **0.0024%**，但仍**高于 294.98M 门槛**。
- `asteriospanoras` v4 的权重再拟合把 λeff 从 46.905894 降到 46.905863
  （−0.000066%），换算 GM +0.0008%，属噪声级。
- C=43（少一列）在固定 angle words 下达不到 20 mHa 门：误差抬到 **21.1 mHa**
  （`qcc-27-30-what-works-what-fails-and-why` 第 3 节）。因此 T<14,728 需要新
  family/新编码，公开件里不存在。

## 排名短名单（按可采纳性与收益排序）

| # | 动作 | 需要的文件 | 预期 GM | 相对现在 | 预期名次* | 成本/风险 |
|---:|---|---|---:|---:|---:|---|
| 1 | 换 invsqrt + 换 chem npz | HW-26 `1ba197b02771` + `junmiaotiao` npz `e52b7cdd` + 15 loaders | **27.31214** | **+0.0203%** | ~147 或略高 | 2 个文件替换；需官方 verifier 复跑 |
| 2 | 只换 invsqrt | HW-26 `1ba197b02771` | **27.31193** | **+0.0195%** | 147（该分数现为 147–148 名） | 1 个 194KB 文件；风险同上 |
| 3 | 只换 chem npz | `junmiaotiao` 的 18 件（或仅 npz `e52b7cdd`） | 27.30683 | +0.0008% | 162 | 收益可忽略；不建议单独做 |
| 4 | 换 4,038 化学 | `a742a60010a3` 等 | 27.30240 | −0.0154% | 252 | **倒退**，不做 |

\* 名次基于 2026-11-14T16:02Z 的最后一次提交快照；榜单会继续移动。
反推用的公开 4,038 化学取 `a742a60010a3` 的 **295,127,884.76**（公开最低），
因此 27.30242 / 27.30774 两个平台与预测值 27.30240 / 27.30772 相差
0.00002（0.00007%），属 LB 取整/权重微差。

**为什么第 1 项只值 +0.02%**：我们在 `e46d90c3` 里已经吃过一个 Toffoli 的红利
（`dcde70780434` 1,552 → 1,551）。HW-26 是从原始基线吃掉两个
（1,552 → 1,550），所以对公开基线是 −0.117%，对我们只剩 −0.058%。
GM 按立方根摊薄后就是 +0.0195%。

**不建议做的**：
- `masonbradleygilhool/qcc-frontier-merge-v119`：化学是旧 family（k0 = 292 Toffoli）。
- 任何 888Q/883Q DQI：贵 10–148%。
- `QVC v0.4.0`（discussion 759244）：自报 26.975–27.016，且 46Q/889Q 与我们同源。
- 追 27.4+：公开件不存在，第 31–146 名用的是私有组件。

## 验证范围（不要把未执行的写成通过）

已执行（本轮）：
- Kaggle MCP 读取：排行榜 3 页 ×100、公开电路 `manifest.csv`（497 行）聚合筛选、
  hedge-wizardry `entries.csv`（24 行）与 `SHA256SUMS`、`junmiaotiao` `MANIFEST.json`、
  dataset 文件清单、9 个 notebook 的 markdown 头（含 11-14 12:00 后全部新件）、2 个论坛主题全文。
- 本地：3 个 invsqrt 的 SHA-256 与 `scripts/inspect_circuit.py` 结构输出
  （只读，不模拟）；`artifacts/20261115_frontier/` 下的下载件校验。

**未执行**：
- 没有跑官方 verifier（invsqrt 默认 salt 是 200,540,928 shots，属重活；
  DQI 102,400 shots 也未跑）。`1ba197b02771` 的 PASS 来自 hedge-wizardry 的
  回执，**本仓库尚未独立复现**。
- 没有生成 `submission.zip`，没有提交 Kaggle，没有修改任何现有代码、README 或提交回执。

**采纳前必须做**：
1. 在 Kaggle notebook（或本地）用未修改的 invsqrt verifier 跑 `1ba197b02771`，
   确认 worst error 与 PASS。注意其 worst error 是容差的 **99.87%**，余量仅 0.13%，
   换 salt 前必须复跑。
2. 若同时换 chem npz，必须重跑 dfthcsos verifier（78,080 shots）确认 e1/e2/E_gap 过门。
3. DQI 保持 `821bf8d1` 不动——它的 3.6021e11 是零失败值，private 重抽仍是最大变量
   （一次 DQI 失败 ≈ −0.153% GM，约等于 8 个 HW-26 的收益）。

## 复现命令

```bash
# 1) 公开电路全量索引（544KB）
KAGGLE_API_TOKEN=$(cat ~/.kaggle/access_token) \
  ~/.local/bin/kaggle datasets download -d manwithacat/vqcc-apache-public-circuits \
  -f manifest.csv -p artifacts/20261115_frontier/meta --unzip

# 2) HW-26 单件 + 哈希
KAGGLE_API_TOKEN=$(cat ~/.kaggle/access_token) \
  ~/.local/bin/kaggle datasets download -d manwithacat/vqcc-hedge-wizardry \
  -f circuits/invsqrt/1ba197b02771.kmb -p artifacts/20261115_frontier/hw26
shasum -a 256 artifacts/20261115_frontier/hw26/circuits/invsqrt/1ba197b02771.kmb
# 期望 1ba197b027713aac164056d12505c87f286c3fcd94f403c522073325763bf2f9

# 3) 结构对比（不模拟）
.venv/bin/python scripts/inspect_circuit.py \
  artifacts/20261115_frontier/hw26/circuits/invsqrt/1ba197b02771.kmb
# 期望 Q=46, static_toffoli_like=1550

# 4) junmiaotiao 组合清单
KAGGLE_API_TOKEN=$(cat ~/.kaggle/access_token) \
  ~/.local/bin/kaggle datasets download -d junmiaotiao/qcc-frontier-20261114f \
  -f MANIFEST.json -p artifacts/20261115_frontier/portfolios/jm_f --unzip

# 5) 采纳前验证（重活，需在 Kaggle 或本机长时间跑）
.venv/bin/python scripts/manual_verify.py invsqrt \
  artifacts/20261115_frontier/hw26/circuits/invsqrt/1ba197b02771.kmb
```

## 产物

- `artifacts/20261115_frontier/meta/manifest.csv`：497 件公开电路索引
- `artifacts/20261115_frontier/meta/entries.csv`：hedge-wizardry 24 条 tweak
- `artifacts/20261115_frontier/hw26/circuits/invsqrt/1ba197b02771.kmb`（198,631 B）
- `artifacts/20261115_frontier/portfolios/jm_f/{MANIFEST.json,invsqrt.kmb}`
- `artifacts/20261115_frontier/portfolios/mason/{invsqrt.kmb}`（= `e46d90c3`）
- `artifacts/20261115_frontier/portfolios/mason_chem/`（旧 family loader，仅核对用）
- `artifacts/20261115_frontier/atlas/circuits.csv`：Atlas v2 的 1,719 件索引

## 复扫 2026-11-15 19:00 UTC（11-14 18:56–19:09 之后的新件）

`manwithacat/vqcc-apache-public-circuits` 已从 497 行涨到 **507 行**
（updated 2026-11-14T18:59Z），`vqcc-hedge-wizardry` updated 18:56Z，
新 notebook `atakanaldemir/qcc-terminal-readout-and-phase-folds`（18:42）。

用 MCP 拉取新 `manifest.csv` 与 `entries.csv` 全量比对：

| 任务 | 公开最好件（11-15 19:00 快照） | 我们现用 | 差 |
|---|---:|---|---:|
| invsqrt | 78,719.526 `330fdd0ca5f5`（manifest 内） | **78,673.569** `1ba197b02771`（HW-26，manifest 未收录） | 我们更优 |
| DQI | 360,209,905,486.02 `821bf8d1` | 同件 | 0 |
| chemistry | **294,984,216.56** `c6e74b63ad82`（asterios v4 λ refit，T=14,728） | 294,991,455.82 | 对方 −0.0024% |

`vqcc-hedge-wizardry` 仍只有 **24 条**，最后一条就是 **HW-26**（我们已在用）。18:56 的更新
没有新增 HW 条目。

因此本次复扫的唯一增量是化学权重 λ refit：拼装后 GM = **27.31215**，比我们的
**27.31193** 高 **+0.00022**（0.0008%）。这是公开件天花板；我们没有为 +0.0002 再消耗
一次提交（现有 27.31193 的 DQI 抽签已是 0 错误地板，重提交只可能持平或更差）。

## 再复扫：`atakanaldemir/qcc-terminal-readout-and-phase-folds` v6

11-14 18:42 的更新里有一张更低的化学成本表（原文摘录）：

```
| Chemistry                  | Cost            | Toffolis | Task qubits |
| Maoxin123 4033 source      | 294991455.819055| 14728    | 427         |
| Our published V15          | 294984413.836437| 14728    | 427         |
| Our new continuation       | 294982944.809323| 14728    | 427         |
```

"Only W/H2_I change. All 15 loaders, angle words, tree, precision, inverse and DQI stay
exact." 同一篇里也确认 invsqrt 那一 Toffoli 的改动是 Asterios 的 V5 变换（即我们已在用的
`1ba197b02771` 线），并明确声明 `Conditional GM 27.30687575207525 is NOT an observed
public score`。

于是公开件的化学最好值从 294,984,216.56 再降到 **294,982,944.81**。拼装（HW-26 +
821bf8d1 + 294,982,944.81）：

```
GM = 27.31193 × (294991455.82 / 294982944.81)^(1/3) = 27.31219
```

比我们的 **27.31193** 高 **+0.00026**。`T=14,728`、`Q=427`、DQI 都不变，只有权重微小变化。
结论不变：公开件天花板 ≈ **27.3122**，我们已在 0.0003 以内；这不足以支撑一次有意义的提交。

## 复扫：`busyaprime/33-qcc-v8-members`（新发现的整包，26 文件 / 43 MB）

此前只扫过 `manwithacat/vqcc-apache-public-circuits` 的 507 行 manifest；这个包是**另一套**
完整提交（三个任务各一份电路 + `atlas.json` 全量指标 + `manifest.json` 哈希清单）。

`atlas.json` 里的官方口径指标（可直接对比）：

| 任务 | 该包 | 我们 | 差 |
|---|---|---|---|
| chemistry | T=14,908，Q=427，λ_eff=46.90764，**cost 298,600,703.93** | T=14,728，λ_eff=46.907，**294,991,455.82** | 我们好 −1.2% |
| DQI | Q=**892**，T=394,416.26，R=1.19673，**cost 375,561,652,398.94** | Q=889，T=383,008，R=1.19，**360,209,905,486.02** | 我们好 −4.1% |
| invsqrt | `reference_cost.invsqrt` 2,076,774.23 | **78,673.569** | 我们好 26× |

另外它的 `chem.before/after` 只差 0.002%（298,600,703.93 → 298,600,061.56），是权重微调。

**结论：这个包三个组件全部劣于我们现用件，无法用来提升分数。**

**副产品：λ 模型得到独立验证。** 它的指标给出 `Lambda = 282.9771`、`E_gap = 3.914898`、
`lambda_eff = 46.90764`，而 `sqrt(E_gap·(2Λ−E_gap)) = sqrt(3.914898×561.9542) = 46.9076`
—— 与我 §headroom.md 里从 `score = λ_eff·T·Q` 反解的 Λ≈283 完全一致。也就是说
**chemistry 的成本完全由 (Λ, T, Q) 三个数决定，Λ=283 是这份 (8,143,44) 基组在 20 mHa 约束下的值**，
要降成本只能降 T（重训更小基组）或降 Λ（更好的分解）。

## 补记：提交件 `1ba197b0` 与重建件 `321aff83` 的真实差别

本机只读 kmb 头实测：

```
shipped 1ba197b0 : Q=46  num_bits=388  static_toffoli_like=1550   （198,631 B，SHA 1ba197b0…）
rebuilt 321aff83 : Q=46                static_toffoli_like=1599   （291,626 B）
```

即**提交件比生成器原版少 49 个 Toffoli**（Asterios V5 变换的产物），而不是我此前记的"一个"。
"一个 Toffoli" 是**相对上一版提交**（27.30661 → 27.31193）的增量，两件事不要混。

对 `1ba197b0` 本身跑 `audit_pairs`+`hold_pass` 的检查**未完成**：把 198 KB 文件送进 Kaggle
的两条路都不通（`kaggle datasets create` 无输出/未建成；`download_competition_submission`
返回 `Permission 'submissions.download' was denied`）。该项上限 ≤ +0.05，记为**未验证的缺口**。
