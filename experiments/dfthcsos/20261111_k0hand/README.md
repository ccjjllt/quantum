# k0 手工合并尝试（2026-11-11）— 关闭，未达判据

分支 `codex/dfthcsos-research`，工作区 `.worktree/dfthcsos/`。
只报实测；未提交 Kaggle、未推送、未改官方验证器/数据；未跑 `verify.py`（判据要求 static 先 −4，不满足即停）。

结论先行：**关闭。k0 与 k1–k3 产品数同量级（217 vs 215 loads，前缀 69 积逐行一致），
但 phase-2 架构完全不同构（54 种控制对 + low-bit 缓存 vs 单一控制对块复用），
严格/宽松抵消搜索均为 0 候选；缺 rank-86 综合器代码，不自研；判据（static −4 双遍 T 且小验证 PASS）未达成。**

## 1. 输入与目标

- 基线：Maoxin303（`artifacts/20261111_maoxin303/`，本地全量 PASS，298,720,881.30）。
- 目标：k0（static 297）手工 −2（→295，−4 双遍 T ≈ −80K/−0.027%），不碰字表
  （e2 余量 0.003 μHa，loader-only 编辑本来也不影响 error_1/error_2/E_gap，只赌 words_match）。
- 约束：静态改 kmx 文本；`heuristic_costs` 验 T；words_match 必须 True；static 297→≤295 且 2440-shot 小验证 PASS 才算数。

## 2. 方法（全部实测，非验证结论）

1. `kickmix.Circuit.to_file` 将 `angle_k_0.kmb` / `angle_k_1.kmb` 转 kmx 文本
   （k0 44319 行 / k1 15993 行），逐行比对 CCX 序列。
2. `scripts/inspect_circuit.py` 取静态门计数（CCX 即 static Toffoli）。
3. 抵消搜索：同一 `(controls,target)` CCX 的相邻两次出现之间，
   (a) 严格版：无任何门触碰 {a,b,t}；(b) 宽松版：无任何门以 a/b/t 为 target
   （CZ 保守计入）。满足任一即两者可删（CCX 自逆 + 不交/只读可交换），省 2 CCX。

## 3. 实测结构对比（kmx 文本 + inspect_circuit）

| 项 | k0（297，未综合） | k1（290，已综合） |
|---|---|---|
| CCX 总数 | 297 | 290 |
| 前缀 AND 级联（q4–q10 → q51–q119） | 69，与 k1 **逐行一致** | 69 |
| 尾部 word-loads | **217**，**54 种控制对**，目标 10 个位（q11–17,q19,q21,q23） | **215**，**1 种控制对**（q126,q127 ×215），目标 6 个位 |
| phase-2 setup CCX（→q120+） | 11（q120–q127 全 CCX 计算） | 6（q120–q125；q126/127 为纯 CX 累加器） |
| CX 总数 | 43704 | 15420 |
| CX→选择低位 q0–q3（low-cache：选择位自身当 scratch 翻转） | **11233**（3604/3591/1920/2118） | 0 |
| CX→word（q11–q50） | 8315（全 40 位） | 2663 |
| word 位作 CCX 控制（clean-word 借位） | **无** | 有（q18×2，q26，q34） |
| R / X | 80 / 21 | 75 / 1 |
| 重复 CCX 行（同 controls+target） | 45 种（如 q125,q1→q11 ×8） | 6 种（单对复用：q126,q127→q11 ×87 等） |

注：T 口径下只有 CCX 计数起作用（CX/X/R 为 Clifford/初始化，不进 T）；
k0→k1 的差距本质是 phase-2：k1 把全部 215 loads 挂到单一累加器对上增量更新，
k0 把 217 loads 散在 54 对控制上并用 q0–q3 自身做缓存。

## 4. 抵消搜索结果：0 候选

- 严格版：0 对；宽松版：0 对。
- 任意重复 CCX 相邻两次出现之间最少有 **139** 个写 {a,b,t} 的门
  （top：`CCX q120 q125 q14` 相邻间隔 139 writes；`CCX q125 q1 q11`×8 间隔 ≥151）。
  重复是刻意的（累加器每次重编程后在不同地址子集上触发），不是冗余。
- 其余 CCX（前缀 69 + setup）与 k1 共有/作者已用综合器处理过（k1–k3 −2、k4–k6 +1），
  手工在 54 对散射结构上复现"块合并"等价于重写 rank-86 综合器（19 维子空间搜索），
  按任务指令不自研。
- 未做任何 kmx 编辑 trial（无 provably-safe 候选；盲改几乎必然破坏 words_match，
  且判据要求先有 static −2）；未跑 `verify.py` 小验证（前置条件未满足）。

## 5. 关闭理由

1. 产品数同量级（217 vs 215）但 phase-2 **完全不同构**：54 对散射 + q0–q3 low-cache
   vs 单对块复用 + clean-word 借位。任务步骤 3 的关闭条件命中。
2. 可证明安全的手工删除数为 0（§4）；功能性合并需要缺失的综合器代码。
3. 作者侧证据同向：同一方法在 k4–k6 上已证 +1（更差），k0 期望 ≤ −2/loader，
   手工无代码路径。
4. 字表侧不可补偿：e2 余量 0.003 μHa，任何改表权重先算 error_2——本轮未动字表。

## 6. 验证范围声明

- 本轮**未调用** `verify.py`（无小验证、无全量验证）；§3–§4 为 kmx 文本算术 +
  `inspect_circuit.py` 静态计数 + 自写抵消搜索脚本（未进 Git，仅跑在
  `/tmp/.../k0hand/` 临时目录），非验证结论。
- 引用基线结论（Maoxin303 全量 PASS 298,720,881.30）来自
  `experiments/dfthcsos/20261111_lera_deep/README.md` §4.2（salt
  `maoxin303-full-20261111`），非本轮复跑。
- 文件：本 README 唯一新增；`artifacts/`、`submissions/` 零改动；未提交、未推送。
