# 解码器族判决性实验（`20261111_decoder2`）：pebbling 交换表＋换族量级＋889Q 归属

日期：2026-11-11；分支 `codex/dqi-research`；工作区 `.worktree/dqi/`。
性质：**纯静态只读**——只读 frontier kmx（`4432ec5f`）与 `/tmp` 残留 889q kmx
（`993c7038`，kmb 已删，kmx 残留可读），不构建候选、不运行官方验证器、
不改动 `data/competition` 验证器、不提交不推送。
输入锚点：`experiments/dqi/20261110_e9diff/`（stage_census.json 实测）、
`20261110_arch_review`（定价：−1 门 947,843 分、887 门/Q）、
`20261110_r1salt/README.md` §B（889Q 画像实测）、`ABANDONED.md`（已关闭方向）。

## 1. C 方向判决性实验：extract→scan→unextract 存活值交换表（实测）

方法（本目录无新框架，两个一次脚本在 `/tmp`，可重跑）：
`boundary_live.py`（流式单遍，按顶层 `INFO_TAG` 栈顶统计每 qubit 触及阶段集合）、
`bypass_list.py`（同口径列出 scan 未触及 qubit）。
阶段顺序（kmx 实测）：`mask_projection/initial/extract/synthesis/convert/scan/unconvert/unsynthesis/unextract/uninitial`。
qubit 触碰口径：行内任一 `q<int>` token 即计入触碰（含读含写，过近似——只会**高估**
跨越值数量，对"不值得"的结论是保守方向）。

### 1.1 实测数字（frontier `dqi.kmx`，58,269,328 ops）

| 量 | 实测值 | 来源 |
|---|---|---|
| 各阶段 distinct qubit | extract 892 / synthesis 892 / convert 891 / scan 851 / unconvert 891 / unsynthesis 892 / unextract 892 | 本轮实测（与 e9 `residual_e9.json` 口径一致） |
| extract∩unextract（必须跨过中间 5 阶段的值） | **892（全部）** | 本轮实测 |
| 其中 scan 内也被触碰（主动持有或重算二选一） | **851** | 本轮实测 |
| 其中 scan 未触碰（免费携带，无 pebbling 决策） | **41**（`q12–q23` 共 12 ＋高区 ancilla 29：`q840,q844,q845,q846,q848,q850–858,q861–864,q876,q877,q879,q882–884,q886–889,q891`） | 本轮实测 |
| extract∩scan / scan∩unextract | 851 / 851 | 本轮实测 |
| cross 值在 synthesis/unsynthesis 被触碰 | 892/892（全部）；convert/unconvert 各 891/892 | 本轮实测 |
| extract→unextract 中间隔 ops（synthesis+convert+scan+unconvert+unsynthesis） | 5,415,382+5,691,373+23,537,838+5,244,671+5,698,618 ≈ **45.5M ops**（其中 scan 23.5M） | `stage_census.json` ops 相加 |

### 1.2 重算/存储交换表（定价沿用 arch_review §2：887 门/Q，947,843 分/门）

重算侧锚点（已记录实测，非估计）：
- unextract 总计 96,888 paid，其中 depth-1 主体 **94,193 CCX**（`decoder_struct` §1 实测）。
- 单值重算上界：平均 94,193/851 ≈ **110.7 门/值**；单块上界 multiply-v **99 CCX/块**、
  inverse24 均 **~56.7 CCX/块**（3,910/69）；历史最高扇出单值 234 复用
  （`(120,859):234`，`decoder_struct` §4 实测，即使整组全擦也只有 234 门）。
- 即：**任何单个跨越值的重算代价上限约 100–234 门**，远 below 887 线。

存储侧（已记录实测，非估计）：
- 全电路 892 线全部被触碰（`exactlive` M_exact=892 真值，ABANDONED 已收录；
  本轮 extract/unextract 均为 892 distinct 佐证），干净闲置线恒为 0
  （deepfix 全跨度 0/1618）。
- 因此持有任一 851 值中跨越 scan 的活跃值，需 **+1Q（+8.41 亿分 = 887 门）**，
  无免费载体可用；41 bypass 值已免费携带，不在决策集内。

交换表（每行都是"花 1Q 存 1 值 vs 重算该值"的独立判决）：

| 候选 | 存代价 | 重算代价（实测上界） | 净账 | 判决 |
|---|---|---|---|---|
| 851 穿 scan 值中任意 1 个 | +1Q ≈ +8.41亿（887 门） | ≤ ~234 门（最高扇出组全擦；典型 ~57–110 门） | ≥ +653 门 ≈ **+6.2亿，净负** | 关闭 |
| 6 个 multiply-v 输出全存（594 门，最大单类） | 串行复用 ≥1Q（跨度重叠，并行需多 Q） | 594 门 | +887−594=+293 门 ≈ +2.8亿，净负 | 关闭 |
| 69 个 inverse24 输出全存（3,910 门） | ≥1Q（串行）至多 Q（并行）；串行仍需逐值重排 | 3,910 门总量但单值 ≤57 门 | 单值判决同首行；总量需 ≥5Q 才并行持有，5×887=4,435>3,910，净负 | 关闭 |
| 幻想情形"1 值擦除整个 unextract" | +1Q（887 门） | 96,888 门（不可能，unextract 含 synthesis 逆等多源） | 名义为正，但无此单值（反证：broadcast 最大组仅 234） | 不存在，关闭 |

### 1.3 结论（方向 C）

**pebbling 重构不值得投入综合器重写——独立 closed**，与 ABANDONED
`qpebble` 双 closed 一致（本轮是更便宜的边界计数复核，不依赖其内部方法）。
理由链（全实测）：跨越值 892→决策集 851→单值重算上限 234 < 887→
存储无免费载体（M_exact=892）→任何单值持有净负至少 ~650 门。
综合器重写（整段 unextract 重综合）的前提"存在 >887 门的单值可擦除"是**空集**；
即使把 unextract 全部 96,888 门计入，也需要先找到一个扇出 ≥887 的单值，
而实测最大扇出组是 234（差 3.8×）。

## 2. B 方向可行性：BM/Euclid/时域 Chien 纸面量级（静态只读，不开代码）

锚点（实测）：extract **59,169 paid**（58,977 CCX+192 CSWAP）；
extract 内场算术占比小：69 inverse24（3,910 CCX）＋6 multiply-v（594 CCX，
每块恰 99）＋75 inverse12，合计 ~4.5k；其余 ~54k 是 depth-1 二进制 AND 网络。
问题参数（验证器只读）：m=4095（码长，`DEFAULT_M`），parity n=70，
degree=12（GF(2^12)），纠错能力 t=35（`arch_review` §1 l=35）。

量级论证（估计，但用**下界**写法——任何优化只能比下界更差，不能更好）：

- Chien 搜索下界：次数 35 的错误定位多项式要在 4095 个位置求值。
  Horner 逐点求值每点 ≥35 次乘 → **≥143,325 次 GF(2^12) 乘**（4095×35）。
  多点求值渐近 O(n log²n) 在此规模下常数更大（≈4095×144），不救。
- Syndrome 下界：70 个伴随式 × 4095 位置，朴素 **286,650 次乘**；即使 NTT
  O(n log n)≈49k 蝶形，每蝶形 ≥1 乘，仍 **≥49k 次乘**。
- 单乘下界：GF(2^12) 一次乘至少 1 个 AND（1 CCX），实测 frontier 优化后是
  **99 CCX/乘**（multiply-v）。取幻想下界 1 CCX/乘（不可能达到，只为关门用）。
- 合计下界：Chien 143k×1 ＋ syndrome 49k×1 ＋ BM/Euclid/Forney（≥1k）≈
  **≥190k paid**，而 extract 总量才 59,169。
  即：**即使每个 GF 乘只花 1 门（低于任何物理实现），BM/Euclid/时域族也已是
  extract 的 ~3.2×；按实测 99 门/乘则是 ~300×。**

verdict：**差距 ≫5%，直接关闭，不开代码。**
当前族（n=4095=2¹²−1 的频域/NTT 友好参数＋二进制 AND 网络）已是渐近正确族；
BM/Euclid/时域 Chien 是 O(n·t) 大常数族，方向反了。
本结论是纸面量级＋下界论证，未实现任一族，未跑验证器。

## 3. 889Q 族（`993c7038`，实 891Q，+1,550 门）归属判定

实测（本轮复核 `/tmp/dqi_889q_993c7038.kmx`，grep/流式计数；成绩引用
`20261110_r1salt` §B.1 kernel 自带 summary，未重跑）：

| 项 | frontier（4432ec5f） | 889q（993c7038） | 说明 |
|---|---|---|---|
| Q / 总 paid / ops | 892 / 395,641 / 58,269,328 | **891 / 397,191（+1,550）** / 58,318,189 | 标题"889"与实测 891 不符（沿用 r1salt 结论） |
| extract inverse24（norm/products/scalar） | 23×3=**69** | 29×3=**87** | 同原语，多 18 块 |
| extract inverse12 | 25×3=75 | 31×3=93 | 同原语，多 18 块 |
| extract multiply v | **6** | **12** | 同原语，多 6 块（+426 paid 主因） |
| scan gf_iadd | 8050 | 8050 | 骨架相同 |
| scan PUSH 守卫 | **4025** | **0** | 889q 无掩码守卫（mean-T 几乎足额） |
| unextract gf_iadd | 140 | 186 | 同原语，多 46 块（+736 paid 主因） |
| unextract PUSH | 50 | 40 | 889q 少 10 区 |
| 窄返回（unextract 无 inverse24/multiply 逆块） | 成立（0） | 成立（0） | 两侧相同，不是差异点 |
| unread_ccx_before_hmr | 0 | **13**（引用 r1salt §B.1） | 889q 有 Kirill 残余，frontier 已清零 |
| 官方成绩（引用） | 374,735,446,628.53 | 375,373,377,713.41（+6.38亿，+0.17%） | Q−1 省 ~8.4亿抵不过 T +14.7亿 |

归属判定：**889q 是同一频域解码器族的弱优化版本，不是独立族。**
证据：块词汇表完全相同（inverse12/24、multiply-v、gf_iadd、PUSH 守卫、
窄返回），scan 骨架逐项相同（8050 gf_iadd），差异只是**同族加料**
（extract 多 18+18+6 块、unextract 多 46 块）＋**缺失已知的同族优化**
（scan 4025 守卫为 0、13 处 Kirill 残余未清）。
按任务判据（"若 extract 29 inverse24+12 multiply 本质是频域同族加料，
换族方向保留"）：**换族方向不由 889q 证伪，保留为开放；但 889q 本身不提供
任何换族正证据**——它只证明"同族写差一点会多花 1,550 门"，不证明"异族能省"。
真正的异族（streamed decoder 生成器路线）本地无源码（`kernels pull` 404，
见 r1salt §B），未测量，不得 claim。
在拿到真异族候选之前，换族方向**保留但冻结**（不投入综合器/BM 实现）。

## 4. 总 verdict 与后续

1. 方向 C（pebbling/综合器重写）：**关闭**（§1 交换表：单值上限 234 < 887，
   无免费载体，任何持有净负 ≥650 门）。
2. 方向 B（BM/Euclid/时域 Chien）：**关闭**（§2 下界 ≥190k vs 59k，
   幻想单价下已 3.2×；不开代码）。
3. 889Q（993c7038）：**同族弱实现**；换族方向保留但冻结，无正证据前不投入。
4. 方向 D（−Q 串行化）与方向 A（−55 已吃透，残余 0）维持 ABANDONED 现状：
   本轮未重做 Q 高水位（e9 画像峰值 892 由四阶段共顶，`e9diff` §4 实测），
   不改变其 closed 状态。

## 5. 验证范围声明

- 本实验**未构建候选、未运行官方验证器**（DQI 102400-shot/单 salt 全未触发；
  `data/competition` 验证器未改动、未调用、未复制）。
- 实测数字来源：本机 `/tmp/dqi_e9diff/dqi.kmx`（frontier，SHA
  `4432ec5f…ce431`）流式计数（§1.1/§3 表）、`artifacts/20261110_e9diff/`
 （stage_census.json、residual_e9.json）、`20261110_r1salt/README.md` §B
  （889q 成绩与 13 处 unread 引用值）、`decoder_struct` 快照（multiply 99、
  inverse24 3,910、depth-1 94,193、扇出 234，见 git `7b52b8e`）。
- 估计部分（§2 量级下界）明确标为纸面论证，非实测；未实现 BM/Euclid/Chien。
- 889q kmx 为 `/tmp` 残留（kmb 已按 ABANDONED 删除），仅只读 grep/计数，
  未复制进仓库；仓库内本目录仅本 README，无大文件、无脚本（脚本为 `/tmp`
  一次性，复现命令见 §1 方法段）。
- 环境：本工作区 `.venv`（Python 3.12，PyPI 原生 kickmix 未调用；
  本轮仅文本 grep/流式计数）；凭据/token 未触碰。
