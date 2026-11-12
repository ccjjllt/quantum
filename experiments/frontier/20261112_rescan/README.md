# 2026-11-12 公开前沿复扫：11-11 之后的新增件

日期：2026-11-12（北京时间，22:37–22:55；UTC 14:37–14:55）
范围：**2026-11-11 00:00 UTC 之后新增/更新**的公开 notebook、dataset，重点为
2026-11-12 07:48 UTC（上一次 459 行 manifest 的截止点）之后的条目。
目标：找声称 27+ / 28+ 的公开 portfolio，或能带来 ≥20% 单任务改进的组件。
不重复 459 行 manifest 的逐件重扫；只对 07:48 之后的新件做独立核验。

## 结论（先给判决）

1. **没有任何公开件声称 26.0 以上。** 对赛事 400 个 kernel 的标题做了完整枚举
   （`kernels list --competition ...` 4 页 ×100，按 lastRunTime 排序），标题中出现
   26.0–39.9 分数的为 **0 个**；dataset 标题中的最高分是 **25.405**。
   公开榜首 29.74602（11-12 更新为 29.76123，Entangled Team），但无任何公开电路/数据释出。
2. **07:48 UTC 之后唯一新的独立解码器件是 `maoxin123/qcc-dqi-392k-toffoli-decoder`**
   （dataset 14:02 UTC）；另有 eae 的 133-T 微改 `8eccde65`（GM +0.011%）。
   maoxin 件官方 verifier 本机全量 102,400 shots **PASS**：
   892Q、mean T=392,016.27、1 次 value error、R=1.19673、
   cost **373,276,386,859.62**。同 salt 下 eae396ba 是 0/0、
   **373,534,964,860.20**，新件仅低 **0.069%**；即使按 0 失败重算也只低 0.526%
   （GM 25.44953，+0.176%）。**远低于 27+，不值得构建/提交。**
3. 其余 11-12 新件全部是 25.40–25.41 plateau 的复制或微改：
   `pramitdas/qcc-public-frontier-25-405` 与 `ghazarosbarseghyan91/vqcc-combo-candidates`
   经 SHA 核对就是**我们的现三件**；`knightfork/areebbb` 的 25.40767 是 eae + 133 个
   保留 AND（DQI −133 T，GM +0.011%）；`attabeezy` 的 invsqrt 精度重调把官方基线
   cost 降 2.93%（2,076,774→2,015,912，GM +0.996%），但依赖基线 26.8% 的误差余量；
   我们的 9c708f7b worst/tol=0.99932（余量 0.07%），该截断不可移植。
4. 公开化学空间仍饱和：Atlas 的 338 个 family 中，15-loader family 的最小
   static T 和是 **4,089**（就是我们的 14,840 件），2,274 个 (npz, table) 组合里
   通过准确率门的最低 λeff 是 **46.874651**（我们 46.907378，仅低 0.07%）。
   公开化学的现实下限约 **297.0M**；27.0 需要 247.6M（−16.7%），公开件到不了。

**因此：本轮没有值得构建的公开组件；没有 27+ 公开件；三件维持现状。**

## 扫描方法与证据

工具：`~/.local/bin/kaggle` 2.2.5，token 取自 `~/.kaggle/access_token`（不落盘）。
数据只下载单文件或小索引；大件（4.8GB 公共 circuits、473MB Atlas）不整包下载。

| 查询 | 结果 |
|---|---|
| `datasets list -s vqcc/qcc/"quantum circuit"/"quantum compilation" --sort-by updated` | 42 个去重 dataset，11-12 新增 4 个（见下表） |
| `kernels list --competition google-verifiable-quantum-circuit-compilation --sort-by dateRun`（4 页共 400 条） | 11-10 之后 60+ 条，逐条标题筛查 26+ 分数，0 命中 |
| `kernels list -s "entangled"/"29.7"/"GM 27"/"LB 27"/"27.0"/"28.0"` | 无相关公开释出 |
| `asteriospanoras/qcc-circuit-atlas` 的 `circuits.csv`/`families.csv`/`sources.csv` | 1,719 个去重文件、338 个化学 family、133 个来源；作为新件索引交叉核对 |

11-12 新增/更新的公开项（UTC）：

| 时间 | 公开项 | 内容 | 判定 |
|---|---|---|---|
| 11-12 02:25 | `matousakura/best-of-public-portfolio` | 自报 24.67x 的组合与收据 | 低于现三件，略过 |
| 11-12 07:48 | `manwithacat/vqcc-apache-public-circuits` | 上一次 459 行 manifest 的截止版本 | 已扫过，不重复 |
| 11-12 09:49/13:52 | `areebbb` / `knightfork` 的 “Product Retention … LB 25.40767” | eae + 133 retained products（`8eccde65e8b7`），自报 cost 373,408,958,733（0 失败） | DQI −0.034%，GM +0.011% |
| 11-12 10:11 | `infnitycoder2009/invsqrt-edit-search` | 在 9c708f7b 上贪心删 24 门，单 seed metric 1219.5674→1217.1642 | 与此前证伪的 `cand_dead22` 同类，未采信 |
| 11-12 11:38 | `attabeezy/gq-invsqrt-precision-retune` | 官方基线 2,076,774→2,015,912（invsqrt −2.93%，GM +0.996%） | 不是我们电路；余量不可移植 |
| 11-12 13:31 | `asteriospanoras/qcc-circuit-atlas` | 54 invsqrt、51 DQI（仅元数据）、1,342 loaders、272 factorizations 的索引 | 索引，非新电路 |
| 11-12 13:37 | `ghazarosbarseghyan91/vqcc-combo-candidates` | 三件组合，license `other` | SHA 核对＝我们的现三件 |
| 11-12 13:49 | `pramitdas/qcc-public-frontier-25-405` | 自报 25.405 | SHA 核对＝我们的现三件 |
| 11-12 14:02 | `maoxin123/qcc-dqi-392k-toffoli-decoder` | 单个 `dqi.kmb.xz`，license CC0-1.0，无生成器源码 | **唯一新的独立组件**，见下 |

## 新 DQI 392k 的独立评分

文件与哈希（下载到 `artifacts/20261112_frontier_rescan/dqi392k/`）：

- `dqi.kmb.xz` 11,271,588 bytes，
  SHA-256 `8449cfc87366ab3ff4eaf632d653fd88507ee1155c46ac92b818c24ccd9c9a55`
- `dqi.kmb` 518,776,865 bytes，
  SHA-256 `4c81b7263c0b4856068a691295d945ae627aa6af4e62e45f2c40411b6d01e5d9`
- 结构：892 qubits、101,418 classical bits、4,165 registers；
  static Toffoli-like **392,346**（CCX 378,884 + CCZ 1,444 + CSWAP 12,018）。
  对照 eae396ba：892Q、static 401,313、mean 394,089.46。
  这是结构性不同的解码器，不是同一件的微调：条件栈 16,425→5,155、
  HMR 87,382→78,591、CCX 386,058→378,884、CSWAP 12,012→12,018。
  dataset 只有 KMB 字节，没有 notebook/生成器；作者名下也没有对应 kernel。

官方 verifier（未修改，`scripts/manual_verify.py dqi`，默认 m=4095/n=70/degree=12/r=2016，
102,400 shots，salt `frontier-20261112`）：

| 件 | 结果 | mean T | R(ε+) | value/phase errors | cost |
|---|---|---:|---:|---|---:|
| `eae396ba`（现件，同 salt） | PASS | 394,089.4628 | 1.1912605 | 0 / 0 | **373,534,964,860.20** |
| `maoxin` 392k（同 salt） | PASS | **392,016.2651** | 1.1967315 | **1 / 0** | **373,276,386,859.62** |
| `maoxin` 392k（假设 0 失败） | — | 392,016.2651 | 1.1912605 | — | 371,569,932,665.12（推算） |

即 T 确实低 **0.526%**，但本次 salt 抽到 1 次 value error，R 从 1.19126 抬到
1.19673（+0.459%），净只低 **0.0692%**。若换 salt 抽到 0 失败，净低 0.526%。
两种情形都不改变结论。

同一 salt 的本地 GM（用精确参考 cost 与本仓库三件）：

```text
现状（eae 同 salt） : 25.40482676
maoxin 392k（实测）  : 25.41069159   (+0.023%)
maoxin 392k（0 失败）: 25.44953217   (+0.176%)
```

参考 cost（用户提供，已用 sample submission 独立验证）：
invsqrt 2,076,774.2337；DQI 24,439,463,583,672.93；chem 3,355,599,588.3155。

## 为什么 27+ / 28+ 在公开空间内不可达

单任务需要的最小改进（GM 按三项几何平均，其余两项不变）：

| 目标 GM | 单任务 cost 需除以 | chem | invsqrt | DQI |
|---|---:|---:|---:|---:|
| 27.0 | 1.2004× | 247.6M | 77,935 | 311.2e9 |
| 28.0 | 1.3388× | 222.0M | 69,879 | 279.0e9 |
| 29.76123 | 1.6077× | 184.9M | 58,193 | 232.3e9 |

对照公开最好件：

- **invsqrt**：`9c708f7b` 93,555.26（62Q）。Atlas 54 件里 static T 更低的只有
  82Q 的 `5482422b1c0f`（1,359），其余全部 ≥1,375（62–63Q 的 1,377–1,405），
  Q 或 mean T 都更差；没有 77,935 级候选。
- **DQI**：公开最低 mean T 是本次 392,016（892Q）；次低 eae 394,089。
  27.0 需要 mean T ≤328,324（−16.2%），公开件差 19%。
  51 个 Atlas DQI 件的 static 最低是 cd71 394,698，也都高于新件。
- **化学**：15-loader family 最小 static 和 4,089；通过准确率门的 λeff 最低
  46.874651（对比 46.907378）。2,274 个组合里 λeff=46.4275 的那行
  E_gap=3.733 < 3.914898 且 e1=75.8 mHa，**不通过**；即使用它的 λeff
  配我们现有 T/Q 也只有 294.2M（−1.0%），仍远不及 247.6M。
  现实下限 ≈297.0M；247.6M 需要 λeff ≈39.2 或等价减行，公开件不存在。

## 值不值得构建

- **maoxin DQI 392k：不值得。** 最好情形 GM +0.176%（25.4495），实测同 salt
  +0.023%；低于 DQI salt 重抽的量级（单次 value error 就 +0.46%），且只有 KMB 字节、
  没有生成器源码（不符合获奖的“可复现生成器”要求）。换 SHA 还会重抽 salt。
- **8eccde65（133 retained products）：不值得。** −133 T = GM +0.011%。
- **attabeezy invsqrt 精度重调：不适用于我们。** 它把官方基线 cost 降 2.93%
  （GM +0.996%），靠的是基线 worst/tol=0.732 的 26.8% 余量；9c708f7b 的
  worst/tol=0.9993238，余量只有 0.07%，再截位会直接越界。即使能移植，
  3% 单任务也只换 GM +1.0%。
- **invsqrt-edit-search：不采信。** 单 seed 贪心删门；本仓库已实测同类
  `cand_dead22`（22 个候选只有 3 个过多 salt 复核、Δ=0.000 分）官方全量 FAIL，
  方法学会把“当前 salt 未触发的条件门”误判为死门。
- **化学：没有新件。** J 批量、R=7、coded2、tree/group 重选仍在各自工作区
  独立推进，不属于公开扫描结论。

## 复现命令

```bash
# 1) 新 DQI 下载与哈希
KAGGLE_API_TOKEN=$(cat ~/.kaggle/access_token) \
  ~/.local/bin/kaggle datasets download \
  -d maoxin123/qcc-dqi-392k-toffoli-decoder \
  -p artifacts/20261112_frontier_rescan/dqi392k --unzip
shasum -a 256 artifacts/20261112_frontier_rescan/dqi392k/dqi.kmb*

# 2) 官方全量验证（salt 仅本地复现用，不是线上 salt）
.venv/bin/python scripts/manual_verify.py dqi \
  artifacts/20261112_frontier_rescan/dqi392k/dqi.kmb --salt frontier-20261112
# 对照件
unzip -p submissions/20261112_14840/submission.zip dqi.kmb > /tmp/eae.kmb
.venv/bin/python scripts/manual_verify.py dqi /tmp/eae.kmb --salt frontier-20261112

# 3) Atlas 索引（只取 CSV）
KAGGLE_API_TOKEN=$(cat ~/.kaggle/access_token) \
  ~/.local/bin/kaggle datasets download -d asteriospanoras/qcc-circuit-atlas \
  -f circuits.csv -p artifacts/20261112_frontier_rescan/meta --unzip
```

## 验证范围（不要混用口径）

- 新 DQI 与 eae 对照：**本机官方 verifier、102,400 shots、salt `frontier-20261112`、
  全量 PASS**。这不是 Kaggle 线上 salt，也不构成线上分数。
- invsqrt 新件、8eccde65、attabeezy、invsqrt-edit-search：**只读 claimed 数字，
  本轮未跑官方 verifier**。它们均未达到需要深入验证的 27+ 门槛。
- 化学：本轮没有新 family 需要跑；引用的 297,237,044.95 来自
  `artifacts/20261112_frontier/chem14840/`（既有 78,080-shot 全量 PASS 记录），
  Atlas 的 family/λeff 数字来自其 CSV 索引，不是本轮重新模拟。
- 未执行：Kaggle 提交、push、任何现有代码修改。

## 下一步

1. 公开扫描线**暂停**：没有 27+ 公开件，25.40–25.41 的复制/微改不再花时间。
2. 若要继续追 27+，只剩两条私有级杠杆：DQI mean T ≤328.3k（或 Q<892 的合法
   重构），化学 ≤247.6M（新 factorization/训练范式）。两者都不是公开件能给的。
3. 监控点：Entangled Team 是否释出生成器/数据；`manwithacat` 聚合集下一次
   manifest 更新（若出现 26+ 的新 SHA，再按本流程复核）。

## 2026-11-13 补充：Kaggle MCP 复核（公开前沿与排行榜）

用 Kaggle MCP 的 `search_notebooks`、`search_datasets`、`get_competition_leaderboard`、
`get_dataset_info`、`list_dataset_files`、`download_dataset` 重查，结论不变。

### 公开 notebook

- 最高公开分是 **25.40767 / 25.40768**，来源：
  - `areebbb/product-retention-133-free-toffolis-lb-25-40767`（及 Knight Fork 同件）
  - `kirilltym/quantum-circuits-retained-product-audit`（审计 Alex Chilton V142，25.40768）
- 它只是在我们的三件上把 DQI 换成 **`8eccde65` = `eae396ba` + 133 个 retained
  products**；invsqrt 仍是 `9c708f7b`，chem 仍是 `5d5007a75784`。官方 cost：
  DQI 373,408,958,733（零失败），比我们的 eae 少 0.0337%。
- **没有 26+/27+/28+ 公开方案。** 搜索 `LB 26/27/28/29` 只返回旧标题和
  25.x 组合；公开 plateau 仍是 25.40–25.41。
- 该 notebook 自己说明：本地空 salt 只打印 **25.3689**，因为 DQI 的 102,400-shot
  draw 会随机出现 0/1 次失败；25.40767 是公开 split 抽到 0 失败的 badge。
  1 次失败约 −0.039，大于 133 Toffolis 的 +0.0029。最终 private 会重新抽签。

### 公开聚合集 `manwithacat/vqcc-apache-public-circuits`（v122，2026-11-12 07:48）

从 `manifest.csv` 正确解析（459 条：DQI 90、invsqrt 77、chemistry 292）：

| 任务 | 公开最佳 | 作者 / SHA | 与我们的件 |
|---|---|---|---|
| invsqrt | **93,555.2627** | Asterios Panoras, `9c708f7b9abc…` | **就是我们当前件，SHA 逐字节一致** |
| DQI | **373,856,548,625** expected（零失败 373,534,939,341） | Atakan Aldemir, `eae396baf0fa…` | **就是我们当前件，SHA 逐字节一致** |
| chemistry | **297,237,044.9509761** | tiraJoon, `5d5007a75784…` | **就是我们当前件，family SHA 逐字节一致** |

- `parts/assembly_best.json` 明确：最佳公开化学 assembly 就是 **`5d5007a75784`**，
  `lambda_eff=46.907378146123214`、`T=14840`、`Q=427`、`verified_cost=
  297237044.9509761`、`verified_status=PASS`。
- 公开 frontier GM（dataset 快照 2026-11-12 07:12）为 **25.39754**，排名约 249；
  我们的 public **25.40482** 已高于该快照。加上 retained-product DQI 的公开
  最高也只是 25.40768，仍只 +0.00286。

### 排行榜（2026-11-12 14:13 UTC 后）

| 排名 | 队伍 | public |
|---:|---|---:|
| 1 | Entangled Team | **29.90871** |
| 2 | Schrödinger’s cat lived | 29.76123 |
| 3 | yicheng guang | 29.02209 |
| 4 | taiseiu | 28.68861 |
| 5 | Some Joint | 28.65116 |
| 10 | trust the transpiler | 27.52478 |

这些是排行榜成绩，**没有对应公开电路/生成器**。公开可复现 frontier 仍约
25.41；到 27+ 的差距只能靠私有级 DQI/化学突破，不能从公开件组合得到。
