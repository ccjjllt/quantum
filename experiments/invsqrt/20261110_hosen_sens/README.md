# 2026-11-10 S1/S2 Hosen 擦除普查 + A3 微角敏感度（新 family `26ebf39d`）

分支 `codex/invsqrt-research`，工作区 `.worktree/invsqrt/`。
固定输入（只读）：主仓库 `artifacts/20261110_gengsr_252268/release/invsqrt.kmb`
（SHA `26ebf39d…ac`，62Q / 36,686 ops / 1,392 静态 Toffoli-like，
本地完整官方验证 PASS 94537.59）。不重复 `7c10edba` 旧结论与已 closed 六方向
（见 `experiments/invsqrt/README.md`）；对象是新电路。
分区：S1=`[8893:16329)`，A3=`[16329:16499)`，S2=`[16499:36427)`（见
`experiments/invsqrt/20261110_gengsr_audit/` §2 七段表与 `evidence.json`）。

## 结论先行

1. **S1/S2 Hosen 擦除：closed，无候选、无验证器运行。**
   复用 20261108 frontier 审计 `unread_ccx_before_hmr` 方法全电路重数：
   **0 unread / 10 guarded，与审计 `evidence.json` 逐数一致**。
   条件帧深度修正后为 0 / 9 / 1（1 处为条件 CCX，非审计口径差异）。
   S1 的 365 个无条件 CCX：290 被 CX 读、74 被 CCX 读、1 被对角守卫，
   S2 同理无裸位点。每处 Hosen 改写净 −1 Toffoli-like（−62 分），
   总预期 **0 分，500–1500 分区间未达到**。
2. **A3 微角敏感度：closed（有 1 个亲手构建的候选 + 验证器 FAIL 仲裁）。**
   21 级 Z_POW 梯逐级单删 + 同 seed 小批量 Simulator 相位自检
   （沿用 20261109_tphase_fusion `prefix_branch_check` 方法，显式 seed，
   容差取验证器 `reference_values`）：最不敏感的是 L1（`@16337`，
   θ=2.886e-11 半圈）与 L2（`@16347`，θ=5.873e-11 半圈），
   24 格点自检 PASS 且静态位移 < 全 x 最小容差。
   构建 L1 单删候选 `artifacts/20261110_hosen_sens/drop16337_L1.kmb`
   （62Q / 36,685 ops）并跑了一次官方验证器：**FAIL**
   （`x=644: phase error -2.360e-09 turns exceeds tolerance 2.349e-09`，
   超差约 1.1e-11 turns ≈ 0.5%，与被删角量级一致——基线薄边余量被顶穿）。
    had it passed，单旋转 T 节省估计 ≈446 分（417–475，见 §3）。

## 1. S1/S2 Hosen 擦除普查（`hosen_census.py` → `hosen_census.json`）

方法：对每个 HMR/R 向后扫描到最近触碰目标线的非 PUSH/POP 操作，
跳过对角门（Z/Z_POW/CZ/CCZ），记 Z_POW 守卫；最近触碰为无条件 CCX
且目标一致、无对角守卫 ⇒ 候选。相对审计版的唯一改进是跟踪
PUSH/POP 条件帧深度（帧内 CCX 判条件，不误判无条件）。

- 全电路重数（审计兼容口径）：`unread=0, guarded=10` —— 与审计一致。
- 帧修正后：candidate 0，guarded 9，ccx_conditional 1，blocked 858。
- 按区：S1（313 HMR/R）：blocked 312 + guarded 1；
  S2（467）：blocked 463 + guarded 3 + conditional 1；
  A3（24）：blocked 23 + guarded 1；其余区：blocked 60 + guarded 4。
- S1 无条件 CCX 去向（365 个，inline 条件 0 个）：
  `blocked_by_CX` 290（目标被复用为控制/操作数，先被非对角读），
  `blocked_by_CCX` 74（目标做他门控制），`hmr_guarded_cliff_diag` 1。

### S1/S2 全部 5 个近 miss 位点逐个评估

| 区 | 类 | CCX→HMR（跨度） | 中间目标线触碰 |
|---|---|---|---|
| S1 | guarded | `CCX q27 q20 q28`@8968 → `HMR q28`@9217（249） | 37 CZ + 5 Z + 7 CCZ（42 条件） |
| S2 | guarded | `CCX q28 q23 q40`@16771 → `HMR q40`@16924（153） | 152 CZ（全条件） |
| S2 | guarded | `CCX q18 q21 q50`@16519 → `HMR q50`@18367（1848） | 14 CZ（4 条件 + 10 无条件） |
| S2 | guarded | `CCX q27 q21 q41`@18501 → `HMR q41`@18508（7） | 6 CZ（全条件） |
| S2 | ccx_conditional | `CCX q14 q22 q30`@35665 → `HMR q30`@35808（143） | 1 Z + 7 CZ（帧内条件，无条件改写不适用） |

逐个否决理由：中间对角门把 `(−1)^{ab·L}` 相位残留在他线/条件位上，
朴素 Hosen（删 CCX + 提前 HMR + 单条件 CZ）会丢掉该相位。
忠实转换需把每个中间 `CZ(q,x[,if c])` 升级为 `CCZ(a,b,x[,if c])`
（+1 Toffoli-like/个），`CCZ(q,·,·)` 需四体门（无干净改写）：
最干净的 `@18501` 位点净 +5（−1+6），其余 +13 以上。全部净正，关闭。

仲裁（自检级，不触发验证器）：删 `@18501` CCX 的改写电路做 8 x × 3 seed
相位自检 → **FAIL，误差恰 1/2 turn**（`worst_err 5.000e-01 turns @x=3`），
与 `ab·L` 奇偶翻转预测一致，证明守卫位点 load-bearing。

经济学：候选 0 处 × −62 分/处 = **0 分**；500–1500 分区间未达到；
无 `.kmb` 构建、无验证器运行。

## 2. A3 微角逐级敏感度（`sens_check.py` → `sens_check.json`）

A3 梯：21 个无条件 `Z_POW q28`，角度 2.886e-11 起逐级倍增至 3.052e-05
（半圈单位；`45 Z_POW = 41 rotation + 3 clifford + 1 t`，全无条件）。
自检：删 1 级 → 全电路 8 x × 3 seed（`[1,2,3,5,64,161,1000,3133452]`，
含 worst_x=161 与容差最紧的 max_x）Simulator 相位 vs
`reference_values` target/tol。基线自检 PASS（worst 0.99932@x=161，
与已知 worst 一致，harness 可信）。

- 24 格点 PASS 且与基线逐数相同（删了等于没删，格点上 q28=0）：
  `@16337`（L1）、`@16347`（L2）、`@16355`（L3）、`@16378`。
- 其余 17 级全部 FAIL（ratio 1.34 起，最大 113289 @max_x）。
- 静态普适界（删转角位移 ≤ θ/2 turns；全 x 最小容差
  `tol(3133452)=621138291 units=3.367e-11 turns`）：
  仅 L1（1.443e-11）与 L2（2.936e-11）严格小于最小容差；
  L3（5.794e-11）起超界。
- q28 分支活性扫描（`activity_sweep.py`，截断前缀读 q28，
  62 x × 3 seed = 186 样本）：L1 活性 27.4%（17/62 x，含 x=1000/3M，
  不含 x=161/max_x）；L2 活性 11.3%（7/62 x，不含 x=161/max_x）。
  即删除确会在部分分支咬合，但最坏位移仍被静态界兜住；
  L2 在 3M 附近位移/容差比达 ~0.87，风险显著高于 L1。

候选决策：只建 L1 单删（L1+L2 联合最大位移 4.38e-11 > 最小容差，
在共活性分支上必超界，不值得占用唯一一次验证器运行）。

## 3. 候选构建与验证器仲裁（1 次，任务授权）

- 构建：`artifacts/20261110_hosen_sens/drop16337_L1.kmb`
  （删 `@16337` 一行；62Q / 36,685 ops；SHA `6e9352ef…`；
  回读 36,685 ops + 格点自检 0.99932 与删前一致，序列化无损）。
- 官方验证器运行 1 次 → **FAIL**：
  `x=644: phase error -2.360e-09 turns exceeds tolerance 2.349e-09`
  （`experiments/invsqrt/20261110_hosen_sens/verifier_drop16337.log`）。
  超差 ~1.1e-11 turns（0.5%），恰为被删角量级：
  基线在该分支余量本就只剩 ~1e-11，被顶穿。方向关闭。
- T 节省估算（had it passed）：新电路 41 个无条件一般旋转；
  `Δscore = 62×ΔT/4`，`ΔT ≈ 0.56·log2(1/eps)+5.3`，
  eps ∈ [2.4e-12, 2.4e-14] ⇒ **417–475 分，中心 ≈446 分/旋转**
  （与 frontier 候选 B 实测 41→40 省 458 分同量级）。

## 验证范围声明（必须如实区分）

- **官方验证器运行 1 次**：L1 单删候选完整验证，**FAIL**（上）。
  未运行基线验证器（PASS 引用主仓库提交回执与作者日志）。
- 其余全部为静态普查 + 同 seed 小批量 Simulator 自检/前缀读数
  （24 格点/级 + 186 样本活性；未改电路语义作裁决依据）。
  任务 1 无候选故无构建、无运行。
- 未打包、未提交、未推送。

## 方法与复现（macOS PyPI kickmix，`.venv/bin/python`）

```bash
.venv/bin/python experiments/invsqrt/20261110_hosen_sens/hosen_census.py
.venv/bin/python experiments/invsqrt/20261110_hosen_sens/sens_check.py
.venv/bin/python experiments/invsqrt/20261110_hosen_sens/activity_sweep.py
```

引用：`unread_ccx_before_hmr` 方法源自 20261108 frontier 审计
（`audit_frontier_7c10edba.py::check_hmr_liveness`，本轮加条件帧深度修正）；
同 seed 相位自检源自 20261109_tphase_fusion `prefix_branch_check`
（脚本已清理，方法见其 README；容差/参考值直接取验证器
`reference_values`，`tol(x)=2^-24/sqrt(x)` turns）。
