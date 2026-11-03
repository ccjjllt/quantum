# Section 4 verdict (bounded): no positive-gain candidate this round

Scope kept exactly as ordered: free Z/CZ elimination with explicit gate sequences (4.1);
g = q23 XOR q21 shared-AND with domain/boundary/out-of-domain checks (4.2);
multi-condition branches up to 8 with GF(2) + inclusion-exclusion coverage (4.3);
256 expressions, seed 8121, then stop.

## 4.1 Free phase elimination: NEGATIVE (screen + exact refutations)

- Screen `free_elim_screen.py` on `shortcache_zero.kmb` (`97e639…`), window [26111,30599),
  38 CCZs (G1 19x `CCZ q18 q23 w` + G2 19x `CCZ q27 q23 w`, word set identical),
  25809 inputs (1..16383 + bit boundaries + random + address/delta + out-of-domain),
  seeds 101/202. Template family per CCZ: {delete, Z u, CZ u v}, u,v over all 62 wires
  (incl. cache q41=ab, q50=abc). Saved per-CCZ option tables in `free_elim_screen.json`.
- All 11 firing CCZs (prod 11..787 on samples): **zero** two-seed survivors — every template,
  cache-wire ones included, refuted on concrete samples (sample mismatch with fixed
  measurement outcomes is a valid full counterexample: data trajectory is
  measurement-independent, only classical guards vary).
- 21 survivors are all vacuous (prod <= 1 on 25809 samples): gates that (almost) never fire
  on samples; deleting them would save ~0 execution-weighted cost regardless of proof.
- Exact Z3 legal-prefix miters (`free_elim_spotproof.py`, 60s timeout, shortcache coords,
  entry x in [1,3133452], symbolic HMR outcomes) for the top firing CCZs x cache templates:
  26655 x {CZ q41 q23, CZ q50 q14, Z q41} and 27227 x {CZ q41 q23, CZ q50 q14, Z q50} —
  all 6 returned **sat (refuted)** with saved counterexample x
  (1651, 1536, 3022, 317, 764, 388; 23k SSA nodes, 3-33s each).
  `free_elim_spotproofs.json` PASS-as-refutations (all verdicts sat, none unknown).
- Verdict 4.1: no free Z/CZ elimination for any firing CCZ, with or without cache wires.

## 4.2 g*u shared AND: domain facts + why no template built

- From the saved 25809-sample matrix (recomputed inputs() reproduces 25809 xs):
  q21 == (x<=63) exactly (matches the proven 65-claim prefix proof in audit_stage1);
  q23&(x<=63)==0; q21&q23==0; G1 fires 3264 / G2 fires 960 / overlap (q18&q27&q23) 192 —
  G1 vs G2 are NOT mutually exclusive; G3/G4 (q21 groups) are exclusive vs q23 groups.
- Correction to the earlier "g恒1" note: it held only on the 1..4096 slice; on the wider
  set q23 fires 4066/25809, g has zeros. g is not constant, but that does not help (below).
- Out-of-domain phase: every CCZ phase monomial syntactically contains its data controls
  (qa&qb&word), so out-of-domain phase is 0 by construction. No `ab·word` term was ever
  treated as a free phase: the only cache-template equalities ever tested are the 6
  Z3-refuted miters above (all sat). No g*u construction was built because 4.1+4.3 close it.

## 4.3 Multi-condition branches (up to 8) with inclusion-exclusion: NEGATIVE by residual count

- `search256_gshared.py` (seed 8121, first 256 u, columns [1]+truth(62)+[u&t(62)]=125,
  8229-sample matrix with Q snapshot + per-candidate rank saved in `search256_gshared.json`;
  script+seed reproduce the matrix; Q snapshot is the saved matrix).
- Result: per-group distinct-nonzero-residual histogram is **{19: 256}** for G1, G2 and the
  joint proxy alike — every trial leaves all 19 targets with pairwise-distinct nonzero
  residuals (best trial 0 still n_res=19, rank 116/125). Observed-distinct on samples
  implies truly distinct (samples can only merge, never split, equal functions).
- A branch with k classical conditions can absorb at most k distinct residuals
  (error = R1·f1 + ... + Rk·fk vanishes iff all k parities are 0; stage-1 recipe is k=1).
  Minimum over 256 trials is 19 > any feasible budget (8 branches x <=3 conditions).
  Inclusion-exclusion coverage computation is moot: no branch with <=7 conditions exists
  in the searched set, so no tree was built, no KMB generated.
- The 256-expression budget for this round is consumed;扩搜停止.

## Cost accounting used (no ~4C)

Comparison window [26111,30599): 2 original ANDs + G1 + G2 + stage1-joint = 5-2^-18 both sides;
four selector groups proper = 3-2^-18 (G1+G2 = 2-2^-18, joint = 1.0). No positive candidate,
so no new cost to audit; diagnostic shortcache stays exactly 0C (proven).

## Status

Sections 2-3 delivered and proven. Section 4: bounded negative (4.1 screen + 6 exact
refutations; 4.2 domain facts, no template built; 4.3 0/256, min residual count 19).
No positive-gain KMB => no sample sim / official verification triggered (per plan, only
the final positive candidate would run them). No Kaggle submission, no push.

## 复核修正（2026-11-05 第二轮，逐条对应）

1. **缓存快照＋真实联合源＋g*u（`shared_search_v2.py`，256表达，种子8121，停止）：**
   - 快照取自 `shortcache_zero.kmb`（`97e639…`），脚本内断言缓存存活：
     `Q[41]==Q[18]&Q[27]`（ab）、`Q[50]==Q[18]&Q[27]&Q[23]`（abc）在26635快照成立。
   - 目标：G1/G2/G3/G4 原始形式（G3/G4 保留 q18/q27 控制，不用 q21·word 代理），
     系数位经 prep BIT 段仿射分解到**真实联合测量源**（并集 29 个 HMR 源，与 stage1 联合分支同源），
     76 个组系数目标折成逐源目标；常数项 T_ONE==0 已验证。
   - 列：`[1]+Q(62)+[u&t]+[(g&u)&t]`（187 列，g=`q23^q21`，u 遍历62线除 q28/q40，缓存线可入选）；
     残差按 **GF(2) 秩**（不是互异计数）判定：256 候选最小残差秩 **25**（n_residuals=29），
     8分支预算（需<=7条件）内无解。`shared_search_v2.json` 存脚本输入、Q矩阵快照、逐候选秩/覆盖。
   - 结论：`NEGATIVE-V2`。R3=R1^R2 只需2个条件的规则已按秩正确执行（先前按计数是错的，特此更正）。
2. **免费消去范围补齐：** `free_elim_fullpairs.py` 全1891 CZ对＋62 Z/门/双seed：
   触发门存活仅26934/26955/27483三处且全是自有线模板；其余19处为单seed vacuously零触发。
   跨门合并：同控制CCZ对 `w==c^d` 并域检验——仅 vacuous 对有witness，无触发对合并；
   守卫栈未统一（合并主张需额外守卫证明），但因无触发对候选，否定结论不受影响。
   10个精确Z3 miter（6缓存模板＋3自有线＋1超时按规则单次归一化拆分复核）**全部sat驳回**，
   反例x已存（`free_elim_spotproofs.json`＋`free_elim_spotproofs2.json`，无unknown遗留）。
   21个vacuous门精确执行成本用实际PUSH栈仿射秩逐门计得，总计 **1535/262144≈0.0058556 C**
   （`vacuous_cost.json`，逐门表），很小但非零，未宣称可删除。
3. **样本混用澄清：** 统一口径为25809矩阵（`free_elim`/`shared_search_v2`输入集，1..16383＋边界＋随机＋地址/增量）：
   q21=63个1（恰为x<=63）、q23=16320个1、互斥、G1/G2/交叠3264/960/192。
   8229矩阵（`search256_gshared.json`，1..1024起）是另一轮输入集，其4066仅属该集；两集脚本＋种子均可复现。
   原CCZ控制为零则相位为零是语法事实，仅用于说明，不替代新表达的域外等价证明（本轮无新表达建成）。

## 多条件分支树：已实际构造建造器并给出不可行判决（2026-11-05 第三轮）

- `tree_build.py`（`--max-branches 8 --cond-budget 7`）：从 v2 数据重建每候选列空间，
  max-pivot/min-pivot 双实现列秩 256/256 一致；逐源残差秩直方图 **{25:256}**（最小=最大=25，
  样本只能低估秩，故真秩>=25）。
- 每分支下界引理（已写入 `tree_build.json`）：分支误差 E(s,x) 须在选中集上恒零，
  则每个 x 切片的源函数 E(·,x) 须落在 k 个条件奇偶张成的空间里；诸切片张成的源函数空间维数
  恰等于残差秩，故任一分支需 k>=25 个独立条件。8分支每支选中概率<=2^-25。
- 精确包含排除处理：对已建成树才可逐项计算；此处置空集，故用乐观上界代替——
  union bound 覆盖<=8·2^-25≈2.4e-7，执行开销>=选中量（守卫栈包含选择条件），净收益<=4·覆盖≈9.5e-7 C。
  即使取界内最乐观值，也比 2C 目标小6个量级、比 vacuous 总量小4个量级。
- 独立复算 `recheck_resrank.py`（min-pivot 全套重实现，同一Q矩阵/源/目标）：256/256 与存档秩一致，
  最小25。`recheck_resrank.log` 存证。途中发现复算脚本自身把 `bitrun` 返回元组拆包反了
  （取到空区间致76回退单键），已修正并重跑通过；v2 主脚本用的是 `[1]` 端，不受影响。
- 结论：`INFEASIBLE`。按计划不触发 KMB 生成；窗口成本维持 stage1 基线（`audit_shortcache_zero.json`
  COST_MITER unsat、CCX=1157/CCZ=102 无增减），本轮新增 **0 C**。比较基准 stage1 成本约100494.89不变。

## 对照实验修正与收官（2026-11-05 第四轮）

- 结构不同的对照：固定 g 不只取 `q23^q21`，横扫 8 种共享控制
  (`q23^q21,q18^q27,q18,q27,q23,q21,q18^q23,q27^q23`)×32 u（种子8122，同预算量级），
  列族 `[1]+Q+[u&t]+[(g&u)&t]` 不变。首轮跑出 43–53，复核发现对照脚本犯了与复算脚本
  相同的 `bitrun` 元组拆包错误（prep 取空→85 个回退单键；正确应为 29 真源），已修正重跑。
- 修正后 8 种 g 的最小残差秩：23–25（`q21`:23，`q27`,`q27^q23`:24，其余25），29源，25809样本，
  `variant_g_search.json`（NEGATIVE-GVARIANTS）。换控制元同样打不开缺口。
- 最终判定：正确模板下（缓存快照存活、29联合源、g*u列）256+256 表达的最小残差秩为23–25；
  8分支/每支≤7条件预算要求秩≤7，无一候选达标（直方图 v2 {25:256}，双主元实现交叉验证一致）。
  按计划不生成候选KMB；窗口成本维持 stage1（COST_MITER unsat，CCX=1157/CCZ=102），
  比较基准 stage1 约100494.89 不变。**本轮新增 0 C** 为有界否定结论（搜索集＋预算内），
  不是全局不可能性证明；不提交Kaggle、不推送。
