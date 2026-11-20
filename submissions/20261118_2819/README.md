# 2026-11-18 公开 28.19 组合（combo W）

**状态：COMPLETE，public 28.18965，ref `58496528`（2026-11-18T05:38:36Z）。**

## 来源

采用公开 Apache-2.0 组合 W，作者 tiraJoon（junmiaotiao）：

- notebook：`junmiaotiao/qcc-28-19-public-frontier-combo-w` v1
- dataset：`junmiaotiao/qcc-frontier-20261118w`
- 作者记录的公开榜成绩：**28.18965**（ref `58492757`，榜单 86–103 名块）

三条腿：

| 腿 | 件 | Q | 官方/作者验证成本 | 说明 |
|---|---|---:|---:|---|
| invsqrt | `864f81cd` | 44 | **74,490.94707587373** | 官方 verifier 200,540,928 shots PASS；C=1,692.976，33 rotations，eps=2.0054e-13，worst/tol 0.9994556 |
| DQI | `5f901c55` | 890 | **346,404,203,610.1118** | 102,400 shots 0 value / 0 phase；mean T 367,110.166 |
| chem | `4d63be3d` + 15 loaders | 427 | **294,642,170.565169** | 78,080 shots PASS；λ_eff 46.92158337，T=14,706 |

几何平均（本地复算）：**28.189660448**；作者在 salt `notebook-verification` 下的实测 GM 为 28.1896523，榜单 ref `58492757` 显示 28.18965。

## 提交件

- 本地文件：`submission.zip`（不在 Git）
- 大小：50,946,580 B
- SHA-256：`ea55e2a9aac319e67c3d9cdd5930fd439f2abae4b584d0bfe44f3b15cf73e928`
- 18 成员，成员 SHA-256 与 notebook 的 pinned 列表逐项一致。关键成员：
  - `invsqrt.kmb` `864f81cd20489d80e302f48014fcedec3b3fb703122fbcbac41b0bb2a395a859`
  - `dqi.kmb` `5f901c556cafd02dc11641eee7766171a454e3a0b6687d890ff9f99944e1934c`
  - `dfthcsos/submission.npz` `4d63be3d5c26cfa447a3464eeaf515a652814a1dd4c78f1f1af2f5b7d9e9b8b3`
  - 15 个 `dfthcsos/angle_k_*.kmb` 与 notebook pinned 列表一致。

## 对比上一版

| 版本 | ref | invsqrt | DQI | chem | GM |
|---|---|---:|---:|---:|---:|
| 上一版 | `58487952` | 74,560.9069 | 346,409,762,292.72 | 294,643,137.73 | 28.180659 |
| 本版 | `58496528` | **74,490.9471** | **346,404,203,610.11** | **294,642,170.57** | **28.189660** |

增量约 **+0.00900 GM**；主要来自 invsqrt `864f81cd`（−69.96）和 DQI `5f901c55`（−6 T）。

## 来源与归属

- invsqrt `864f81cd`：maoxin123 的 2026-11-18 重跑，原始生成器线归 Syed Asad Ali；44Q 调度归 maoxin123。
- DQI `5f901c55`：Grant Prater 的 merged closings（`575b043f`）+ boristown 的 PW4 补丁（−6 CCX）；上游归 Syed Asad Ali、Hayato Hikawa、James Barlow（manwithacat）、Balram Srinivasan、Atakan Aldemir。
- chem `4d63be3d`：leotang09 的 refit 表 + maoxin123 的 4,022-Toffoli loaders；基础表归 Lera（marculera）。

## 验证范围

- **独立复核已完成**：内核 [`jiyujia/qcc-verify-combo-w-20261118b`](https://www.kaggle.com/code/jiyujia/qcc-verify-combo-w-20261118b) **v2**，`COMPLETE` 2026-11-18T05:52Z，CPU only（`enable_gpu=false`、`enable_tpu=false`），未改动的官方 verifier，默认 salt 与默认 shots。
  - invsqrt `864f81cd`：**74,490.94707587373**，200,540,928 shots PASS，33 rotations，worst/tol 0.9994556。
  - DQI `5f901c55`：**346,404,203,610.1118**，102,400 shots 0 value / 0 phase PASS，mean T 367,110.166。
  - chem `4d63be3d` + 15 loaders：**294,642,170.565169**，78,080 shots PASS，λ_eff 46.921562797，T=14,706。
  - GM 复算 **28.18966044813323**。
- 已提交的 zip 是作者容器 `ea55e2a9…`，其 18 成员内容摘要 `fe9fa7b0…` 与新构建的 `134ceaaa…` 相同；因此上述逐成员官方验证适用于 ref `58496528`。
- 本提交只换件，不改官方 verifier。
- **Kaggle 回执：`COMPLETE`，public score `28.18965`**（ref `58496528`，2026-11-18T05:38:36Z）。榜单四舍五入与本地 GM 28.189660448 一致。
- 2026-11-18T06:40Z 公开榜快照：**rank 149 / 3300**，位于 28.18965 并列块；银线为前 5%（165 名），当前在银线内（06:07Z 为 147）。
