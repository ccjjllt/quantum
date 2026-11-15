# 20261115 升级总结

## 已落地

| 项 | 值 |
|---|---|
| 第一次提交 | ref **58349843**，`maoxin123/qcc-v27-4033-toffoli-coded-word-chemistry` v2 输出，MCP **COMPLETE 27.30661** |
| 升级提交 | ref **58350759**，HW-26 invsqrt `1ba197b02771` + DQI `821bf8d1` + maoxin 4,033 chemistry，**COMPLETE 27.31193** |
| 包 | `submissions/20261115_public_2731/submission.zip`，SHA-256 `46d53bde…c933`，18 文件 |
| 独立验证 | HW-26：未修改官方 invsqrt verifier，200,540,928 shots **PASS**，78,673.56921101942，worst/tol 0.9986660009 |

第一次提交已把本账号从 **27.00209 → 27.30661（+0.30452）**；升级包 **58350759**
已 COMPLETE **27.31193**，MCP 名次 **175 / 3055**（2026-11-15 复核；提交时为 159 / 3053）。

## 公开前沿扫描结论

- `manwithacat/vqcc-apache-public-circuits` v125（497 件）与 11-14 后新件中：
  - invsqrt 最低 Q = **46**；HW-26 `1ba197b02771` 是唯一更低 cost（78,673.57）。
  - DQI 最低 cost 仍是 `821bf8d1`（预期 360.947e9）；Q<889 的公开件全部更贵
    （最便宜 888Q 398.27e9，+10.56%）；无 840Q。
  - chemistry 最低 T = **14,728**（4,033 loader），最低 cost **294.984M**；
    没有 3,9xx loader 或更低 T。
- 公开可复现上限 **27.31214**（HW-26 + npz `e52b7cdd` + 821bf8d1）。
  排行榜第 31–146 名（27.40–27.61）使用未公开组件，公开件无法直接到达。

## 逐项判决

### invsqrt

- HW-26 是唯一确定正收益：−1 Toffoli，GM +0.00532。
- Q=45 需要补价 ≤38 Toffoli；公开最便宜覆盖 +196（4560ac0c）/+257（321aff83），
  GM −0.78/−1.05。当前 46Q 峰值段 77.7% 的 op 同时占 46 线，不建议继续。
- 64→32 行表、删旋转、divider 重写均不可行（详见 `invsqrt_plan.md`）。

### DQI

- cutoff 18 最优；19/20/21 负 EV；retention 的 241 个乘积已饱和，
  `max_hops=0/1/2` 均只宿主 241，输出逐字节等于 `821bf8d1`（本次 Kaggle 实测，
  官方 verifier PASS 360,209,905,486.02）。
- 840Q no-go；888Q 是唯一剩余结构杠杆（预算 ΔT≤862，预期 +0.01–0.02 GM），
  需要源码级单线重分配，未在本轮构建。

### chemistry

- 公开点已四面贴边（e2 余量 3.2e-8、E_gap 余量 4e-9、λ 距地板 0.26%）。
- 唯一 ≥1% 杠杆是 B=143→129（T −3.1–4.0%，GM 27.52–27.68），但闸门是
  B=129 的 8-bit e2 地板。Stage A 已完成：B=143 对照精确复现公开件
  （e2 19.99997 mHa、λeff 46.9070、cost 294.99M、PASS）；B=139 e2 64.31 mHa、
  B=129 e2 138.07 mHa，C=48 也救不回。截断+权重 refit 的廉价形式已关闭；
  要打开 B<143 必须重训 U/词表并重做 15 个 loader，属独立 factorization 研究线。

## 下一步（按收益/可行性）

1. 58350759 已 **COMPLETE 27.31193**，保留为当前最佳。
2. 用 `junmiaotiao` npz `e52b7cdd` 替换化学权重，可到 27.31214（+0.0002，零风险，
   但需要重新打包/提交；不建议为此单独消耗提交次数）。
3. 剩余唯一正 EV 的杠杆是 **DQI 889Q → 888Q**（源码级单线重分配，预期 +0.010–0.021，
   即约 27.321–27.333）。chemistry B<143 已由 `chem_b129/CLOSED.md` 实测关闭。
4. 不追公开榜第 31–146 名：其组件未公开，公开件天花板已确认。

## 2026-11-15 18:03 UTC 进行中

- `qingyu1232/qcc-chem-b129-full`（T4 GPU）已启动：从公开 (8,143,44) 表做 full-U
  L-BFGS shrink，schedule `139x44,135x44,131x44,129x44`，`--fit 2500 --final 8000
  --select impact --device`。这是 B=129 的关键判决；只看连续 error_2 是否足够低
  （目标 ≤15 mHa），不通过就关闭 B<143 线。
- `qingyu1232/qcc-chem-b139-shrink` 是 139 的快速闸门，但 B129 full 已覆盖它。
- 两 run 均在 Kaggle，未在本机跑模拟；结果出来后只对通过点做 8-bit rounding、
  loader build 和官方 78,080-shot 验证，且只有 GM ≥27.50 才打包提交。

## 2026-11-15 结论：B<143 已被实测关闭（不是时间盒）

`qingyu1232/qcc-chem-b129-full` **v1 已 COMPLETE**，full-U L-BFGS 实测连续 error_2：

| B | 连续 e2 (mHa) | 门槛 ≤12.5 | 预期 GM |
|--:|--:|---|---:|
| 139 | **16.173** | FAIL | 27.42 |
| 135 | 18.408 | FAIL | 27.52 |
| 131 | 20.713 | FAIL | 27.63 |
| 129 | **19.830** | FAIL | 27.69 |

上游 `recipes/finish_merged_b8.toml` 写明 "Rounding has cost 6-8 mHa on merged shapes,
so the fit should be <= ~12.5 mHa"。B=129 的 19.830 mHa 高出门槛 7.3 mHa，量化后约
26–28 mHa，超过 20 mHa 硬闸门。且 GM≥27.50 需要 T≤14,428（B≤135），B=135 的 e2 同样
不过。**两条约束同时否证**，详见 `chem_b129/CLOSED.md`。

未做 8-bit rounding / loader build / 官方 78,080-shot 验证（第 1 步未过门槛，后续无意义）。
当前最佳保持 **27.31193（ref 58350759；提交时 159/3053，复核 175/3055）**。

## 2026-11-15 追加实测：DQI 无免费 qubit

`qingyu1232/qcc-dqi-q888-probe`（CPU，COMPLETE）读到 `821bf8d1` 的原始日志：

```
num_qubits 889 num_bits 154157 static_toffoli_like 383414
distinct_indices_used 889 min 0 max 888
UNUSED_IN_0..Q-1 0 []
FREE_SHRINK_IF_RENUMBERED 0 (Q -> 889 )
usage_least10 [(13606,15),(14180,23),(14852,11),(15232,35),...]
```

889 条 wire 全部在用，`0..888` 无空洞，最冷门的一条也有 13,606 次操作。
→ "声明宽度 > 实用宽度，重编号白拿一个 qubit"（+0.0205 GM）**不存在**。
889→888 只能走真实 release-and-recompute（预算 ΔT ≤ 862，源码级 7 族改造，预期 +0.0095…+0.0205）。

详见 `dqi_plan.md` §8。

## 2026-11-15 最终标定：这一族 rounding 代价 5.22 mHa，只有 B=143 过闸门

`qingyu1232/qcc-chem-rounding-calibration`（T4，COMPLETE）：同 seed、**同形状 (8,143,44)、
不剪枝**，只做 full-U L-BFGS refit：

```
    8x143x44: error_2   20.000 ->   20.000 mHa   (3 s)    # 已 8-bit 的公开表
 143x44 x0.5: ...  16.727 mHa       143x44 x0.2: ...  16.178 mHa
    8x143x44: error_2   16.178 ->   14.777 mHa  (166 s)  # 连续地板
```

- **rounding 代价 = 20.000 − 14.777 = 5.22 mHa**（这一族的实测值，上游只给了泛化的 6–8）。
- 每减 1 个 B 的误差代价 ≈ 0.361 mHa；每减 1 个 B 只省 42.4 T（0.29% 成本、+0.10 GM）。
- 逐点：B=141 → 20.7、139 → 21.4、135 → 23.6、129 → 25.1 mHa（全部 >20）。
  **只有 B=143 本身能过 20 mHa 闸门**，这解释了公开件里完全没有 B<143 化学表。
- 副产品：本轮 shrink 管线只比作者数万 epoch 的地板差 ~2 mHa，说明 `e2_c(129)=19.830`
  是真实水位、不是欠训练，B=129 彻底关闭。

## 三个任务的成本模型（全部从官方 verifier 反解 + 实测钉死）

| 任务 | 官方 score 公式 | 现值分解 | 剩余杠杆 |
|---|---|---|---|
| invsqrt | `rep · Q² · T_mean` | 46² × T_mean 1,478.75；static 1,550，142/1,550 条件门 | Q−1 = +0.2008（需 ≤38 T，公开最便宜 +196）；T−1 = +0.00532 |
| DQI | `R(eps_+) · Q² · T_mean` | 1.19 × 889² × 383,008；static 383,414 | Q−1 = +0.0205（需真实重分配）；R 已在 0 错误地板 |
| chemistry | `λ_eff · T_total · Q_total`（**T 是静态门数**，非均值） | 46.907 × 14,728 × 427 | T−1% = +0.122；B<143 已实测关闭 |

三条关键实测：

1. **chem T 是静态的**（`toffolis = sim.operation_statistics().num_toffoli_like / (num_vectors*repeats)`），
   所以化学件**没有** HMR/条件门可省 —— 这条最诱人的 "把 uncompute 变条件门" 思路对化学无效。
2. **DQI T 是逐 shot 均值**，但 `T_mean/static = 0.99894`（只有 ~812 个条件门，0.2%），
   结构上已经榨干；`R` 已踩 0 错误地板 1.19。
3. **chem rounding 代价 5.22 mHa**、连续地板 14.78 mHa → 只有 B=143 能过 20 mHa 闸门。

## 公开件天花板（2026-11-15 19:00 UTC 复扫）

507 行 manifest + 24 条 HW 条目：invsqrt 最好仍是我们的 HW-26（78,673.569），DQI 仍是
`821bf8d1`，化学最好 294,984,216.56（asterios v4 λ refit）。拼装后 **27.31215**，
比我们的 **27.31193** 高 +0.00022。这就是公开件的绝对上限。

## 2026-11-15 最终：INV-45C 关闭 invsqrt 宽度线（实测）

`qingyu1232/qcc-inv45c-census`（Kaggle CPU，COMPLETE，全场 110 s）：

- **Q=46 工具链闸门 PASS**：同源码 + 比赛 kickmix，85 s 逐字节重建
  `321aff836362…35177`，exact proof `PASS_EXACT_NATIVE_TEXT_ALL_REQUESTED_INPUTS_ALL_HMR_TRANSCRIPTS`。
- **Q=45 rc=1**，死在 `patches/patch_w47_body.py:210`

```
assert builder.max_qubits in (46, 47, 48)
AssertionError
```

生成器只写了 **46/47/48** 三个手写 body，**没有 45 线 body**；而且 46 线的余量已经被
作者用掉（`A6_EARLY ... gives coef1 its 46th-wire headroom at zero extra Toffolis`）。
再加上两个 loader certificate 钉死 `peak 46 / entry 46`，Q45 需要的是**新合成一个 45 线
body + 重搜证书**，不是找回 ≤66 Toffoli 的排布余量。

**invsqrt 宽度线关闭**。修正后的估值（`score ∝ Q²`）：Q45 若 0 补价可达 GM **27.715**，
盈亏平衡 ΔT ≤ 66 Toffoli —— 但这条曲线现在没有可执行入口。

当前最佳 **27.31193**（ref 58350759，rank 177/3056）。

## 2026-11-15 追加：换轴（B → C）与 Adam 的真实轨迹

本轮在用户提供的 `jiyujia` / `zhuating` 配额上用**官方 CLI 2.2.5 + KGAT token** 重开了
Kaggle 计算，并把研究方向换了一条轴。四条实测结论：

### 1. 卡住的问题解决了，而且不需要 UI 操作

- 官方 CLI 2.2.5 支持 `KAGGLE_API_TOKEN`（`~/.kaggle/access_token_<user>`），可直接以
  `jiyujia` / `zhuating` 身份推送脚本型 kernel；两者配额 **29.1h / 30.0h GPU**。
- **脚本型 kernel 不受 qingyu1232 那三个卡死 notebook session 的影响**：同一账号
  `qingyu1232/qcc-chem-buildgate` 立刻 RUNNING。所以之前"需要用户在 UI 里手动停止 session"
  的请求可以撤回。
- 排队而不是配额：`machine_shape=NvidiaTeslaT4` 在 jiyujia 上 QUEUED 55 分钟，
  改成 `machine_shape=""`（任意 GPU）后 30 秒 RUNNING。

### 2. 官方闸门再次确认

`verifiers/dfthcsos/verify.py`：`ERROR_2_THRESHOLD = 0.020`、`ERROR_1_THRESHOLD = 0.020`、
`LAMBDA_FLOOR = 49.0`、`E_GAP_FLOOR = 3.914898`、`QUBIT_CAP = 128`、`SHOTS_PER_ADDRESS = 64`。

### 3. 新发现：T 对 **C（乘积数）** 的敏感度是 **B（基函数）** 的约 40 倍

用官方自己的 `scoreinfra/costs_prepare.py` 代入 (R,B,C)=(8,143,44) 得 model=6,662，
而实测件 T=14,728 ≈ 2×model+1,404，于是

```
dT/dC ≈ -156 Toffoli / 乘积      (+0.098 GM / 个)
dT/dB ≈   -4 Toffoli / 基函数    (+0.004 GM / 个)
```

原因是 `inner_state_prep` 的 QROAM 项 `R*C*ceil((B+1)/2^k2)`：C 是线性乘数，B 只在跨
`ceil` / `QR` 台阶时跳变。**此前整条 B<143 线（`chem_b129/CLOSED.md`）追的其实是只值
+0.02~+0.03 GM 的轴**；真正值钱的是 C。详见 `chem_c_axis/PLAN.md`。

### 4. 实测：砍 C 的精度账单 + 第一条 Adam 轨迹

`jiyujia/qcc-chem-cprobe`（L-BFGS，同预算）：连续 error_2 = **20.103 mHa（C=40，+5.33）**、
**29.127 mHa（C=36，+14.35）**，基准 (143,44) 是 14.777。

`zhuating/qcc-chem-adam-traj-129`（Adam 24,000 步，**默认 lr 1e-3**）：

```
start 20.179 -> 1000 步 100.879（被打坏）-> 13000 步 20.112 -> 24000 步 19.486
```

即默认 lr 把 L-BFGS 起点摧毁、用 13,000 步才爬回来，净收益仅 **−0.69 mHa**。
这既解释了"Adam 看起来没用"，也指出真正的变量是**学习率**。

因此下一轮的决定性实验已上线：`zhuating/qcc-chem-lrtune` —— 同一配方只把 lr 改成
1e-4→1e-6、36,000 步，分别在锚点 (143,44)（需要证明能低于 14.777）与 C 轴目标 (143,40)
（需要 ≤15.02）上跑。若 (143,40) 过闸门 → chem cost 282.4M → **GM 27.71**（+0.40）。

当前最佳仍是 **27.31193**（ref 58350759，COMPLETE），本轮没有产生可提交的候选。

## 2026-11-15 重要更正：竞赛上限是 29.91，不是 27.31

`get_competition_leaderboard`（2026-11-14T21:03 快照）原文：

```
rank 1  29.90871   Entangled Team
rank 2  29.76123   rank 3  29.57973   rank 4  29.41453   rank 5  29.14389
rank ~15 28.21378                       我们  27.31193  (rank 201 / 3058)
```

所以此前"27.31193 是天花板"**只在公开件可拼装的意义上成立**。真实差距 **+2.60**，
需要成本乘积下降 23.9%。比赛给的参考件极弱（本机只读 kmb 头实测）：
`sample_submission/invsqrt.kmb` **Q=260 / T=7,735**，`dqi.kmb` **Q=1,893 / T=5,725,461**。
差距全部来自参赛队自建电路。详见 `headroom.md`。

## 2026-11-15 化学：三条轴全部实测关闭

`jiyujia/qcc-chem-adam-traj-gpu`（T4，COMPLETE）给出本会话第一组完整 Adam 轨迹：

| 形状 | L-BFGS 连续 e2 | Adam 24k 步 | 闸门 | 判决 |
|---|--:|--:|--:|---|
| (8,143,44) | **14.777**（166 s） | 15.095（2,308 s） | ≤14.78 | Adam **不如** L-BFGS |
| (8,135,44) | 17.924 | **17.382** | ≤15.0 | FAIL（−0.54 远不够） |
| (143,44)→(135,44) 剪枝 | 17.924（直接剪） | **19.388**（先长训再剪） | ≤15.0 | 上游"prune far better"不成立 |
| (8,143,40) | 20.103 | — | ≤15.02 | 需 −5.08，Adam 只能 −0.54 |
| (8,143,36) | 29.127 | — | ≤15.28 | 连未量化 20 mHa 都过不去 |

**化学关闭**：B 轴（官方模型下只值 +0.02）、C 轴（精度账单 1.3 mHa/份，Adam 补不上）、
Adam（实测不如 L-BFGS）三条轴同时否证。

## 2026-11-15 DQI：889 是"五见证平台"

`dqi_ancilla/REPORT.md`（源码级审计）：49 个 ancilla = 24 + 1 + 24，且这 5 个调用点
**各自都恰好顶到 889**。Q 取全局最大，所以**任何单点补丁都改变不了 Q**。
唯一可行是把三个 1-bit predicate 改成经典控制：ΔT 下界 0、悲观 +600、盈亏平衡 +863，
收益 **+0.006…+0.0205**。Q=887 及以下需要新的算术恒等式。

当前最佳仍 **27.31193**（ref 58350759，COMPLETE）。

## 2026-11-15 本轮新结果：三个否证 + 一个实质进展

**否证（全部 Kaggle 实测）**

1. 化学 C 轴：`(143,42)` 10× L-BFGS = **16.362**（闸门 14.90）、`(143,40)` 短预算 20.103 →
   10× 预算 **19.006**（闸门 15.02）。10 倍预算只买 −1.10 mHa，账单是真实截断误差。
2. 化学 Adam：`(143,44)` 20.000→**15.084**，而 L-BFGS 同起点 166 s 到 **14.777**（Adam 更差）；
   `(135,44)` 17.924→**17.382**；"先长训再剪枝" **19.388** 比直接剪枝 17.924 更差。
   （`zhuating/qcc-chem-headroom` 独立复现：adam143 = 15.084，(143,36)=29.068、(135,44)=17.826）
3. DQI qubit：源码审计确认 889 是"五见证平台"（49 = 24+1+24，5 个站点各自顶到 889），
   单点补丁 Q 不变；最多 1 qubit（+0.006…+0.0205）。

**实质进展：invsqrt Q45 的墙被缩小到一条线**

`qingyu1232/qcc-inv45d-stack`（CPU）四档变体：

```
q46         Q=46 PACK=False A6_EARLY=True   -> 141 s，SHA 321aff83…  GATE PASS
q45_stack   Q=45 PACK=True  A6_EARLY=True   -> arithmetic.py:38 _compute_carry
                                                allocated 45 + requested 1 = 46 > max 45
q45_pack    Q=45 PACK=True  A6_EARLY=False  -> 同一站点
q45_a6only  Q=45 PACK=False A6_EARLY=True   -> loader: 26 + 20 = 46 > 45
```

关键：把 `PACK=True`（h0 打包）叠加上去后，**Q45 的 body 第一次真的跑起来**，loader 那关
（26+20=46）被越过，只死在 `engine/fusion/arithmetic.py:38` 的 `outgoing = alloc_qubits(1)`
—— 那一刻 45 条线全满。也就是说 Q45 的缺口是**一处、一条线**，而不是"没有 45 线 body"。
再退休一个可重建操作数（照作者给 a6 的手法）即可；成功后 ΔT 只有个位数，
盈亏平衡 66，收益 **+0.20…+0.40 GM**。

当前最佳仍 **27.31193**（ref 58350759，COMPLETE，rank 216/3061）。

## 2026-11-15（本轮）DQI 24→23 判定：不存在（决定性数值证据）

`qingyu1232/qcc-dqi23bit`（CPU，COMPLETE）。用作者自己的
`controller_work/night_root/extension24_tensor.py`（`F4096[t]/(t²+t+delta)`，rank-99 张量，
`DELTA=2048`，99 terms）做经典求值：

```
unit basis bit: 0
unit identity on 2000 random values: True        <- 1 * v == v
reachable output bits: 24 of 24   bitmap 111111111111111111111111
bit 23 reachable: True            first pairs [(0,23),(1,22),(2,21),...] -> 0x800000
span rank of {a*b : a,b basis} : 24 of 24
random products with bit 23 set: 2482 of 5000
```

结论：乘积的像就是整个 GF(2²⁴)（单位元在基里 ⟹ 2²⁴ 个值），**23 位 scratch 在代数上不可能**；
12+12 塔拆分也不省线（两个半字都是通用 GF(2¹²) 元素）。Q=888 只能来自**算法级重写**
（流式半字 + 相位重推）。

配套的构建级证据（前几轮）：墙① tail flag 与墙② third-pivot `zero_flag` 已用运行时补丁推倒
（后者用 `push_condition` 古典化，ΔT **−24**），墙③ 的活线恰为 **840 + 24 + 1**，没有可复用的
bank。**DQI 的 Q 轴在"补丁 / 位宽"意义上永久关闭。**

## 2026-11-15（本轮）invsqrt 7-AND：最后一级阶梯，GPU 执行中

0–6 AND 已全域 0/10（判定域 3,133,452 个官方输入）。7-AND 在 CPU 上按实测 8.6M 查询/秒要
11.8 h/线，本轮改用 T4（`torch.searchsorted`）执行：S3 = 385M 值在主机排序后上传，946 个目标
（`fp(target) ⊕ fp(c_i)`）逐个 sweep，命中一律在全域精确复核。

如果 7-AND 也是空，则 invsqrt 的 Q 轴在**可枚举恒等式**意义上关闭，且 T 轴早已关闭
（重建件 614 对 / 提交件 645 对可重算，0 可 hold）——两条宽度/深度路线都没有剩余便宜收益。
