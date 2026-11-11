# DQI 已放弃方向总览（2026-11-11）

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
- 残余 15/72 低于 Syed V11 口径 21/72——w17 重建期望净账更小，
  R 项不再投入（`20261110_r1salt/README.md`，shard JSON 在 `artifacts/20261110_72salt/`）。

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

## 已落实、可复用（保留，不属放弃）
- `20261110_e9diff`：−55 定位（convert/unconvert 各 −24 CSWAP 模板 A + unextract −7 模板 B），残余 0。
- `20261110_e9diff_889`：889Q 实为 891Q（`993c7038…`，+1550 门），非压缩目标。
  505MB kmb 及画像小 JSON 已删（ census 表全文见该目录 README §B.1，可凭 SHA 重下复算）。
- `20261110_r1salt` + `artifacts/20261110_72salt/`：72-salt 原始证据保留。

## 删除清单
- `experiments/dqi/` 下除本文件、`20261110_arch_review/`、`20261110_e9diff/`、
  `20261110_e9diff_889/`、`20261110_r1salt/`、`README.md` 外全部目录。
- `artifacts/` 下除 `20261110_e9diff/`、`20261110_72salt/`、
  `20261110_r1salt_1salt0000.log` 外全部目录及 `20261110_e9diff_889/dqi_889q_993c7038.kmb`。
