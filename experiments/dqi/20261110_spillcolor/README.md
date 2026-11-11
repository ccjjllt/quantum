# DQI 干扰图着色（`20261110_spillcolor`）：严格图＋MIS＋{D,H} 组合验证

日期：2026-11-10；分支 `codex/dqi-research`；工作区 `.worktree/dqi/`。
本轮是第一次解冲突。不重复首片段/规模化/统一调度/全局推进的推导
（见 `20261110_spillfrag`、`20261110_spillmulti`、`20261110_spillunified`、
`20261110_spillglobal` 四份 README）。
固定输入只读——e9 包 `dqi.kmb`
（`artifacts/20261108_public_frontier/release/dqi.kmb`）及 kmx 缓存
（`$TMPDIR/dqi_e9diff/e9.kmx`，58,341,262 文件行）。

## 0. 结论（先行）

- 严格干扰图（6 节点 S/D/E/F/G/H，边＝任一方向窗触借线/受害线，或
  gap 侵入/改写引入交叉/kill 碰撞；窗两两不交、改写零新增交叉、
  gap 零侵入、kill 互异皆已断言）：8 条边，**最大独立集唯一，
  大小 3＝{D,H,S}**（`colorgraph.json`，6 节点暴力枚举）。
- brief 指引的 {D,E,S}（已证 D+E＋两个严格干净边 D-S/E-S；D-E 严格有边，
  但 spillunified 已证 MERGE_EQUAL，属 grandfathered）：合并 diff 已产出，
  组合切片（止于最末 D kill，4-shot，种子 99，输入 `0xD91`）
  **qubit 892/892 全等＋确定性重跑一致，但 1554/150003 bit 不等，
  verdict `MERGE_MISMATCH`**（`spillcolor_DES.{diff,json}`）。
  诊断（§3）：不等全来自 S 切口的 +1 行形状（restore-`R` 插入）扰动
  下游 HMR 结局位——S-only 长尾对照与 DES 的 mismatch 集合**逐位相同**
  （双向差集皆 0），D/E 改写贡献 0；qubit 全程全等，`AND==0` 实测成立。
  即：不是语义反例，是本仿真器 HMR 结局位对长度变化的已知全局敏感性
  （首片段 §4 的 O0-vs-O8 对照先例）。S 参与的任何子集都过不了
  bit-exact 门——{D,E,S} 与严格-MIS {D,H,S} 在此口径下同 closed
 （后者不再烧一次 40M 切片，理由见 §3；顺序-spill 方向见 §5）。
- **首个严格干净＋等长＋覆盖最末块的组合切片：{D,H} `MERGE_EQUAL`**
  （`spillcolor_DH.{diff,json}`）：892/892 qubit＋150003/150003 bit 全等＋
  确定性重跑一致；paid `10→10`＋`10→10`，总 delta 0。
- paid：所有合并皆纯改名＋免费 `R` 一换一；未构建全电路 kmb，
  未跑官方验证器，无提交。

## 1. 干扰图（严格边）

节点窗（文件坐标；S 取保守窗 `[16446733..16446738]` 含未改写尾行，
合并改写仅动其中前 4 行）：

| 节点 | victim→借线 | 窗 | kill | 借线出生（文件）/gap |
|---|---|---|---|---|
| S（首片段） | q22→q20 | [16446733..16446738] | 无（不改 kill） | 16446596 / 137 |
| F | q848→q15 | [13831839..13832124] | b100685 | 13831428 / 411 |
| G | q852→q879 | [16051849..16053224] | b101253 | 16051755 / 94 |
| E | q878→q875 | [41258103..41258109] | b99126 | 41247877 / 10226 |
| H | q861→q849 | [52088951..52089238] | b99619 | 52087388 / 1563 |
| D | q863→q845 | [52299461..52299746] | b99524 | 52101869 / 197592 |

借线出生皆后向扫描实测（`HMR qB b*` 行＋出生..窗零触碰双向断言），
D/E/F/G/H 出生与既有轮次记录逐字一致（脚本内 `RECORDED_BIRTH` 断言）。

邻接表（`colorgraph.json`；非零窗触碰全表见该文件
`window_touches_nonzero`；改写引入交叉全零、gap 侵入零、kill 互异）：

| 边 | 原因（方向＋次数） |
|---|---|
| F-S | Fwin 触 q20(Sb)×45 |
| F-G | Fwin 触 q852(Gv)×35；Gwin 触 q848(Fv)×48 |
| G-S | Gwin 触 q22(Sv)×298、q20(Sb)×42 |
| G-H | Hwin 触 q852(Gv)×44、q879(Gb)×57 |
| E-H | Hwin 触 q878(Ev)×24 |
| D-F | Dwin 触 q848(Fv)×23；Fwin 触 q845(Db)×57 |
| D-G | Gwin 触 q845(Db)×104 |
| D-E | Dwin 触 q875(Eb)×19（spillunified 顺序复用先例，见下） |

干净对（无边）：S-D、S-E、S-H、D-H、E-F、E-G、F-H。
暴力枚举（2^6）：**MIS 大小 3，唯一 {D,H,S}**。

与同期 `20261110_spillglobal` 生存分析型门的关系：对方把上表触碰
逐项时戳分类（a 出生前／b stale-victim 透明／c kill 后顺序复用／
d 重生后）后放行 5 合并并跑出 `MERGE_EQUAL`（见该轮 README §2）。
本轮是保守口径：任何非零触碰即成边。两轮结论不矛盾——
{D,H} 在两种口径下皆干净（本轮切片独立实证）；D-E 边在严格口径下
存在，但已有 spillunified 的组合切片实证 grandfathered。

## 2. {D,E,S}：合并 diff＋组合切片（MISMATCH，诊断 closed）

选择理由：brief 指引"从已证 D+E 起步，加不冲突者"——S 与 D、E 皆
严格干净（S-D、S-E 无边），凑出 size-3 {D,E,S}（D-E 用既有
`MERGE_EQUAL` 豁免）。

- 合并 diff：`artifacts/20261110_spillcolor/spillcolor_DES.diff`——
  S 段 4 行→5 行（`spillfrag.diff` 逐字），E/D 段 1:1 改名；
  paid S `1→1`、E `1→1`、D `10→10`，总 delta 0。
- 组合切片：header `[:54146]`＋`[12006935..52299746]`（覆盖最末 D kill），
  4-shot，仿真种子 99，输入种子 `0xD91`；892Q＋全 bit＋确定性重跑。
- 结果（`spillcolor_DES.json`）：**qubits_equal=true（892/892），
  qubits_deterministic=true，bit_mismatches 共 1554/150003，
  verdict `MERGE_MISMATCH`**。
- 实施勘误（诚实记录）：首版脚本先 splice S（+1 行）后按原坐标写
  E/D 改名，导致 E/D 改写错位一行，首跑出 qubit 不等＋kill 位错；
  已修正为"D/E 改名先行、S splice 最后"，并重跑为全量 bit 列表。
  该 bug 仅污染首跑输出（未归档为证据），终版产物为修正后重跑。

## 3. 诊断：S 的 +1 行形状 vs 仿真器 HMR 全局敏感性

- S-only 长尾对照（S 改写单独作用，tail=E_K）：qubit 892/892 全等，
  32 bit 不等——全部映射到 S 插入点下游的 HMR 行
 （含 E kill `b99126` 与 `b101242+` 簇；后者正是首片段 TAIL=8000
  已记录的仿真器敏感簇），无未映射位（`diag_S.json` §A/C）。
- `AND==0` 实测：S 窗值切片（tail=S_K）读得 q18 全 0
  （q143 有 1，但合取恒 0），q22/q20 全 0——测试种子下 S 改写是
  严格 no-op（`diag_S.json` §B）。
- 决定性对照（§D）：S-only tail=D_K 的 mismatch 集合与 DES 的
  **逐位相同**（双向差集皆 0，同为 1554 位），qubit 皆全等。
  故 D/E 1:1 改名贡献 0 翻转；全部 1554 翻转来自 S 的 +1 行插入，
  且 qubit 轨迹恒等——与"语义分叉"不相容，与首片段 §4 已确立的
  "HMR 结局位对电路长度/尾长全局敏感"（O0-vs-O8 同版本对照 24 位
  翻转先例）相容。
- 推论：**任何含 S 的子集（含严格-MIS {D,H,S}）都过不了本仿真器的
  bit-exact 组合门**——不是切口语义错，是等长门槛（length-preserving）
  问题。{D,H,S} 不再重复烧 40M 切片（预期同构的 1554 位翻转），
  如实记为"诊断 closed（bit-exact 口径）"，不虚构验证。
  若后轮采用 HMR-结局不敏感的比较口径（如仅比 qubit＋非 HMR 位，
  或 HMR 位单独归因），{D,H,S}/{D,E,S} 可重跑——本轮不做。

## 4. {D,H}：合并 diff＋组合切片（MERGE_EQUAL，本轮交付）

- 选择理由：严格干净（§1 无边对）、双切口皆等长 1:1 全窗重演
  （免疫 §3 的长度敏感）、覆盖最末块 D、此前从未组合验证过。
  E 因 E-H 边被排除（两种口径下皆不干净：严格有边；生存分析口径
  为 d-重生后类——本轮保守口径不取）。
- 合并 diff：`artifacts/20261110_spillcolor/spillcolor_DH.diff`——
  H 段 `[52088951..52089238] q861→q849`、D 段
  `[52299461..52299746] q863→q845`，行号原文件坐标；
  脚本内重断言两窗互零触碰通过。
- 组合切片（同协议，tail=D_K，约 40M 文件行 ×3 遍）：
  **qubits_equal=true（892/892），bit_mismatches=[]（150003/150003，
  含两 kill 比特 `b99619/b99524`），qubits_deterministic=true，
  verdict `MERGE_EQUAL`**（`spillcolor_DH.json`）。
- paid：H `10→10`＋D `10→10`，总 delta 0；HMR 流位置不动
  （仅 kill 行 qubit 操作数交换）。

## 5. 验证范围声明（诚实区分）

- **组合级功能证据**：{D,H} 最小公共切片 TAIL=0（约 40M 文件行前缀 ×3：
  orig/rewritten/rewritten-repeat，4-shot，892Q＋150003b 全等，
  输入 `0xD91`、仿真种子 99）＋确定性重跑；{D,E,S} 同协议跑出
  qubit 全等＋1554 HMR 位翻转（诊断 closed，非语义反例）。
- **静态精确**：6 切口借线 `|0>`（出生行文本＋出生..窗零触碰双向断言，
  D/E/F/G/H 出生与既有轮次交叉核对一致）、窗角色/paid 改名前后计数、
  kill 互异、窗两两不交、改写零新增交叉（6 切口全重算，非沿用断言）、
  gap 零侵入；MIS 为 2^6 暴力枚举确证唯一。
- **未做**：全电路候选 kmb（未构造）；官方验证器（基线字节未动）；
  下游 TAIL>0 等价性不主张（kill 比特下游 guard 不在切片内）；
  全局 8650 块 hitting-set（本轮只解决 6 节点着色＋验证 1 个新对）；
  {D,H,S} 的 bit-exact 切片（§3 诊断 closed，预期同构翻转，不烧算力）；
  HMR-结局不敏感口径的重跑（方法变更，留后轮）。
- **候选/提交/推送**：无。验证器未改动。凭据无。
- 环境：本工作区 `.venv`（Python 3.12，PyPI 原生 kickmix；
  macOS 未用数据包内 Linux `kickmix.so`）。

## 6. 过程文件与引用

- 脚本：`experiments/dqi/20261110_spillcolor/` 内 `color.py`
  （严格普查＋MIS；输出 `colorgraph.json`）、`merge_slice_DES.py`
  （{D,E,S} 合并 diff＋组合切片；输出 `spillcolor_DES.{diff,json}`）、
  `diag_S.py`（S-only 对照＋AND 检查＋bit→HMR 归因＋§D 决定性对照；
  输出 `diag_S.json`）、`merge_slice_DH.py`（{D,H} 合并 diff＋组合
  切片；输出 `spillcolor_DH.{diff,json}`）。切片协议源自
  `20261109_dqi_decoder_struct/README.md` §5 的 `s7_broadcast` 经
  `spillfrag/spillmulti/spillunified` 传递。
- 产物：`artifacts/20261110_spillcolor/` 内 `colorgraph.json`、
  `diag_S.json`、`spillcolor_DES.{diff,json}`、`spillcolor_DH.{diff,json}`。
- 引用：`20261110_spillfrag/README.md`（S 形状、点火条件、HMR 全局
  敏感性 O0-vs-O8 对照——本轮 §3 的机制来源）；`20261110_spillmulti`
  与 `20261110_spillglobal/cuts.json`（D/E/F/G/H 窗/借线/kill 行号表——
  本轮只读复用，出生独立重扫复核）；`20261110_spillunified/README.md`
  （D+E `MERGE_EQUAL`、D→q875 顺序复用先例——本轮 D-E 豁免依据；
  合并 diff 格式与切片协议模板）；`20261110_spillglobal/README.md`
  （同期生存分析型门＋5 合并 `MERGE_EQUAL`——与本轮严格口径的对照，
  结论相容处见 §1）；输入只读：`artifacts/20261108_public_frontier/
  release/dqi.kmb`、`$TMPDIR/dqi_e9diff/e9.kmx`。
