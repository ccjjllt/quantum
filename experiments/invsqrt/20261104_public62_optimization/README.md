# 62Q invsqrt：公开基线迁移 + 有界结构优化（2026-11-04/05）

## 父基线与迁移候选

- 父基线：Kirill V5 `kirill_v5_invsqrt.kmb`（SHA `ed77292a…172b`，62Q，48088 ops），
  单 seed 官方复核成本 98309.13505417833（seed 20261031，200,540,928 shots）。
- 迁移候选：`artifacts/20261104_public62_optimization/invsqrt/public62_nofallback.kmb`
 （SHA `5541151c…766ff38`，62Q，49904 ops，全部 93 条 Z_POW 逐项不变）。
- 生成器：`experiments/invsqrt/20261104_public62_optimization/migrate_public62_nofallback.py`
  （`--baseline` 即真实构造输入并校验固定 SHA；只替换窗口 `[27745,28753)`；
  窗口外逐项一致；新比特 `42006..42014`，基线最大为 `42005`）。

## 第一阶段证据（全部手动实测）

- 独立审计 `audit_migrated.json`：PASS。新前缀 65 项 UNSAT（q21→x≤63、q28/q40 全零、
  63 点全线）、三分支 ANF 输出恢复 + HMR 相位消去 + 相位含 q21、原两选择器 generic 语义
  UNSAT×2、三失败互斥 UNSAT、反例（删一条 CZ 修正必被拒绝）PASS。
- 精确计费（实际字节全条件栈）：旧窗口 `524287/262144`（2−2⁻¹⁸，38 笔）、
  新窗口 `1`（3 笔），净省 `262143/262144 ≈ 0.999996 C`。
- 实际模拟 `sample_migrated.json`：seeds 101/202/303 × 21760 输入，
  0 恢复失败、0 scratch、0 相位差、0 容差失败，最坏 x=161、误差比 0.9993237 与基线一致，
  观测省约 0.99–1.03 Toffoli/shot。
- 完整官方验证 seed 20261031（`verify_migrated_seed20261031.log`）：PASS，
  候选 98247.13887582964，比同环境父基线降 61.99617834869（观测约 0.99994 C，
  与精确预测 0.999996 C 一致，差值在单 seed 噪声内）；62Q、41 旋转、rotation_eps、
  最坏 x/误差比均与基线一致。seed 20261101 同样 PASS（98247.10733802804，
  同 SHA/旋转/误差比，`verify_migrated_seed20261101.log`）。

## 第二阶段（以迁移候选 `5541151c…` 为父基线，均已收官）

- Route A（非连续乘积复用）：7 个公开模板固化为 `routeA_templates.json`
  （Kirill 恒等式 A/B 两形＋Syed 条件 Z 模板，附来源版本）；
  `scout_routeA.py` 扫描：5+2 已应用位点逐字节确认（坐标已随迁移移位），
  48-op/10-wire/统栈/无障碍/夹杂门不交集规则下新嵌入 0 个；
  Kirill/Syed 两套 CCX 骨架拓扑预扫均为 0（`diag_topo.py` 及 Syed 对照扫描）；
  合成非连续正例对照通过（matcher 本身有效）。
  结论 `routeA_scout.json`：NEGATIVE，0/32 窗口，0 次证明（无候选故未耗求解预算）。
- Route B（消除剩余恢复计算）：`diag_routeB.py` 普查 902 个 HMR，
  屏障自由＋统深度 64 窗内仅 10 个类逆计算位点，均为自由门（CX/X）梯子或
  前向算术 CCX 链；同目标 CCX 对＋HMR 结构 0 个。CX/X 逆计算消除省 0 成本，
  无窗口满足 `t=ab⊕l` / `t=ab⊕cd⊕l` 模板前件。
  结论 `routeB_survey.json`：NEGATIVE-B，0 窗口进入 Z3 证明。

## 分账表（相对旧 stage1_nofallback 同 seed 口径之外，本轮以公开基线为起点）

| 项 | C 收益 | 成本 | 说明 |
|---|---:|---:|---|
| 公开基线收益（Kirill V5 相对旧 stage1） | 约 35.254（−2.175%） | −2185.76 | `local_comparison.json`，同 seed 20261031 |
| 选择器迁移收益（本轮候选相对公开基线） | 262143/262144 ≈ 0.999996 | −62.00 | 精确计费＋官方同 seed 复核 −61.996 |
| 结构优化收益（A/B 两线） | 0 | 0 | 有界否定：A 0/32 窗，B 0 窗口达标 |
| 累计（旧 stage1→本轮候选） | 约 36.254 | −2247.75 | 100494.89 → 98247.14（跨基线单 seed 比较） |

当前研究基线：`public62_nofallback.kmb`（`5541151c…`，约 98247.14）。
旧 stage1 / shortcache 候选保留为历史对照，不覆盖、不提交 Kaggle、不推送代码。
