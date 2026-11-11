# Q 高水位串行化 + 跨阶段 pebbling（`20261110_qpebble`）：双 closed，附判决性数字

日期：2026-11-10；分支 `codex/dqi-research`；工作区 `.worktree/dqi/`。
固定输入（只读）：主仓库 `artifacts/20261110_public_candidates/ozer_v91/submission.zip`
内 `dqi.kmb`（SHA-256 `e9f54be3…`，已核 `/tmp` 解包 `e9.kmb` 同哈希，见下）；
`e9.kmx` 为既有 `/tmp/dqi_e9diff/e9.kmx`（58,269,417 ops，流式读，不驻留）。
不重复六项 closed 与 e9 差分（残余 0、Q 892 无冗余、84 对净负）——本轮是
`20261110_arch_review` 方向 C/D 的判决性实验：Q 高水位熔接报价 + 跨阶段
pebbling 交换表。未构建候选、未跑验证器。

计分口径（`arch_review` §0）：`score=R·Q²·T`，`R=1.19126046`，`Q²=795,664`；
静态 −1 门 ≈ 947,843 分；Q −1 ≈ −8.41 亿分（≈887 门，`1783·T/Q²=886.6`）；
break-even：省 1 Q 需新增 paid < 887 门。

## 0. 结论（先行，双 closed）

1. **Q−1 熔接：closed。** 真活区间 `[首写,末读]`（上界，sound 方向）max 重叠
   `M=892`，且是**单个 55.3M-op 团块** `[2858014,57907640]`（全电路 58.3M 的 95%），
   892 线全员穿越。整线消除不可能（最短跨度线仍 55.1M ops > 最长死区 23.6M）；
   打孔（峰内逐读重算）下界：读数最少的线 `q23` 团内 22,438 读 ⟹
   `≥44,876 paid` vs 预算 887——**超 50 倍**，无正收益设计。
2. **跨阶段 pebbling（持有代替重算）：closed。** 三级漏斗（`q_gate.json`）：
   58,658 对窗（毛上界 58,658 门）→ 宿主覆盖 25,958（|0>-确定死区全覆盖
   `[p0,ext]`，短窗 <1M 占绝大多数；top-30 长窗 3.7–5.2M 宿主 0/30）
   → 控制值等价扫后幸存 **0**（25,580 死于 a/b 窗内重写 = 线复用假重复，
   378 死于 t 中间写）。1% 标尺 968 门可行 0/968。毛上界 60× 是假重复堆出的
   海市蜃楼（与 dirtyk2 §5 CCZ 196 组假重复同构，本轮在 CCX 上复现并量化到 98.5%）。

## 1. Q 高水位：从整线熔接到打孔定价

### 1.1 整线消除不可能（`q_live.py`）

读写分类（保守：未知含 q op 按读，只漏记不误记；`unknown_ops={}` 全集已覆盖）：
写 `X/CX-t/CCX-t/CSWAP(全)/SWAP(全)/R`，杀 `HMR/R`（开死区），其余读（作废死区）。
死区 = 零触碰 `(kill → 下次写)`，133,857 个（sound 熔接窗）。

- 892 线首末触碰跨度：**最短 `q889` 55,053,564 ops**（全电路 58,269,417 的 94.5%）；
  最长死区 `q846` 23,590,595 ops（HMR→CX，scan→unconvert）。55.1M > 23.6M，
  无整线可装入他线死区 ⟹ 整线消除 0 机会。
- 语义基础：HMR 清空 ancilla（research-map §DQI 行，主办方讨论 752344#3545879；
  电路自身亦 recycling 作证：scan  ancilla 如 `q885` 携 4084 R / 4233 HMR，
  即每 rung `R+CCX+HMR` 循环复用）。R/HMR-start 死区宿主必为 `|0>`
  （不依赖 R-force 假设：HMR-start 由组织方背书，head-start 由初态保证）；
  纯重命名不改变 op 多重集/顺序，确定性模拟器下与原电路 bit-exact（至多重标记），
  无 RNG 流风险。任何增删 op 的设计须重估 HMR 结局位移
 （`decoder_struct` s7 tail-8k 同类伪影先例）——本轮无此类设计。

### 1.2 判决性覆盖：M=892 单团块（`q_cover.py`）

真活区间 `[首写,末读]`（无读线视为空；892/892 非空——无免费消除线）：
max 重叠 **M=892 @2858014**，团区间**唯一** `[2858014,57907640]`。
即：从 extract 头部到 uninitial，892 值同时存活——寄存器重着色需 892 色，
891 不可行（充分条件 sound：上界重叠 892 ⟹ 真重叠 892 ⟹ 着色下界 892）。

### 1.3 打孔定价：下界超预算 50 倍（`q_reads.py`）

团块内读数最少 `q23`（22,438 读；前十见 `q_reads.json`，22k–29k）。
打孔须在团块每处读点前后反算/重算（producer ≥1 paid/端）⟹
`T_add ≥ 2×22,438 = 44,876 paid` vs 预算 887（50.6×）。
净账：`−8.41亿 + 44,876×947,843 ≈ +417亿`（+11%），反向 500 倍。
其余 891 线读数更多 ⟹ 全员不可行。**Q−1 无净正设计，closed。**

片段证据：无（任一方向净正时才构造；本轮双向皆负，见任务约束）。

## 2. 跨阶段 pebbling：unextract 重算窗交换表（`pebble.py` + `q_gate.py`）

unextract：5,794,499 ops，94,295 无条件 CCX，同字面组 15,212（≥2 次），
连续对窗 58,658，毛上界 58,658 门。跨度分布（M ops 桶）：<1M 占 58,479；
≥1M 仅 179；top-30 窗 3.7–5.2M 宿主覆盖 0/30（`q_fuse.py` 门控）。

宿主覆盖（阶段 1）：死区全量 `gaps.jsonl`（133,857），宿主须 |0>-确定
（HMR-start 或 s==0）且覆盖 `[p0,ext]`（ext=p1 后 t 下次写；无后继写则须 TAIL）：
覆盖 26,053 窗（全短窗）。

价值等价（阶段 2，`q_gate.py` v2，活跃窗单遍扫）：窗内 `(p0,p1)` 若 a/b 被写/杀
或 t 被中间写 ⟹ 假重复（线复用），剔除。结果（`q_gate.json`）：

- 宿主覆盖：25,958（阶段 1 修正版：t 无后继写时须 TAIL 宿主；旧 26,053 含 95 个
  尾部作用域不足窗，已剔除）→ 价值幸存：**0**。
  其中 25,580 死于 a/b 窗内重写（控制值已变，持有语义不成立），378 死于 t 中间写
  （链断裂）；`25,580+378=25,958` 与覆盖数精确 reconcile（每窗恰计一次失败原因）。
- 幸存窗省值下界：**0 paid vs 1% 标尺 968**（unextract 96,881 的 1%）⟹
  1% 可行性 0/968；毛上界 58,658（60×）的组分：宿主覆盖 44.3%，价值等价 0%。
- 价值谓词诚实边界：`a/b 窗内零写`是充分非必要条件（同值重写会被误杀）；
  但同值重写情形受 deepfix 函数级结论约束（unextract clean 1030 组 0 重复、
  结构哈希 1618 组 0 可持有；`dirtyk2` CCZ 196 组字面重复全函数互异），
  且 98.5% 的 a/b-fail 呈相邻迭代紧邻对形态（span 14/29，如
  `CCX q828 q834 q857 [52125321,52125350]`），与 gf_iadd 梯逐迭代线复用一致。
- 结论：**pebbling 持有方向 closed**——载体（死区宿主，26k）不是瓶颈，
  瓶颈是值本身在被复用（与 deepfix“干净载体恒 0”是同一根因的另一面：
  电路在 52/52 压力下既无闲线可持，也无静值可持）。
- 反向（重算代替持有以压峰值）：须先有可压的峰——§1 已证团块不可压
  （打孔下界超预算 50×），故反向同样 closed，无需独立实验。

## 3. 验证范围声明

- **未构建候选、未跑官方验证器**（无 kmb、无 102400-shot；基线字节未动）。
- 数字来源：本目录 `artifacts/20261110_qpebble/` 内
  `q_live.json` / `pebble.json` / `q_fuse.json(+gaps.jsonl)` /
  `q_cover.json` / `q_reads.json` / `q_gate.json`。
- 静态声称均为 sound 方向（上界/下界标注明确）；RNG 流安全仅对纯重命名成立，
  任何增删 op 的设计须重估 HMR 结局位移（s7 tail-8k 同类伪影先例）。
- 引用：`20261110_e9diff`（e9 输入哈希、−55 谱系、0 残余），
  `20261110_arch_review`（方向 C/D、定价），`decoder_struct`（84 对/+Q 净负先例、
  s7 切片方法），`dirtyk2`（干净载体要求、假重复陷阱），入口 README（六项 closed）。
- 环境：本工作区 `.venv`（Python 3.12，PyPI 原生 kickmix）；中间 kmx 在
  `/private/var/folders/.../T/dqi_e9diff/`（非仓库）。

## 复现

```bash
.venv/bin/python experiments/dqi/20261110_qpebble/q_live.py    # ~8 min
.venv/bin/python experiments/dqi/20261110_qpebble/pebble.py    # ~8 min
.venv/bin/python experiments/dqi/20261110_qpebble/q_fuse.py    # ~10 min
.venv/bin/python experiments/dqi/20261110_qpebble/q_cover.py   # ~8 min
.venv/bin/python experiments/dqi/20261110_qpebble/q_reads.py   # ~8 min
.venv/bin/python experiments/dqi/20261110_qpebble/q_gate.py    # ~18 min（双阶段）
```
