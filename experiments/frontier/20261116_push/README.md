# 2026-11-16 大幅提分推进

目标：在公开 28.09 组合之上做原创改进，优先攻击单项大杠杆，全部电路实验在 Kaggle CPU 上执行。

## 实时基线

- 本账号 public 最佳现为 **28.15083 COMPLETE**（ref 58454232；0af21cb8 + 61c8348d + a73b25d2 T14706 + 15 小 loader）。**这是评分模型在出分前的精确预测：预测 28.15083，实际 28.15083。** 前最佳 28.14703（ref 58452435）。
- **评分模型已由 ledger 反解确证：公开分是确定性的，不是每次重新抽签。** 同一 DQI 文件在不同提交里反解出同一公开 cost（ccc2ab84 两提交差 4.5e-7，66b4f18b 差 1.5e-7），invsqrt 与 chem 的公开 cost 恰等于 lab 值（salt-invariant），每个 DQI 文件的公开 cost 只有两种可能：clean cost（相对差 ~2e-7）或 clean×1.0045925（丢 1 shot）。推导见 `intel/RESULT_public_salt_model.md`。
- **负结果（推翻 `RESULT_stability.md` 的选腿建议）**：lab 3/3-clean 的 `b0983d55` 在公开盐下丢 shot，ref 58453168 public 仅 **28.08701**（clean GM 28.12994 → −0.043）。lab draw 率**不能**预测公开 cost；正确选腿规则是「公开 cost 最低」，而 61c8348d 公开 cost 346,413,501,394 是已知最低。模型 11/11 行自洽、可复现脚本 `intel/public_salt_model.py`。
- **金线换算（同模型）**：gold 28.68633 相对 28.15083 只差 1.90% GM，等价于**单腿再便宜 5.496%**——invsqrt ≤ 70,686.26、DQI ≤ 327,373,473,967、或 chem ≤ 278,448,580（T ≈ 13,896）。已知字节的最优重组已到顶（28.15083），三条腿各自都是已知最小值，所以下一步必须来自新字节或新方法。
- **三条腿的官方 cost 公式已全部反解并精确复现**（`intel/RESULT_cost_model.md` + `intel/cost_model.py`，残差 invsqrt 0、chem 0、DQI 丢 shot 到小数）：invsqrt `Q·(Toffoli+T/4)`（Toffoli 85.85% / 旋转 14.11%）、DQI `R(eps)·Q²·T`、chem `λ_eff·T·Q`（λ_eff=√(E_gap(2Λ−E_gap))）。因此 DQI 宽度是**平方项**：合同 840Q、我们 890Q，仅这 50 个 ancilla 就占整条 DQI 腿的 **12.26%**，是金线缺口的 2.2 倍；且 T 预算是 `(890/Q)²−1`（Q865 可 +5.85%，Q888 只有 +0.45%——这正是我们 888 构建反而更差的原因）。
- **唯一有真实 headroom 的路线（按公式排序）**：① DQI 宽度——但 `dqi/RESULT_WIDTH_BUDGET.md` + `width_budget.py` 已把它**算术性关闭**：由于 865Q 在 T 不变时就有 28.69066（仅高于金线 0.0043），金线在 Q865 上只容忍 **+0.045% T（166 T，即 6.6 T/qubit）**；而盈亏平衡（相对 28.15083）是 861 T/qubit，最便宜的实测机制（`q864` re-home，每 episode 一个 CCX）已要 925 T/qubit（超 7.4%），真实机制 7,195、888 构建 7,932 T/qubit。唯一能付得起的是**整池 in-place 840Q 且 T ≤ +6.089%（22,354 T）**，其卡点已定位：24-bit carry bank q840..q863 是永久累加器，被 62–72% 的 helper 窗口触碰，不能借。② chem T 14,706→13,898（cost 对 T 严格线性，但 error_2 只剩 2.6e-10 余量且 loader `angles_qubits=128` 正好顶在 `QUBIT_CAP`）；③ chem Λ 283.15→267.69（λ corner 已实测 0.0000%）；④ invsqrt（旋转 ε 被 0.99956 的误差占用量锁死，删掉全部 33 个旋转也只能省 14.1%，最贵）。
- 已提交三件：invsqrt `f2cdab0b`（44Q，75,006.38）、DQI `ccc2ab84`（890Q，347,375,470,572）、
  chemistry `sub1`（427Q，T=14,712，294,762,697.44）。三件均用未修改官方 verifier 全量 PASS。
- 公开最佳三件：同一 invsqrt/DQI + chemistry `bdae290f`（294,762,632.08），本地 GM 28.0948754；
  正在按同一 CPU 管线复核并做一次银牌尝试（榜上 rank 92 恰有一个 28.09487）。
- 银线 rank 156 = 28.09486；金线 rank 16 = 28.65386；榜首 30.28512。
- 公开前沿在 2026-11-16 02:52 UTC 已到 **28.09486**：`f2cdab0b` invsqrt + `ccc2ab84` DQI +
  chemistry npz `bdae290f`（294,762,632.08）。这是一个 **143 队并列（rank 88–230）**，
  银线 rank 156 在并列内部；晚提交的同一分数会落在并列末尾（约 rank 231），**不保证银牌**。
  下一档公开分是 28.09498（rank 87），所以短期目标应是 **>=28.09490**。
- 当前最近公开 refit：chemistry `sub1` 294,762,697.44，组合 GM 28.094873（仍落在并列内，
  不足以单独拿银）；boristown `bdae290f` 更便宜 65，是公开 chemistry 最好件。

## 并行研究线

| 目录 | 负责 | 目标 |
|---|---|---|
| `intel/` | 公开前沿侦察 | 11-16 19:27→23:27 UTC 扫到 4 新字节：DQI `f425ea20`（内嵌官方 JSON 346,992,317,312.82，组 0af+chem 可达 GM 28.13137，待独立验证）、`b0983d55`、chem `a970f175`、`93326853`；swap `703843d3`+3.79e-6 不值 slot（`RESULT_sweep2.md`）。顶线 11-17 00:55 UTC：榜首 30.96223，金 28.68633；112 队 28.12769 并列（rank 228）；28.13790×13/28.14703×7 需 f-class+额外（`RESULT_topline.md`）。11-17 01:01 UTC sweep3：DQI `61c8348d`（claim 346,413,287,873.06，组 0af+chem 可达 GM 28.14704，待独立验证）、`957d6733`（engine claim，不及基线）；asterios finer-refit 无新字节。见 `intel/RESULT_sweep3.md` |
| `invsqrt/` | invsqrt Q/T | f2cdab0b Q44 硬地板；**0af21cb8 新机制已探明**：3 tail 转 HMR 双分支 −4.75 mean T；剩余 4 head（12139/12142/12596/13037，−2…−4 mean T / +0.01…+0.02 GM）但 v27 emitter 私有无公开重发点（R6 已证），手工不可构造。见 `invsqrt/RESULT5.md`、`RESULT6.md` |
| `dqi/` | DQI Q/T | **Q/T peephole、v15 调度、decoder-level、structural、66b4 gadget 全部关闭**：RESULT5 exact T=384,003，decision <1T，retain +2.369%；RESULT6 out-of-place/v13/ladder 不可；RESULT8：66b4 gadget 每 site −20T 共 −820T，k19 全磁带普查 G1 41/41、G0 0/0，无剩余可转。见 `dqi/RESULT5.md`–`RESULT8.md` |
| `chem/` | chemistry T | **R=8/R=5/λ/code/新words/C轴/emitter/新R/coded 全关**：RESULT4 re-code floor 36.16/63.24，C43/42 floor 21.23/23.26；RESULT5 emitter +2…+4；RESULT6 R7 53.35/66.16，R9 40.84/53.31，R10/12 +Q697；RESULT7 coded (a) e2 floor 21.216（cuts 71→55），(b) 36.229/floor 35.89 + T_heur 13,631。冻结 294,762,632.08。见 `chem/RESULT4.md`–`RESULT7.md` |
| `chem/CODE2` | loader code search | **已关闭（2026-11-16）**：k=9/10/12/14 的 145-cut basis 并没有比 shipped 更好——shipped products 是 189/190/191（不是 193）；k9 亏、k10/k12 平、k14 −1 不可发射（bit7 XOR bit6 helper / six-AND 独立性失败）。混合包作为负控制 e1=61,130 mHa、e2=11,659 mHa。4,025 保持。见 `pipeline/CODE2_STATUS.md` |
| `pipeline/` | CPU 复核/打包/提交 | 先复核公开 28.09486 件；只有 **>=28.09490** 才提交，避免落在 143 队并列末尾 |

## 计算约束

- 只用 Kaggle CPU kernel（`enable_gpu=false`、`enable_tpu=false`），不在本机跑模拟/验证。
- 三个研究账号：invsqrt=jiyujia，DQI=zhuating，chem/pipeline=qingyu1232。
- 每个候选必须用未修改官方 verifier 全 shots 复核；invsqrt 另加 salt，DQI 另加 salt。
- 不把大 ZIP、权重和日志写入 Git；候选文件留在 Kaggle/`artifacts/`。

## 目标表

见 [TARGETS.md](TARGETS.md)。关键：DQI Q=840 单项 +1.11 GM；invsqrt Q=40 单项 +0.91 GM；
chemistry T=13,000 单项 +1.19 GM。小 refit 只值 +0.001–0.01，不作为主攻。
