# DQI 1-salt 试点 + 889Q 下载画像（`20261110_r1salt`）

日期：2026-11-10；分支 `codex/dqi-research`；工作区 `.worktree/dqi/`。
用户已批准：DQI 1-salt 试点（CPU kernel，不烧 GPU 配额）+ 889Q 下载画像。
只跑 1-salt；未批准推 72 全量；不提交 competition、不 push git remote。

## A) 1-salt 试点（CPU kernel，进行中）

- 电路：e9 `dqi.kmb`（主仓库 `artifacts/20261110_public_candidates/ozer_v91/submission.zip`
  内 `dqi.kmb`；529,242,404 B；SHA-256 `e9f54be3…e969bc4`；本地暂存
  `/tmp/dqi_1salt_stage/dqi.kmb` 已验 SHA 一致）。
- 数据集（新建私有）：`qingyu1232/qcc-dqi-e9-1salt`，内容 =
  `dqi.kmb` + `run_1salt.py`（最小跑脚本：调同目录 `verify_submission_dqi.py`
  副本的 `verify()`，ProblemSpecDQI 默认 `m=4095,n=70,degree=12,r=2016`，
  `--salt 1个、102400 shots、batch 256、max_workers 4`，输出 value/phase errors +
  mean_T + wall 秒）+ `verify_submission_dqi.py`（官方验证器未改动副本）。
- 烟测（本地，本工作区 `.venv`，PyPI 原生 kickmix）：
  `run_1salt.py --num-shots 256 --batch-size 256` → 0/0 errors，
  `effective_error_rate=0.2929 >= 1/16` → FAIL（符合预期：256 shots 在
  `log2_delta=-128` 下置信不足；脚本通路正常），`load 0.29s / wall 1.32s`
  （仅 256-shot 通路验证，不作外推依据）。
- 状态：数据集 `create` 已提交（后台上传 529MB 中）；kernel 待建
  （`enable_gpu=false, internet true, dataset_sources` 指向新 dataset）。
  kernel push 后轮询（间隔≥120s，最多60分钟），COMPLETE 后取日志回填下节。

### A.1 实测与外推（待 kernel COMPLETE 后填）

- 单 salt 实测：value_errors=__ / phase_errors=__ / mean_T=__ / wall=__秒。
- 72-salt 外推：__小时（线性 ×72；总量 7,372,800 shots）。
- 费用/排队观察：__（CPU kernel，不耗 GPU 配额；排队 __ 分钟）。

## B) 889Q 画像（实测完成，本地）

目标：`somejoint/quantum-circuits-22-77-local-gm-889-qubit-dqi`。
`kernels output -p /tmp/889q_out` 成功取回 `submission.zip`（27MB，
archive SHA `e6d44b…9cdf`）+ `summary.json` + `submission-members.sha256`；
`kernels pull` 同 ref 报 404（`GetKernel: Not Found`），源代码/嵌入生成器未拿到——
只报实测：本次画像基于 output 的 `.kmb`，无生成器。

- 解包 `dqi.kmb`：529,710,680 B；SHA-256
  `993c70386a3dde6664ecea36315db3aa60fb18a96dc714a18160cae3472378db`
  （与 `submission-members.sha256` 一致）；落盘
  `artifacts/20261110_e9diff_889/dqi_889q_993c7038.kmb`（大文件，gitignored，不进 Git）。
- 官方自带成绩（`summary.json` 实测引用，未重跑）：DQI
  `score=375373377713.41`，`verified_shots=102400`，`value=0/phase=0`，
  `R=1.19126046`，`mean_T=396918.49`，`max_T=397191`，`Q=891`，
  `num_ops=58336065`，`reaction_depth=5866`。
- **标题与实测不符**：kernel 标题称 889-qubit，但 `num_qubits=891`
 （summary.json 与本机 kickmix `Circuit.from_file` 一致）；GM 22.77139 系正文报告值。

### B.1 同口径阶段 census（`census_889q.py`，与 `20261110_e9diff/stage_census.py` 同口径）

`artifacts/20261110_e9diff_889/stage_census_889q.json`；Q=891；
total paid **397,191**（= 官方 max_T 397,191，吻合）；total ops 58,318,189；
`unread_ccx_before_hmr=13`（frontier/e9 均为 0）。

| 阶段 | 889q paid | frontier paid | Δpaid | 889q 门类（CCX/CCZ/CSWAP） | frontier 门类 |
|---|---|---:|---|---|
| convert | 60,796 | 60,687 | +109 | 55947/0/4849 | 56095/0/4592 |
| extract | 59,595 | 59,169 | +426 | 59403/0/192 | 58977/0/192 |
| scan | 44,275 | 44,275 | 0 | 44275/0/0 | 44275/0/0 |
| synthesis | 31,637 | 31,635 | +2 | 31613/0/24 | 31611/0/24 |
| unconvert | 62,711 | 62,558 | +153 | 56669/256/5786 | 56794/72/5692 |
| unsynthesis | 40,553 | 40,429 | +124 | 40260/269/24 | 40143/262/24 |
| unextract | 97,624 | 96,888 | +736 | 94480/955/2189 | 94309/1043/1536 |
| **总计** | **397,191** | **395,641** | **+1,550** | — | — |

静态计分换算（`≈947,843 分/门`）：+1,550 门 ≈ +14.69 亿分；
Q 891 vs 892：−1 Q ≈ −8.41 亿分（`R·T` 量级下）。
合计 889q 系静态劣约 +6 亿分（未计 R 差异；官方分差
375373377713.41−374735446628.53=+637,931,084.88 ≈ +0.17%，方向一致，
差额来自 mean_T 与 R 口径）。

### B.2 结构画像（`decoder_struct` §1 同清单，kmx INFO_TAG 实测）

- extract：`inverse24` block ×**29**（norm/scalar/products 各 29 enter；
  frontier/e9 各 23）+ `multiply v` ×**12**（frontier/e9 ×6）。
  extract 多 +426 paid 与此对应（更多逆元/乘法块）。
- scan：`gf_iadd` 标签 8050（与 frontier/e9 相同）；**PUSH 守卫 0 个**
 （frontier/e9：4025 个 `PUSH_CONDITION if b101254` 掩码守卫区）。
  scan 静态 paid 相同（44,275）但 889q 系无"掩码非零才跑"跳过机制——
  mean-T 中 scan 恒为足额（官方 mean_T 396918.49 仅比静态低 272.5，
  对照 frontier mean 395356.94 比静态低 284.1；守卫缺席但均值贴近静态，
  说明其 scan 跳过本来贡献就小，见 §B.3 结论）。
- unextract：`gf_iadd` ×**186**（frontier/e9 ×140）；PUSH 守卫区 ×**40**
 （frontier/e9 ×50，重建段口径）；paid +736。
- 窄返回：unextract 内无 `inverse24`/`multiply` 逆块标签（enter 事件 0；
  frontier/e9 同样 0）——窄返回（单遍逆节点）两侧均成立，不是差异点。
- 分阶段 qubit 触及（distinct/max）：extract 891/890、unextract 891/890、
  synthesis 890/890、unsynthesis 890/890、convert/unconvert 889/890、
  scan 851/886。峰值 891 由 extract＋unextract 顶住（e9 侧为 892 由四阶段顶住）。

### B.3 结论

889q 系（`993c7038`，实 891Q）是另一解码器族存在性参考：extract
（29 inverse24＋12 multiply）与 unextract（186 gf_iadd）更重、scan 无掩码守卫、
13 处未读 CCX-HMR 残余；静态 +1,550 门、Q −1，净静态劣约 +6 亿分。
不是当前 892Q Syed 系的压缩目标；e9 仍是当前族最优（−55 closed 已确权，
见 `20261110_e9diff/README.md`）。

## 验证范围声明

- A：本地只跑 256-shot 烟测（通路验证）；102400-shot 单 salt 在 Kaggle CPU kernel
  上跑，不在本地跑。`data/competition` 验证器未改动（数据集内为未改动副本）。
- B：纯静态只读（kmx 解析＋INFO_TAG 计数＋qubit 触及），未运行官方验证器；
  官方成绩引用 kernel 自带 `summary.json`，未重跑。`kernels pull` 404 如实记录。
- 凭据（`~/.kaggle/access_token_qingyu1232`）仅 `export` 传值，不打印、不进 Git；
  大文件（529MB kmb）仅 `/tmp` 与 gitignored `artifacts/`，不进 Git；
  未提交 competition、未 push git remote。

## 续（服务器重启后，2026-11-10）
- dataset `qingyu1232/qcc-dqi-e9-1salt` ready（`dqi/dqi.kmb` 529242404B + runner + verifier副本；列表压缩尺寸37MB为压缩后大小，文件本身完整）。
- kernel `qingyu1232/qcc-dqi-e9-1-salt-pilot` v1 已push（CPU，`enable_gpu=false`），RUNNING。脚本动态发现 kmb/runner，缺kickmix则pip装，跑单salt 102400 shots/batch256×4 workers。
- 待COMPLETE后取日志回填 A.1（value/phase/mean_T/wall→72-salt外推）。

### A.1 实测与外推（kernel COMPLETE 2026-11-10）
- 单salt `0000`：PASS，102400 shots，value 0 / phase 0，`effective_error_rate=0.00086606`，`R=1.19126046`，`mean_T=395304.59`，`max_T=395586`，Q=892，`score=374686718534.84`，SHA `e9f54be3…e969bc4`（与基线一致）。`load 3.72s / wall 225.48s`（约3.8分钟；log见 `artifacts/20261110_r1salt_1salt0000.log`）。
- 与作者数对照：作者 `374686873086.94 / mean_T 395304.76`；本测低约15万分（0.00004%），来自 mean_T 采样差0.17×R·Q²，方向量级一致。
- 72-salt外推：单job约3.8分钟+启动pip约1-2分钟≈5分钟；72 jobs并行→总CPU约6小时（72×5min），挂18 kernels×4 salts约每kernel 20分钟。CPU kernel，不耗GPU配额。7.37M shots可行，需排队。

## 72-salt全量（用户已批准，2026-11-10）
- 切分：9 kernel×8 salt（k00-k08，salt 0000-0071）；CPU kernel，不耗GPU配额。
- 推送：k00-k04 v1成功（RUNNING/QUEUED）；k05-k08被拒（Maximum batch CPU session count of 5），待空位后补推。
- 待全部COMPLETE后取回各shard json（8 salts×value/phase/mean_T），汇总失败率与R，与Syed V11 `27→21/72 draws`口径对照。

## 72-salt前40（k00-k04 COMPLETE，k05-k08已补推）
- k00-k04各8 salts（0000-0039）全PASS（status全PASS，失败指1个error shot仍PASS但R惩罚上升）。
- 失败：5/40 salts各1 error（0005 v1、0013 p1、0023 v1、0027 v1、0039 v1），其余35个0/0。失败salt得分约37640751万 vs 干净约37468671万，单失败+17.2亿分（+0.46%），与定价一致。
- 外推72：5/40→约9/72，低于Syed V11残余21/72口径（不同salt集合，直接对比需谨慎）。待k05-k08（0040-0071）回填后做72全量均值与Clopper-Pearson上界。
- shard json已存 `artifacts/20261110_72salt/shard0-4.json`。

## 72全量（k00-k08 COMPLETE，2026-11-10）
- 72 salts（0000-0071）各102400 shots，总计7,372,800 shots，全PASS（status）。
- 失败salt 15个，各1 error（14 value + 1 phase：0005/0013p/0023/0027/0039/0041/0049/0052/0056/0057/0061/0064/0068/0070/0071），57个0/0。
- 均值：72全量375045278747.2；干净57均值374686789667.4；单失败约+17.2亿。min 374686501484.3 / max 376407721443.9，pstdev约6.99亿。
- 对照：Syed V11 `27→21/72 draws`口径；本测e9为15/72（salt 0000-0071顺序串）。salt集合与权重口径差异需谨慎，但量级上e9残余低于Syed修复后残余——w17重建的期望净账（+175门≈+1.66亿 vs 省~6 fails≈-1.4亿）需重算，R项杠杆可能比arch_review估计更小。
- shard json：`artifacts/20261110_72salt/shard0-8.json`（9文件，72条）。
