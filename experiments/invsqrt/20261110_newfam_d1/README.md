# 新 family 方向①落地：S1/S2 Hosen 普查 + A3 微角敏感度（`20261110_newfam_d1`）— closed

日期：2026-11-10；分支 `codex/invsqrt-research`；工作区 `.worktree/invsqrt/`。
固定输入（只读）：主仓库 `artifacts/20261110_gengsr_252268/release/invsqrt.kmb`
（SHA-256 `26ebf39d…c5cc…` 已复核，62Q / 36,686 ops；S1=`[8893:16329)`，
A3=`[16329:16499)`，S2=`[16499:36427)`，见 `20261110_gengsr_audit/README.md` §2 七段表）。

**先说与既有工作的关系（避免重复计功）：**
方向①在同一新电路上已由 `20261110_hosen_sens/` 完整执行并 closed
（S1/S2 普查 0 候选 + A3 L1 单删候选 1 次官方验证器 FAIL）。
本目录不是第二次独立全量普查，而是在新行号上的落地复核记录：
用逐字移植的方法在本目录重新执行只读普查（`recheck_d1.py` → `evidence.json`），
数字与 `hosen_sens` 逐数一致；完整 21×24 Simulator 网格与唯一一次验证器仲裁
引用既有证据，不重跑、不再消耗验证器运行。

## 结论先行

1. **S1/S2 Hosen 擦除：closed，无候选，本目录无构建、无验证器运行。**
   本目录重跑：审计兼容口径 `unread=0 / guarded=10`，帧修正后
   `candidate 0 / guarded 9 / ccx_conditional 1 / blocked 858`
   （分区见下），与 `hosen_sens/hosen_census.json` 逐数一致。
   S1 的 365 个无条件 CCX 去向：290 被 CX 读、74 被 CCX 读、1 被对角守卫。
   每处干净改写净 −1 Toffoli-like（−62 分），候选 0 处 ⇒ **总预期 0 分，
   500–1500 分区间未达到**。
2. **A3 微角敏感度：closed，本目录无新候选、无验证器运行。**
   本目录重算 21 级静态界：仅 L1（`@16337`，1.443e-11 turns）与
   L2（`@16347`，2.936e-11 turns）严格小于全 x 最小容差
   （`tol(3133452)=621138291` units=3.367e-11 turns）。
   完整网格结论引用 `sens_check.json`：24 格点 PASS 且与基线逐数相同的
   是 L1/L2/L3（`@16355`）/`@16378`，其余 17 级 FAIL（ratio 1.34 起）。
   最不敏感的是 L1、L2；L1 单删候选已在 `hosen_sens` 构建并跑过
   唯一一次官方验证器 → **FAIL**（`x=644` 超差约 1.1e-11 turns ≈0.5%，
   恰为被删角量级）。had it passed，单旋转 T 节省估计 ≈446 分
   （417–475）。

## 1. S1/S2 候选位点表（本目录重跑 + 既有逐个评估）

方法：对每个 HMR/R 向后扫描到最近触碰目标线的非 PUSH/POP 操作，
跳过对角门（Z/Z_POW/CZ/CCZ，记 Z_POW 守卫），跟踪 PUSH/POP 条件帧深度；
最近触碰为无条件 CCX 且目标一致、无对角守卫 ⇒ 候选。
逐字移植自 20261108 frontier 审计 `audit_frontier_7c10edba.py::check_hmr_liveness`
（本轮加条件帧深度修正；旧电路结论不继承）。

本目录重跑分区（`evidence.json`）：

| 区 | blocked | guarded | ccx_conditional | candidate |
|---|---|---|---|---|
| S1（313 HMR/R） | 312 | 1 | 0 | 0 |
| S2（467） | 463 | 3 | 1 | 0 |
| A3（24） | 23 | 1 | 0 | 0 |
| 其余 | 60 | 4 | 0 | 0 |
| 合计 | 858 | 9 | 1 | **0** |

S1 无条件 CCX 去向（365 个，inline 条件 0 个）：
`blocked_by_CX` 290 / `blocked_by_CCX` 74 / `hmr_guarded_cliff_diag` 1。

S1/S2 全部 5 个近 miss 位点逐个评估（行号为新电路序号，
中间触碰与净门数引用 `20261110_hosen_sens/README.md` §1，本目录重跑确认位点存在）：

| 区 | 类 | CCX→HMR（跨度） | 中间目标线触碰 | HSM 改写净门数 |
|---|---|---|---|---|
| S1 | guarded | `CCX q27 q20 q28`@8968 → `HMR q28`@9217（249） | 37 CZ + 5 Z + 7 CCZ（42 条件） | 净正（忠实转换需把每个中间 `CZ` 升级为 `CCZ`，`CCZ` 需四体门；最干净位点以下已量化） |
| S2 | guarded | `CCX q28 q23 q40`@16771 → `HMR q40`@16924（153） | 152 CZ（全条件） | 净正（+13 以上量级） |
| S2 | guarded | `CCX q18 q21 q50`@16519 → `HMR q50`@18367（1848） | 14 CZ（4 条件 + 10 无条件） | 净正（+13 以上量级） |
| S2 | guarded | `CCX q27 q21 q41`@18501 → `HMR q41`@18508（7） | 6 CZ（全条件） | **最干净，仍净 +5**（−1+6）；删 CCX 改写 8 x × 3 seed 相位自检 FAIL，误差恰 1/2 turn，守卫 load-bearing |
| S2 | ccx_conditional | `CCX q14 q22 q30`@35665 → `HMR q30`@35808（143） | 1 Z + 7 CZ（帧内条件） | 不适用无条件改写（帧内 CCX 判条件） |

否决理由（通用）：中间对角门把 `(−1)^{ab·L}` 相位残留在他线/条件位上，
朴素 Hosen（删 CCX + 提前 HMR + 单条件 CZ）会丢掉该相位；
忠实转换需把每个中间 `CZ(q,x[,if c])` 升级为 `CCZ(a,b,x[,if c])`
（+1 Toffoli-like/个），`CCZ(q,·,·)` 需四体门。全部净正，关闭。

经济学：候选 0 处 × −62 分/处 = **0 分**；500–1500 分区间未达到。

## 2. A3 微角敏感度表

A3 梯：21 个无条件 `Z_POW q28`，角度 2.886e-11 起逐级倍增至 3.052e-05
（半圈单位）。本目录静态重算（`evidence.json:A3_static_bound`，两最小与既有值一致）；
完整 8 x × 3 seed 同分支网格结论引用 `20261110_hosen_sens/sens_check.json`
（方法沿用 `20261109_tphase_fusion` `prefix_branch_check`：同显式 seed ⇒
同 HMR 硬币流；容差取验证器 `reference_values`，`tol(x)=2^-24/sqrt(x)` turns）：

| 删级 | 角（turns） | 静态安全（max_shift < min_tol） | 24 格点自检 | worst |
|---|---|---|---|---|
| L1 `@16337` | 1.443e-11 | ✅ true（266M < 621M units） | PASS（与基线逐数相同） | 0.999@x=161 |
| L2 `@16347` | 2.936e-11 | ✅ true（542M < 621M） | PASS（逐数相同） | 0.999@x=161 |
| `@16355` | 5.794e-11 | ❌（1069M > 621M） | PASS（逐数相同，格点上 q28=0） | 0.999@x=161 |
| `@16378` | 4.662e-10 | ❌ | PASS（逐数相同） | 0.999@x=161 |
| `@16363` 起其余 17 级 | 1.16e-10 ～ 3.81e-6 | ❌ | **全部 FAIL**（ratio 1.34 起，最大 113289@max_x） | 见既有 JSON |

补充（引用既有，不重跑）：q28 分支活性扫描 62 x × 3 seed = 186 样本，
L1 活性 27.4%（17/62 x，含 x=1000/3M，不含 x=161/max_x），
L2 活性 11.3%（7/62 x）；L2 在 3M 附近位移/容差比达 ~0.87，风险显著高于 L1。
候选决策：只建 L1 单删（L1+L2 联合最大位移 4.38e-11 > 最小容差，
在共活性分支上必超界，不值得占用验证器运行）。

T 节省估算（had it passed）：新电路 41 个无条件一般旋转；
`Δscore = 62×ΔT/4`，`ΔT ≈ 0.56·log2(1/eps)+5.3`，
eps ∈ [2.4e-12, 2.4e-14] ⇒ **417–475 分，中心 ≈446 分/旋转**。

## 3. 候选与日志（本目录无）

- 本目录：**未构建任何 `.kmb` 候选，未运行官方验证器**（无净负改写，无触发条件）。
- 引用的既有仲裁（`20261110_hosen_sens/`，同一新电路对象）：
  构建 `artifacts/20261110_hosen_sens/drop16337_L1.kmb`
  （删 `@16337` 一行；62Q / 36,685 ops；SHA `6e9352ef…`）并跑一次官方验证器 →
  **FAIL**（`x=644: phase error -2.360e-09 turns exceeds tolerance 2.349e-09`，
  `verifier_drop16337.log`，EXIT=1）。超差 ~1.1e-11 turns（0.5%），
  恰为被删角量级：基线在该分支余量本就只剩 ~1e-11，被顶穿。方向关闭。

## 验证范围声明（必须如实区分）

- **本目录官方验证器运行 0 次**：无候选故无构建、无运行。
  引用的 1 次 FAIL 运行归属 `20261110_hosen_sens/`（上），
  引用的 PASS（94537.59）为主仓库提交回执与作者日志（既有证据）。
- 本目录执行：只读复核脚本 1 个（`recheck_d1.py`，macOS PyPI kickmix，
  `.venv/bin/python`），输出 `evidence.json`
  （分区门数断言 + 审计兼容重数 + 帧修正普查 + 21 级静态界两最小重算；
  实际运行输出见执行记录）。
- 引用的其余证据：`20261110_hosen_sens/hosen_census.json`（全表）、
  `sens_check.json`（21 级网格 + `@18501` 仲裁 FAIL 1/2 turn）、
  `activity_sweep.json`（186 样本活性）、`verifier_drop16337.log`。
- 未打包、未提交、未推送；只写本目录（无候选 `.kmb` 写入 `artifacts/`）。

## 方法与复现（macOS PyPI kickmix，`.venv/bin/python`）

```bash
.venv/bin/python experiments/invsqrt/20261110_newfam_d1/recheck_d1.py
```

引用：
- `unread_ccx_before_hmr` 方法源自 20261108 frontier 审计
  `audit_frontier_7c10edba.py::check_hmr_liveness`（本轮加条件帧深度修正，
  见 `20261110_hosen_sens/hosen_census.py` 头注）；
- 同 seed 相位自检源自 `20261109_tphase_fusion` `prefix_branch_check`
  （脚本已清理，方法见其 README；容差/参考值直接取验证器 `reference_values`）；
- 分区/S1 描述：`20261110_gengsr_audit/README.md` §2 与 `evidence.json`
  （`hmr_peephole_new` 未读 0 / 守卫 10；本目录重跑逐数一致）；
- 上游 family 来源：`gengsr/lb-25-2268-shifter-46-own-chemistry-loaders` v1
  （交叉对照 Özer v91、Maoxin 25.218，见审计 README §0）。
