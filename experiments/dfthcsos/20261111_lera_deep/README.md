# Lera 11.2x 机制解剖 + Maoxin303 转向（2026-11-11）— 实测，未提交

分支 `codex/dfthcsos-research`，工作区 `.worktree/dfthcsos/`。
只报实测；未提交 Kaggle、未推送、未改官方验证器/数据；token 未进 Git。

结论先行：**Maoxin303（`artifacts/20261111_maoxin303/`）本地 78,080-shot 全量 PASS，
score 298,720,881.30，比 Lera（298,942,333.64）再降 221,452.34（−0.0741%）。
建议把基线候选换成 Maoxin303**（治理侧独立重跑一次全量验证并核对
`submission_sha256 a9385b97…` 后替换 Lera）。Lera 的 XOR 机理解剖已做完，
下一刀不在 Lera 轴上，而在 Maoxin 的 rank-86 重综合轴（仅 k0 有理论余量，
且缺生成代码，不可本地立项）。

## 1. Lera 机制解剖（相对 P0，全部本地实测）

源码：`marculera/df-thc-11-2x-codes-on-the-xor-of-five-words`（notebook 已 pull，
`/tmp/lera/`，未进 Git）。关键原文：loader 一次写五个字，码可以坐在五字 XOR
上而非逐字（bit1/bit2 XOR 码 + bit0 逐字码）；表为 (8,143,44) cluster 种子 + refit；
44 拷贝相对 45 在 state prep 省 ~79 T。

### 1.1 符号一致性（notebook §2 口径，`sum(1)` 按 copy 求和，非全局符号）

| 项 | P0 | Lera | Maoxin303 |
|---|---|---|---|
| two-body one-norm | 269.218 | 270.317 | 269.904 |
| sign-mixing excess | 0.133 | 0.045 | **0.014** |
| sum\|w\| / \|sum w\| | 411.05 / 410.82 | 411.30 / 411.25 | 411.25 / 411.23 |
| minority-sign weight | 0.115 | 0.028（日志原文 6.7e-05） | **0.009** |

“同号到 0.03”是**每个 copy 内 B=143 个权重的符号一致性**，不是 W 全局符号
（全局正/负各半：P0 211.4/199.7，Lera 201.8/209.5，Mao 201.9/209.4，无差异）。
Lera 相对 P0：excess 0.133→0.045，但 lam2 反而 269.218→270.317（+1.099，
Lambda +0.379、λeff +0.0323 的来源）——化学侧是亏的，全靠 T 扳回。
Maoxin303（ozertuu refit 权重，W maxabs 差 4.1e-3、H2_I 差 1.7e-2）把 lam2
压回 269.904、excess 压到 0.014：refit 吃掉了 Lera 留下的符号混合。

### 1.2 码结构（notebook §3 `degree()` 原样重跑，加测 bit3）

P0：bit0 逐字码 batch3–14 已有（degree 1，somejoint 低比特码）；
bit1/bit2/bit3 的逐字与五字 XOR **全部 degree 4（无约束）**。
Lera/Maoxin303（字表逐字节一致，1220/1220 行全同，见 §4）：

| batch | bit0逐字 | bit1 XOR | bit2 XOR | bit3 XOR/逐字 |
|---|---|---|---|---|
| 0–2 | 4（无码） | 4（无码） | 4（无码） | 4 / 4（无码） |
| 3–7 | 1（仿射） | **2（二次）** | 4（无码） | 4 / 4（无码） |
| 8–14 | 1（仿射） | **1（仿射）** | **2（二次）** | 4 / 4（无码） |

### 1.3 省的 38 angles T 落点（per-loader static，double-pass）

P0：`[297,291,291,291,271,271,271,271,271,271,271,271,270,270,270]`（sum 4148）
Lera：`[297,292,292,292,270,269,269,270,270,267,268,268,268,268,269]`（sum 4129）
差值（Lera−P0）：`[0,+1,+1,+1,−1,−2,−2,−1,−1,−4,−3,−3,−2,−2,−1]`，和 −19/遍（−38 双遍）。
**k1–3（覆盖无码 batch0–2）反而 +1/loader 倒退 +6；k4–14 靠 bit1/bit2 码共省 −44；
净 −38。** Q 都是 427（qmax 128，sel 11；Lera k10/k11/k14 用到 127 vs P0 全 126，
heuristic inner_temp 303 钉死 Q，不搬动）。

## 2. 推广搜索（零训练，纯静态 + `heuristic_costs`，已实测）

### 2.1 bit3 XOR 码：CLOSED（零训练无结构可用）

§1.2 加测：bit3 五字 XOR 与逐字 degree 在**全部 15 个 batch 都是 4**。
XOR 码的前提是字表已携带低次结构（bit1/bit2 是 Lera 建表时种进去的）；
bit3 无结构时 loader 无法利用，改字 = 改化学 = 要重训练（盆地已关，
见 `ABANDONED.md`：R5 50k 40.24 / R4 73.07 / 新形状 50.46/53.29）。
Lera finding #4（one-body 行加码无收益）同向。不立项。

### 2.2 C44→C43/C42：CLOSED（不等式先行 + 结构证据）

`heuristic_costs(76,8,143,C,8)` 实测：C43 省 78 T（6662→6584），C42 省 157 T，
Q 不变（427）。打平线 λeff 允许上升 +0.5255%（C43）/ +1.0634%（C42），
绝对值 +0.247 / +0.499——看起来很宽，但化学侧是 Ha 量级失败：
`CLOSED_RESEARCH.md` §E（固定字删 1 最弱 B 向量/组即 error_1 0.342 Ha；
删 1 rho 组 error_2 2.9–4.5 Ha），且 e2 余量 Lera 仅 5.65 μHa、Mao 仅 0.003 μHa，
而 refit 吸收量级是 mHa（KKT 切空间已证极限）。减拷贝 = 新表 + 新码 + 新 loader，
三重未达，无切口。不立项。

### 2.3 per-word 码与 XOR 码其它位分配：CLOSED

bit0 逐字仿射 batch3–14 已是 P0/Lera 共有（无新增空间）；
bit1/bit2 逐字 degree 全 4（§1.2 加测），逐字路线在 bit≥1 无结构；
batch0–2 三个 batch 在逐字和 XOR 下全是 degree 4——这正是 k1–3 最贵（292/290）
且 Lera 码够不着的原因。该方向的唯一活口是 loader 综合本身（§4）。

## 3. 训练结合：CLOSED（余量判死 + 作者结论 + 本地证据三重）

- Lera（λeff 46.9235，T/Q 固定）做一轮轻 refit：任何 λeff 下降都是纯收益，
  无打平线问题，唯一约束是误差门。e2 余量 5.65 μHa；历史汇率上 W-only refit
  已到 KKT 极限（frontier −15,251 → b9 −0.74，本分支实测）。
- ozertuu 已经做了这轮 refit（§1.1：excess 0.045→0.014，λeff −0.0159），
  代价是把三门吃到 nHa 量级（Mao e1 余量 0.02 μHa、e2 余量 0.003 μHa，
  E_gap 余量 3.0e-9 Ha）。作者结论“再 refit 仅 +0.002%（≈+6K）”与 KKT 证据一致。
- 在 Mao 表上再做轻 refit：期望 ≤6K，风险是顶破 deterministic 门（余量已无）。
  不立项。

## 4. Maoxin 转向（本轮优先级，全部实测）

情报：`maoxin123/lb-25-303-combined-invsqrt-refit-chem` v6（GM 25.30339）。
`kernels output … -p /tmp/maoxin303/` 取回 `submission.zip`（26.7M）+
kernel 日志；notebook v1–v6 全 pull（`/tmp/maoxin303/v*/`），确认：
**v6 的 k1–3 loader 以嵌入 blob 形式存在（`LOADERS={'1':…,'2':…,'3':…}`），
无生成代码**；“217 products→215”的 rank-86/19维方法只有文字描述，
无可复用代码（v2–v5 同样只有 blob + WEIGHTS，无综合器）。

### 4.1 落盘与静态（`artifacts/20261111_maoxin303/`，大文件未进 Git）

- `submission.npz`（`ff5e05ee…`）+ 15 loader + `kernel.log`（作者日志原文已存）。
- 字表关系（npz 数组级实测）：**U/tree_edges/angle_words 与 Lera 逐字节一致**
  （1220 行全同）；W 微调（maxabs 4.1e-3）、H2_I 微调（maxabs 1.7e-2）。
- loader 字节：k0、k7–k14 与 Lera **9/15 逐字节一致**；k1–k6 重综合。
  per-loader static：`[297,290,290,290,271,270,270,270,270,267,268,268,268,268,269]`
  （sum 4126），相对 Lera 差值 `[0,−2,−2,−2,+1,+1,+1,0,0,0,0,0,0,0,0]`，
  和 −3/遍（−6 双遍）。k1–3 用到 128 qubit（Lera 126），qmax/Q 不变。
- 口径：T = 8252（angles 双遍）+ 6662（heuristic）= 14914；Q = 427；
  λeff 46.907638344332305；pred = 298,720,881.3002。

### 4.2 本地官方验证（`scripts/manual_verify.py`，未改验证器）

- 小 shot：`--salt maoxin303-small-20261111 -- --shots-per-address 2`（2440 shots），
  exit=0，**PASS**，score 298,720,881.30016786（= 静态预测到小数点后 4 位）。
- 全量：`--salt maoxin303-full-20261111`（默认 64/地址，`verified_shots=78080`），
  exit=0，**PASS**，score **298,720,881.30016786**，
  `submission_sha256 a9385b97…`（全值见 `verify_full.log`），
  T=14914.0 / Q=427 / λeff=46.907638344332305，
  error_1 19.99998 mHa / error_2 19.999997 mHa / E_gap 3.914898003。
  日志：`artifacts/20261111_maoxin303/verify_{small,full}.log`。
- 未在其它 salt 下复核；化学门部分是确定性计算，shots 只覆盖 loader 字恢复。

### 4.3 −221,452 拆解（静态算术，非验证结论）

Mao303（298,720,881.30）vs Lera（298,942,333.64），Δ = −221,452.34：
- 权重轴：λeff 46.9235→46.9076（−0.0159），同 T=14920 下 −101,275；
- loader 轴：T 14920→14914（−6），同 λeff 下 −120,177。
- 混合对照（Lera λeff × Mao T = 298,822,115.54）比 Mao303 差 101,234，
  故**整包采用，不做杂交**。

### 4.4 推广到其余 12 loader：不可本地立项（缺代码 + 结构证据）

- k4–k6 作者已重综合，结果相对 Lera **+1（更差）**：该方法在这三 loader
  上不增益（或作者取了 k1–3 最优而容忍 k4–6 回退，净 −3/遍）。
- k7–k14 已在 267–271，`CLOSED_RESEARCH.md` §C.1  planner 配对下界已饱和
  （195 products 量级），期望 ≤0。
- k0（297，无 clean word、双相 low cache 特殊结构）是唯一理论余量：
  若 297→295（−4 双遍 T）≈ −80K（−0.027%）。但 rank-86 方法原文只描述
  “每个 loader 的 217 products”（k1–3 量级），k0 产品数/结构是否适用未知，
  且无生成代码。** verdict：本地不立项；只监控公开代码，若综合器出现则
  第一优先级试 k0。**

## 5. 死胡同清单（本轮新增，对表自查用）

- bit3 XOR/逐字码（15 batch 全 degree 4，无零训练结构）。
- C43/C42（省 78/157 T，打平 +0.53%/+1.06%，但删拷贝 Ha 级失败 + 余量 nHa/μHa）。
- 固定字 W-only/联合 refit（KKT 极限 + 作者 +0.002%，三重关闭）。
- Lera 杂交（§4.3 整包更优，不组杂交包）。
- 复现 rank-86 综合器（无代码；等公开，不自研——期望 ≤80K/loader，不值得）。
- 换 B/换种子/训练盆地（`ABANDONED.md` 已封：R5 40.24 / R4 73.07 /
  新形状 50.46 / 53.29；brot6 地板；B 悬崖；重复的不做）。

## 6. 采用建议（治理侧执行，不在本工作区组包）

main 仓独立重跑一次全量验证并核对 `submission_sha256 a9385b97…` 后，
把化学基线候选定为 Maoxin303（298,720,881.30），Lera 退为回退，P0 再退一级。
DQI `9fcda0c1`（374,685,006,336）与本地实测一致，invsqrt `a15b0d73`（93,925.35）
作者称 unmodified verifier 已验——两项非本工作区验证范围，只转述，
采用前各跑一次 `manual_verify.py`。

## 7. 验证范围声明

- §1–§2 为精确算术（numpy + 官方 `evaluate_words`/`heuristic_costs`/`circuit_costs`/
  `recover_words_from_circuits` shots=2 计量 + degree/Moebius 变换），无 `verify.py`
  调用；不等式为乘法口径换算，非验证结论。
- 官方 78,080-shot 本地验证仅运行两次（Lera 见 `20261111_lera11x/README.md`；
  Mao303 见 §4.2，salt `maoxin303-full-20261111`），结论均为 PASS；
  未在其它 salt/seed 下复核，未提交 Kaggle，未推送。
- 文件：`artifacts/20261111_maoxin303/{submission.npz,angle_k_*.kmb,kernel.log,
  verify_small.log,verify_full.log}`（大文件未进 Git）；
  notebook 源码在 `/tmp/{lera,maoxin303}/`（未进 Git，用完即焚也可）。
