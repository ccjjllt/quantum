# 62Q 短期 ab/abc 缓存：修正 + 零收益诊断 + 256 表达 bounded 搜索（2026-11-05 实测）

固定新基线 `stage1_nofallback.kmb`（`80ba3fef…`），62Q，68 Z_POW，尾部补丁保留。新增收益从零起算。

## 1. 三处修正（已完成）

- 重开短期缓存路线：`STAGE2.md` 加修正记录。Stage1 三 `u` 中 12 条 `CX q41/q50↔q28` 的源在入口恒零
  （25897/25905 HMR 后零触碰），可删除；缓存只到相位选择器结束（Stage1 坐标 30599 前栈空处自带 HMR+CZ 清理），
  不依赖逆算清理。原“纯缓存不可行” verdict 仅针对长活+复用清理的限定实现。
- 撤回严格零上界：§2 改为限定发现（4096 零测样本、固定列模板、单残差模板），删除“8 分支限 3 失败条件”类推断；
  本轮重搜保存完整脚本、矩阵、逐候选残差秩和覆盖率（`search256_gshared.py` + `search256_gshared.json`，不在 /tmp）。
- 补强尾部审计：`audit_stage1.py` 固定 three_and KMB `c2c255…`、证明 `9031f7…`（`local_miter=unsat`、
  5 个 clean 全 unsat）、审计 `34403c…=PASS`，逐项比对实际 95 条尾指令（SHA `a8472447…`），删除仅查位名逻辑；
  重跑 `TAIL_STRICT_OK len 95`，`FINAL_RESULT PASS`。负例：内存改 `CZ q18 q13 if b90003→CZ q18 q12 if b90003`
  （保留 b90001/b90004），旧弱检查仍 PASS，新严格比对 1 处 mismatch 拒绝（SHA 变 `3b1da7…`）。
  `stage1_nofallback.json` 的 pending 状态已更新为 PASS（证明/成本/抽查/双 seed 官方验证）。

## 2. 零收益纯缓存诊断电路（已生成+已证明，不替换基线，不跑官方验证）

- 生成器 `experiments/invsqrt/20261105_shortcache/shortcache_build.py`
  （`--baseline/--baseline-sha/--output`；锚指令+窗口内容哈希定位：`ops26111=ca577950…`、
  `ops26340_26341=d26533c4…`、`ops30594_30598=c3ed57b2…`；直接拼接 Stage1 实际序列）。
- 候选 `artifacts/20261105_shortcache/invsqrt/shortcache_zero.kmb`
  SHA `97e6391503cb463a72666a393d9c20b1b5f18359c79d89b1ff76157eff21e9da`，62Q，49090 ops，
  68 Z_POW 不变，终栈深 0。拼接：26111 后 `CX q28 q41`、26340 后 `CX q40 q50`、删 12 条 u-CX、
  30599 前栈空处 `HMR q50 b42100; CZ q41 q23 if b42100; HMR q41 b42101; CZ q18 q27 if b42101`
 （新位 42100/42101 全电路未用；q18/q27/q23 在 [26111,30599) 零写入，q28/q40 入口零经 HMR 25940/25937+零写入段证明）。
- 独立审计 `audit_shortcache.py`（`--baseline/--baseline-sha/--candidate`，实际 KMB，不导入生成器）：
  15 个差异块与预期逐项一致；入口零+生命周期静态成立；62 线输出恢复+旧位/栈/总相位 miter `unsat`；
  成本 miter `unsat`，CCX=1157、CCZ=102 无增减，精确新增 **0 C**。`audit_shortcache_zero.json PASS`。
  途中曾因 q28/q40 入口未钉零出现 phase SAT，已补静态前提（HMR 25940/25937+零写入段）后通过，如实记录。

## 3. 256 表达 g*u 搜索（bounded 负结果，有范围限定）

- 脚本 `search256_gshared.py`（种子 8121，首轮 256 个 `u`，列 `[1]+truth(62)+[u&t(62)]=125`；
  目标 G1/G2（q23 组各 19 系数）+ G34_q21 联合代理；4096 零测样本实得 8229 输入）。
- 产物 `search256_gshared.json`（2.9M）：Q 快照、xs 哈希、逐候选 `u_pop`/秩/各组单残差秩与残差、覆盖率 0/256。
- 结果：`n_success=0`，`verdict=STOP-AT-256`。四组选择器窗口成本口径按 `3−2^-18`
 （G1+G2 联合 `2−2^-18` + Stage1 联合 1.0；含前两次原始 AND 则双方按 `5−2^-18` 起算，未用旧 ~4C）。
  无正收益候选，不生成 KMB，不跑官方验证；不把“缓存可用”写成“优化成功”。

## 证据命令（本机实测）

```sh
uv run --offline --with z3-solver python experiments/invsqrt/20261104_stage1_nofallback/audit_stage1.py --candidate artifacts/20261104_stage1_nofallback/invsqrt/stage1_nofallback.kmb --baseline artifacts/20261102_hw06_opt/invsqrt/baseline_hw06.kmb --baseline-sha bce2948ff24e20fe59666d131f7fc4316a905103937272c52fdd39d494b6fe47
# TAIL_STRICT_OK len 95 ... FINAL_RESULT {"status":"PASS",...}
uv run python experiments/invsqrt/20261105_shortcache/shortcache_build.py --baseline artifacts/20261104_stage1_nofallback/invsqrt/stage1_nofallback.kmb --baseline-sha 80ba3fe75262c6cdb0b6829bfde6e368946d897b6eef2ed7e7626b6355f346a3 --output artifacts/20261105_shortcache/invsqrt/shortcache_zero.kmb
# SHORTCACHE_BUILT 97e6391503cb463a... Q 62 ops 49090
uv run --offline --with z3-solver python experiments/invsqrt/20261105_shortcache/audit_shortcache.py --baseline artifacts/20261104_stage1_nofallback/invsqrt/stage1_nofallback.kmb --baseline-sha 80ba3fe75262c6cdb0b6829bfde6e368946d897b6eef2ed7e7626b6355f346a3 --candidate artifacts/20261105_shortcache/invsqrt/shortcache_zero.kmb
# MITER unsat / COST_MITER unsat / FINAL_RESULT PASS
uv run python experiments/invsqrt/20261105_shortcache/search256_gshared.py --n-expr 256 --seed 8121
# {"n_expr":256,"samples":8229,"n_success":0,"verdict":"STOP-AT-256",...}
```

## 计数与声明

- 生成候选：诊断电路 1 个（`97e639…`，0C，已证明）；正收益候选 0 个。
- 官方验证：诊断电路按计划不单独跑；正收益候选不存在，故无完整官方验证；无 Kaggle 成绩、无推送。
- 本轮实际取得的新增收益：**0 C**（诊断电路）；256 表达 bounded 搜索无正收益，停止扩搜。

## Section 4 结果（bounded negative，2026-11-05追加实测）

- 4.1：`free_elim_screen.py`（38 CCZ × {delete,Z,CZ全线}，25809输入含1..16383/边界/域外，双seed）：
  11个实际触发CCZ零双seed存活；21个存活全是prod<=1的vacuous门（删了也省~0）。
  `free_elim_spotproof.py`对顶部CCZ×缓存模板6个精确Z3 miter全部sat驳回（反例x已存）。
  结论：无免费Z/CZ消去。见 `SECTION4_VERDICT.md`。
- 4.2：域事实以25809矩阵核验（q21==(x<=63)、q23&(x<=63)==0、G1/G2交叠192样本不互斥、
  g在宽集上非常1）；域外相位按语法含控制恒零；未把任何ab·word当免费项（唯一测试过的6个已Z3驳回）。
- 4.3：`search256_gshared.py`首轮256表达（种子8121）逐候选残差秩/覆盖率已存；
  三组n_residuals直方图均为{19:256}，单分支需<=k个残差对应k个条件，8分支预算内无解，停止扩搜。
- 成本口径：比较窗5-2^-18、选择器组3-2^-18，未用旧~4C。本轮实际新增：**0 C**。

## 复核修正后状态（2026-11-05）
- 共享搜索已按“缓存快照＋真实联合源＋g*u列”重做（`shared_search_v2.py`，256表达种子8121后停止）：
  缓存存活经断言、并源29个、残差秩最小25 → `NEGATIVE-V2`（判据为秩，非互异计数）。
- 免费消去补到全1891 CZ对＋62 Z/门＋同控制对合并检验；10个精确Z3 miter全sat驳回
  （1次超时按规则单次拆分复核后同样sat）；vacuous 21门精确合计1535/262144 C，未删。
- 域统计统一到25809矩阵：q21=63、q23=16320、G1/G2/交叠3264/960/192。
- 本轮实际新增仍为 **0 C**；无正收益候选，无仿真/官方验证触发，无提交推送。

## 可复现性说明
- 含25809-bit大整数的JSON（`shared_search_v2.json` Q矩阵快照）读写需
  `sys.set_int_max_str_digits(0)`（Python 3.11+默认4300位限制）；生成/读取脚本均已内置。

## 树构建器判决（2026-11-05）
- `tree_build.py`：8分支/每支<=7条件预算下 `INFEASIBLE`（最小残差秩25，直方图{25:256}，
  覆盖上界2.4e-7，净收益上界9.5e-7 C）。`tree_build.json` 存证。
- 残差秩经 `recheck_resrank.py` 独立实现复算，256/256一致（`recheck_resrank.log`）。
- 无正收益候选：不生成KMB、不跑官方验证（按计划仅正收益候选触发）；新增0 C。

## 收官（2026-11-05）：对照g横扫已修正，有界否定
- `variant_g_search.py`：8种g×32u（种子8122），修正prep元组bug后最小残差秩23–25（29源），
  `NEGATIVE-GVARIANTS`。首轮43–53系bug产物（85回退源），已作废，以修正轮为准。
- 全轮结论：正确模板下最小秩23–25 vs 8分支/≤7条件预算 → 不可行 → 无候选KMB → 新增0 C。
  唯一线上/本地收益仍是上轮 Stage1 的 0.125 C（成本约100494.89，双seed官方PASS）。
