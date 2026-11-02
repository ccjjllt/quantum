# s6narrow.md：降宽第三步（S6 常数增量窄化）—— 证明通过，生成器已换

分支 `invsqrt-generator-rebuild`。上一步（`a1narrow.md`）：A1 窄化否决，
Q=159，SHA `55b829c9…4341`，预筛 A/B/C+DUMP-V PASS。本轮只动 S6，
不碰 A1/R1/查表/窗口/恢复钩子；不读旧 KMB/tray；不数值拟合；
不截位；不跑官方 200M-shot 验证；产物只在
`experiments/invsqrt/20261102_generator_v2/`（本文 + 证明/生成器/预筛修改）
与 `artifacts/20261102_generator_v2/invsqrt/`（KMB/stats 由生成器写，不在本轮提交）。

## 0. 文件取舍（说明理由）

- **不新建 `s6narrow62.py`，直接延续 `width_opt62.py`**：与 `a1narrow.md §0`
  同一理由——`width_opt62.py` 已是带 STAGE 标记的工作线，
  `prescreen_width_opt.py`/`width_liveness.py` 均 `import width_opt62`。
  新建文件需复制 ~730 行并重接三处引用，double-build 谱系分叉风险 > 收益。
  延续单线，SHA 谱系清晰。
- **单立本文，不并入 `width_opt.md`/`a1narrow.md`**：前两篇分别是第一步（R1
  生效）与第二步（A1 否决）的审计定稿，改数字会破坏其证据链；本轮是第三步
  （S6 生效），独立成篇保留。
- **`liveness_gen2.json`/`width_report.md` 被 `width_liveness.py` 重写**：
  该脚本固定写这两个文件名（单线跟踪当前电路），本轮重跑后它们即对应
  S6 窄后状态（SHA `a0992bc0…`），不再对应 R1 窄后。这是单线工作流的预期
  覆盖，如实记录。

## 1. 证明（先行，已 PASS）

`narrow_proof.py` 新增三项（S6 形状：36 位分 18/18，低通用经典 +1 →
`flip(Tlow<1)` 求 `(low_new==0)` → `CCX(c,cout,gated)` 门控真进位 →
高通用经典 +1 → 自逆清进位；6/3 缩比穷举）：

- `test_s6_split_inc(6,3)`：窄增正向 vs 整数 oracle `(tv+ctl) mod 2^n` 穷举；
- `test_s6_split_dec(6,3)`：和态出发的窄减（重算进位→高 `isub`→清进位→
  低 `isub`）vs 原值 `tv` 穷举（逆正确）；
- `test_s6_split_roundtrip(6,3)`：窄增后紧接窄减回，一电路 roundtrip
  恒等，暂存两侧均 free。

实测输出（`uv run python .../narrow_proof.py`）：

```
uncontrolled n=3: 64/64 ok
controlled-via-copy n=3: 128/128 ok
split noff=2 nlow=2 nhigh=3: 256/256 ok
split-reverse noff=2 nlow=2 nhigh=3: 256/256 ok
a1sub noff=3 nlow=3 nhigh=2: 512/512 ok
a1roundtrip noff=3 nlow=3 nhigh=2: 512/512 ok
s6inc n=6 k=3: 128/128 ok
s6dec n=6 k=3: 128/128 ok
s6roundtrip n=6 k=3: 128/128 ok
NARROW-PROOF PASS
```

正确性要点（`gated=c&(low_new==0)` 即真进位 `c&(low_old==all1)` 的充要性）：
`c=0` 时 `low_new==low_old`，`low_new==0` 的误触发（`low_old==0`）被
`CCX(c,…)` 门掉 → `gated=0`，高不动，正确；`c=1` 时
`low_new==0 ⟺ low_old==all1`（`+1` 回绕当且仅当低全 1），`gated` 即进位，
正确。`flip`/`CCX` 均自逆，逆向为严格逆序（重算进位→高减→清进位→低减）。
**证明只管等价性，不管宽度**——宽度由 §2 孤立探针裁决。

## 2. 宽度实测（孤立单行探针，先测量后决策）

探针方法沿用 `a1narrow.md §2`：单行独立成电路，
`extra = num_qubits − base`，全局峰 `= 115 + extra`
（基座 `x22+lz5+coef33+V55=115`）。探针代码在仓库外（tmp，不进产物），
`uv run python` 实测：

| 探针 | qubits / base | extra | 全局等效峰 |
|---|---|---|---|
| 通用受控经典 `iadd(1)→T36`（现 S6 行） | 72 / 37 | **35** | 150（与 `width_opt.md` 一致） |
| 通用非受控经典 `iadd(1)→T36` | 71 / 36 | **35** | 150 |
| 窄增量受控 18/18（本轮采用） | 56 / 37 | **19** | **134** |
| 窄增量非受控 18/18 | 54 / 36 | **18** | 133 |
| 窄增量受控 12/12/12（三块） | 52 / 37 | 15 | 130 |
| 窄增量受控 9/9/9/9（四块） | 51 / 37 | 14 | 129 |
| 窄增量受控 6×6（六块） | 52 / 37 | 15 | 130（回升：显式进位 `2·(m−1)` 主导） |
| 行内构件（`iadd(1)→T18` 受控 / `flip(T18<1)`） | — | 各 17 | —（瓶颈，串行复用） |

否决项（如实记，不硬换）：

- **1–2 暂存手写进位链（逐位单进位）未采用**：单进位原地更新
  `carry←carry&~T_new` 需以自身为目标的 `CCX`（control/target 碰撞），
  双进位乒乓则旧进位在 `(T_new,tmp)=(1,0)` 时无法由局部信息确定性清除
  （`carry_old∈{0,1}` 歧义，§1 证明前已用 6 位穷举外的手工枚举确认）；
  全局重算清除需 `O(n²)` 门 + 脏借位多控分解，证明负担远超分块方案。
  故“手写进位链”在本轮的具体形态即**分块进位链**（块内通用、块间
  `flip+CCX`），不单独做逐位链探针——不是隐瞒，是架构选择（`a1narrow.md`
  否决准则在此天然成立：常数加无需 copy 源寄存器，无 `2·nlow<len` 约束）。
- **三块/四块/六块不采用**：extra 15/14/15 虽更窄，但 S6 窄至 134 后已比
  全局峰（A1_J0，159）低 25，不再是瓶颈；更细分块每行多 `+13~+20` toff
  （四块行 toff 94 vs 二块 74 vs 通用 37），属非瓶颈上的过度优化。
  二块 18/18 以最小门增换取足够的宽度胜利，为本轮最优点。

决策：**生成器换**（与 A1 否决相反——S6 窄 extra 19 < 35，胜利明确）。

## 3. 替换 diff（只做一处：S6 正/逆的常数增量行）

- `width_opt62.py` 新增 `_narrow_s6_inc_fwd` / `_narrow_s6_inc_rev`
  （S6 专用，36 位分低 18/高 18，`flip+CCX` 进位链；注释写明峰值/门数/只换 S6）。
- `build_shift_round_phase` 的通用
  `b.iadd(1, target=v[0:36), control=v[54])`
  → `_narrow_s6_inc_fwd(b, v[0:W_P], v[W_V-1])`；
  `build_shift_round_phase_rev` 的通用
  `b.isub(1, target=v[0:36), control=v[W_V-1])`
  → `_narrow_s6_inc_rev(b, v[0:W_P], v[W_V-1])`（严格逆序逆操作）。
  正逆一起换；`build_a1`/`build_r1`/QROM/窗口/恢复钩子不动。
- 单行结构（正向）：低通用受控 `+1`（暂存 17）→ 分配 `cout+gated` →
  `flip(Tlow<1)` 置 `cout` → `CCX` 置 `gated`（暂存 17+2=19，峰值 134）→
  高通用受控 `+1`（workspace 复用，峰值 134）→ `CCX`/`flip` 自逆清进位 →
  `free`。逆向为严格逆序（重算进位→高 `isub`→清进位→低 `isub`，峰值同 134）。

double-build：`eq True`，两次 SHA 一致（`§4` 实测）。
Q 断言 `≤160` 通过（159，S6 不再是峰值）。

## 4. 成本对比（Q×C 实测，不用旧纸面成本）

| 口径（静态实测） | 上轮（R1 窄后，`a1narrow.md §3`） | 本轮（S6 窄后，实测） | 变化 |
|---|---|---|---|
| Q（`num_qubits`） | 159 | **159** | 0（峰值仍在 A1_J0；S6 行 150→134，退居次峰以下 25） |
| 文本 SHA | `55b829c9…4341`（旧 REC_SHA） | `a0992bc0…5a370d0`（新 REC_SHA，`prescreen_width_opt.py` 已同步） | 电路已变，如实记录；**旧 SHA 作废声明：`55b829c9…4341` 作废** |
| `num_instructions` | 100618 | 101200 | +582（含 S6 正逆两行各 +290 左右） |
| CCX / CSWAP / CX | 12278 / 446 / 41020 | 12352 / 446 / 41022 | CCX +74（每行 +37：双通用 19+19 + flip 17×2 + CCX×2 的净值），CSWAP 0，CX +2 |
| `toffoli_like`（CCX+CSWAP） | 12724 | 12798 | +74 |
| Q×toff（静态） | 159×12724=2,023,116 | 159×12798=2,034,882 | +0.58%（宽度优先，门数涨如实记） |
| S6 行 toff（单行，孤立探针） | 37（通用） | 74（窄 18/18） | 行内门换宽 |
| S6 行 extra（单行，孤立探针） | 35（峰 150） | 19（峰 134） | −16，胜利 |

预筛（16 样本 `1,2,3,8,31,32,63,128,161,888,2047,2048,2097151,2097152,2506015,3133452`，
`prescreen_width_opt.py` 新 REC_SHA 下重跑）：

```
PRESCREEN-A PASS（双 SHA=a0992bc0…=recorded）
checked 16 samples x 159 qubits: x-recovery ok, scratch all zero: True → PRESCREEN-B PASS
16/16 dphase=0，余量全>0，最坏 x=2506015 margin_units=271129065.0（与基线同点同值）→ PRESCREEN-C PASS
x=1 ... OK / ... / x=3133452 ... OK（16/16，t=8…19 全覆盖）→ DUMP-V PASS
```

## 5. 下一步

1. **square/比较器评估**：当前峰值 159 @A1_J0（`isub off22→tgt44`，A1 否决后
   的全局瓶颈）。square 最大行 `S[j:17)` extra 17（峰 132）、sweep 131、
   S1 flip 21 均非瓶颈；下一步评估对象是 A1 两级分裂（`a1narrow.md §5.2`
   预估峰 ~140，需独立证明与门数核算）或 square/比较器细项，二选一，
   每次只动一处（本轮工作流：先探针再证明再换）。
2. **送完整官方验证建议**：暂不送。送验前需先完成 A1 瓶颈处理并重跑
   B/C + 全阶段 liveness（`width_liveness.py` 已随本轮重跑，阶段表见
   `width_report.md`）；官方 200M-shot 仍为门禁，不在本轮跑。
3. 位宽截短继续禁止；`btol` 全程 inf。
