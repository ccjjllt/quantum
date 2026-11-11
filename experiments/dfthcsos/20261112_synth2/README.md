# 综合器 stage-2：toy BFS + k0 试探（2026-11-12）— toy 通过，k0 关闭，整线关闭

分支 `codex/dfthcsos-research`，工作区 `.worktree/dfthcsos/`。
只报实测；未提交、未推送、未改官方验证器/数据；字表冻结（未动）。
判据（三者全齐才算候选）：toy BFS 原理成立 + k0 static −4 双遍 T + 小验证 PASS。
实测：toy 通过，k0 静态门未达（297→≤295 不满足，未跑小验证），故无候选，stage-2 关闭。

## 0. 输入与口径

- 基线：`artifacts/20261111_maoxin303/`（Mao303）与 `artifacts/20261111_lera11x/`。
- 优化问题口径：`experiments/dfthcsos/20261112_synth/README.md` §4（min |S|+m'，
  约束 C1–C4；k4–k6 反例早停，只动 k0，k7–14 饱和不动）。
- 本轮新增文件（本目录，仅 2 个单文件脚本 + 本 README）：
  `toy_bfs.py`（toy 精确最小重拆分）、`k0_try.py`（k0 因子合并静态搜索）。
  `artifacts/`、`submissions/` 零改动；`data/competition/` 未动。

## 1. toy 微实例 BFS（通过）

- 取子：k0 q11 的 6 个**互异**静态 products（每无序对取 1 代表）：
  {(q0,q1),(q0,q125),(q0,q126),(q1,q125),(q1,q126),(q125,q126)}→q11，
  在 `angle_k_0.kmb` 中的计数为 2/8/5/8/6/4（脚本断言 existential，§实测输出）。
  控制位 4（x0=q0,x1=q1,x2=q125,x3=q126）≤6，products 6 ≤12。
  取互异代表的原因：同名静态对在全电路不同时刻是不同函数（CX 重编程），
  多拷贝在“冻结快照”抽象下会偶数抵消（伪节省）；取 distinct 是保守切片，
  每个静态对的功能采样于一个时间点。
- 抽象（快照）：4 控制变量独立输入；q11 输出 f = 6 个两两 AND 的 XOR
  （2 阶初等对称 e2，真值表 16 位 `0x7ee8`）。CX/X 免费（仿射组合免费），
  CCX 计 1。X/CX/CCX 电路任一 AND 输入必为（主变量+先前 AND 输出）的仿射组合，
  搜索覆盖全部此类电路，故下界精确（乘法复杂度）。
- 原代价 6；上界：3-AND 分解 `(x0^x1)&(x2^x3)+(x0&x1)+(x2&x3)` 成立已验。
- 下界（穷举）：k=1 全部 140 个非线性 AND（31 个非零仿射输入的无序对，
  去退化/去重）无一使 `f` 落入 `span(仿射, w)`；故最小 >1。
  k=2 首命中 witness（早停，精确性只需 k=1 穷举 + 一个 k=2 实例）：
  `w1=0x000f=(x3+1)&(x2+1)`（即 ¬x3&¬x2），
  `w2=0x1881=(x1+x2+x3+1)&(x0+x2+x3+1)`（w1 系数 0，无链式 setup），
  输出 `f=w1^w2^(x0+x1)`（余量 `0x6666=x0^x1`，已断言验算）。
  故精确最小 =2：**6→2，省 4 CCX（切片内）**，原理成立。
- 实测命令与输出：
  `uv run python experiments/dfthcsos/20261112_synth2/toy_bfs.py` exit=0，
  输出：pairs 2/8/5/8/6/4；`k=1 exhaustive: 140 ... match=False`；
  `k=2 ... match=True`；witness 如上；`TOY PASS (2 < 6)`。
- 范围：纯静态 + 穷举（16 位掩码位运算），**未调用 `verify.py`/`manual_verify.py`**，
  未做电路编辑，未碰字表。结论仅为“组合核心可打包”，不等价于全 loader 可省。

## 2. k0 试探（关闭：静态门未达，未跑小验证）

- 模式：同目标共享一控制的两 loads 合并
  `CCX a b→t + CCX a c→t ⇒ CX c→b; CCX a b→t; CX c→b`（删第二条），净 −1 CCX，
  +2 CX（T 免费）。需 ≥2 处不交合并才达 static 297→≤295。
- 安全条件（充分，kmx 文本静态判）：开区间内 (i) 任何提及 t 的行禁入
  （含 CX/CCX/HMR/CZ/R，否则区间读 t 见不同值）；(ii) a/b/c 作 target 禁入；
  (iii) R/HMR/CZ 提及 a/b/c 禁入。a/b/c 作 CX/CCX 控制允许（读冻结值）。
- 实测（`uv run python experiments/dfthcsos/20261112_synth2/k0_try.py`，exit=1）：
  `phase2 ccx=228 setup=11 loads=217`；
  同目标共享恰一控制对总数 **2677**，阻断分布
  `{'t-mention': 2677, 'write': 0, 'phase': 0}`——**100% 被区间内提及 t 的 CX 阻断**
  （word 位全程被 CX 重编程为活位，无局部干净窗口）；
  安全候选 **0**。`k0hand` 的同对抵消 0 加上本轮同目标因子合并 0。
- 门控执行：static 停留在 297，未达 297→≤295，故按约束**未跑 2440-shot 小验证**，
  未调 `heuristic_costs`（T 未变）、未做 `recover_words` words_match 试验
  （无编辑对象可测）、未写任何 kmx（`/tmp/synth2_k0*.kmx` 仅中间文本，
  未落 `artifacts/`）。字表/树/权重冻结未动（e2 余量 0.003 μHa，未评估即未触）。
  k4–k6、k7–14 未动。

## 3.  verdict

- toy：PASS（6→2 精确最小，§1）。
- k0：FAIL（安全因子合并 0，static 297 未动，不满足“static −4 双遍 T”前置，
  小验证未跑）。按“三者全齐”判据，**无候选，stage-2 关闭**。
  后续若出现作者综合器代码或 word-CX 调度级重写能力，可另立项；
  纯 kmx 文本局部合并路线在本轮数据下已穷尽（k0hand 0 + 本轮 0）。

## 4. 验证范围声明

- 本轮**零次** `verify.py`/`manual_verify.py` 调用（k0 门控未过故无小验证；
  toy 为位运算穷举；`kickmix.Circuit.from_file/to_file` 仅作 kmx 文本读写，
  非验证结论）。引用的基线（Mao303 全量 PASS 298,720,881.30、Lera 机制、
  k0hand 0 候选）来自既有 README，非本轮复跑。
- 资源口径：toy 切片 6→2 是 4 变量快照抽象内的 AND 数，不等于 loader T；
  k0 T/Q/λeff/score 全未变，无 −80K。未把未执行的验证写成通过。
- 文件：本目录 `toy_bfs.py`、`k0_try.py`、本 README 为仅有新增；
  未提交、未推送；大文件/token 未进 Git。
