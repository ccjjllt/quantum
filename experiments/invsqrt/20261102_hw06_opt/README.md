# 20261102_hw06_opt：新基线与工具修正（主线程）

日期 2026-11-02（北京时间）。分支 `invsqrt-generator-rebuild`。三路子智能体并行中：
Track A 语义恢复（ses_e68248090ffeqrmepBuaTjEH3y）、Track B 近似拟合（ses_e6824808cffezE0vaGhkpNwxQW）、Track B 离散优化（ses_e68248089ffeGoRkU082bynf6B）。
本文件记录主线程交付：版本映射 + 布尔等价 + 输入坐标。

## 1. 基线身份（已核对）

- 提交包 `submissions/20261101_public_hw06/submission.zip` 内 `invsqrt.kmb`：
  468731 字节，SHA-256 `bce2948ff24e20fe59666d131f7fc4316a905103937272c52fdd39d494b6fe47`。
  已复制为 `artifacts/20261102_hw06_opt/invsqrt/baseline_hw06.kmb`（同哈希）。
- 旧基线 `artifacts/20261031_invsqrt62_replay/invsqrt/ahmed.kmb`：468242 字节，`6dbb98b3…f392f4`，47201 ops。
- 新基线 47258 ops（kmx 文本口径，不含头）。净 +57。
- 作者完整验证成本 100568.4992；5% 阈值 95540.0742。回本线（等价门）：62Q 约 81.10，63Q 约 105.56，64Q 约 129.26。
  新基线已含六处 CCX 节省，不得重复计收益。

## 2. 六处改写映射（ahmed → hw06，kmx op 编号）

`difflib` 对齐共 20 个差异块，聚为 6 个改写区（Ehan 两处 3-to-2 AND 合并 + 四处同类）：

| 区 | 旧 a 区间 | 新 b 区间 | 内容 |
|---|---|---|---|
| R1 | 21333:21342 | 21333:21350 | 删 `CCX q40 q36 q16`、`CCX q28 q36 q16`；`CCX q28 q10 q17` → 经 q16 中转 + CX 清理 |
| R2 | 21446:21468 | 21454:21459+21460:21466+21479:21482 | 插入 5-op（含 `CCX q18 q8 q19`）；`CCX q14 q53 q19` → 经 q14/q18 中转；删 `CX q8 q53;CCX q18 q53 q19;CX q8 q53`；`CX q9 q8;CCX q18 q8 q14` → `CX q57 q14;CX q14 q57`；删尾 `CX q9 q8` |
| R3 | 21543:21552 | 21557:21579 | 删 `CCX q27 q34 q20`、`CCX q28 q34 q20`；`CCX q28 q6 q25` → 经 q20 中转 + CX 扇出 |
| R4 | 21562:21571 | 21589:21611 | 删 `CCX q19 q35 q20`、`CCX q26 q35 q20`；`CCX q26 q25 q27` → 经 q20 中转 + CX 扇出 |
| R5 | 21579:21588 | 21619:21641 | 删 `CCX q16 q37 q20`、`CCX q28 q37 q20`；`CCX q28 q27 q40` → 经 q20 中转 + CX 扇出 |
| R6 | 25458:25477 | 25511:25534 | `CCX q21 q29 q40` → q29 扇出 + `CCX q21 q28 q40`；删 `CX q0 q29;CCX q28 q29 q40;CX q0 q29`；`CCX q28 q0 q21` → 经 q40 中转 |

- R6 结束处 b 对 a 偏移 +57（25534−25477）。R6 之后所有旧切点统一 +57；一切探针绑定电路哈希 + 指令锚点，不直接沿用旧编号。
- 静态门 census（kmx 文本口径，对称计数，已复核）：`CCX 1159→1153`（−6，即六处 CCX 节省）、`CX 29271→29334`（+63）、其余门类（R/X/HMR/CZ/CSWAP/Z/NEG/SWAP/Z_POW/PUSH/POP/BIT_*/CCZ=141）全同。
- Tangfastic `2366…` 样本另建映射，不移植操作编号。

## 3. 工具修正

- `booleq62.py`：三值判定。相同 value-id → 等价（充分条件）；不同 ID → 真值表/ANF（≤12 自由变量）或 Z3（>12，`uv run --with z3-solver`，单次 60s，超时记未知）；绝不把“不同 ID”当反例。测量位版本与条件环境独立保留。
- `coords62.py`：完整分解 `m=x<<lz`、`a=(parity<<7)|((m>>14)&127)`、`delta=m&16383`，含 bit20，全合法域往返一致；物理线路地址编码单独建模；允许非连续寄存器；无连续 19 位 T 假设、无零系数 Horner 占位检查。

## 4. 运行记录

- `uv run --with z3-solver python experiments/invsqrt/20261102_hw06_opt/booleq62.py --self-test`：op25623 恒等式判 EQUIVALENT（truth-table+anf，4 行）；非恒等式判 DIFFERENT 并给出反例 → PASS（2026-11-02 实测）。
- `uv run python experiments/invsqrt/20261102_hw06_opt/coords62.py --roundtrip`：全域 3133452 个输入往返 n_fail=0；x=2 → (lz20,m2097152,a0,delta0)，x=3 → (lz20,m3145728,a64,delta0)，互异 → PASS（2026-11-02 实测）。

旧实验目录保留为历史证据，不覆盖已提交 ZIP。
