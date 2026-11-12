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
- **newcirc_residual**：9f 相对 e9 的 −2 CCX 是新模板 C，template A/B 残余 0/0。

## 已落实、可复用（保留，不属放弃）
- `20261110_e9diff`：−55 定位（convert/unconvert 各 −24 CSWAP 模板 A + unextract −7 模板 B），
  残余 0；模板 A/B 方法证据保留。889Q 与 72-salt 的关键数字已收入本文件，原始目录删除。

## 删除清单
- `experiments/dqi/` 下除本文件、`20261110_arch_review/`、`20261110_e9diff/`、`README.md`
  外全部目录（含 decoder2/newcirc_residual/qbatch/unextract_hmr/cd71_diff/e9diff_889/r1salt）。
- `artifacts/` 下除 `20261110_e9diff/` 外全部目录（含 72salt、cd71_diff 1.4G、
  unextract_hmr 2.1G、qbatch、newcirc_residual、r1salt 日志）。
