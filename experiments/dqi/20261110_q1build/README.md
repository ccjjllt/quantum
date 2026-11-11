# DQI 首个全电路 Q−1 构建（`20261110_q1build`）：消除线普查 → closed，未硬构

日期：2026-11-10；分支 `codex/dqi-research`；工作区 `.worktree/dqi/`。
本轮是第一次全电路构造尝试。不重复片段级推导（见 `20261110_spillfrag`、
`20261110_spillmulti`、`20261110_spillunified`、`20261110_spillglobal`、
`20261110_spillcolor` 五份 README：D/E/F/G/H 各自全等、D+E 与 D+H 合并
MERGE_EQUAL、5 合并 CONFLICT→MERGE_EQUAL（生存分析口径）、MIS 唯一 {D,H,S}、
S 系 bit-exact 关闭）。固定输入只读：e9 包 `dqi.kmb`
（`artifacts/20261108_public_frontier/release/dqi.kmb`，
sha256 `4432ec5f…e01fece431`，`num_qubits=892/num_bits=200003`）及 kmx 缓存
（`$TMPDIR/dqi_e9diff/e9.kmx`，58,341,262 文件行）。已有方法：
`spillunified.py` / `spillmulti_sim.py` 的改写 placement 规则、
`punch.json` 全 892 行借线表、`longblocks.json` 块清单——本轮只复用，
不重推。

## 0. 结论（先行）：closed，不硬构，不跑验证器

- 首选消除线 **q845**（D 借线，HMR 出生、D 窗借用已在 {D,H} MERGE_EQUAL 中验证）：
  全电路 occ **318,499 次触碰**，其中 positional 落入 6 已验证窗的仅 **161**
  （F 窗 57＋G 窗 104，S/E/H/D 均为 0），窗外 **318,338**（99.95%）。
  且这 161 次是 F/G 窗内的第三方触碰（F diff 改 `q848→q15`、G diff 改
  `q852→q879`，均不动 q845），**被已验证 diff 实际改道的触碰数为 0**。
  D 窗本身按构造对 q845 零触碰（借线 gap），故 D 窗对消除 q845 的覆盖亦为 0。
- 换第二根线 **q849**（H 借线，HMR 出生、H 窗借用已在 {D,H} MERGE_EQUAL 中验证；
  brief 允许最多换 2 根，本轮即用满 2 根预算）：
  全电路 **198,892 次触碰**，落入 6 窗的为 **0**（H 窗按构造零触 q849），
  窗外 198,892（100%）。被已验证 diff 改道数亦为 0。
- 故两根候选的"计算+使用"均远超已验证窗覆盖：**全局 hitting-set 未闭合**。
  按 brief 第 4 条不硬构——无候选 kmb、无验证器运行（0 次，≤1 次预算未动用）、
  无提交。缺口清单见 `artifacts/20261110_q1build/gaps_q84{5,9}.txt`
 （全量窗外行号+读写类型）与 `occ_summary.json`（统计+首 60 样例）。
- 补救评估：q845 有 185×R provision＋476×HMR kill（数百 lifetimes，
  文件跨度 `[2698653..57989562]`，4 个 10M 桶全有分布）；
  q849 有 4078×R＋4196×HMR（数千 lifetimes，跨度 `[2698656..57990362]`，
  6 个 10M 桶全有分布）。覆盖任一线需数百–数千新切口＋8645 未打孔块的
  hitting-set——本轮 6 窗覆盖 161/0，连单 lifetimes 都未闭合，不展开。

## 1. 消除线选择与已验证窗（只读复用）

| 窗 | victim→借线 | 文件窗 | kill | 出生（文件） |
|---|---|---|---|---|
| S | q22→q20 | [16446733..16446738] | 无（不改 kill，+1 行形状） | 16446596 |
| F | q848→q15 | [13831839..13832124] | b100685 | 13831428 |
| G | q852→q879 | [16051849..16053224] | b101253 | 16051755 |
| E | q878→q875 | [41258103..41258109] | b99126 | 41247877 |
| H | q861→q849 | [52088951..52089238] | b99619 | 52087388 |
| D | q863→q845 | [52299461..52299746] | b99524 | 52101869 |

脚本内重断言 D/E/H 窗边界文本通过（`R q863/HMR q863 b99524` 等）。
消除线优先复用 {D,H} 已验证的两根借线：q845（首选）、q849（备选）。
理由：HMR 出生、借点 `|0>` 已双向扫描实证、D/H 窗借用已在
`spillcolor_DH.json` MERGE_EQUAL（892Q＋150003b 全等＋确定性重跑）。

## 2. occ 普查方法（程序化，`q1occ.py` 可复现）

- 全 kmx 单遍 token 精确扫描（`q845` 子串预过滤＋`if` 截断前 token 全等，
  避免 `q84` 误配），58,341,262 行一次通过。
- 读写类型（role-aware，与 exactlive transfer 一致）：
  `R`=provision-write；`HMR`=measure-read+reset；`CX`-target=write /
  control=read；`CCX`-target=write（compute）/control=read；
  `CZ/CCZ/Z`=read(phase)；`SWAP/CSWAP` 全员 write；`X`=write。
- 窗内外划分：6 窗文件坐标（含 S 保守窗）；窗内再分"positional 落入"
  与"被已验证 diff 实际改道"（后者要求该行在对应窗 diff 中被重命名——
  q845/q849 在任何已验证 diff 中均非改名对象，故恒 0）。

## 3. 读写点清单（occ 表）

### q845（首选消除线）：total 318,499

- per-op：`CX 296378 / CZ 11890 / CCX 6185 / SWAP 2345 / Z 777 / HMR 476 /
  R 185 / CSWAP 121 / CCZ 92 / X 50`。
- per-role：`write(CX-target) 123879 / read(CX-control) 172499 /
  write(CCX-target) 2335 / read(CCX-control) 3850 / read(phase) 12759 /
  write(SWAP) 2345 / write(CSWAP) 121 / write(X) 50 /
  provision-write(R) 185 / measure-read+reset(HMR) 476`。
- 窗内 positional：S 0 / F 57 / G 104 / E 0 / H 0 / D 0，合计 161；
  **被已验证 diff 改道：0**（F 窗 57 如 `CCX q20 q845 q848` 中 q845 为 control，
  F diff 只改 q848；G 窗 104 如 `CX q73 q845`，G diff 只改 q852；D 窗 0 触碰）。
- 窗外：**318,338（99.95%）**，跨度 `[2698653..57989562]`，
  10M 桶：0–10M 138016 / 10–20M 67474 / 40–50M 25287 / 50–58M 87561——
  全电路四段全有分布，非局部可包。
- provision/kill：R 185＋HMR 476（数百 lifetimes；尾例
  `57989562:HMR q845 b98360`，头例 `2698653:CX q840 q845` write）。

### q849（备选消除线）：total 198,892

- per-op：`CX 164351 / CCX 13287 / CZ 11308 / SWAP 1093 / Z 395 / HMR 4196 /
  R 4078 / CSWAP 116 / CCZ 30 / X 38`。
- per-role：`write(CX-target) 106079 / read(CX-control) 58272 /
  write(CCX-target) 4945 / read(CCX-control) 8342 / read(phase) 11733 /
  write(SWAP) 1093 / provision-write(R) 4078 / measure-read+reset(HMR) 4196`。
- 窗内 positional：6 窗全 0（含 H 窗按构造零触碰），合计 0；
  被已验证 diff 改道：0。
- 窗外：**198,892（100%）**，跨度 `[2698656..57990362]`，
  10M 桶：0–10M 113628 / 10–20M 7786 / 20–30M 8645 / 30–40M 8645 /
  40–50M 6125 / 50–58M 54063——六段全有分布。
- provision/kill：R 4078＋HMR 4196（数千 lifetimes）。

全量窗外缺口（行号+读写类型+原文前 90 列）：
`artifacts/20261110_q1build/gaps_q845.txt`（318,338 行＋1 头）、
`gaps_q849.txt`（198,892 行＋1 头）；统计＋首 60 样例见
`occ_summary.json`。样例头尾：
q845 头 `2698653:CX:write(CX-target):CX q840 q845`、
尾 `57989562:HMR:measure-read+reset(HMR):HMR q845 b98360`；
q849 头 `2698656:CX:write(CX-target):CX q840 q849`、
尾 `57990362:HMR:measure-read+reset(HMR):HMR q849 b98360`。

## 4. 覆盖缺口与补救评估（closed 的精确位置）

- 缺口规模：q845 需补 318,338 触碰（含 2335 CCX-target compute 写、
  123879 CX-target 写、172499 CX-control 读、12759 phase 读、185 R、476 HMR）；
  q849 需补 198,892 触碰（含 4945 CCX-target、106079 CX-target、
  4078 R、4196 HMR）。两线 2 根预算内均未闭合。
- 补救选项：(a) 新增切口覆盖缺口 lifetimes——q845 数百、q849 数千 lifetimes，
  且 8650 块中仅 6 块有切口（D/E 覆块头或全窗、F/H 覆块头、G 覆整块、
  S 覆 min 块），8644 块无切口，hitting-set 缺口在"几乎所有 max 块"，
  非某几行可补；(b) 换消除线——已用满 2 根（q845→q849），victim 线
  （q863 total 163870/D 窗仅覆 41；q861 total 241773/H 窗仅覆 41，
  一次性探针见 §5 注）同样量级，不再烧预算。
- 精确未闭合位置：**全电路除 6 窗外的所有 q845/q849 触碰行**
  （`gaps_*.txt` 全枚举），最早缺口在文件 ~2.7M 行（远早于首窗 F 13.8M），
  最晚缺口在 ~58M 行尾（晚于最末 D 窗 52.3M），且中间 10M 桶全覆盖——
  即"全局 hitting-set 未闭合"不是某段缺失，是除 6 个窄窗外全线缺失。

## 5. 验证范围声明（诚实区分）

- **本轮实际执行**：全 kmx occ 单遍普查（58M 行，token 精确＋role 分类＋
  6 窗划分＋R/HMR 计数＋桶分布；脚本 `q1occ.py` 可复现，输出
  `occ_summary.json`＋两份全量 gaps 文件）；窗边界文本重断言通过。
- **静态精确**：借线出生/窗坐标沿用 spillcolor 记录并重断言 D/E/H 窗边界；
  paid/placement 规则未动（无改写可验 paid）。
- **未做**：候选 kmb（未构造——缺口未闭合，按 brief 不硬构）；
  静态 Q=891/paid-delta/操作数核验（无对象可核）；
  官方 DQI 验证器（**0 次运行**，brief 预算"候选存在时最多一次"未动用；
  参考成功先例仅为主仓库 `artifacts/20261110_trio_candidate/verify_dqi.log`
  的 PASS 格式，未借用其字节）；
  切片仿真（无改写对象，不虚构 MERGE_* verdict）；
  下游 guard/尾部 DCE（超出本轮范围）。
- **候选/提交/推送**：无。验证器未改动。凭据无。
- 环境：本工作区 `.venv`（Python 3.12，PyPI 原生 kickmix；
  macOS 未用数据包内 Linux `kickmix.so`）。

## 6. 过程文件与引用

- 脚本：`experiments/dqi/20261110_q1build/q1occ.py`（本轮唯一脚本，为 occ 普查＋
  缺口枚举脚本；**kmx 文本变换（改写）脚本未生成——按 brief 第 4 条，
  缺口未闭合时不硬构**；
  窗坐标源自 `spillcolor/colorgraph.json`＋`spillglobal/cuts.json`；
  role 分类源自 `20261110_exactlive/README.md` §方法 transfer）。
- 产物：`artifacts/20261110_q1build/` 内 `occ_summary.json`、
  `gaps_q845.txt`、`gaps_q849.txt`。
- 引用：`20261110_spillfrag/README.md`（借线 `|0>`＋HMR 流钉住否决）；
  `20261110_spillmulti/README.md`（全窗重演无条件形状、D/E 借线出生与 gap、
  A/B/C 无借线否决）；`20261110_spillunified/README.md`
  （独立借线调度、组合切片协议）；`20261110_spillglobal/README.md`
  （5 切口＋生存分析口径 MERGE_EQUAL）；`20261110_spillcolor/README.md`
  （严格干扰图＋MIS 唯一 {D,H,S}＋{D,H} MERGE_EQUAL＋S 的 +1 行长度敏感诊断——
  本轮消除线即取自该 {D,H} 对的两根借线）；
  `20261110_exactlive/{exact_live,longblocks,punch}.json`（8650/238 块清单与
  M_exact=892 背景）；输入只读 `artifacts/20261108_public_frontier/release/dqi.kmb`
 、`$TMPDIR/dqi_e9diff/e9.kmx`。
- 注：q863/q861 total（163870/241773，窗内各 41）为一次性探针值，
  非本轮交付 occ 对象；备选预算已用于 q849，不再立项。
