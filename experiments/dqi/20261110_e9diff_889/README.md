# `e9f54be3` −55 差分定位 + SomeJoint 889Q 画像方法（`20261110_e9diff_889`）

日期：2026-11-10；分支 `codex/dqi-research`；工作区 `.worktree/dqi/`。
性质：**纯静态只读**——复用 `20261110_e9diff` 已落盘的静态审计产物，不构建候选、
不运行验证器、不改动 `data/competition` 验证器、不下载大文件、不推送 Kaggle。
本目录是方向 A+B 第一实验的**汇总口径**（差分结论引用已验证产物；889Q 报缺失+方法准备）。

## 0. 计分口径（只读理解，未改动验证器）

- `data/competition/verifiers/dqi/verify_submission_dqi.py`：`score=R(ε+)×Q²×T`，
  `ε+` 为失败率单侧 Clopper-Pearson 上界（`log2_delta=-128`），须 `<1/16`；
  `R(eps)=ln2/-ln(1/2+2√eps)`（`repetition_overhead`）；抽样按
  `optimal_dqi_weights` 主特征向量权重、`seed=SHA256(kmb+salt)` 决定输入与
  `HMR`/`R` 结果，`num_shots` 须为 `batch_size`（默认 256）倍数。
- 定价（`20261110_arch_review` §0/§2 沿用）：静态 −1 门 ≈ 947,843 分（`=R·Q²`，
  默认 salt `R=1.19126046`，`Q²=795664`）；Q ±1 ≈ ±8.41 亿分。

## 1. 假设

- H1：−55 可按 `SEMANTIC` 阶段精确归因到少数新模板，与 −38 谱系（Ozer/Isabe
  字面复用、Kirill HMR 窥孔、Syed 仿射）无交集。
- H2：e9 侧同形残余为 0（closed），frontier 侧同形位点数与改写数精确一致。
- H3：SomeJoint 889Q（`quantum-circuits-22-77-local-gm-889-qubit-dqi`）本地无电路，
  只做方法准备；不同解码器族，不直接对标 T。

## 2. A）−55 差分定位（实测，引用 `artifacts/20261110_e9diff/`）

输入（只读，未复制/修改）：frontier 主仓库
`artifacts/20261108_public_frontier/release/dqi.kmb`
（SHA-256 `4432ec5f…ce431`，892Q，505M）；e9 主仓库
`artifacts/20261110_public_candidates/ozer_v91/submission.zip` 内 `dqi.kmb`
（SHA-256 `e9f54be3…e969bc4`，529,242,404 B；gengsr/Ozer-v91/Maoxin 三包同字节，
`references/public-baseline.json`；作者数静态 395,586，均值 T 395304.76）。

方法：`20261108_frontier_audit/audit_frontier_4432ec5f.py` 口径原样搬运的流式实现
`20261110_e9diff/stage_census.py`（kmx+`INFO_TAG @enter/@exit` 栈顶、`CCX/CCZ/CSWAP/CCX_CARRY` 付费）；
`paid_diff.py` 按阶段付费门序列贪心对齐（11 hunks），`residual.py` 单遍扫描残余。
frontier 侧复算与 `20261108_frontier_audit` 审计表逐项一致。

### 2.1 阶段差分表（`stage_census.json` 实测）

| 阶段 | frontier paid | e9 paid | Δpaid | ΔCCX/ΔCCZ/ΔCSWAP | Δops |
|---|---|---:|---:|---|---:|
| convert | 60,687 | 60,663 | −24 | 0/0/−24 | +48 |
| extract | 59,169 | 59,169 | 0 | 0 | 0 |
| scan | 44,275 | 44,275 | 0 | 0 | 0 |
| synthesis | 31,635 | 31,635 | 0 | 0 | 0 |
| unconvert | 62,558 | 62,534 | −24 | 0/0/−24 | +48 |
| unextract | 96,888 | 96,881 | −7 | −14/+7/0 | −7 |
| unsynthesis | 40,429 | 40,429 | 0 | 0 | 0 |
| **总计** | **395,641** | **395,586** | **−55** | **−14/+7/−48** | **+89** |

`unread_ccx_before_hmr` 两侧均为 0（Kirill 类无新增）；总 ops 58269328→58269417（+89，
与 convert/unconvert 各 +48、unextract −7 加总一致；kmb 大 773 B 方向一致）。
计分换算：−55 门 ≈ −52,131,365 分（≈−0.0139%）；作者分差
374686873086.94−374735446628.53=−48,573,541.59（≈−0.0130%），差约 3.6M 来自均值 T 口径。

### 2.2 差异窗口分类（`paid_diff.json`，n=11，全为新模板）

- 模板 A（CSWAP-双目标测量消除，Kirill 谱系新变体）：4 位点 ×12 对 = **−48 CSWAP**，
  每对净 −1 paid（`CSWAP c x y; HMR x; HMR y` → `CX x y; HMR x; CZ c y if bx; HMR y; BIT_INVERT bx if by`，
  +2 ops/对）。位点 F 行：convert `16137584`、`16287848`；unconvert `42154384`、`42304623`
  （A2/A4 为逆序镜像）；4 位点控制线均为 `q18`。旧侧窗签名 `CX`24+`CCX`1+`CSWAP`12+`HMR`24。
- 模板 B（相位回踢 sandwich 吸收）：7 位点 ×（−2 CCX +1 CCZ）= **−7 paid**，
  `CCX(a,b;t); CZ(c,t); CCX(a,b;t) ⇔ CZ(c,t); CCZ(a,b,c)`（compute/uncompute 对内配对消除，
  非跨位点复用；无 HMR/R；字面已相同无需仿射）。全在 unextract，F 行
  `52712906 / 53305438 / 53862198 / 54381951 / 54864140 / 55308652 / 55715870`，
  新增如 `CCZ q874 q856 q846` 等 7 条。
- 四类旧形态计数：字面复用 0、Kirill CCX-HMR 窥孔 0、Syed 仿射类 0、旧模板复现 0
 （`by_label: 新模板 11`；B2/B6 启发式“字面复用”标签已人工核验更正为同一 sandwich）。

### 2.3 残余（`residual_e9.json` + `residual_frontier_check.json`）

- e9 侧：模板 A 同形（CSWAP 后 80 行内双目标均 HMR 且其间无触碰）**0 处**；
  模板 B 严格同形（`CCX…单CZ(c,t)…同CCX`，t 无其他触碰）**0 处** → closed。
- frontier 侧召回对照：(a)=48（convert 24+unconvert 24）、(b)=7，与改写数精确一致，
  且预测的 7 条 `CCZ a b c` 与 e9 新增逐字相同 → 扫描器召回率 100%，e9 零残余可信。

## 3. B）SomeJoint 889Q 画像：本地缺失 + 方法准备（未下载）

本地搜寻（实测）：`find artifacts -iname *889*` 无命中；`*somejoint*` 仅有
`20261106_high_return_research/public/somejoint_q26*`（= `somejoint/qcc-dqi-892-q26`，
892Q）、`somejoint_898_metadata.json`（= `somejoint/qcc-dqi-898`，898/897 overlay，
本地重建 `Q=897/T=454252`）、`phase_recovery/{somejoint898,prior_backhalf}/`
（`prior_backhalf` 889Q 重建 `T=459792`，`.kmb` 已删，仅 `dqi.build.json`/`verify_4096.json`
保留；`decode_q8q9` 889Q `T=486571`）。**目标电路
`somejoint/quantum-circuits-22-77-local-gm-889-qubit-dqi`（research-map 索引，
正文报告本地 GM 22.77139，带嵌入生成器）本地无 `.kmb`/无解包副本**，
按任务要求不下载大文件，先报缺失。

文献对照画像（非同族，不对标 T；来源 `20261106_phase_recovery/README.md` §2）：
同族 889Q 重建静态 T 高 9–16%（459,792 / 486,571 vs 395,679），−3Q 省约 25 亿分
远抵不过 T 惩罚（400 亿量级）；e9 分阶段 qubit 触及 extract/synthesis/unsynthesis/
unextract 均为 892（`residual_e9.json`），峰值 892 由四阶段共同顶住，无死线——
889Q 是另一解码器族的存在性参考（−3Q 可行但 T 代价高），不是当前族的压缩目标。

方法准备（待授权下载后执行，与 A 同口径，不新增框架）：
`20261110_e9diff/stage_census.py` 仅替换 `FRONTIER/E9` 路径为 889Q kmb，
输出 `Q/各阶段 paid/门类细分/ops/unread_ccx_before_hmr`；再加一次只读画像遍：
extract 是否含 `inverse24`（69×~3910 CCX 量级特征）/`multiply-v`（6×~594 CCX）、
scan 是否 4025 掩码守卫形态、unextract 是否窄返回（无 multiply/inverse 逆块），
对照 `20261109_dqi_decoder_struct` §1 的 frontier 画像表逐项打勾/打叉。

## 4. 算力评估：72-salt（≈7.37M shots）Kaggle 可行切分（仅评估，未推送）

- 实测环境：本工作区 `.venv` Python 3.12.13，PyPI 原生 kickmix 可导入；
  Kaggle CLI `~/.local/bin/kaggle` 2.2.5 可用；`~/.kaggle/access_token_qingyu1232`
  存在（38B，内容不进 Git）；`qingyu1232/qcc-dfthc-train-bundle` 状态 ready，
  内容为 `fastfit.py/slim_train.py/prob_r5.npz/seed_r4.npz/seed_r5.npz`——
  **化学专用，不可复用**，DQI 需新建 dataset（注意 `dqi.kmb` 529MB 未压缩体积）
  + 新 kernel。**未执行任何创建/推送，需用户确认。**
- 切分（公式，非实测耗时）：总量 72 salts × 102,400 shots = **7,372,800 shots**
  （Syed V11 `27→21/72 draws` 口径）；`--salt STR` 逐 salt 独立 seeding
  （`_initial_seed=SHA256(kmb+salt)`），天然可拆为 **72 jobs × 1 salt**
  （或 18 kernels × 4 salts 视排队情况合并）；每 job `batch_size=256` → 400 batches，
  `max_workers=4`（验证器默认并行上限）；只跑 DQI（`--m 4095 --n 70 --degree 12 --r 2016`），
  输出每 salt `(value_errors, phase_errors, mean_T)` 即足，无需回传大文件。
- GPU/CPU：kickmix `Simulator` 为 CPU-bound（验证器走 `ProcessPoolExecutor` 多进程，
  默认 4 workers），**GPU 配额不解决瓶颈**；Kaggle 侧应申请 CPU kernel 并行位，
  GPU 配额（P100/T4 周限额）无需消耗。CLI 无法查询剩余额度（需网页控制台确认），
  故不报具体小时数；本地无 2048-shot wall-time 日志（`baseline_2048shot.stderr` 为空），
  不编造单 shot 小时。先跑 1-salt 试点测速再线性外推 72-salt，才是可确权的做法。

## 5. 验证范围声明

- 本实验**未构建候选、未运行官方验证器**（DQI 102400-shot/4096-shot 全未触发；
  `data/competition` 验证器只读理解、未改动、未调用）。
- A 节数字来源：本工作区 `artifacts/20261110_e9diff/stage_census.json`、
  `paid_diff.json`（人工核验修正）、`residual_e9.json` + `residual_frontier_check.json`；
  作者数引用主仓库 `references/public-baseline.json`、
  `submissions/20261110_gengsr_252268/README.md`（作者日志 DQI 374686873086.94，
  0/0 失败，本机未重跑）。
- B 节：本地缺失为实测 `find` 结论；889Q 重建数引用
  `20261106_phase_recovery/README.md` §2 与 `dqi.build.json`/`verify_4096.json`；
  research-map 链接仅作索引引用，未下载。
- 环境：本工作区 `.venv`（Python 3.12，PyPI 原生 kickmix）；中间 kmx 落盘
  `/private/var/folders/.../T/dqi_e9diff/`（非仓库）。
- 凭据/token/签名 URL 绝不进 Git（token 仅 `cat` 存在性确认，未打印内容）。
