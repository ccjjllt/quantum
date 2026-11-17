# 2026-11-17 深度并行轮 — 总结果

四条研究线并行（DQI 宽度/均值 / invsqrt 合成 / chemistry 形状与 λ / 公开前沿侦察），
全部在本机只做静态分析与算术，所有电路仿真与官方验证在 **Kaggle CPU kernel**
（`enable_gpu=false`）。本文件只写**已实测/已由官方公式确证**的东西。

## 0. 一句话

**没有找到任何 PASS 且更便宜的候选；28.15083 仍然是「公开字节 × 三条腿实测下界」的上限。**
本轮的价值是把三条腿「还能不能动」从「不知道」变成**三个带数字的 NO-GO**，
并留下一个已经端到端跑通的复核/出包管线。

## 1. 结果表

| 线 | 攻击面 | 判定 | 决定性数字 |
|---|---|---|---|
| **DQI** | 全 50 条 pool wire 的宽度 | **NO-GO** | 最便宜单 wire `q889` 重算 **1,831 T/qubit**，盈亏平衡 **826 T**（超 2.2×，GM 28.12526 = **−0.026**）；全池平均 3,822；整池 840Q 需 191,122 T，tie 预算 45,005 / 金线 21,254。**即使按物理不可能的「每窗口 1 个 AND」下限 62,664 T，GM 仍只有 27.76** |
| DQI | mean-T 条件化 | **NO-GO** | 全件均值折扣只有 **873 T = 0.237% T = +0.008 GM**；45,356 T 已在 1-bit 条件区且 ~98% 触发；门集无 `H`，`HMR`=X 基测量 ⇒ 无法把计算基值读进经典 bit |
| DQI | 新解码器代际 | **NO-GO** | 论文给出的空间最优 `2nb`=**1,680 Q**（参考电路 1,893 Q）；我们 890 Q = 0.53×；LLM 解码器 442,397 T @ 1,837 Q，Q²T 差 **5.1×** |
| **invsqrt** | compute/uncompute（MBU） | **NO-GO** | 付费 uncompute 只占 **≤6.7%**（52 对镜像 CCX / 1560）；**1,276 个 HMR 已把 83.6% 的 AND 用测量回收**，630/697 条件块只含相位门 ⇒ 这条路线已经用尽 |
| invsqrt | 宽度 Q44 | **NO-GO** | 令牌峰值 **44 @ op 1689**，44 条线全部承载令牌；**0 对** scratch 生命期不相交；x 线本身被当 AND 工作区（503/1526 CCX 目标 + 360 HMR） |
| invsqrt | Toffoli 面复查 | **NO-GO** | 0 相邻对消 / 0 死 CCX / 0 CCX→CX 降级；唯一量化发现（2 个「死」CCZ）被官方 verifier 全 shots **FAIL 证伪**（`x=12: phase error 0.5 turns`） |
| invsqrt | **Q43**（+0.217 GM） | **NO-GO** | 逐线定价表（22 行）：预算 **+158.2 T**，而最近的两条也超 —— q25 **≥77 Toffoli = 308 T（1.95×）**、q24 ≥220 T（1.39×），其余 4.1×–957×。按 q25 造的 Q43 候选被官方 verifier 判 **FAIL: `x was not restored`**（kernel `jiyujia/qcc-invsqrt-q43-retire-q25` v2），原因已定位（holder 语义须为「支集**等于** {atom}」，按精确语义 77/80 个读点没有 holder） |
| **chemistry** | 形状（rows = 76 + K·B/C） | **NO-GO** | `B ≤ 128` → `inner_temp` 从 303 跳到 510–575 ⇒ **Q ≥ 629（+47%）**；唯一保 Q=427 的是 `B∈[129,255]`，K=352 时最小 rows=1,108，最好只 +0.16 GM，且 `(8,129,44)` 连续 e2 19.83 已超门 |
| chemistry | brot=7 | **NO-GO** | `inner_state_prep` 不依赖 β，β 只进 Givens(−300 T) 与 Q(−5) ⇒ 真实收益 **+0.30 GM** 而非 +0.6；7-bit 网格把量化罚从 13.7 翻到 ~27 mHa |
| chemistry | 免费形状缩减 | **NO-GO** | `W` 无全零 copy 列 / base 行 / rank（最小列 Σ\|w\|=0.717） |
| chemistry | Λ 的公开基线 | **NO-GO** | starter kit 只有 FeMoCo 一个可提交：Λ=308.45 / λ_eff=49.25 / e2=16.13 mHa，全面劣于我们 283.15 / 46.92 / 20.00 |
| chemistry | **loader 的 T 轴** | **NO-GO** | 15 个 loader 全是 `CX+CCX+R+HMR+CZ+Z`，**0 PUSH/POP、0 CCZ、0 条件 Toffoli** ⇒ `mean T = static T = 268.1`，没有条件化面；每条 Toffoli 都是无条件 CCX，77 条 ancilla 各被写 1 次再 HMR 免费清掉 ⇒ **MBU 无可回收对象**；表双稠密（比特密度 50.0%、ANF 满支撑 2,048/2,048、953/bit）⇒ 无代数捷径。shipped 是「共享乘积网络」，**比唯一公开构造便宜 4.6×**（4,022 vs 18,270 per pass）。金线要求 angles −10%（每电路 212 vs 265–292）|
| chemistry | **Λ 的 \|W\| 集中杠杆** | **算术 +0.6~+2.7 GM，交付成本在盈亏线两侧** | `lam_h2 = 0.25Σ(a+|W|)²` 里 **52% 是 cross 项** `2Σa|W| = 452.6`；`W` 不进 e2，只进 `h1_prime`/`E_SOS`。把 `\|W\|` 集中到最小 a 的 k 个 cell：Λ 283→195（k=44）/ 174（k=1）⇒ **λ_eff 38.8/36.7 ⇒ GM 29.99/30.56**。三个卡点：①`E_gap` 恰在 floor（需 `sign(W)` 搜索补偿）；②76 条 one-body 行须重量化且 e1 ≤ 20 mHa（现件贴门无余量）；③**没有公开 emitter** 能同成本重建 15 个 loader（唯一公开的 `taylorclark637/dfthcsos-generator` 是 1,218/电路 = ×2.94），且 **0 成本改 CX 已否证**：292 个 Toffoli 里 80 个是地址乘积、**212 个与表相关**（操作数是 ancilla∧ancilla），块局部改写需 **+40…+200 CCX/电路**，而**盈亏平衡是 +120/电路** |

| **侦察** | 公开新字节 | 无价值 | 唯一新 DQI `575b043f`：346,409,762,292.72（3 salts 3/3 PASS）→ 组合 GM **28.15093204（+0.00010）**，且有已知 weight-35 见证错误 → 不占提交名额 |
| 侦察 | 开源/论文 | 无可用代码 | arXiv 2610.23832 / 2610.22367 / 2502.15882 均无代码；`alexchilton/qcc-schur-dqi-rebuild` 是 24.94 时代；`Agnuxo1/qvc-chemistry-compiler` composite 26.98–27.02 更差 |

## 2. 本轮新增的工具与证据

| 资产 | 说明 |
|---|---|
| `scripts/kgpu.py` | CPU-only Kaggle kernel 推/查/取（账号 `jiyujia` / `zhuating` / `qingyu1232`） |
| `scripts/gm.py` | 三腿官方 cost → GM；`--current` 精确复现 **28.15082863** |
| `integration/` | 通用三腿集成：18 成员按 SHA-256 定位 → 未改官方 verifier full shots → GM → `submission.zip`。**已端到端 PASS**（`qingyu1232/qcc-deep-integrator-re-verify-28-15083` v3） |
| `docs/ceiling-20261117.md` | 天花板备忘：逐腿交换率、金线所需单腿、榜首反解 |
| 各线 `RESULT*.md` | DQI 全 50 wire 表、invsqrt 逐线角色表、chem 形状预算、侦察扫描表 |

## 3. 结论与下一步

**28.15083 是这一代电路的极限。** 金线 28.71339 需要单腿 **−5.77%**，而三条腿都已在
各自族的下界（DQI 差 2.2×、invsqrt MBU 已饱和、chem Λ 贴精度门）。榜首 31.01379
反解为「至少两腿同时领先」，最可能是 chemistry 明显更便宜 + DQI 接近 840 —— 都是未公开的
新一代电路。

剩余两个月唯一有意义的方向（按性价比）：

1. **chemistry：在 shipped 形状上做「min Λ s.t. e2 ≤ 15 mHa」的全局 (U,w,W) 优化**
   （队伍只做过固定 words 的局部 refit）。Λ 每 −1% → +0.17 GM；Λ 283→250 → +0.4 GM。
   已派给 chem 线，判据 cost < 294,643,137.73。
2. **chemistry loader：MBU/条件化重写下界**（angles 占 T 的 55%；−20% → +0.37 GM）。
   已派给 DQI 线（其 opcode 级分析能力）。
3. **DQI/invsqrt 换族**：需要新的可逆调度 / 新合成体，属于研究项目，不是 tape 手术。

## 4. 验证范围声明

- 三条腿的官方 cost 由本会话 kernel `qingyu1232/qcc-deep-integrator-re-verify-28-15083` v3
  用**未修改官方 verifier** full shots 复算：chem 294,643,137.73357135 / DQI
  348,004,440,260.464（默认盐 dirty draw）/ invsqrt 74,797.36535717871。
- 公开榜 28.15083 属于 ref `58454232`（clean draw）。本轮**没有提交**任何新包。
- 各线的静态结论（wire 表、令牌峰值、形状算术、Λ 分解）都是读 tape/npz 与官方公式算术，
  不是仿真结果；凡涉及 PASS/FAIL 的都单独标注了 kernel。
