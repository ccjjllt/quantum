# DQI Q−1 统一 spill 规模化（`20261110_spillmulti`）：5 见证块全窗重演

日期：2026-11-10；分支 `codex/dqi-research`；工作区 `.worktree/dqi/`。
首个片段（`20261110_spillfrag`）之后的第一轮规模化：固定输入只读——e9 包
`dqi.kmb`（`artifacts/20261108_public_frontier/release/dqi.kmb`）及 kmx 缓存
（`$TMPDIR/dqi_e9diff/e9.kmx`，58,269,417 counted ops）。
本轮把 borrow-reroute 模板从"部分窗＋条件点火"升级为"全窗重演＋死后 victim"，
并在 5 个真团见证块上逐个验证。

## 0. 结论（先行）

- 5 块中共 2 块可构造（D、E），3 块经静态证明无借线（A、B、C，未构造）：
  | 块 | 区间（op） | span | victim 窗 | 借线 | paid delta | 点火条件 | 切片 verdict |
  |---|---|---|---|---|---|---|---|
  | A | [6633495,6634836] | 1341 | q852 [6633494..6634847] | 无（静态已证） | — | — | 未构造（无借线） |
  | B | [52022400,52023741] | 1341 | q861 [52022399..52023752] | 无（静态已证） | — | — | 未构造（无借线） |
  | C | [52028980,52030331] | 1351 | q881 [52028979..52030332] | 无（静态已证） | — | — | 未构造（无借线） |
  | D | [52227905,52233023] | 5118 | q863 [52227904..52228189] | q845（HMR@52030323，严格零触碰） | 0（10→10） | 无（全窗重演，victim 死后） | 全等通过（§4） |
  | E | [41187182,41187187] | 5 | q878 [41187181..41187187] | q875（HMR@41176959，严格零触碰） | 0（1→1） | 无（全窗重演，victim 死后） | 全等通过（§4） |

- 新模板（全窗重演，§2）：`R qV; …qV 全触碰…; HMR qV bX` →
  `R qB; …qV→qB 全改道…; HMR qB bX`（同位、同比特、HMR 流不动）。
  与首片段的部分窗形状不同：victim 窗值有人全程接盘（含 SWAP/CX-target 写），
  kill-HMR 改道后 victim 永死（下一触碰为 R/HMR 重生），故**无点火条件**——
  唯一条件是借线借点 `|0>`（静态已证＋切片比特全等佐证）。
- 切片验证（仿 `s7_broadcast`/`spillfrag` 协议：header + convert 入口
  `12006935`..改写点，4-shot，仿真种子 99，输入种子 `0xD91`）：
  D、E 均为 TAIL=0 **892 qubit 全等＋全部 bit 全等＋确定性重跑一致**。
- 否决记录：A/B/C 在严格 q20 判据（HMR 出生＋零触碰）及放宽判据
  （R/HMR 出生＋其后仅 control/phase 读）下均无借线——全历史前向普查
  （`search.py`→`search.json`）已证，不是"没找到"，是"不存在"。
  deferred-birth 形状仍 closed（`hmr_toy.json` 本轮重跑确认）。

## 1. 块选择

- 长块：238 长块（span>1000）中跨度最小的 3 个（`longblocks.json` 按 span 排序）：
  A `[6633495,6634836]`（1341）、B `[52022400,52023741]`（1341）、
  C `[52028980,52030331]`（1351）。
- 短块：M_at 块 D `[52227905,52233023]`（span 5118，含 `M_exact=892@52233023`）
  ＋除首片段 `[16391916,16391920]` 外最小的短块 E `[41187182,41187187]`
  （span 5，`exact_live.json` full_runs 排序）。
- 三长块边界形状一致：块前 `(R;CCX)×2` 双 ancilla 对
  （A：q851/q852；B：q849/q861；C：q863/q881），窗内 32–33 次 CX 读＋尾部 HMR。

## 2. 改写规则（全窗重演）与借线安全

记 victim 窗 `[b..k]`：`b=R qV` 出生，`k=HMR qV bX` 杀死，
窗内 `qV` 触碰角色 ∈ {CCX-target（算）、CX-control（用）、CX-target、
SWAP、HMR}（D 含后三者，A/B/C/E 仅前二＋首尾；脚本逐块断言角色集合，
`spillmulti_sim.py:verify_block`）。改写 = 窗内所有 `qV` token→`qB`
（含出生 R 与 kill-HMR，同位、同比特），其余行不动。

- P1（借）：借 R 落在被删 victim-R 位；要求借线在该点可证 `|0>`：
  出生为 R/HMR，且出生到 kill 窗内零触碰（严格 q20；脚本对 D/E 独立
  双向扫描复核：出生行文本断言＋`(birth..F_B)` 零触碰＋`[F_B..F_K]` 零触碰）。
- P2（算/用/写全接）：窗内每次 `qV` 触碰 1:1 改道（含 CX-target 写与 SWAP；
  SWAP `q854 q863→q854 qB` 等价因前缀归纳相等，初值同为 `|0>`）。
- P3（杀）：kill-HMR 改道到借线（同比特、同流位；HMR 总数/位置不变，
  仅 kill 行 qubit 操作数改变）。借线以 `|0>` 结束（HMR 重置），与原版
  "未触碰故 `|0>`" 一致；victim 全程 `|0>`，窗后原版值已死（被 HMR 读走），
  下游一致。
- P4（paid）：纯改名，`CCX/CCZ/CSWAP` 数不变（D：10→10；E：1→1，delta 0）；
  新增 `R qB`（免费）／删除 `R qV`（免费），只允许免费门增减 ✓。
- 有效性：全窗重演是精确重放（初值同 `|0>`、操作序列同构、kill 同位），
  故对**任意输入**语义等价——无点火条件；与首片段（部分窗＋`AND==0` 条件）
  的本质区别。HMR 不移位（`hmr_order_toy.py` 本轮重跑：
  移位/交换 HMR 即改比特结局，`hmr_toy.json`），故 HMR 出生借线可用
  （出生不动，只借其 `|0>` 值）。

## 3. A/B/C 无借线的静态证明（否决记录，非构造）

`search.py`（= `/tmp/fullsnap3.py` 定稿版）：全历史单遍前向，
role-aware 值影响跟踪（写角色：X、CX-target、CCX-target、SWAP/CSWAP 全员、
R/HMR；control/phase 读不影响 `|0>`），快照每块窗起点 `b` 处
`last_affect`，窗内触碰集 `[b..k]`（k 延到 kill-HMR，超出块尾）。

- A：窗内未触碰 855 线中，`last_affect∈{R,HMR}` 者 0 个（`search.json`）。
- B：同上，0 个。C：同上，0 个。
- 即：在严格 q20（HMR 出生＋零触碰）与其放宽版（R/HMR 出生＋其后仅
  control/phase 读）下，三块对"跨越整窗"的借线需求都无解——855 条闲置线
  的最近值影响操作皆为写（持有累积值），符合 892-live 稠密区的预期。
- 窗内出生借用亦无：A/B 窗内出生仅尾部单个 HMR（其后无 victim 触碰可接）；
  C 尾部 HMR 群（`@52030321–31`）之后 victim 仅剩 kill-HMR，无算子可改道。
- 结论：A/B/C 在 borrow-reroute 模板下**未构造**（不是点火反例 closed，
  是无借线；全局 hitting-set 需其他形状，follow-up）。

## 4. D/E 切片验证

协议同首片段 §4（header + `[12006935..kill]`，4-shot，种子 99，
输入 `0xD91`；892Q＋全 bit＋确定性重跑）：

- E（短块 span 5，全块覆盖）：TAIL=0（止于 `HMR q875 b99126`，
  文件 `41258109`）：892/892 qubit 全等，101362/101362 bit 全等
  （含 kill 比特 `b99126`），确定性重跑一致（`spillE.json`）。
  窗角色 `{R:1,CCX:1,CX:4,HMR:1}`，paid 1→1 delta 0，
  借线出生 `HMR q875 b99126 @op41176959`，gap 10226 文件行零触碰
  （脚本双向断言）。洞覆盖整窗 `[41187181..41187187]` ⊇ 块。
- D（M_at 块头，全窗重演；注意洞只覆盖块头 `[L..L+284]`，M_at 点
  `52233023` 不在洞内，如实声明）：TAIL=0（止于 `HMR q845 b99524`，
  文件 `52299746`）：892/892 qubit 全等，150003/150003 bit 全等
  （含 kill 比特 `b99524`），确定性重跑一致（`spillD.json`）。
  窗角色 `{R:1,CCX:1,CX:36,SWAP:2,HMR:1}`（41 次改道，含 2 SWAP 与
  CX-target 写），paid 10→10 delta 0，
  借线出生 `HMR q845 b99564 @op52030323`，
  gap 197592 文件行零触碰（脚本双向断言）。

## 5. 验证范围声明（诚实区分）

- **片段级功能证据**：D/E 各 TAIL=0（前缀＋改写点 ×3：orig/rewritten/
  rewritten-repeat，4-shot，892Q＋全 bit 全等，输入 `0xD91`、仿真种子 99）
  ＋确定性重跑；A/B/C 为全历史静态普查（实际执行，有输出），无切片
  （无构造对象，不虚构验证）。
- **静态精确**：借线 `|0>`（出生行文本＋双向零触碰扫描双重断言）、
  victim 窗角色集合断言、kill-HMR 同位改道、paid 改名前后计数、
  HMR 流位置不变（窗内 HMR 仅 kill 一行，前后断言）。
- **未做**：全电路候选 kmb（未构造）；官方验证器（基线字节未动）；
  全局 8650 块 hitting-set（本轮 5 块中 2 构造＋3 否决，远未覆盖全局）；
  下游 TAIL>0 等价性不主张（kill 比特下游 guard 如 E 的
  `CZ q48 q36 if b99126` 不在验证范围内）。
- **候选/提交/推送**：无。验证器未改动。凭据无。
- 环境：本工作区 `.venv`（Python 3.12，PyPI 原生 kickmix）。

## 6. 过程文件与引用

- 脚本：`experiments/dqi/20261110_spillmulti/search.py`（借线普查，全历史单遍；
  输出 `artifacts/20261110_spillmulti/search.json`；逻辑源自
  `20261110_exactlive/punch.py` 的 role 分类＋`longblocks.py` 的块扫描）、
  `borrow_strict_check.py`（严格零触碰抽查，一次性探针，数见 §4）、
  `spillmulti_sim.py`（D/E 改写＋切片＋diff 生成；协议源自
  `20261109_dqi_decoder_struct/README.md` §5 的 `s7_broadcast` 与
  `20261110_spillfrag/spillfrag.py`）、`hmr_order_toy.py`（`spillfrag` 同名
  脚本的复刻重跑，ART 路径指向本轮）。
- 产物：`artifacts/20261110_spillmulti/` 内 `search.json`、`spillD.{diff,json}`、
  `spillE.{diff,json}`、`hmr_toy.json`。
- 引用：`20261110_exactlive/{exact_live,longblocks,punch}.json`
  （块清单与候选）；`20261110_spillfrag/README.md`（首片段：部分窗形状、
  点火条件分析、deferred-birth 否决——本轮 D/E 形状是其无条件升级版）；
  输入只读：`artifacts/20261108_public_frontier/release/dqi.kmb`、
  `$TMPDIR/dqi_e9diff/e9.kmx`。
