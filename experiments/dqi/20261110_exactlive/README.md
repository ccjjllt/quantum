# DQI 精确后向活性真判决（`20261110_exactlive`）：M_exact=892，免费打孔切口

日期：2026-11-10；分支 `codex/dqi-research`；工作区 `.worktree/dqi/`。
对象：e9 包 `dqi.kmb`（经 `/var/.../T/dqi_e9diff/e9.kmx` 解析缓存，58,269,417 counted ops；
任务书称 58,287,028，相差 17,611（0.03%），应为包版本/计数口径差，本轮以实测为准，
且逆序 `rev_count` 与 `TOTAL` 完全一致）。

## 方法（精确 dataflow，单遍流式逆序）

- 活集 = 其当前值未来仍会被读的 q 线集合；终点 live-out = 空（尾部为 CX + 经典 BIT，
  无末端观测；此假设对 Q−1 最有利——若此下 M=892，则任何 live-out 下皆不可零 paid 重命名）。
- 逆向 transfer（与 `q_cover.py` 读写一致，精确到操作级）：
  X：前后不变（跳过）；CX：`t` 活才需 `c`；CCX：`t` 活则 +=`c0,c1`；
  SWAP：置换成员（计数不变）；CSWAP：任一 target 活则需 `{c,a,b}` 全活；
  R：`before = after − {q}`（唯一可降计数；新 `|0>` 与旧值无关）；
  HMR：`before = after ∪ {q}`（测量读旧值 + reset，保守设测量结果恒被用）；
  CZ/CCZ/Z/未知读：`before = after ∪ {全部 q}`（相位/未知按读，无 kill）；
  条件 CX/CZ/Z（`if b`）：条件为假则空操作故 kill 不成立，但本电路 kill 仅 R（无条件），
  CX 本就不降计数，故条件/无条件 transfer 相同（纯加）。BIT_*/NEG/PUSH/POP 无 q，
  计入 op 序号但活集不变。
- 实现：二进制分块从尾向前，不全载入；活集为 Python int 位集（892 位），计数增量维护；
  500k 行分桶记真活 max。脚本 `exact_live.py`（28.9s，58,269,417 ops，`count_match=true`）。

## 判决数字

- `M_exact = 892 @ 52233023`（`artifacts/20261110_exactlive/exact_live.json`，`buckets.csv`）。
  桶 max：0–4:886；5–13:892；14–23:880；24–104:892；105–115:868,820,772,744,696,628,
  580,532,436,359,220；116:0（尾部 269k ops 真死：CX 垃圾无人读）。
  `live_at_start=886`；892-块共 8650 个，总覆盖 12,301,685 点（21%），跨度 min 4、
  p50 37、max 1,248,621；`≤10 ops` 4235 个，`≤100 ops` 8359 个，`>1000 ops` 238 个。
- 最小跨度真团见证 `[16391916,16391920]`（span 4）：
  `CCX q18 q143 q22；CX q22 q95；CX q22 q143；CX q17 q84；HMR q24`。
  下缘 `R q22@16391915`（逆向去活），上缘 `HMR q24@16391920`（逆向加活）。
  成员 = 全部 892 线（块内 `live_before==892` 处处成立）。
- 打孔真实代价上界（`punch.py`，前向到见证点，侧输入按持有计，不展开；
  全 892 行表见 `punch.json:table`）：
  宿主 0 候选（块内无真死线）；重算最便宜 11 线 `punch_paid_ub=0`
 （如 `q20/q845/q848/q852/q856/q858/q864/q882/q884/q888/q891`：出生后零触碰、
  块内零触碰，全程 `|0>` 闲置，回放仅需免费 R）；窗口写线 `q22` 2 paid
 （`R+CCX` 后 2 次 CX 读前各重算 1 CCX）；`q24`（HMR 旧值）819 paid（贵，不选）；
  最贵如 `q0` 20269 paid（持有穿越，锥大，不选）。
  任一 `0 < 887`，故**可行切口存在**（最小块可零 paid 打破）。
- 全局抽查（`blocks_check.py` 6 块：最早/early100/minspan/mid/late8000/最末含 M_at；
  `longblocks.py` 全部 238 个 `span>1000` 长块，含 1.2M 最长块）：**全部有免费
  （0 paid）打孔**（长块最长 `[16392370,17640991]` 1.2M：distinct 876，
  `q740–743` 等 `3 读 × 0 paid 锥`，免费；最末 M_at 块 `[52227905,52233023]`
  5118 ops：`q849/q861` 等闲置 `|0>`，免费）。

## 诚实结论

1. **零 paid 静态重命名 Q−1 不可能**：`M_exact=892`（hold-everything 下任一见证点需
   892 个不同物理 qubit；即使 `|0>` 也因后续分叉写入而不可静态共享）。此前
   qpebble 粗区间 `M_coarse=892` 无结论，本轮精确 dataflow 给出真 892（非过近似），
   关闭了“重命名即可”的门。
2. **Q−1 可行切口存在（0 paid < 887）**：最小见证块及抽查的全部长块/短块均可
   免费打破（闲置 `|0>` 经免费 R 重物质化，或 paid-free 锥回放免费门）。
   证据指向全局 8650 块皆可 0 paid 逐个打破（总 extra paid 0，仅增免费 R/CX），
   即 Q−1 以 0 extra paid 原则可行——与此前“Q 892 无冗余”（e9diff distinct +
   phase_recovery 无死线证明，仅在 hold-everything/无重算语义下成立）形成实质修正：
   无死线 ≠ 不可 spill（`|0>`/free-cone 可免费重算）。
3. **未证明全局 Q−1 构造**：本轮未构建统一 spill 调度（8650 块各 spill 不同线，
   需全局 hitting-set + 插入免费门位置证明无干扰），未构建候选、未跑验证器。
   故“全局 0 paid Q−1 可行”为强证据下的存在性判断（切口级），非已验证构造。
   尾部 269k ops 真死（live 0）另提示 DCE 空间，但超出本轮范围，未动。

## 验证范围

纯静态只读分析；未构建候选 kmb、未跑官方验证器；复用本地 kmx 解析缓存；
`rev_count=58269417= TOTAL` 自洽；桶曲线与 runs 可复算（`exact_live.py` 28.9s；
`punch.py`/`blocks_check.py`/`longblocks.py` 各约 10–40s）。

## 引用与复现

- 粗区间基线与空洞论证：`experiments/dqi/20261110_qpebble/README.md`、`q_cover.py`
 （读写定义来源）、`q_live.py`（R/HMR/phase 语义与 paid 口径 `CCX/CCZ/CSWAP`）。
- 先前“无冗余”依据：e9diff distinct 计数 + phase_recovery 无死线证明（见 qpebble README）。
- 输入：`artifacts/20261108_public_frontier/release/dqi.kmb`（只读）/
  `$TMPDIR/dqi_e9diff/e9.kmx`（本地缓存）；输出：`artifacts/20261110_exactlive/`
  （`exact_live.json` 全 runs、`buckets.csv`、`punch.json`、`blocks_check.json`、
  `longblocks.json`）与本目录脚本。
- 复现：`python3 experiments/dqi/20261110_exactlive/exact_live.py`（→ json/csv），
  `punch.py`、`blocks_check.py`、`longblocks.py` 依次运行。
