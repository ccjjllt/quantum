# DQI Q−1 统一 spill 调度（`20261110_spillunified`）：D+E 双块独立借线合并

日期：2026-11-10；分支 `codex/dqi-research`；工作区 `.worktree/dqi/`。
本轮是第一次做"统一"：多块组合＋全局一致性。固定输入只读——e9 包
`dqi.kmb`（`artifacts/20261108_public_frontier/release/dqi.kmb`）及 kmx 缓存
（`$TMPDIR/dqi_e9diff/e9.kmx`，58,341,262 文件行）。不重复首片段与规模化的
推导（见 `20261110_spillfrag/README.md`、`20261110_spillmulti/README.md`）；
本轮只证组合相容性。

## 0. 结论（先行）

- 选块：M_at 块 D `[52227905,52233023]` 头窗（victim `q863`→借线 `q845`）
  ＋短块 E `[41187182,41187187]` 全窗（victim `q878`→借线 `q875`）。
  两块均为 `spillmulti` 已验证无点火全等（全窗重演＋victim 死后），
  故组合不引入条件点火；首片段块（含 `AND==0` 条件）有意不选。
- 调度：**各块独立借线**（起步方案即终选）。同一根被消除线在结构上互斥
  （§2），未硬合。
- 干涉普查（§2）：E 窗零触 `q845/q863`；D 窗零触 `q878`；两改写均不引入
  新增交叉触碰；借线 gap 无对方窗口侵入。唯一记录在案的交叉是 D 窗内
  19 次第三方 `q875` 触碰（E 借线在 E kill+HMR 重置**之后**的顺序复用，
  非 gap 侵入，由组合切片覆盖）。
- 组合切片（header＋`[12006935..52299746]`，两处改写同时生效，4-shot，
  仿真种子 99，输入种子 `0xD91`）：**892 qubit 全等＋150003 bit 全等＋
  确定性重跑一致**（`spillunified.json`，verdict `MERGE_EQUAL`）。
  即"两个 Q−1 切口同存"的片段级组合证据。
- paid：D `10→10`＋E `1→1`，**总 delta 0**（纯改名＋免费 `R` 一换一）。
- Q 含义（诚实声明，§4）：两块各自 spill 不同线 ≠ 全局 Q−1。
  全局 Q−1 仍需 hitting-set 论证（8650 块中 2 块同存，本轮只证相容性，
  不宣称 Q−1 达成）。

## 1. 统一调度设计：两种方案比较

- 方案 A（同一根被消除线）：两窗共用一条借线。要求该线在
  `[E_B..D_K]`（文件 `41258103..52299746`，约 11M 行）全程 `|0>` 可借。
  结构性否决（无需全历史普查）：
  - D 的借线 `q845` 出生于文件 `52101869`（`HMR q845 b99564`），**晚于 E 窗**
    （`E_K=41258109`），不能覆盖 E 窗；
  - E 的借线 `q875` 在 D 窗内被写 19 次（含 4 次 `CCX` target 写，
    如 `CCX q840 q885 q875 @52299600`），不能横跨 D 窗。
  故 `{q845,q875}` 中无共享借线；其他线的共享可能性本轮未普查，
  不作主张。方案 A 关闭（否决记录）。
- 方案 B（各块独立借线，终选）：E 用 `q875`、D 用 `q845`，各借各、
  各杀各（kill-HMR 同位、同比特：`b99126`/`b99524`，HMR 流位置不动）。
  相容条件＝两窗改写集合不交＋借线 gap 互不侵入（§2 逐项验证）。
- 为何选 D+E 而非 D+首片段块：D/E 皆无条件等价（全窗重演＋死后 victim），
  组合切片的任一 mismatch 都可直接归因于合并本身；首片段块带
  `AND(q18,q143)==0` 点火条件，会污染组合 verdict 的归因，故不选。

## 2. 干涉普查（合并前静态门，脚本内断言）

文件坐标（原文件为准；E 窗 `[41258103..41258109]`，D 窗 `[52299461..52299746]`）：

| 检查项 | 结果 |
|---|---|
| E 窗触 `q845` / `q863`（D 的借线/victim） | 0 / 0 行 |
| D 窗触 `q878`（E 的 victim） | 0 行 |
| D 窗触 `q875`（E 的借线） | 19 行（`CX×15`＋`CCX×4`），全部位于 E kill（`41258109`）之后，顺序复用，非 gap 侵入 |
| E 改写引入的新增交叉触碰 | 无 |
| D 改写引入的新增交叉触碰 | 无 |
| E 窗落入 D 借线 gap（`52101869..52299461`） | 否（E 窗远早于 `q845` 出生） |
| D 窗落入 E 借线 gap（`41247877..41258103`） | 否（D 窗远晚于 E kill） |
| kill 比特 | `b99126` vs `b99524`，互异；各窗 HMR 仅 kill 一行，前后无 HMR 移位 |

任一门失败即回退单块、不硬合——本轮全门通过，故合并改写。

## 3. 合并改写与组合切片验证

- 合并 diff：`artifacts/20261110_spillunified/spillunified.diff`——两块各自
  diff 上下文拼接（E 段 ±3 行、D 段 ±3 行，行号以原文件为准）。
  经字节比对：E 段与 `spillE.diff`、D 段与 `spillD.diff` 正文完全一致
  （仅文件头标注块名），即合并改写＝两单块改写的直接叠加，无额外编辑。
- 组合切片：`header[:54146]`＋`[12006935..52299746]`（覆盖 E 窗与 D 窗的
  最小公共切片，改写止于后一块 TAIL=0），4-shot，仿真种子 99，
  输入种子 `0xD91`；比较 `q0..q891`＋全部 bit；改写版确定性重跑。
  脚本 `spillunified.py`（仿 `spillmulti_sim.py` 切片方法；改写、断言、
  diff 生成、仿真一体，可复现）。
- 结果（`spillunified.json`）：`qubits_equal=true`（892/892），
  `bit_mismatches=[]`（150003/150003，含两 kill 比特 `b99126/b99524`），
  `qubits_deterministic=true`，verdict `MERGE_EQUAL`。
  覆盖约 40M 文件行的三遍仿真（orig/rewritten/rewritten-repeat）一次通过，
  无 mismatch、无回退。

## 4. paid 与 Q 含义（只证相容性，不宣称 Q−1）

- paid 总账：D `10→10`（`CCX×10` 纯改名），E `1→1`（`CCX×1` 纯改名）；
  新增 `R q845`/`R q875`（免费）各 1，删除 `R q863`/`R q878`（免费）各 1；
  **总 delta 0**。
- Q 含义：D 洞覆盖块头 `[L..L+284]`（`M_at` 点 `52233023` 不在洞内，
  见 spillmulti §4），E 洞覆盖全窗。两洞同存时，各自窗口处 live−1，
  但窗口时段不重叠，全局 max 是否 −1 取决于其余 8648 块的 hitting-set——
  **本轮未构造，只证"两切口可同存且语义全等"，不宣称全局 Q−1 达成。**

## 5. 验证范围声明（诚实区分）

- **组合级功能证据**：最小公共切片 TAIL=0（约 40M 文件行前缀 ×3：
  orig/rewritten/rewritten-repeat，4-shot，892Q＋150003b 全等，
  输入 `0xD91`、仿真种子 99）＋确定性重跑；干涉普查 7 项全过（实际执行）。
- **静态精确**：借线 `|0>`（沿用 spillmulti 出生＋双向零触碰断言）、
  victim 窗角色集合、kill-HMR 同位改道、paid 改名前后计数、
  HMR 流位置不变、合并 diff 与单块 diff 正文一致。
- **未做**：全电路候选 kmb（未构造）；官方验证器（基线字节未动）；
  下游 TAIL>0 等价性不主张（kill 比特下游 guard 如
  `CZ q48 q36 if b99126`、`CZ q850 q840 if b99524` 不在验证范围内）；
  全局 8650 块 hitting-set（2 块同存，远未覆盖）；共享借线全历史普查
  （方案 A 仅结构性否决，不宣称全局无共享借线）。
- **候选/提交/推送**：无。验证器未改动。凭据无。
- 环境：本工作区 `.venv`（Python 3.12，PyPI 原生 kickmix；
  macOS 未用数据包内 Linux `kickmix.so`）。

## 6. 过程文件与引用

- 脚本：`experiments/dqi/20261110_spillunified/spillunified.py`
  （干涉普查＋合并改写＋组合切片＋diff/JSON 生成；切片协议源自
  `20261109_dqi_decoder_struct/README.md` §5 的 `s7_broadcast` 经
  `20261110_spillfrag/spillfrag.py`、`20261110_spillmulti/spillmulti_sim.py`
  传递）。
- 产物：`artifacts/20261110_spillunified/` 内 `spillunified.diff`、
  `spillunified.json`。
- 引用：`20261110_spillmulti/README.md`（D/E 全窗重演形状、无点火全等、
  A/B/C 无借线否决、paid 口径）；`20261110_spillfrag/README.md`
  （首片段部分窗＋点火条件——本轮未选用，理由见 §1）；
  输入只读：`artifacts/20261108_public_frontier/release/dqi.kmb`、
  `$TMPDIR/dqi_e9diff/e9.kmx`。
