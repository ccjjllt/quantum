# dfthcsos 系统性复盘：新架构方向（2026-11-10）

分支 `codex/dfthcsos-research`，工作区 `.worktree/dfthcsos/`。
本复盘不重复 closed 结论的推导，只引用；不训练、不跑验证器。
所有数字来自所列来源的已记录结果，本轮新增的仅为只读静态对比
（npz/kmb 字节比较 + numpy Givens 解码，属于精确算术小算例，无 shots、无 `verify.py` 调用）。

来源版本：
`CLOSED_RESEARCH.md`（11-09 行）、`20261108_frontier_refit/README.md`、
`20261109_compact_multikink/README.md`、`20261109_joint_budget/README.md`、
`20261109_longloss/README.md`、`20261109_ubasis_retrain/README.md`、
`20261109_angles_r5/README.md`；主仓库 `references/public-baseline.json`
（gengsr `lb-25-2268-shifter-46-own-chemistry-loaders` v1，2026-11-10 采纳）、
`docs/research-map.md`；官方验证器 `data/competition/verifiers/dfthcsos/`
（只读：`SCORING_README.md`、`verify.py`、`scoreinfra/`）。

## 1. 历史脉络

化学契约（见 `SCORING_README.md`）：`score = lambda_eff × T_total × Q_total`，
其中 `lambda_eff = sqrt(E_gap·(2·Lambda − E_gap))`；
硬门 `error_1/error_2 ≤ 20 mHa`、`Lambda > 49.0`、`E_gap > 3.914898 Ha`（严格大于，
等号拒绝）；每条 ANGLE 电路 ≤ 128 qubit；`Q_total` 合并存活寄存器并对可复用
workspace 取 max。

| 节点 | λeff | T/Q | score | 增量来源 |
|---|---|---:|---:|---|
| Syed V9 (`c76d568c`) | 46.893662078701 | 14966/427 | 299,673,103.43 | 基线（`CLOSED_RESEARCH.md` §B） |
| Public Frontier (`c1321df2`，源自 Maoxin123 V2) | 46.891275464716 | 14966/427 | 299,657,851.81 | **−15,251.61**，全部来自 `W`/`H2_I` 权重（含 λ58 谱折点钉扎与三门裕度收紧至 ~2.3e-10 Ha）；15 个 `angle_k`、`U(8,143,76)`、`tree(75,2)`、`angle_words(1220,75)` 与 Syed 逐字节一致（`20261108_frontier_refit` §1） |
| 切空间 refit (`b9eced3e`) | 46.891275349493 | 14966/427 | 299,657,851.08 | **−0.74**，78,080-shot 本地 PASS（salt `local-frontier-refit-20261108`）；KKT 切空间投影梯度范数 0.13–0.15，固定 `(8,143,44)` 字已近极限（`20261108_frontier_refit` §2、`CLOSED_RESEARCH.md` 11-09 行） |
| gengsr 系（v1，作者数 299,497,671.22） | 46.891275464716 | **14958**/427 | 299,497,671.22 | **−160,180**，见下节静态拆解 |

### gengsr −160K 拆解（本轮静态对比，新证据）

对照 `release/dfthcsos/submission.npz`（= `c1321df2`）vs
`artifacts/20261110_public_candidates/gengsr_252268/submission.zip` 内
`dfthcsos/submission.npz`（主仓库只读；`cmp/gengsr_252268.npz` 与 zip 内 npz
逐字节一致）：

- **权重没变**：`W(8,143,44)`、`H2_I(8,44)` 逐字节完全一致（`exact=True`）。
- **角度字变了**：`angle_words(1220,75)` 有 14,935/91,500 字不同（16.32%）；
  `U(8,143,76)` 19,927/86,944 元差异 > 1e-9（maxabs ≈ 1.99，即符号量级）。
- `tree_edges`、`H1_I`、`Hsym_lower` 逐字节一致；15 个 `angle_k_*.kmb`
  与当前全不同（抽查 batch0/1/14 SHA 皆异，batch0 字节数 390,615 → 400,247）。
- 作者 `verify_results.json`（PASS，78,080 shots）：`angles_toffoli` 8296
 （当前 8304，**−8 T**），heuristic 6662 不变，Givens 2250 不变，
  故 `T = 14958`（−8）；`metrics`（error_1/error_2/Lambda/E_gap/λeff）
  与 `c1321df2` 在 1e-12 内一致。

Givens 解码核验（固定树、`brot=8`，numpy 精确算术）：1220 行解码向量与
`c1321df2` 的内积全部为 **+1（917 行）或 −1（303 行）**，偏差 ≤ 6.7e-16；
685 行有字变化，685/685 全部 gauge 等价（中位每行 24 字变化，2–42 分布）。
连 one-body 区（row 3 起）也在翻转之列——THC 一/两体重建用外积，
逐行符号翻转是化学上**精确对称**操作，与 W 无关。

结论：gengsr 的 −160K **全部来自 T −8**（46.89127546 × 427 × 8 ≈ 160,181），
λeff 一字未动。它不是权重 refit，而是一次**规范变换 + loader 重综合**：
303/1220 行符号翻转 → 等价但不同的字表 → 更便宜的 ANGLE 实现（8304→8296）。
同包 `ozer_v91` 的 npz 与 gengsr **逐字节一致**，但 15 个 kmb **0/15 相同**——
同字表下 loader 综合非唯一（ozer 无作者 verify 数，T 未知，只记多样性存在）。
`maoxin_25218` 则是互补轴：`U`/字/tree 与 `c1321df2` 逐字节一致，
`W`（maxabs 6.4e-2）/`H2_I`（maxabs 6.8e-2）不同——纯权重分支。

含义：分支此前默认的"角度字固定"前提被外部证据打破。
`CLOSED_RESEARCH.md` A.4（loader 在固定字下已最优）与 C.2（7568 对列旋转
最大下降 5.33e-15）都不覆盖**换等价字 + 重综合**这一轴——两者证的是
固定字表内的最优性，gengsr 换的是字表本身。

## 2. 大收益杠杆排序（量化）

以 `b9eced3e`（299,657,851.08，`T×Q = 6,390,482`）为分母：

| 杠杆 | 量级 | 分数换算 | 状态 |
|---|---|---:|---|
| `T×Q` −1% | ≈ **−300 万分**（1% ≈ 2,996,579） | −3.0M/% | 主杠杆 |
| λeff −1% | 同量级 | −3.0M/% | 固定字下已近 KKT 极限（§1），须换字才有空间 |
| R5/B135/C70 保守（angles 不变，精确 `SpinFreeData_V1`） | `T×Q` −0.23%（heuristic 省 35 T） | ≈ −0.70M | 精确数；打平线 λeff ≤ 47.0012（+0.23%）。上限低 |
| R5 预算（需新 planner 电路） | `T×Q` −5.27%（T 14177，打平 λeff 49.5009） | ≈ −15.8M | 实测新电路只拿到 −0.41%（T 14905，缺口 **728 T**；heuristic 省 35 + angles 省 26 = 61 T，仅为预算 754 T 的 8%）。且新字连续 e2 尚在 85–182 mHa，未成候选（见下） |
| R4/B131/C83 保守 | `T×Q` −1.70%（220 T + Q−1） | ≈ −5.1M | 精确数；打平线 λeff ≤ 47.7026（+1.73%）。PSD 必要界 9.687 mHa（必要非充分） |
| R4 预算 | −8.53% | ≈ −25.6M | 同上，需新电路 + 训练过门，双重未达 |
| R6/B143/C59 保守 | +0.13%（更差） | — | closed，不训（`compact_multikink` §1） |
| gengsr 规范变换（已实现） | −0.0535%（T −8） | −160,180 | 外部 PASS；可与 `b9eced3e` 权重叠加（§4 方向一） |
| 固定字 W refit（KKT 极限） | −0.00000025% | −0.74 | 已 PASS，无后继（`frontier_refit` §2） |
| 第二折点 W-only（j59，正，理想上界 −1372） | 实际 **+0.17 / +18.4**（step 4e-7/4e-6，曲率主导） | 正（变差） | closed（`compact_multikink` §3） |
| 负特征值钉扎（j57，理想 −252K） | 假象：`E_gap` → 3.90831，破严格下界 | FAIL | closed（同上；KKT 线性估计即 +8.9） |
| 联合 W+1LSB Newton | **+711 / +321**（两探针；W 收敛但 λeff 代价 169/309 uHa） | 正 | closed；LSB 三门齐破（e1/e2/E_gap 裕度仅 ~2.5e-11 Ha ≈ 0.025 nHa），回缩价数倍于收益（`joint_budget` §1） |
| 误差预算再分配 | e2 汇率 −2203/uHa，但剩余裕度仅值 **~0.05 分**；e1 汇率是 e2 的 1/1390；E_gap ±1uHa = ±35.7 分 | ~0 | 门内无预算，closed（`joint_budget` §2） |
| 单 LSB 翻转最小扰动 | +3.96 uHa vs 裕度 0.000025 uHa（1.6e5 倍） | FAIL | closed（`compact_multikink` §4） |

训练盆地（ sufficiency 侧，供新形状评估用）：
R5 同起点 500 步 182.0 mHa（变体 181.3，同盆地；换基 rand 373/dft 593/R4-eigrr 180；
分阶段 297.7；Huber 440.8/joint 183.5），分段续训 2000 步到 85.31 mHa，
指数尾渐近 L2 **63.3** / joint 74.3 mHa——门（20）在渐近线之下 43+ mHa，
按当前尾律无限步不可达（`longloss`、`ubasis_retrain`）。
PSD 必要界（R5 7.552 / R4 9.687 / R4-C82 10.267 mHa）不能证伪形状，
卡住的是充分性（共享 U 基 + L1 + SOS gap + one-body + 8-bit 量化 + 综合）。
另：`Q_total = 84 + 40(J·brot) + max(90, 303, angles_temp) = 427`
被 heuristic inner_temp 303 钉死——angles_temp 降到 303 以下不搬动 Q；
ANGLE 单电路 128-qubit 上限当前已顶满（gengsr `angles_qubits=128`），
R5 新电路 qubits_max 101 反有 headroom。

汇率小算例（精确算术，非验证）：`T −8 ↔ −160K` 实测成立；
反推 `T −1 ↔ −20,023 分`，`Q −1 ↔ −46.89×14966 ≈ −701,775 分`（Q 目前被
inner_temp 钉死，动不了）；λeff −1e-6 ↔ −6,390 分。
R5 预算缺口 728 T ↔ 约 1,458 万分——这就是新电路必须补的量。

## 3. 新架构方向

已关闭的不再列（W-only refit/第二折点/联合 Newton/LSB/换 loss/换基/
分阶段/换位宽——只见上表引用）。以下方向均不在 closed 范围内：

**方向 A：规范 + 树 + loader 联合优化（固定化学，零训练）。**
对称性保证：逐行符号翻转（2^1220 空间，已证 303 翻转 −8T）、
Givens 树重选（验证器只验形状 + 父先子 + 0 根连通，树本身是自由变量，
同向量不同树 → 不同字表 → 不同 loader 成本；化学 metrics 逐位不变）、
loader 重综合（同字非唯一实现，ozer/gengsr 0/15 同批即证）。
筛选成本只有"字表生成 + loader 构建 + T 计数"，比训练便宜数个量级，
且候选化学正确性由构造保证（metrics 不变是定理：外积重建下符号/树重参
不改变积分）。未知：gengsr 的 303 翻转是否最优、树空间有多大油水、
翻转×树×综合三者的联合搜索策略（贪心/退火，用 planner 静态成本做代理，
kickmix 实测只在终选做）。

**方向 B：loader 族与装配参数扫描（固定字，零训练）。**
A.4 关闭的是"固定 (J,brot,字表) 下的共享 planner 最优"。
未被关闭的自由度：`J`（batch 数，`K=ceil(75/J)`；`J·brot` 常驻 40 qubits，
动 J 同时动 T、Q、`angles_temp` 三者）、`brot`（字宽动 Givens 精度 2250 T
与 heuristic 两项，化学字需重舍入——属半训练，要单列成本）、
非共享-planner 的第三种装载（朴素 QROM 已证 +94%，排除；但共享 planner
之外的结构化综合，如按 gauge 等价类拼 batch、delta-XOR 感知的跨批联合
优化，未被探索——注意 C.1 helper 上限 58 针对的是旧构造）。
筛选同样零训练（同字表，T/Q 直接可测）。

**方向 C：紧凑形状重训练（换字，高上限，高阻塞）。**
R5 预算 −5.27% / R4 保守 −1.70% 是全场最大的预算数字，
但充分性三关全未过：连续 e2 离门 43–162 mHa（渐近线下）、
8-bit 量化把未收敛字炸到 Ha 量级（`angles_r5` §2：e1 2.31 Ha / e2 461 mHa）、
新电路 −0.41% 只是成本数（字不可用）。PSD 界 + 训练曲线表明缺的不是步数
（2000 步 85 → 渐近 63）而是 basin/优化器/表达范式（本机 JAX cpu 已证伪
Huber/joint/换基/分阶段四条路）。此方向需 GPU + 换优化器（二阶/自然梯度）
或新种子范式，且必须把"量化后门内 + 新电路 T 实测"作为双门控，
不再接受连续 e2 单指标。

**不列为方向的**：误差预算再分配（门内裕度 ~0.05 分，汇率已算死；
"改门"不可行——阈值是验证器硬编码，`Lambda>49`/`E_gap>3.914898` 动不了；
`joint_budget` §2）。门不动，只能走"不碰门的改进"——正是方向 A
（gauge 操作的 Δe1=Δe2=ΔE_gap=0，裕度消耗为零）。

## 4. 排序（2-3 个，先后即优先级）

1. **A：规范×树×loader 联合优化（P0，零训练，可直接开工）。**
   外部已证 −160K；与 `b9eced3e` 权重正交可叠加（gauge 对称 W-无关，
   同一 303-翻转模式可原样搬到 `b9eced3e` 字表，预期 ≈ 299,657,851 − 160,181
   ≈ 299,497,670，待一次 `evaluate_words` + loader 重建 + 78k-shot 验证确认，
   复盘阶段不断言 PASS）。搜索空间大（2^1220 × 树 × 综合），gengsr 几乎
   不可能是最优——8 T 只是起点。第一步：复现 gengsr 翻转模式的 T 节省
   归因（哪些翻转贡献了 8 T），再贪心扩展。
2. **B：J/装配/第三种装载扫描（P1，零训练，与 A 共工具链）。**
   与 A 共用"loader 构建 + T/Q 计量"管线，可并行；单项期望小（J 扫描是
   百 T 级扰动），但与 A 的字表搜索是乘法关系（便宜字 × 便宜装配）。
   先做 `J ∈ {3,4,6,7,8}` 在当前字表的精确 T/Q 表（`SpinFreeData_V1` +
   planner 静态 + kickmix 实测三列对齐），再决定 brot 是否值得动。
3. **C：紧凑形状重训练（P2，冻结至 GPU/新优化器就绪）。**
   上限最高（R5 预算 −15.8M），但本机 cpu 已把四条路走死，
   继续投步数是负期望。冻结条件：有 GPU 后以"2000 步连续 e2 ≤ 40 mHa
   且量化字 e1/e2 ≤ 50 mHa"为第一门控，否则不发新电路、不跑验证器。

## 验证范围声明

- 本轮**无 78,080-shot 运行、无 `verify.py`/`manual_verify.py` 调用、
  无训练、无新候选 NPZ**。78k-shot PASS 仅指既有 `c1321df2` 与 `b9eced3e`
 （salt `local-frontier-refit-20261108`）与作者自带 `verify_results.json`
 （gengsr，submission SHA `634b84e5…`，npz SHA `9c358a8e…`）。
- 本轮新增计算：只读 npz/kmb 字节比较 + numpy Givens 解码内积
 （§1 内积 ±1、偏差 ≤ 6.7e-16）；`T −1 ↔ −20,023 分`等为乘法口径换算，
  非验证结论。
- 未提交 Kaggle，未推送，未改官方验证器、官方数据与共享环境；
  主仓库三包只读引用（`artifacts/20261110_public_candidates/`），
  未复制大产物进本工作区。
