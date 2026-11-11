# DQI Q−1 统一 spill 全电路推进（`20261110_spillglobal`）：D+E+3 新切口共存

日期：2026-11-10；分支 `codex/dqi-research`；工作区 `.worktree/dqi/`。
本轮是第一次向"全电路"走（此前止于 D+E 双块，见
`20261110_spillunified/README.md`）。不重复首片段/规模化/统一调度的推导
（见 `20261110_spillfrag`、`20261110_spillmulti`、`20261110_spillunified`
三份 README：D/E 无点火全等、A/B/C 静态无借线、D+E 合并 MERGE_EQUAL paid
delta 0）。固定输入只读：e9 包 `dqi.kmb`
（`artifacts/20261108_public_frontier/release/dqi.kmb`）及 kmx 缓存
（`$TMPDIR/dqi_e9diff/e9.kmx`，58,341,262 文件行）。

## 0. 结论（先行）

- 从 238 长块中选出 3 个新切口 F/G/H（§1），各经独立 TAIL=0 切片验证
  （4-shot，仿真种子 99，输入种子 `0xD91`）：**892 qubit 全等＋全部 bit
  全等＋确定性重跑一致**，paid delta 均为 0（F `10→10`，G `43→43`，
  H `10→10`；G 窗内 42 个第三方 paid 原样保留）。
- 5 切口（D+E+F+G+H）干涉普查：窗范围两两不交、改写零新增交叉触碰、
  borrow gap 零带触碰侵入、kill 比特 5 方互异。但**对方窗零触碰不成立**：
  9 对有序窗触碰非零（§2）。逐项时戳证明全部落入 4 类已证无害形状
  （a 出生前触碰／b stale-victim 透明组合／c kill 后顺序复用／
  d 重生后触碰；D→q875 的 c 类是 spillunified 既有先例），`bad={}`，
  故合并（任一真反例即 closed 不合并——本轮无真反例，有 9 处已证无害触碰，
  如实记录而非宣称"全不交"）。
- 5 合并 diff + 覆盖最末块的组合切片（header＋`[12006935..52299746]`，
  5 处改写同时生效）：**`MERGE_EQUAL`（892Q＋150003b 全等＋确定性一致）**
  （`artifacts/20261110_spillglobal/spillglobal5.{diff,json}`）。
- paid 总 delta **0**（5 窗全纯改名＋免费 `R` 一换一）。
- Q 含义（§4）：5 切口共存的片段级组合证据 = **"准全局"证据**；
  **不宣称 Q−1 达成**（覆盖度 5/8650 块；全局需 hitting-set 覆盖全部
  8650 块＋全 kmb＋验证器，均未做）。

## 1. 新切口选择（238 长块普查 → 3 块）

- 结构事实（`scan.py`→`scan.json`）：238 长块在 op `L−1` 处**全部为
  `R qV`**（238/238），即每块自带 victim 窗起点 `b=L−1`；kill 取窗后首个
  `HMR qV`。83 块具干净全窗形状（窗内零条件、恰一 victim-HMR、
  ≥1 HMR 出生借线）；194 块 victim 窗后被复用（非死后，见下）。
- victim 存活形状（`stale.py`→`stale.json`，role-aware 前向普查）：
  83 候选中 72 块 victim stale-`|0>`（窗前最后一次**值影响**操作为
  R/HMR 出生，其后仅 control/phase 读）。stale-victim 的组合性质：
  改写后 victim 恒持 `|0>`（= 原版 kill 后 `|0>`），下游演化恒一致，
  故与其它窗透明组合；这是本轮选块采用 stale 而非死后形状的理由。
- 入选 3 块（`spillglobal.py: NEW`；借线 HMR 出生、窗内零触碰、
  victim stale 独立后向复核、kill 互异、六线与 D/E 全互异）：

  | 切口 | 长块 | victim→借线 | 窗（文件） | kill | paid | 借线 gap |
  |---|---|---|---|---|---|---|
  | F | blk31（span 5034，窗覆块头 285 ops） | q848→q15 | [13831839..13832124] | b100685 | 10→10 | 411 行（HMR 出生） |
  | G | blk99（span 1365，窗覆整块 1375 ops） | q852→q879 | [16051849..16053224] | b101253 | 43→43 | 94 行（HMR 出生；与 victim 前 HMR 相邻） |
  | H | blk234（span 3224，窗覆块头 287 ops） | q861→q849 | [52088951..52089238] | b99619 | 10→10 | 1563 行（HMR 出生） |

  kill 5 方互异：`b100685/b101253/b99126(E)/b99619/b99524(D)`。
  排除例：kill=`b99126` 的候选群（与 E 同比特）、victim∈{q878,q863}、
  借线∈{q875,q845} 及与已选线共享者（`scan.json` 全表可审计）。
- 否决形状记录：G 窗尾 12-HMR 簇——首版 `hO==1` 断言误杀；
  其余 11 条是其它线的 HMR（重演归纳下两值恒等、位置不动），断言修正为
  "窗内触碰 victim/借线的 HMR 恰为 kill 一行"（脚本内注释）。

## 2. 干涉普查（5 切口两两，分析型门）

窗范围两两不交 ✓；5 窗改写零新增交叉触碰 ✓；positional gap 侵入
（窗落入对方借线 gap 且触碰借线）零 ✓；kill 5 方互异 ✓。
**对方窗零触碰不成立**：9 对有序触碰非零，逐项时戳分类（脚本内断言机
`classified`，`bad={}` 才放行合并）：

| 对 | n | 类 | 无害理由（位置证据） |
|---|---|---|---|
| Fwin→q852(Gv) | 35 | b-stale | q852 stale-`|0>`，恒透明 |
| Fwin→q845(Db) | 57 | a-出生前 | 全在 q845 出生（文件 52101869）之前，出生重置 |
| Gwin→q848(Fv) | 48 | b-stale | q848 stale-`|0>` |
| Gwin→q845(Db) | 104 | a-出生前 | 同上，全在出生前 |
| Hwin→q852(Gv) | 44 | b-stale | q852 stale-`|0>` |
| Hwin→q879(Gb) | 57 | c-kill 后 | 全在 G kill（16053224）之后，顺序复用（同 D→q875 先例） |
| Hwin→q878(Ev) | 24 | d-重生后 | E victim 重生 `R q878 @41258131`（kill 后 22 行，脚本实算），全在其后 |
| Dwin→q848(Fv) | 23 | b-stale | q848 stale-`|0>` |
| Dwin→q875(Eb) | 19 | c-kill 后 | spillunified 既有结论，逐字沿用 |

门规则：借线触碰混合时序（一部分出生前一部分 gap 内）→否决；
死后 victim 重生前触碰→否决；窗内互触（范围重叠）→否决。
本轮三者皆无，故合并。诚实声明：本轮门控严于"零触碰"字面、
宽于其精神——放行依据是逐项时戳证明＋组合切片实证，不是无视触碰。

## 3. 验证（3 块逐个＋5 合并）

协议沿用 `s7_broadcast/spillfrag/spillmulti`（header `[:54146]`＋
convert 入口 `12006935..kill`，4-shot，种子 99，输入 `0xD91`；
892Q＋全 bit＋确定性重跑；脚本 `spillglobal.py` 可复现）：

- F：892/892 qubit，101362/101362 bit（含 kill `b100685`），确定性一致
  （`spillF.json`）；victim 下游复用 `CCX q12 q20 q848`（stale 覆盖）。
- G：892/892 qubit，101362/101362 bit（含 kill `b101253`），确定性一致
  （`spillG.json`）；victim 死后＋stale 双成立（下一触碰 `R q852`）。
- H：892/892 qubit，150003/150003 bit（含 kill `b99619`），确定性一致
  （`spillH.json`）；victim 下游 `CCX q841 q853 q861`（stale 覆盖）。
- 5 合并（`spillglobal5.json`）：最小公共切片 TAIL=0（止于最末 D kill，
  ~40M 文件行 ×3 遍），892/892 qubit＋150003/150003 bit 全等
  （含 5 kill 比特），确定性一致，verdict `MERGE_EQUAL`。
- paid：F `10→10`＋G `43→43`＋E `1→1`＋H `10→10`＋D `10→10`
  （全纯改名；新增 `R qB`×5/删除 `R qV`×5 皆免费），**总 delta 0**。

## 4. 覆盖度声明与验证范围（诚实区分）

- **覆盖度**：5/8650 块有切口共存（E、G 覆整窗；D、F、H 覆块头；
  其余 8645 块未打孔）。paid 总 delta 0 是 5 窗精确账，不是全局账。
  全局 Q−1 仍需 hitting-set 覆盖全部 8650 块——**未构造，不宣称达成**；
  本轮是"准全局"证据（5 切口跨 13.8M–52.3M 文件行三区段共存且全等）。
- **功能证据**：3 块各 TAIL=0（前缀 ×3：orig/rewritten/rewritten-repeat，
  4-shot，892Q＋全 bit，输入 `0xD91`、种子 99）＋确定性重跑；
  5 合并最小公共切片 TAIL=0（同协议，40M 行 ×3）＋确定性重跑；
  干涉 9 项逐项时戳分类（实际执行，非字面零触碰，见 §2）。
- **静态精确**：借线 `|0>`（HMR 出生行文本＋出生..窗零触碰双向断言）、
  victim 窗角色集合断言、victim stale-`|0>`独立后向复核（F/G/H 各验；
  D 沿用 `stale.py` blk237；E 沿用死后＋重生位点实算 `41258131`）、
  kill-HMR 同位改道、paid 改名前后计数、HMR 流位置不动、
  G 窗尾 HMR 簇逐行归属（仅 kill 触 victim/借线）。
- **未做**：全电路候选 kmb（未构造）；官方验证器（基线字节未动）；
  下游 TAIL>0 等价性不主张（kill 比特下游 guard 如
  `CZ ... if b99126/b99524` 不在切片内）；全局 8645 块 hitting-set；
  点火条件类形状（首片段 min 块的 `AND==0` 条件窗本轮未选用）。
- **候选/提交/推送**：无。验证器未改动。凭据无。
- 环境：本工作区 `.venv`（Python 3.12，PyPI 原生 kickmix；
  macOS 未用数据包内 Linux `kickmix.so`）。

## 5. 过程文件与引用

- 脚本：`experiments/dqi/20261110_spillglobal/` 内 `scan.py`（238 长块
  victim 窗＋HMR 借线普查→`scan.json`）、`stale.py`（role-aware victim
  stale-`|0>`→`stale.json`）、`spillglobal.py`（stage1 三块 verify＋切片＋
  diff；stage2 分析型干涉门＋合并 diff＋组合切片；用法见文件头）。
- 产物：`artifacts/20261110_spillglobal/` 内 `spill{F,G,H}.{diff,json}`、
  `spillglobal5.{diff,json}`、`cuts.json`、`scan.json`、`stale.json`。
- 引用：`20261110_exactlive/{exact_live,longblocks}.json`（8650 块清单与
  238 长块表——本轮块源；`punch` 表的 0-paid 是锥上界口径，不含出生/
  角色信息，借线形状由 `scan.py` 独立重建）；`20261110_spillmulti/
  README.md`（全窗重演形状、无点火全等、D/E 借线细节与 A/B/C 否决）；
  `20261110_spillunified/README.md`（独立借线调度、组合切片协议、
  D→q875 顺序复用先例）；`20261110_spillfrag/README.md`
  （首片段部分窗＋点火条件——本轮 5 切口皆无条件形状，未选用）；
  输入只读：`artifacts/20261108_public_frontier/release/dqi.kmb`、
  `$TMPDIR/dqi_e9diff/e9.kmx`。
