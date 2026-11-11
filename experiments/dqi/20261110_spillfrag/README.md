# DQI Q−1 统一 spill 第一个候选片段（`20261110_spillfrag`）：min 见证块借线改写

日期：2026-11-10；分支 `codex/dqi-research`；工作区 `.worktree/dqi/`。
本轮是第一次构造（非数字推导）：固定输入只读——e9 包 `dqi.kmb`
（`artifacts/20261108_public_frontier/release/dqi.kmb`）与 kmx 缓存
（`$TMPDIR/dqi_e9diff/e9.kmx`，58,269,417 counted ops，坐标系与
`20261110_exactlive` 的 op_idx 一致，`rev_count == TOTAL` 已自洽）。

## 0. 结论（先行）

- 切口：最小真团见证块 `[16391916,16391920]`（op 坐标；文件行
  `16446734–16446738`，convert 段内），块内容：
  `R q22；CCX q18 q143 q22；CX q22 q95；CX q22 q143；CX q17 q84；HMR q24 b101243`
  （`R q22` 在块前一 op `16391915`）。
- 改写（borrow-rerouting，0 新增 paid）：victim `q22` 的窗内 `R` 删除，
  计算与两次使用改道到借线 `q20`（块内已知 `|0>`，见 §2），借后立刻归还：
  `R q20；CCX q18 q143 q20；CX q20 q95；CX q20 q143；R q20`。
  paid `1→1`（delta 0），新增门全免费（`+2 R`），删除 `1 R`（免费）。
- 切片验证（仿 `s7_broadcast.py` 协议：header + convert 入口 `12006935`..
  改写点，4-shot，仿真种子 99，输入种子 `0xD91`）：
  **TAIL=0：892 qubit 全等＋101,362 bit 全等，确定性重跑一致**
  （`artifacts/20261110_spillfrag/spillfrag.json`）。
- 有效性条件（§3）：本片段的语义正确性**以窗口点火条件
  `AND(q18,q143)@window == 0` 为条件**。静态已证：victim `q22` 窗后存活
  （`CX q22 q143 @16393282` 读窗口值，早于其下一次 `R`），故一旦点火，
  改写即语义不等。点火需 7 路合取
  （`q855&q91&q93&q92&q94&q95&q143` 在相邻节拍取值全 1，
  经 `R+CCX` 梯 `@15633053–63` 冻结为 `q18`，见 §3）。
  124 输入种子 ×4-shot（496 shots，
  输入种子 `0xD91–0xDA8` 与 `0xE00–0xE63`）＋真机初态（全 `|0>`）×60 仿真种子
  （240 shots）均未观测到点火（`firescan.py` 两模；若后续捕获点火种子，
  本片段即转 closed）。
- 否决掉的备选（§5）：11 条 0-paid 闲置线的 deferred-birth
  （出生全为 HMR，移动必扰 RNG 流，toy 实证）——静态 0 paid 上界成立，
  但 bit 精确语义下不可行（对 `punch.json` 口径的实质修正，见 §5）。

## 1. 切口选择

`20261110_exactlive` 的判决：`M_exact=892 @52233023`，最小跨度真团见证
`[16391916,16391920]`（span 4），块内 `live_before==892` 处处成立，
宿主 0 候选（无块内真死线）。11 条 `punch_paid_ub=0` 线
（`q20/q845/q848/q852/q856/q858/q864/q882/q884/q888/q891`，
出生后零触碰、块内零触碰）经本轮核查**出生全部为 HMR**
（op `16391771–16391781`，bit `b101242–b101252`），见 §5。
故统一 spill 的第一实例选最小见证块＋借线改道形状。

文件行映射（op→file）：`16391915→16446733（R q22）`，
`16391916→16446734（CCX）`，`16391917→16446735`，
`16391918→16446736`，`16391919→16446737（CX q17 q84）`，
`16391920→16446738（HMR q24 b101243）`。阶段：convert
（`@enter:convert` 文件行 `12006935`，`@enter:scan` 在 `17698710`）。

## 2. 改写规则（placement）与借线安全

借线 `q20` 在借点已知 `|0>`：`HMR q20 b101249 @16391778` 后到窗口结束
零触碰（`punch.json: cone_touch_ub=0, uses_in_block=0`；本脚本另行独立扫描
复核：`[16391778,16391920]` 内仅出生一行）。规则：

- P1（借）：借 `R` 精确落在被删 victim-`R` 位置（文件 `16446733` 行对行替换），
  要求借线在该点可证 `|0>`（HMR/R 出生＋其后零触碰），且借 `R` 与 compute 间
  无其他触碰借线的 op（此处相邻）。
- P2（算）：compute 改道 1:1（`CCX q18 q143 q22 → CCX q18 q143 q20`），
  paid 数不变（`1→1`，新增 paid 0）。
- P3（用）：每次使用 1:1 紧跟改道（`CX q20 q95`、`CX q20 q143`），不跨
  其他触碰相关线的 op 重排。
- P4（还）：restore-`R` 紧跟最后一次使用之后（零间隙），只杀死后无人读的
  scratch 值（`q20` 的 AND 值用途止于窗内两次 `CX`；`q20` 下一触碰在
  `CCX q37 q361 q20 @16406484`，相隔 14k ops，restore 后为 `|0>` 与原版一致）。
- P5（victim 可丢条件）：victim 窗内值在窗后不再被读（dead-after），
  **或** 窗内计算恒不点火（本例走第二条，见 §3；第一条在此窗不成立：
  `q22` 在 `@16393282 CX q22 q143` 被读，早于其下一次 `R`）。

静态 paid：窗内 `1 CCX → 1 CCX`；新增 `R×2`（免费）；删除 `R q22`（免费）。
unified diff 见 `artifacts/20261110_spillfrag/spillfrag.diff`（±3 上下文，
文件行坐标，仿 `s7_broadcast.diff` 格式）。

## 3. 点火条件与有效性边界（本片段的核心诚实声明）

改写丢弃了 `q22` 的窗口值（重写后 `q22` 保持 `HMR@16391782` 后的 `|0>`，
窗内零触碰）。原版 `q22` 窗后值 `= AND(q18,q143)@window`。
两者一致 ⟺ 窗口 `CCX` 不点火。静态追踪（计入 `CSWAP`-control 不写、
`CZ/Z` 只改相位不改计算基值、`CX`-control 不写）：

- `q18` 在窗前最后一次计算基写入是 `CX q19 q18 @15633063`
  （其前 `HMR q18 @15632848`，之后到窗口全为 control/phase 用途——全区间
  397 次触碰逐一分类，仅 1 次 `CX`-target 写），故 `q18 ≡ q19@15633063`。
- `q19`：`R q19 @15633061` 后仅 `CCX q12 q95 q19 @15633062`，
  故 `q19 ≡ (q12&q95)@15633062`。
- `q12`：`R q12 @15633059` 后仅 `CCX q21 q94 q12 @15633060`；
  `q21`：`R q21 @15633057` 后仅 `CCX q876 q93 q21 @15633058`；
  `q876`：`R q876 @15633055` 后仅 `CCX q855 q92 q876 @15633054`。
  即一段 `R+CCX` 冻结梯 `@15633053–63`，`q18` 被冻结为多叶合取。
- `q143` 在窗前最后出生 `HMR q143 @15996986`，之后有真写
 （`SWAP q143 q882`、`CSWAP q18 q83/q95 q143 ×3`），故窗值初态相关，
  非恒零（866 次触碰已全分类，`control/phase` 外 4 次真写）。

于是点火条件 ≈ `q855&q91&q93&q92&q94&q95&q143` 在梯子节拍全 1
（7 路合取；`q18` 侧 6 路经梯子冻结，`q143` 侧独立）。
**一旦点火且 `q22` 窗后被读（`@16393282` 确实读），改写语义不等。**
本片段的有效性以 `AND≡0` 为条件；该条件在 496+240 shots 中成立
（§4），但未被证明。全局 Q−1 链使用此形状前必须先证（或逐用例验）
点火条件，否则另选 victim-dead-after 窗口（follow-up）。

若条件成立，空洞论证：`q22` 从 `HMR@16391782` 到下一次真写
（`CCX q372 q480 q22 @16416076`，其间 `@16393282/83` 为 control读、
`@16393295` 为 `HMR` 重置）恒为 `|0>`；改写后该区间 `q22` 无需存储
（stale 值即 `|0>`，下游读一致），窗口处 live 值 891（`q20` 被借用但
仍持一值，`q22` 不持值，净 −1）。全局 max 仍 892（其余 8649 块未打孔；
全局 hitting-set 未构造，见 §6）。

## 4. 切片验证

协议（仿 `s7_broadcast.py`）：header（文件 `[:54146]`）＋
`[12006935..改写点]`，4-shot，仿真种子 99，输入种子 `0xD91`；
比较 `q0..q891`＋全部 bit（本改写无新增 bit，无 scratch 除外项）；
重写版确定性重跑。脚本 `spillfrag.py`（可复现；断言 6 行窗文本）。
约 440 万行切片，单次仿真秒级（kickmix 函数-bit 仿真）。

- TAIL=0（止于 restore-`R`；对应原版止于 `16446736`）：
  `qubits_equal=true`（892/892），`bit_mismatches=[]`（101362/101362），
  确定性重跑一致（`spillfrag.json`）。注：本轮 4-shot 下 `q18` 全 0，
  点火条件未被激发——等价性在此输入下成立，其普遍性受 §3 条件限制。
- TAIL=8000（下游 8000 文件行，含 `@16393282` 重读点）：
  892 qubit Z-读全等（含 `q22`，因 §3 条件成立时上下游值一致）；
  20 个 bit 差异，全部落在 HMR 结局位（`b101242–101252,101254–101266`）。
  对照实验：**同版本**加长 tail（O0-vs-O8）即产生 24 个同类 bit 差异，
  故系 Simulator 的 HMR 结局全局敏感性（与片段无关的方法学伪影），
  不是片段导致的语义分叉；但 TAIL=8000 亦不能排除经分叉 guard 位的
  条件相位分叉，故下游等价性**不作主张**，仅如实记录
  （`spillfrag_tail.json`）。
- 点火搜索（反例猎取）：24 输入种子 ×4-shot（496 shots，
  输入种子 `0xD91–0xDA8`）＋真机初态（全 `|0>`）×60 仿真种子
  （240 shots），`AND(q18,q143)` 全 0，未捕获点火输入。
  （脚本：`/tmp` 一次性探针 `sweep.py/sweep100.py/realseed.py`，
  逻辑见 §7；若后续捕获点火种子，本片段即转 closed。）

## 5. 否决的备选：deferred-birth（11 闲置线）

`punch.json` 称 11 线 `punch_paid_ub=0`（出生后零触碰、块内零触碰）；
本轮核查其出生**全部为 HMR**（`@16391771–81`）。deferred-birth
（把出生 HMR 移到窗后、空洞覆盖窗口）会移动 HMR 在 RNG 流中的位置。
玩具对照（`hmr_order_toy.py`→`hmr_toy.json`）：同一 seed/init 下，
单 HMR 移位即改变**所有** HMR 结局位（含被移 HMR 自身），相邻两 HMR
交换亦然。真窗内含 `HMR q24` 且出生块本身是 11 连 HMR，任何移位必扰
下游 guard/mask 位 → bit 精确语义下不可行。结论：`punch` 的 0-paid
是静态锥上界（成立），但 HMR 出生不可移（RNG 流钉住）是其未计入的
硬约束——deferred 形状仅适用于 R 出生 victim（min 窗无此类闲置线）。
此是否决记录（closed），不是构造。

## 6. 验证范围声明（诚实区分）

- **片段级功能证据**：TAIL=0（440 万行前缀 ×3 次：orig/rewritten/
  rewritten-repeat，4-shot，892Q＋101,362b 全等，输入种子 `0xD91`、
  仿真种子 99）＋确定性重跑；点火搜索 496+240 shots 阴性。
- **静态精确**：借线 `|0>`（出生＋零触碰区间扫描）、victim 窗后读点
  （`@16393282`）、`q18` 冻结梯（`@15633053–63`逐跳）、`q143` 真写点、
  paid 计数（`CCX/CCZ/CSWAP` 口径与 `q_live` 一致）。
- **未做**：全电路候选 kmb（58M 行链不可行，未构造）；官方验证器
  （基线字节未动）；全局 8650 块 hitting-set（本片段只打一个窗，
  全局 Q−1 未证明）；点火条件的证明或点火输入的存在性证明
  （§3 条件悬置）。
- **候选/提交/推送**：无。验证器未改动。凭据无。
- 环境：本工作区 `.venv`（Python 3.12，PyPI 原生 kickmix；
  macOS 未用数据包内 Linux `kickmix.so`）。

## 7. 过程文件与引用

- 脚本：`experiments/dqi/20261110_spillfrag/spillfrag.py`
  （切片＋diff 生成）、`hmr_order_toy.py`（HMR 移位对照）、
  `firescan.py`（点火扫描：orig-only TAIL=0 切片上扫 `q18/q143`；
  `init-seeds` 模（输入种子 `0xE00..`，仿真种子 99）与
  `real-init` 模（全零初态，变仿真种子）；§4 的 496+240 shots
  即此脚本两次运行的观测值，可复跑子集）。
- 产物：`artifacts/20261110_spillfrag/` 内 `spillfrag.diff`、
  `spillfrag.json`、`spillfrag_tail.json`、`hmr_toy.json`。
- 引用：`20261110_exactlive/README.md`（`M_exact=892`、最小见证块、
  `punch.json` 11 线表——其 HMR 出生细节见本轮核查）；
  `20261109_dqi_decoder_struct/README.md` §5（`s7_broadcast` diff 格式与
  切片协议来源；`s7_broadcast.diff/json` 为格式模板）；
  输入只读：`artifacts/20261108_public_frontier/release/dqi.kmb`、
  `$TMPDIR/dqi_e9diff/e9.kmx`。
