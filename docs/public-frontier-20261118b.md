# 公开前沿 2026-11-18b：组合 W 端到端官方验证与 28.19 以上公开包扫描

本页回答两件事：组合 W 是否在未改动的官方验证器上整包 PASS，以及是否存在高于 28.19 的**公开**包。
结论先说：**组合 W 三条腿全部 PASS，分数与作者记录逐位一致，GM 28.189660448；没有找到任何高于 28.19 的公开包。**
榜单 28.19358–28.18976 的 21 个名次（73–93）未发现对应的公开 QCC notebook 或 dataset，属于非公开组合。

## 1. 复核环境

| 项 | 值 |
|---|---|
| 内核 | [`jiyujia/qcc-verify-combo-w-20261118b`](https://www.kaggle.com/code/jiyujia/qcc-verify-combo-w-20261118b) **v2**，`KernelWorkerStatus.COMPLETE` |
| 完成时间 | 2026-11-18T05:52Z（v1 因数据挂载路径写死报错，未运行任何验证器；v2 改为挂载发现） |
| 硬件 | CPU only；`enable_gpu=false`、`enable_tpu=false`、`enable_internet=false`，无 accelerator |
| 数据 | `junmiaotiao/qcc-frontier-20261118w` **v1**，2026-11-18T04:13:43Z，[dataset](https://www.kaggle.com/datasets/junmiaotiao/qcc-frontier-20261118w) |
| 验证器 | 比赛数据内未修改的 `verifiers/invsqrt`、`verifiers/dqi`、`verifiers/dfthcsos`；默认 salt（空串），默认 shots |
| 证据文件 | [`docs/evidence/20261118b/`](evidence/20261118b/)：`combo_w_verification.json`、`verify_invsqrt.json`、`verify_dqi.json`、`verify_dfthcsos.json` |

复现命令（内核内，工作目录 `/kaggle/working`）：

```bash
python /kaggle/input/.../verifiers/invsqrt/verify_submission_invsqrt.py submission/invsqrt.kmb
python /kaggle/input/.../verifiers/dqi/verify_submission_dqi.py submission/dqi.kmb
python /kaggle/input/.../verifiers/dfthcsos/verify.py submission/dfthcsos
```

本仓库 `data/competition/verifiers/` 中对应入口脚本的 SHA-256（用于说明未改）：

```text
ddef520dec6b68d1cf0a6f328ddd36d79eb84570b9192cf3f7acaf073f06733a  invsqrt/verify_submission_invsqrt.py
f14274bc0943fb9769ddb01131be6063191a15009fe1caf1d4bdd9fd25194e65  dqi/verify_submission_dqi.py
0775be7a528922367caebe9e4d051d6199811f1aefeaa4b793eaaa4621b8ec9d  dfthcsos/verify.py
```

## 2. 三条腿的官方验证结果（默认 salt、全 shots）

| 腿 | 件 | 官方 cost | Q | 其他精确字段 | 运行时间 |
|---|---|---:|---:|---|---:|
| invsqrt | `864f81cd` | **74,490.94707587373** | 44 | `toffoli_equivalent` 1,692.9760699062213；`toffoli_count` 1,453.3740955163028；`max_toffoli_count` 1,548；`t_count` 4.000092764106487；33 rotations；`rotation_eps` 2.0054235445130315e-13；`worst_error_over_tolerance` 0.9994556024653497（worst_x 231）；`verified_shots` 200,540,928；PASS | 650.7 s |
| DQI | `5f901c55` | **346,404,203,610.1118** | 890 | `toffoli_count`（mean）367,110.16626953124；`max_toffoli_count` 367,983；`value_errors` 0；`phase_errors` 0；`repetition_factor` 1.1912604648115832；`log2_delta` -128.0；`verified_shots` 102,400；PASS | 158.5 s |
| chem | `4d63be3d` + 15 loaders | **294,642,170.565169** | 427 | `lambda_eff` 46.921562797126406；`T` 14,706（angles 8,044 + heuristic 6,662）；`error_1` 0.019999999800000907；`error_2` 0.01999999979999996；`Lambda` 283.1439644065389；`E_gap` 3.914898003116832；`submission_sha256` 167c25d785abd53cf50955c5b6da5afe77f9f22b4320627f3e30b5dab7df1426；`verified_shots` 78,080；PASS | 27.2 s |

几何平均（本仓库 `scripts/gm.py` 复算，唯一输入是上面的官方 cost）：

```text
GM = 28.18966044813323
ratios = 27.8795520158974 / 70.55186781503457 / 11.388728171120182
```

与作者记录 `74,490.94707587373 / 346,404,203,610.1118 / 294,642,170.565169` 和 GM `28.18966045` 在给出的位数内一致。
公开榜 ref `58492757` 记录 **28.18965**，差异仅来自榜单四舍五入。

## 3. 新构建的 `submission.zip`

| 项 | 值 |
|---|---|
| 大小 | **50,946,580 B** |
| SHA-256 | **`134ceaaa8945f8c5ddb0556997f3a77b485f61629078f34db0ebaedf229b5366`** |
| 成员数 | 18 |
| 内容摘要 | `fe9fa7b02ca7b77497072e17ab9850cff87ee62963f8a19942a3730203f1990f`（按成员名排序后 `name + bytes` 的 SHA-256） |

构建方式：从 pinned dataset 复制 17 个文件并 `xz -dc` 解压 `dqi_5f901c55.kmb.xz`；逐个 SHA-256 断言后，
以固定时间戳 `2026-11-18 00:00:00`、`ZIP_DEFLATED` level 6 写入；随后**重新打开 zip**，逐成员重算 SHA-256 并与清单比对，18/18 一致。

作者 notebook 输出的 zip（`ea55e2a9aac319e67c3d9cdd5930fd439f2abae4b584d0bfe44f3b15cf73e928`，同为 50,946,580 B）
与本次新构建的 zip **容器 SHA 不同、成员内容摘要相同**（均为 `fe9fa7b0…`）。已提交的 ref `58496528` 用的是作者的 zip，
因此本次对 18 个成员的官方验证结果同样适用于该提交。

18 个成员 SHA-256（与 dataset `MANIFEST.json` 和 notebook pinned 列表逐项一致）：

```text
dfthcsos/angle_k_0.kmb   ed6487084d30b0c772e8bd1109b56b501945d2bc708a343fd8bdf3551f3b7538
dfthcsos/angle_k_1.kmb   8e3a04e0e0450dbaa4725dc421708291ad4cec1522611e363936c90121885fbd
dfthcsos/angle_k_2.kmb   e620e957a4942bb9ddb1b246519d177f9de104ae27c95261a88bd9e7ed99303f
dfthcsos/angle_k_3.kmb   b1f4286282ab66463a4b7bd4513a7b3ecf67cdd8ede1bd86293169aa17cce76e
dfthcsos/angle_k_4.kmb   ee54d6f926f72276cd28439352b0d994bb77a3ed91b9d915291293192ceca07d
dfthcsos/angle_k_5.kmb   21b49673d23b09dbd3ad45e620cb799d54c64ebe5b4850bd17ac163a9b2a2856
dfthcsos/angle_k_6.kmb   1ae55a71e6877ce23c671df157a532b594694001a9623cc7315cc332306973e1
dfthcsos/angle_k_7.kmb   8ccf17b0113fb5451f64bd1df02dd8de262c7976f98fc8f621551a0430fbe8f0
dfthcsos/angle_k_8.kmb   0ace34e6eab90c9f2a0165671cca4dd1f4cc94e18f7d517a39c3156629234563
dfthcsos/angle_k_9.kmb   b4a2d0ce4bc3c5fa8055a4f386507bc7d35dccdcb68f5545cc7970843c85da71
dfthcsos/angle_k_10.kmb  41069152b81cbd62f0f00d24990d69db58a5ef2bcee099c078c811b1ed4286a6
dfthcsos/angle_k_11.kmb  76c24260f8ec945e01de34ab8185f2ce0d7608f45da6f05101a47fb7136a9aca
dfthcsos/angle_k_12.kmb  e8ed58a46db6500c0b0f0b2d5b8dd674d965de268683343ab942e6235b672f7f
dfthcsos/angle_k_13.kmb  9e415e21dacce531c03d5c9322b5aa57f641ae7990b3426ad5574a6c1f9d93d8
dfthcsos/angle_k_14.kmb  fe94999841456f828d26c6b375d632f3b28f0f64def2a3bfffdc79873e3a928f
dfthcsos/submission.npz  4d63be3d5c26cfa447a3464eeaf515a652814a1dd4c78f1f1af2f5b7d9e9b8b3
invsqrt.kmb              864f81cd20489d80e302f48014fcedec3b3fb703122fbcbac41b0bb2a395a859
dqi.kmb                  5f901c556cafd02dc11641eee7766171a454e3a0b6687d890ff9f99944e1934c
```

来源链（dataset `MANIFEST.json` 的 notes，原文可查）：

- `864f81cd`：maoxin123 2026-11-18 重跑的 44Q invsqrt；生成器线归 Syed Asad Ali，64 行表归 Ali Haydar Özdağ，角度 refit 归 Ertuğrul Özer。
- `5f901c55`：Grant Prater 的 merged closings `575b043f` 上，boristown 的 PW4 补丁（−6 个 Toffoli-like）；上游归 Syed Asad Ali、Hayato Hikawa、manwithacat、Balram Srinivasan。
- `4d63be3d`：leotang09 在固定 word 上对 `703843d3` 的 W/H2_I refit；表/word/tree 归 Lera（marculera），15 个 4,022-Toffoli loader 归 maoxin123。
- 许可：dataset 元数据为 CC0-1.0；随包 `licenses/` 保留 Apache-2.0 NOTICE（Syed Asad Ali 首位）。

## 4. 榜单块与“28.19 以上”的算术

榜单快照：2026-11-18T05:36:57Z，3,298 行，[公开榜](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/leaderboard)。
快照 CSV 的 SHA-256 为 `146d6752d6d0e0a204eccb76d259bee46ebf9af04429f51c98ebc585c963f3e8`；
本页只保留 1–130 名的摘录：[`leaderboard-ranks-1-130.csv`](evidence/20261118b/leaderboard-ranks-1-130.csv)。

| Rank | Score | Team | Last submission |
|---:|---:|---|---|
| 1 | 31.50701 | aadi_stonks | 2026-11-18 02:39 |
| 10 | 29.14389 | Some Joint | 2026-11-13 20:41 |
| 73 | 28.19915 | re | 2026-11-17 10:54 |
| 74 | **28.19358** | Panagiotis Anagnostou | 2026-11-17 19:41 |
| 75 | 28.19334 | Juan Correa Zapien | 2026-11-18 04:26 |
| 76 | 28.19303 | syouya tobita | 2026-11-18 00:09 |
| 77 | 28.19265 | Efthimios | 2026-11-17 20:17 |
| 78–85 | 28.19234 → 28.19073 | Carlos Bosch … catv eg | 11-15 → 11-18 |
| 86 | 28.19071 | Balram Srinivasan | 2026-11-17 14:52 |
| 94–134 | **28.18965** | 组合 W 及大量复现者 | 11-18 03:22 → 05:09 |
| 135–151 | 28.18964 | 同件不同 zip/细微差异（含 暗黑AGI 28.18964） | 11-18 |

组合 W（tiraJoon）在快照中为第 101 名；94–134 名同为 28.18965。`submissions/20261118_2819` 的提交 ref `58496528` 在 05:38:36Z 发出，
已返回 **`COMPLETE`，public 28.18965**，与本地 GM 28.189660448 和作者记录一致。

**73–93 名不是公开包。** 差值为：

```text
(28.19358 / 28.18965)^3 = 1.000418
```

即单腿成本需再低 **0.0418%**。按三条腿分别折算：

| 若只改 | 需要的公开件 | 公开现状 |
|---|---|---|
| invsqrt | cost ≤ 74,459.8（44Q 下 C+T/4 再低 0.706） | 公开最好仍是 `864f81cd` 74,490.947；`t_count` 只有 4.0001，无法靠减 T 达到 |
| DQI | mean T ≤ 366,956.8（再少 153.4 Toffoli/shot） | 公开最好 `5f901c55` 367,110.166；`bb9bf415` 比 `575b043f` 只低 0.00087%（约 367,112.9），更差 |
| chem | cost ≤ 294,519,000，即同 λ 下 T = 14,700（少 6 T） | 公开最好 T = 14,706；没有任何 4,019/4,020-Toffoli 公开 loader |

`chem` 的 6 T 差额恰好给出 28.19359（用 `scripts/gm.py` 验算），与第 74 名的 28.19358 只差最后一位四舍五入；
另一种等价解释是 DQI 在该隐藏 salt 下 mean T 少 153。两者都要求**不同的电路文件**；独立复现记录显示 DQI 的 salt 相对变化
只有 <1.5e-6（`akkki8844/google-quantum-kaggle` 的 default/s1/s2 三次），远小于所需的 4.18e-4。
同一组文件在同一隐藏 salt 下复现同一 cost，所以这些名次不是同一 W zip 的随机波动；它们不构成可采用的公开包。

## 5. 公开来源扫描（截至 2026-11-18T06:00Z）

| 来源 | 最新状态 | 与 28.19 的关系 |
|---|---|---|
| [`junmiaotiao/qcc-28-19-public-frontier-combo-w`](https://www.kaggle.com/code/junmiaotiao/qcc-28-19-public-frontier-combo-w) v1 + [dataset W](https://www.kaggle.com/datasets/junmiaotiao/qcc-frontier-20261118w) v1 | 本页已整包 PASS | **公开最高**，28.18965 |
| [`boristown/qcc-gap-3-residue-repair-and-c43-native-compiler`](https://www.kaggle.com/code/boristown/qcc-gap-3-residue-repair-and-c43-native-compiler) v32（2026-11-18 04:19） | 输出日志 GM **28.18966275**；chem `294,642,299.763`（T 14,706，λ 46.92158337），比 W 的 chem 高 129.2 | 低于 W |
| [`leotang09/vqcc-t7421-submission`](https://www.kaggle.com/code/leotang09/vqcc-t7421-submission)（2026-11-18 03:40） | 输出 zip 的 18 个成员与 W **逐字节相同**（zip SHA `593897aa…`，内容摘要 `fe9fa7b0…`）；无独立 verifier JSON | 等于 W |
| [`asteriospanoras/qcc-28-18084-could-be-top-1-public-try-it`](https://www.kaggle.com/code/asteriospanoras/qcc-28-18084-could-be-top-1-public-try-it)（2026-11-17 23:31） | receipt：invsqrt `563d0583` 74,560.907、DQI `5f901c55` 346,404,203,610、chem `f05297b4` **294,642,299.763**；GM **28.18084** | 低于 W |
| [`atakanaldemir/qcc-shared-products-and-controlled-refits`](https://www.kaggle.com/code/atakanaldemir/qcc-shared-products-and-controlled-refits)（2026-11-18 05:43 重跑，`RUNNING`，无新输出） | 榜单本人 28.18070（rank 392）；重跑不改变已公开件 | 低于 W |
| [`maoxin123/qcc-28-18-4-022-toffoli-chemistry-loaders`](https://www.kaggle.com/code/maoxin123/qcc-28-18-4-022-toffoli-chemistry-loaders)（2026-11-18 02:56） | 记录 **28.18284**；其 `864f81cd` 已并入 W | 低于 W |
| [`manwithacat/vqcc-hedge-wizardry-notebook`](https://www.kaggle.com/code/manwithacat/vqcc-hedge-wizardry-notebook) v32（2026-11-17） | 最新 DQI `957d6733` mean T 367,375.47，比 `5f901c55` 差 265；无 >28.19 组合 | 低于 W |
| `junmiaotiao` 其他 dataset | 最新依次为 W、U、S、R；U/S/R 均 ≤28.181 | 低于 W |
| QVC GitHub [`Agnuxo1/qvc-chemistry-compiler`](https://github.com/Agnuxo1/qvc-chemistry-compiler) | main `3ee172b7bf1502781c7e78378dab4b17e155c576`；v0.4.0 之后只有 5 个 provenance/NOTICE 文档提交，无新电路、无新 tag | 无新包 |
| arXiv [2610.23832v2](https://arxiv.org/abs/2610.23832)（官方竞赛论文） | 任务/验证器设计说明，无新的可提交电路 | 无候选 |
| arXiv [2610.22367v1](https://arxiv.org/abs/2610.22367)（LLM 电路发现） | 通用任务上的资源表；无竞赛实例的可下载电路/文件契约 | 无候选 |
| arXiv 最新 DQI（[2611.15794](https://arxiv.org/abs/2611.15794)、[2611.12718](https://arxiv.org/abs/2611.12718)） | 分别是 DQI 路径规划应用、局部 decoder 无指数优势的理论结果；无竞赛 decoder 电路 | 无候选 |
| arXiv `"inverse square root" quantum circuit` 最新 8 条（2026-11-18 检索） | 最新为 2611.16398（Grover 噪声）等，无新的 44Q 反平方根构造 | 无候选 |
| GitHub [`akkki8844/google-quantum-kaggle`](https://github.com/akkki8844/google-quantum-kaggle) `PLAN.md` §9.16 | 独立复现 v4（`864f81cd`+`5f901c55`+`703843d3`）：DQI 在 default/s1/s2 三个 salt 为 3.46404204e11 / 3.46403695e11 / 3.46403824e11（相对差 <1.5e-6）；提交 **28.18964** | 低于 W；证明 salt 变化不足以解释 28.19358 |
| Kaggle 数据集按 `qcc`/`quantum circuit` 按更新时间扫描 | 2026-11-17/18 的新件均已被 W 吸收或更差（`vqcc-combo-candidates`、`vqcc-verified-public-floor`、`vqcc-portfolio-v23-artifacts` 都早于 W） | 无 >28.19 |

对 73–93 名用户的公开主页也做了核对：`panosanag`、`juancorreazapien`、`syouyatobita`、`efthimiosfousekis`、
`carlgauss37`、`ramanaprabhusana`、`getties`、`xthistle999`、`uttamlimbani`、`catveg`、`syaugialkaf`、`refv00`
均无 QCC notebook；有公开 notebook 的也与本竞赛无关。这支持“28.19 以上是私有件”的判断。

## 6. 建议

1. **采用组合 W**：`submission.zip` 容器 SHA `134ceaaa…`（新构建）或 `ea55e2a9…`（作者/已提交 ref `58496528`），
   18 成员内容摘要 `fe9fa7b0…`。三条腿在官方默认 salt、默认 shots 下全部 PASS，GM **28.189660448**。
2. 本节结论在 2026-11-18T14:00Z 之后已更新：**出现了 >28.19 的公开件**，见 §7。

## 7. 更新（2026-11-18T14:46Z）：公开前沿到 28.20041

`maoxin123/qcc-28-20-4-022-toffoli-chemistry-loaders` **v4** 嵌入了一份新的 44Q invsqrt
**`d0227f3c548ae7f1a409159a143cf4a401de56a2414a5230a3efc4b38e0a8160`**，作者报告官方
full-shot **PASS, 74,405.73**（44Q；`864f81cd` 是 74,490.947，少 **85.22**）。
`asteriospanoras/qcc-28-20041-lb-what-works-what-fails-and-why` **v23** 独立重建并复核了
同一组合（`d0227f3c` + `5f901c55` + chem），榜单 **28.20041**。

- 只换 invsqrt：`(74490.94707587373/74405.73)^(1/3) = 1.000381622` → GM **28.200418**（+0.01076）。
- 已提交 ref **`58514074`**（2026-11-18T14:46:45Z），包 `artifacts/candidate_2820_l9.zip`
  （49,434,074 B，SHA-256 `f57f2b42…a31c`），18 成员 SHA-256 见
  `submissions/20261118_2820/README.md`。
- 该件的来源链：Syed Asad Ali 的生成器线 → maoxin123 的 44Q 调度（v4 base64 内嵌）。
- 这也解释了 14:40Z 榜单的变化：`≥28.19915` 的队数从 12:46Z 的 77 涨到 **120**，
  `28.18965` 并列块扩到 **335 队**，我们的名次从 149 滑到 **224**。

仍要注意：这份 invsqrt 只比 `864f81cd` 便宜 85.2（0.11%），属于同一代电路的微调；
>29.2 的 11 个队仍是私有件。

## 8. 旧的“无 >28.19”结论（已被 §7 取代）

2. **不存在可直接采用的 >28.19 公开包**。若要让公开榜进入 73 名以内，需要非公开的
   chem 少 6 T（或 DQI mean T 少 153）级别微调；这属于新一轮研究，不是打包问题。
3. 私有 salt 风险：W 的 DQI `5f901c55` 在 boristown notebook 的第二个 salt 上曾出现 2/102,400 失败 shot
   （见 `alexchilton/28-18-lb-which-circuits-survive-private-salt` 的正文），失败会把该腿 cost 抬高约 0.46%。
   `575b043f` 更保守但公开成本高 0.0016%。公开榜按提交时的 salt 记分，ref `58492757`/`58496528` 的公开成绩不受未来 salt 影响；
   私有榜评估时再按当时规则选择最稳的提交。
