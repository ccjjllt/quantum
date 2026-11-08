# 2026-11-08：公开前沿组合提交（25.14222 基线）

按用户要求检查 Kaggle 最新最高分公开方案并提交一次，同时将该公开组合更新为当前研究比较基线。

## 来源与归属

- 固定公开 notebook 输出：[Alex Chilton v126 / run366869858](https://www.kaggle.com/code/alexchilton/24-94-lb-verified-three-task-portfolio?scriptVersionId=366869858)（同组合亦由 [Hosen42 v7](https://www.kaggle.com/code/hosen42/vqcc-our-submission) 与 [Özer v25](https://www.kaggle.com/code/ozertuu/25-137-starter-notebook) 发布）。
- 作者公开提交 `58121501`（team `alex chilton`）与 `58120775`（team `Hack2Publish` / Hosen42）在公共排行榜的实际 Public Score 均为 **25.14222**（由 Kaggle MCP `list_team_public_submissions` 确认；不是本账号本次实时成绩）。
- 本账号 `ccjjllt` 提交 **58123354**，API 返回 `Successfully submitted`；创建时间 `2026-11-08T09:59:12.773Z`（北京时间 `2026-11-08 17:59:12.773`）。
- 创建后只读回一次，平台确认 `submission.zip`（28,076,689 bytes）。同时在提交前去重检查中被动读回上一次提交 `58041132`（Syed V9）状态为 `COMPLETE`，本账号实际 Public Score 为 **24.94081**。

## 18 个成员文件与上游演进链

原始 `submission.zip`（SHA-256 `baf4639dd948f32fc40cea98ec13f8ac7cc8e9b837c94e373890b717da6199ec`，28,076,689 bytes，解压后 536,897,239 bytes）未做任何字节修改直接上传：

1. **`invsqrt.kmb`**（547,775 bytes，SHA-256 `7c10edbac5835e441fe8f40782bd7dbc7b36834718c3a4e3509607a9d2a454d3`）：
   - 62Q，上游报告成本约 **95,430.78–95,430.98**（相比 Syed V9 的 97,747.22 降低约 2,316.4 分 / 37.36 等效 Toffoli）。
   - 演进链：Syed V10/V11（基于 mrmeows → busyaprime → yoyobar）→ Maoxin V3（`95621d7e`，q57/q61 测量前移）→ Kirill V22（移植 Hosen V4/V5 的进位擦除 carry erasure）+ Atakan V2（删除定义域冗余 `CSWAP q23 q6 q28`）得到 Özer V15 / Kirill V23 的 `13b5bf7a`（成本 95,492.96）→ Hosen42 V6（将 `HMR q25 b0` 之后到读取前的 2 CCX + 9 CX 只写段坍缩为 1 个 CCX + Clifford）得到 `7c10edba`。
2. **`dqi.kmb`**（529,241,631 bytes，SHA-256 `4432ec5fd63d7d70aab92d32f719d47539d0ff66ae0cb0b964c914e01fece431`）：
   - 892Q，静态 Toffoli-like 395,641，上游报告默认 salt（0 错误）成本 **374,735,446,628.53**（相比 Syed V9 的 3.747724e11 减少约 38 个平均 Toffoli）。
   - 演进链：Syed C1 解码器（基于 jday96314 / SomeJoint / Ali Haydar Özdağ）→ Atakan & MAIDANG 乘积复用 → Ahmed Berat Özer V5 `77bace9d` → Kirill V21 `337cb049`（14 处测量顺序恒等式改写）→ Isabe11aM00re V12 `4432ec5f`（新增 3 条乘积缓存路由，共 6 处有序流补丁，以 X 测量 + 条件 CZ 擦除）。
3. **`dfthcsos/submission.npz`**（1,847,692 bytes，SHA-256 `c1321df252e15ccd92f5086048ad6e4c376862bec5a4dd58d603edbbc3623cf1`）及 **`dfthcsos/angle_k_0..14.kmb`**：
   - 15 个 `angle_k_*.kmb` 与 Syed V9 字节完全相同（SHA-256 见 `artifacts/20261108_public_frontier/submission_receipt.json`）。
   - `submission.npz` 为 Maoxin123（`lb-25-14-public-frontier-refit-chem-weights` V2）在固定 Syed V9 `(8, 143, 44)` 角度字和树结构下，经 Isabe11aM00re、James Barlow `dfthc_refit`（active-set、gauge、二阶流形轮次）重拟合的 `W` 与 `H2_I`：$\lambda_{\text{eff}} = 46.8912755$，上游验证成本 **299,657,851.81**（比 Syed V9 的 299,673,103.43 低 15,251.62 分）。

## 验证范围

- 本次提交直接采用公开前沿原包，已核对 18 个成员文件的 SHA-256 与公开前沿笔记本一致；提交前未在本机重跑全量官方验证器。
- 后续各子任务工作区（`invsqrt`、`dqi`、`dfthcsos`）的独立审计、局部验证与进一步降本实验分别记录在各分支。
