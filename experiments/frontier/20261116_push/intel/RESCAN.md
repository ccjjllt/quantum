# RESCAN — 2026-11-16 08:30–09:45 UTC

增量侦察（接 `RESULT.md`）。只读，无重计算。结论：**没有新的公开件超过 28.09486**；
公开天花板仍是 `f2cdab0b` + `ccc2ab84` + `bdae290f`（raw 28.0948754）。
但榜面变了，我们把并列带撑大了并且**没有拿到银位**，见 §2。

---

## 1. 窗口内新/更新的 notebook 与 dataset（全部逐字节核过）

`kaggle kernels list --sort-by dateRun`（page 1，过滤 2026-11-16 08/09 时）：

| 时间 | 对象 | 实际输出 | 判决 |
|---|---|---|---|
| 09:36 | `aiokajima/quantum-alex-2809486-reproduction-public` | submission.zip **51,854,649 B**，archive sha `4ff192a5…`；成员 `f2cdab0b` / `ccc2ab84` / `bdae290f` | alexchilton 28.09486 的**逐字节搬运复现**（其正文自述 “Byte-identical transport reproduction”，提交 58424123）。无新组件 |
| 09:05 | `ozertuu/quantum-ai-fast-runner-starter-notebook`（重跑） | submission.zip **56,360,753 B**；成员 `1ba197b0` / `821bf8d1` / npz `3b7d0cd9` | 仍是 27.31 时代旧包，无新组件 |
| 09:39 | `yorixum/quantum-circuits-iso-gap-dqi-h5`（重跑） | submission.zip **850 B** | 占位/从未跑通（旧 `NameError` 笔记本） |
| 08:59 | `radheshversharma/notebook77dad68819` | 输出只有 `.virtual_documents` + 800 B 日志 | 无提交文件 |

`kaggle datasets list -s qcc --sort-by updated`：**08:01 之后没有任何 dataset 更新**
（最新仍是 `junmiaotiao/qcc-frontier-20261116n` 08:01、`drpatrickchan/qcc-chem-sub1-weights` 07:42）。

```text
aiokajima zip  sha256 4ff192a5a34b73fd…   （boristown 同件是 8bc371be…，仅压缩/成员序不同）
  invsqrt.kmb            f2cdab0b7afc
  dfthcsos/submission.npz bdae290f5d6b
ozertuu 0905 zip 56,360,753 B
  invsqrt.kmb            1ba197b02771
  dqi.kmb                821bf8d157c0
  dfthcsos/submission.npz 3b7d0cd9068d
```

→ **08:30–09:45 没有任何 chemistry < 294,762,600、没有 DQI Q<890 且 T<368k、没有 invsqrt < 75,006 的新件。**

## 2. 榜面变化（09:41:09 快照，3160 行）

| 指标 | 08:01 | 09:41 |
|---|---:|---:|
| 28.09486 并列队数 | 143（rank 88–230） | **187（rank 93–279）** |
| 28.09487 | 0 | **1（rank 92，`Johnny` / jonathanabuelouf）** |
| 28.09498 | 1（rank 87） | 1（rank 91，`gcyyfun`） |
| >28.0949 的队数 | 87 | **91（+4）** |
| 我们 | 28.09090（rank 273） | **28.09486（rank 188）** |


**08:01 快照之后榜面上出现/提高的队（逐条 diff 两个快照）**：

| 队 | 新分 | rank | 提交时间 | 08:01 时 |
|---|---:|---:|---|---|
| Furkan Pirinc | 28.11289 | 58 | 07:50:09 | 未结算（不在 >28.0949 组） |
| ZihangL1 | 28.10585 | 65 | 08:25:19 | 未结算 |
| tanadai | 28.10036 | 68 | 07:49:52 | 未结算 |
| EyobAleB | 28.09753 | 79 | 08:16:42 | 未结算（原在 28.09486 带内） |
| Jongwon | 28.16800 | 25 | 08:13:20 | 28.15181（+0.016） |
| m&m | 28.14597 | 34 | 08:14:00 | 28.11392（+0.032） |
| Hiểu Vy | 28.10179 | 67 | 08:40:32 | 28.09638（+0.005） |
| Apoorv Saraogee | 28.11137 | 61 | 08:01:03 | 28.10733（+0.004） |

其中**落在 08:30–09:45 窗口内的真实提分只有 1 次**（`Hiểu Vy` 08:40:32 → 28.10179，+0.005）；
其余是 08:01 快照后、08:30 前提交或结算的。全部落在 28.097–28.168，**没有一个人跳到 28.3/28.5/29+**。

把它们换成单件等效（相对公开天花板 28.09486）：

| 队 | 分 | 成本需降 | chem T | loader 门/pass | DQI T | λ_eff |
|---|---:|---:|---:|---:|---:|---:|
| EyobAleB | 28.09753 | −0.029% | −4.2 | **−2.1** | −105 | −285 ppm |
| tanadai | 28.10036 | −0.059% | −8.6 | **−4.3** | −216 | −587 ppm |
| Hiểu Vy | 28.10179 | −0.074% | −10.9 | **−5.5** | −272 | −740 ppm |
| ZihangL1 | 28.10585 | −0.117% | −17.3 | **−8.7** | −432 | −1174 ppm |
| Furkan Pirinc | 28.11289 | −0.193% | −28.3 | **−14.2** | −709 | −1925 ppm |

注意 λ 那一列：公开同一 T 的 9 个条件 λ 跨度只有 **129 ppm**，所以 285–1925 ppm 的 λ 改动
**不可能**靠 refit 得到。这几支队只能是 **loader 少 2–14 个门/pass**（或 DQI 少 105–709 T）。
也就是说：**榜上这几支队等效于把 chemistry loader 从 4,025 往下推了 2–14 个门**
（都是私有件，没有公开）。这和 §3 的“一个门 = +0.00127 GM”完全对得上，
也说明 loader 这条轴在别人的私有实现里还有货——尽管公开 4,025 已被证明 0 可删门。

我们的最新提交是 **ref 58424363（09:06:57）**：`f2cdab0b` + `ccc2ab84` + **`sub1`** chem
（294,762,697.44），COMPLETE **28.09486**。两点：

1. 并列带在 1.7 小时内从 143 队涨到 187 队，**银线 rank 156 仍在带内**，而我们被排在 188，
   所以这次提交**没有拿到银位**。带内排序不是纯时间序（rank 191/192 是 02:32 的老提交，
   rank 93 是 07:45），机制未知；但 187 队同分时，**谁在里面排第几基本是平台内部排序**，
   不是我们能控制的。→ 结论不变：必须严格高于 28.09486。
2. `sub1` 比 `bdae290f` 贵 65.36（≈2.1e-6 GM），但带内宽度 ~1e-5，**换 `bdae290f` 也不会改变显示**
   （raw 28.0948754 → 在公开 salt 下仍是 28.09486）。所以上一轮没换错，但也没赚。

## 3. 差多少才能出带（这是本轮唯一的新情报）

以我们 raw≈28.094860（公开 salt）为基线：

| 目标 | 需要的成本变化 | 等价单点 |
|---|---:|---|
| 28.09487（rank 92，`Johnny`） | −3.6e-7 | **chemistry λ_eff −1.1 ppm**，或 DQI T −0.39，或 invsqrt −0.002 门 |
| 28.09498（rank 91） | −4.3e-6 | λ −12.8 ppm，或 DQI T −4.7，或 invsqrt C −0.022 门 |
| 28.0961（≈rank 88） | −4.4e-5 | **chemistry T −1.95（≈一个 Toffoli = 2 T）**，或 λ −132 ppm |

（相对量 = 3·ΔGM/GM；λ 是 λ_eff 的相对变化，T 是总 T 的绝对变化。）

- **一个 chemistry Toffoli（T−2）就值 +0.00127，直接到 rank ~88**，但 `mizeroluckygall`
  的精确扫描已证明当前 15 个 loader **0 个可删门**（correct dirty-word 模型），
  所以这一档只能换 loader/表，不能清理。
- 出带最小的一步是 **λ refit ≥1.1 ppm**：T=14,712 这一族公开 9 条件的 λ 跨度是 **129 ppm**
  （46.9216024 … 46.9276435），最好的一条恰好是我们/boristown 的 46.9216024。
  也就是说，**rank 85–92 这一段很可能全部是 chemistry 权重 refit 的 ppm 级差别，不是新电路**。
  风险：error_1/error_2 已经贴在 0.0199999985（余量 1.5e-9），λ 与误差是此消彼长，
  1.1 ppm 是否还在可行域内未知。
- DQI 方向的单点更贵：−1 个 Toffoli（平均 T−1）值 +2.5e-5（2.5 个显示单位），已经越过 rank 92；
  Atakan 08:06 的 joint226 四段扫描对 `ccc2ab84` 是 0 saving。

## 4. 判决

1. **没有新公开件**：08:30–09:45 的 4 个更新全是复现/占位，公开上限不变。
2. 唯一在 1 小时内新出现的“比我们高”的队是 `Johnny`（28.09487，rank 92），
   **没有任何本赛题公开 notebook**（`kernels list --user jonathanabuelouf` 只有 2023 年的
   一个无关 kernel），无法核对组件；差值只有 1e-5，属 ppm 级 refit 量级，不像结构改动。
3. 我们已在公开天花板上（28.09486），但要银位必须**再挤出 ~1.1 ppm λ 或 1 个 DQI Toffoli（+0.000025）**；
   这两条都不是“再换一个公开包”能解决的，公开空间已经到底。

## 5. 证据路径

```text
artifacts/20261116_intel/lb2/google-...-publicleaderboard-2026-11-16T09:41:09.csv
artifacts/20261116_intel/kernels/aiokajima_quantum-alex-2809486-reproduction-public/
artifacts/20261116_intel/outputs2/aiokajima_.../submission.zip        51,854,649 B
artifacts/20261116_intel/outputs2/ozertuu_0905/submission.zip         56,360,753 B
artifacts/20261116_intel/kernels/radheshversharma_notebook77dad68819/
```
