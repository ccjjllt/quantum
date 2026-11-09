# invsqrt T/4 相位融合普查 + 条件 CZ 配对审计（新方向，有候选仲裁）

日期：2026-11-09；分支 `codex/invsqrt-research`；工作区 `.worktree/invsqrt/`。
基线：Public Frontier `7c10edba`（`artifacts/20261108_public_frontier/release/invsqrt.kmb`，
62Q / 53,686 ops / 静态 Toffoli-like 1,403 = CCX 1,086 + CCZ 91 + CSWAP 226，
报告成本 95,430.78）。计费 `score = Q×(Toffoli + T/4)`，
T 成本来自 41 个一般旋转的剩余误差合成预算（verifier 316–323 行），不是静态 T 门数。

本实验与已 closed 的 CCX 缓存/借用/61Q（`20261109_cache_borrow_mincut/`）无重叠：
只动相位层（Z_POW）与免费对角门（CZ/Z），不动 CCX/CSWAP 结构。

## 结论先行

1. **T 融合：closed（有 1 个亲手构建的候选 + 验证器 FAIL 仲裁）。**
   48 个 Z_POW = 41 一般旋转 + 1 T + 6 Clifford，全部无条件（depth 0、无 `if`）。
   44 对同线连续旋转对**全部被阻断**（41 对被 HMR 复位 + CSWAP 非对角触碰隔开；
   3 对 Clifford 被 CSWAP 触碰隔开）。零分支全定义域掩码HAO 似给出 11 个全零掩码
   （n=37..47），但同分支真机前缀实测推翻：21/24 个 (x,seed) 格点在 11 点取值不同
   → 掩码两两不同 → 任何角度求和合并都改变相位函数。
2. **候选 B（对合并 25860+25903 → 41→40，静态奖金 ≈458 分/7.39C）已构建并送验证器：
   FAIL**（`x=6: phase error 6.103e-05 turns exceeds tolerance 2.433e-08`，
   2509×，误差恰为被搬移角 θ/2）。T 侧无空间。
3. **CZ 配对：1,311 对 CZ + 191 对 Z 在版本化守卫下确为同币对消恒等式，
   但全部是免费门 → Δscore = 0。**CCZ（付费门）：91 个操作数三元组全部互不相同、
   0 退化 → 0 对可消。**第二选择器 [27486,27976)：19 CZ + 0 CCZ**（已是最优形态）。
   综上期望 Δscore = 0，无候选电路产出（除 1 个 FAIL 仲裁原型）。

## 1. Z_POW 相位门普查表（`phase_census.json`）

| 类（verifier `z_pow_class`） | 数量 | 明细 |
|---|---|---|
| clifford（半圈整数/半整数倍） | 6 | q0 1.5, q2 1.5, q3 1.0（op 15941/15942/15943）；q0 0.5, q2 0.5, q3 1.0（op 16277/16278/16279） |
| t（1/4 半圈） | 1 | q28 0.25（op 16275，梯-A 末端，每 shot 执行，t_base=1） |
| rotation（一般角） | 41 | 梯-A 15 个（op 15950..16270，7.6e-6→0.125 半圈）；梯-B 26 个（op 25738..25931，2.9e-11→9.8e-4 半圈） |

- 按线：q28 42 个（41 rot + 1 T），q0/q2/q3 各 2 个（Clifford）；**全部 48 个无条件**。
- 角度分布（turns=半圈/2，按量级）：1e-11×3、1e-10×4、1e-9×3、1e-8×3、1e-7×4、
  1e-6×5、1e-5×6、1e-4×7、1e-3×3、1e-2×3（合计 41）。
- 同线连续对 44 对，可合并 0 对：q28 的 41 对每对跨 1 次 `HMR q28` 复位
  （+ CSWAP 非对角触碰）；q0/q2/q3 的 3 对被 30+ 个 CSWAP 非对角触碰隔开
  （`CSWAP q27 q28 q0` 等，控制/交换线含本线即非对角）。
- 层级计数（`operation_statistics`）：L1 48 / L2 46 / L3 42 / L4 41，
  `num_t_like=1`，与上表一致（L1=2 个 Z、L2=4 个 S、L3=1 个 T）。

### 掩码分析：零分支假阳性 → 同分支实测证伪

- 零分支位并行仿真（3,133,452 输入，跳条件块/对角门，HMR/R 置零）：
  41 旋转掩码中 n=37..47（梯-B 尾部 11 个，op 25852..25931）全零 → 疑似可 11→1。
- 同分支真机检验（`prefix_branch_check.py`）：11 个截断前缀电路 + 真实 Simulator，
  相同显式 seed（共享前缀 ⇒ 相同 HMR 硬币流 ⇒ 同分支），8 个 x × 3 seed：
  **21/24 格点在 11 点取值不同**（`branch_check.json`），且读数在 seed 间完全一致
  （旋转线取值与硬币无关，但与零分支仿真不同——锥内有条件量子写，零分支跳过
  导致失真；与 `20261106_cleanup` §20 的分支教训一致）。
- 结论：11 掩码两两不同，不存在“同系数角求和”合并；最近似对（op 25860/25903，
  8 探针读数同为 `11111100`）也只是小样本巧合（见候选 B 仲裁）。

## 2. 融合候选与 Δscore（`fusion_eval.json`）

模型：`Δscore = 62×ΔT/4`（Q、Toffoli 不变，min_margin 不变），
`eps41 = 2.434041480874084e-13`（maoxin_v2 实测，n_rot=41；frontier 未测，±10×敏感带）。

| 候选 | n→n′ | ΔT（proxy/×0.1/×10） | Δscore（Q=62） | 裁决 |
|---|---|---|---|---|
| A：11→1（op 25852..25931 求和→末点，角和 9.76e-4 turns 精确二进制分数） | 41→31 | 294.7/313.3/276.0 | 4567/4855/4279 | **dead**：21/24 同分支格点分歧，无需构建 |
| B：对合并（25860 1.907e-6 + 25903 1.221e-4 → 和 1.23978e-4 精确小数，删后者） | 41→40 | 29.56/31.42/27.70 | 458.2/487.1/429.4 | **built + verifier FAIL**（见下） |
| C：Clifford 对（q3 1.0 @15943+@16279） | 41→41 | 0 | 0 | blocked（CSWAP 触碰）+ 本来零奖金 |

候选 B 仲裁（`artifacts/20261109_tphase_fusion/candidate_pair_merge.kmb`，
53,685 ops / 62Q，角度精确求和 `Fraction` 验证，`verifier_candidateB.log`）：

```
{"status": "FAIL", "error": "x=6: phase error 6.103e-05 turns exceeds tolerance 2.433e-08."}
```

误差 6.103e-05 = 被搬移角 θ₂/2（2509× 容差），与掩码差判据一致。T 融合方向关闭。

## 3. 条件 CZ 配对审计（`cz_audit.json`，版本化守卫键）

- 普查：CZ 共 16,458（无条件 0；inline-`if` 15,687；PUSH 帧 771）。
  第二选择器 [27486,27976)（过滤后 op 序号；raw 序号下同样 0 CCZ）：**CZ 19 + CCZ 0**，与 Step-1“第二选择器 0 CCZ”谱系一致。
- 方法修正：初版静态扫描得 1,360 对，抽查发现守卫位 `b12600` 在对跨度内被
  `HMR q34 b12600`（op 15141）重写——同名位≠同币。改用版本化守卫键
  （HMR/BIT_STORE/NEG/BIT_INVERT  bump 世代；PUSH 栈 + inline 位双记）后重扫。
- 结果（不交叠、跨度内所涉线仅对角门、无守卫重写、同帧同币）：
  **CZ 1,311 对（1,345 重复组，平均跨度 6,639，最大 7,288，全部顶层 inline 守卫，
  例 `CZ q50 q40 if b13` @36450/@42155，b13 仅在 op 21376 定义一次）；
  Z 191 对；CCZ 0 对（91 个三元组全部互不相同）；CCZ 零分支退化 0。**
- 计分：CZ/Z 免费 → 全部删除也只省 3,004 ops，**Δscore = 0**；
  CCZ 无对 → 无付费节省。“替换为免费门”无对象（CCZ 无退化/无对消）。
- 未构建对消电路（Δscore=0 静态可证：恒等式 `CZ·CZ=I` 同币下逐 shot 成立，
  不依赖分支；验证器运行只会复述免费门不计分）。

## 方法与证据

- kmx 解析 + 全定义域位并行仿真（48,961×uint64；X/CX/CCX/SWAP/CSWAP/HMR/R，
  条件块与对角门跳过/无操作；CSWAP (c,a,b) 语义经最小电路真机验证）。
- 同分支掩码比较：11 个截断前缀 + `km.Simulator`（显式 seed 101/202/303，
  8 个 x），共享前缀同 seed ⇒ 同硬币流，可比。
- 候选构建：`Fraction` 精确角求和 → 精确十进制串回填（`Fraction(dec)==total` 断言）。
- 复现（macOS PyPI kickmix，`.venv/bin/python`）：
  ```bash
  .venv/bin/python experiments/invsqrt/20261109_tphase_fusion/scripts/phase_census.py
  .venv/bin/python experiments/invsqrt/20261109_tphase_fusion/scripts/prefix_branch_check.py
  .venv/bin/python experiments/invsqrt/20261109_tphase_fusion/scripts/fusion_eval.py
  .venv/bin/python experiments/invsqrt/20261109_tphase_fusion/scripts/build_candidate_pair.py
  .venv/bin/python experiments/invsqrt/20261109_tphase_fusion/scripts/cz_audit.py
  .venv/bin/python data/competition/verifiers/invsqrt/verify_submission_invsqrt.py \
      artifacts/20261109_tphase_fusion/candidate_pair_merge.kmb
  ```

## 验证范围声明（必须如实区分）

- **官方验证器运行 2 次**：均为同一候选 B 电路
  （`candidate_pair_merge.kmb`）的完整验证，2 次皆 **FAIL**
  （`x=6: phase error 6.103e-05 turns exceeds tolerance 2.433e-08`；
  失败在首批 shots 内触发，非全量 PASS）。
- **未运行基线 7c10edba 的官方验证**（报告成本沿用公开值；eps 用 maoxin_v2
  实测值代理并给 ±10× 敏感带，不假装是 frontier 实测）。
- 其余全部为**静态结构统计 + 零分支/同分支仿真探针**（不改电路语义；
  零分支掩码仅作筛查，裁决依据是同分支真机读数与验证器 FAIL）。
- **未产生可提交候选**（唯一构建电路为 FAIL 仲裁原型），无打包、无提交、无推送。
