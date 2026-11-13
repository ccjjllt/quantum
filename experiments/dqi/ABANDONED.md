# DQI 已放弃方向总览（2026-11-12）

分支 `codex/dqi-research`。本文件是所有已关闭/不再做方向的唯一保留记录。
系统性复盘见 `20261110_arch_review/README.md`（保留）。
定价口径（`20261110_arch_review` §2）：静态 −1 门 ≈ 947,843 分；
失败 −1 shot ≈ 17.21 亿分（≈1817 门）；Q ±1 ≈ ±8.41 亿分（break-even 887 门/Q）。

## 局部改写（载体枯竭）：全部关闭
- 仿射/深非线性/结构乘积缓存（`deepfix`）：全跨度持有 0/1618、连续子间隔 0/1882、
  小间隔宽池 0/40——归零线供给恒为 0，不是需求问题。
- 脏线借用（`dirtyk2`）：正确模型每处 +1 CCX，648 位点净 +648，做即亏。
- CCZ 缓存 / 广播 / 84 稳定对（+1Q 换 −84 门，净 +7.61 亿）/ 检测守卫
  （+2Q 换 +2 门，净 +16.8 亿）：Q 换 T 差一个数量级，死于 887 线。
- scan 掩码守卫移植 / node-3 极点 / inverse24 accidental-zero 守卫：
  前者已足额存在，后两者期望净负或不可归因。

## R 项：关闭（72-salt 实证，2026-11-10/11）
- 72 salts × 102400 shots = 7,372,800 shots（CPU kernel，不耗 GPU 配额）：
  15 salts 各 1 error（14 value + 1 phase），57 个 0/0；
  全量均值 375045278747.2，干净均值 374686789667.4，单失败 +17.2 亿分。
- 残余 15/72 低于 Syed V11 口径 21/72——w17 重建期望净账更小，R 项不再投入。
  原始 shard 目录与 `20261110_r1salt/`（已删） 已删除；关键数字保留在本节。

## Q−1 / spill / pebbling：全部关闭
- 全电路 Q−1 构建（`q1build`）：q845/q849 缺口 31.8 万/19.9 万触碰，不硬构。
- 统一 spill（`spillcolor/spillfrag/spillglobal/spillmulti/spillunified`）：
  切片成立、全电路不闭合；MIS 唯一 {D,H,S}，S 系 bit-exact 关闭；5 合并 CONFLICT 机理清楚。
- 高水位串行化 + 跨阶段 pebbling（`qpebble`）：双 closed。
- 精确活性（`exactlive`）：M_exact=892 真值，零 paid 重命名不可能。

## 旧基线系（历史）
- `20261106_closed/high_return/leo_merge/phase_recovery/syed_v9`（Syed V9 395,679 门系）、
  `20261108_frontier_audit`（−38 谱系：Ozer −21/Kirill −14/Isabe −3/Syed-V10 −62/R 项 +175）、
  `20261109_affine_cache/decoder_struct`（阶段画像：extract 59,169/unextract 96,888 占 24.5%）：
  方法（`audit_frontier_4432ec5f.py` 口径）已由 `20261110_e9diff` 继承，结论不再复用。

## 2026-11-11/12 追加关闭（以下目录均已删除，数字保留在本节）
- **Q-batching**（`20261111_qbatch`）：验证器契约要求 S0..S69 各 12 个 disjoint qubit，
  Q≥840；b=2 的 446Q 直接非法，可行 b≤892/840=1.0619，整数只有 1。最窄公开 883Q
  仅 +2.01% 上界、需 8,081 T 预算；当前 892Q/394,416 T 已在 Q²T 前沿
  （889Q 件 T +43.5k，净差 +10.3%）。
- **unextract→HMR**（`20261111_unextract_hmr`）：unextract 93,787 CCX 中 75,472 目标 S、
  18,315 目标 ancilla；liveness 0 dead targets；HMR 是 X-basis 随机、无 Z 测量，
  无法读/清 S；A/B 候选 256 shots 均 FAIL（256/256 value；B 另 127/256 phase）。
- **cd71 差分**（`20261111_cd71_diff`）：cd71 相对 9f 的 −886 门来自 extract −427 /
  unextract −506，是 generator-level “zero-chart/GF16 constant-multiplication
  linearization”，非局部模板；template A 残余 48、B 残余 1。`cd71_tmplAB` 同 seed 0/0、
  −48.5 mean T，但换 SHA 重抽 salt 的期望惩罚 ~0.096% > 0.0123% 收益，不提交。
- **decoder2**：pebbling 交换表单值上界 234 < 887，净负；BM/Euclid/时域 Chien 下界
  ≥190k vs extract 59k，纸面关闭；889Q `993c7038` 实为 891Q、同族弱实现（+1,550 门）。
  （口径更正：该 ≥190k 是**朴素时域** BM/Chien/syndrome 的乘法数 × 幻想 1 CCX/乘，
  对照对象是 extract 子阶段而非整颗解码器；它不覆盖 half-gcd，也不构成当前频域族的
  下界。详见 `20261112_decoder_family/README.md` §3.2。）
- **newcirc_residual**：9f 相对 e9 的 −2 CCX 是新模板 C，template A/B 残余 0/0。
- **branch-recovery / conditional-routing（`20261112_branch_recovery`，保留目录）**：
  eae396ba 的决策机器总量 **57,119 T = 14.2%**（scan 4,025×11=44,275 + 其余
  zero-test ladder 832 + routing CSWAP 12,012），每项都在 n−1 CCX/n-bit 零测试
  与 1 CSWAP/T 的下界上；可归因于「存储/重算分支决定」的 ≤832 T，不存在 ≥10k
  的可替换块。全电路 45.3% 的 T 是 42-T GF(2^12)（3,406 块）与 99-T GF(2^24)
  （390 块）乘法。unextract 比 extract 多的 44,293 T 中 +23,265 是 9 个
  homogeneous group 的第二条 scalar chain（重建 head 以重放 gauge phase）。
  只读分析 + n=12 toy 穷举；未构建候选、未跑验证器。

## 已落实、可复用（保留，不属放弃）
- `20261110_e9diff`：−55 定位（convert/unconvert 各 −24 CSWAP 模板 A + unextract −7 模板 B），
  残余 0；模板 A/B 方法证据保留。889Q 与 72-salt 的关键数字已收入本文件，原始目录删除。

## 2026-11-12/13 追加关闭（详细目录已删除，数字保留）
- **96-salt paired**（`20261112_96salt`）：52 paired seed 下 `eae396ba` 比 `cd71c482`
  paired mean −0.08285%、stderr 0.0000073%；失败 seed 相同。结论已用于
  `submissions/20261112_eae_253957/`，不属于继续研究方向。
- **近似解码**（`20261112_approx`）：非精确双线性乘子每次调用出错概率下界 **1/4**
  （丢 1 项实测 0.250000）；丢 6 项实测 0.8154–0.8220；单 shot 有 1,148–5,900 次调用，
  ε 直接越过 1/16。近似路线死在 ε，不是 R 惩罚。
- **解码器族**（`20261112_decoder_family`）：目标要求 convert+unconvert ≤61,884 T；
  扩展 Euclid 算术本身下界 77,280 T；half-gcd 1,027 乘/方向（+7.5–9.4%），
  plain EEA 920；完美 EEA 也只到 398.4k static。不存在 Q≤892、static T≤340k 的族。
- **direct phase/MBU**（`20261112_direct_phase`）：uncompute 三段占 51.3% static；
  phase 门贯穿所有阶段（unextract 125,333 CZ + 25,117 Z + 2,912 CCZ），没有可整体
  搬移的末端 phase 块；局部 phase 搬移/HMR 清理 no-go。
- **external-chain 共享**（`20261112_external_share`）：两个乘法调用点逻辑值被 gauge
  分开；理论上限仅 15 T/步（99−84），不是 75–99 T/步；且需 24Q 暂存。no-go。
- **low-ancilla**（`20261112_low_ancilla`，1.0G artifacts）：889Q 的 49 个 ancilla 中
  48 个是 24-bit external word，峰值 49 = 全部 ancilla，slack 0；892Q 同。
  公开生成器本来就用零 workspace 乘法。Q 无法降。
- **乘法秩**（`20261112_mulrank`）：`rank(GF(2^3))=6` 严格证明（2,869,685 候选 0 解），
  35 项路线死；`rank_sym(GF(2^4))=9`；最好仍差目标 471 T。秩路线达不到。
- **下一代解码器**（`20261112_next_decoder`，845M artifacts）：BM 参考电路实测
  5,725,461 T / 1,893Q，比 eae 差一个量级；normal bases 144 vs 42；没有 ≥20% 新族。
- **Q=840 重算**（`20261112_q840`）：52 ancilla 中 48 个是 24-bit external word，
  70.5% paid 门至少一个操作数落在其上；每阶段 840 syndrome 全用。不是可重算缓存。
- **392k combo**（`20261113_392k_combo`）：392k 严格逐 draw 便宜 0.5261%，失败模式
  与 eae 完全相同；retention 最多省 2 T；组合 expected GM 25.4329。已由主仓库提交
  58290992 验证，不再作为研究线继续。

## 2026-11-13 停止研究
公开 889Q DQI `7cbe8ecf…14cd9` 成本 360.73e9，比自研 `eae396ba`（892Q，373.53e9）
低 3.4%。892Q 局部面、Q−1、Q-batching、unextract、解码器族均已有可核查下界；
剩余 13.5% 只能换算法族，停止推进。总览见 main `docs/abandoned-research.md`。

## 删除清单
- `experiments/dqi/` 下除本文件、`20261110_arch_review/`、`20261110_e9diff/`、
  `20261112_branch_recovery/`、`README.md` 外全部目录（含 96salt/approx/decoder_family/
  direct_phase/external_share/low_ancilla/mulrank/next_decoder/q840/392k_combo）。
- `artifacts/` 下除 `20261110_e9diff/`、`20261112_branch_recovery/` 外全部目录
  （含 next_decoder 845M、low_ancilla 1.0G、frontier_source、external_share、mulrank、
  392k_combo 等）。
