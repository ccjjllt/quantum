# a1split.md：降宽第四步（A1两级分裂 11+11）—— 证明通过，生成器已换

分支 `invsqrt-generator-rebuild`。上一步（`s6narrow.md`）：S6 窄化生效，
Q=159（峰值仍在 A1_J0 通用 44），SHA `a0992bc0…5a370d0`，
预筛 A/B/C+DUMP-V PASS。本轮只动 A1（两级分裂），不碰 R1/S6/查表/
窗口/恢复钩子；不读旧 KMB/tray；不数值拟合；不截位；不跑官方
200M-shot 验证；产物只在 `experiments/invsqrt/20261102_generator_v2/`
（本文 + 证明/生成器/预筛修改 + 单线 liveness 重写）。

## 0. 文件取舍（说明理由）

- **不新建 `a1split62.py`，直接延续 `width_opt62.py`**：与 `a1narrow.md §0` /
  `s6narrow.md §0` 同一理由——`width_opt62.py` 已是带 STAGE 标记的工作线，
  `prescreen_width_opt.py`/`width_liveness.py` 均 `import width_opt62`。
  新建文件需复制 ~900 行并重接三处引用，double-build 谱系分叉风险 > 收益。
  延续单线，SHA 谱系清晰。
- **单立本文，不并入 `a1narrow.md`**：`a1narrow.md` 是第二步（A1 同窄否决，
  44=44 平局）的审计定稿，改数字会破坏其证据链；本轮是第四步（A1 两级
  分裂生效，新架构非同窄），独立成篇保留。
- **`liveness_gen2.json`/`width_report.md` 被 `width_liveness.py` 重写**：
  该脚本固定写这两个文件名（单线跟踪当前电路），本轮重跑后它们即对应
  A1 两级分裂后状态（SHA `4d43d989…`），不再对应 S6 窄后。这是单线工作流
  的预期覆盖，如实记录。

## 1. 证明（先行，已 PASS）

`narrow_proof.py` 新增三项（A1 两级形状：源 22→11+11，目标低 11+11+高；
进位跨级 `c2=(T1<Cp1)|(c1&(T1==Cp1))`，新值对 ADD、旧值对 SUB 均成立；
`flip_if_equal` 单次 11 暂存；SUB 为 ADD 严格逆；2+2+2 缩比穷举）：

- `test_a1_twolevel_add(2,2,2)`：窄加正向 vs 整数 oracle
  `(tv+(sv if ctl)) mod 2^ntgt` 穷举；
- `test_a1_twolevel_sub(2,2,2)`：窄减正向（ADD 严格逆：旧值设进位→高
  `isub`→先清 `eq/lt`（T1 仍旧）→中 `isub`→低 Cuccaro 逆清 `c1`）vs
  整数 oracle `(tv-(sv if ctl)) mod 2^ntgt` 穷举（含进位跨级正确性）；
- `test_a1_twolevel_roundtrip(2,2,2)`：窄加后紧接窄减回，一电路 roundtrip
  恒等，暂存两侧均 free（逆正确）。

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
a1two-add 2+2+2: 2048/2048 ok
a1two-sub 2+2+2: 2048/2048 ok
a1two-roundtrip 2+2+2: 2048/2048 ok
NARROW-PROOF PASS
```

正确性要点（跨级进位充要性）：`c2=(T1new<Cp1)|(c1&(T1new==Cp1))`
对 ADD（T 为新值）、`b2=(T1old<Cp1)|(c1&(T1old==Cp1))` 对 SUB（T 为旧值）
均经 2048 穷举证实；`lt` 与 `s=c1&eq` 互斥（`a1=1` 时 `T1mid≤2^11−2`
故 `s=0`），`c2=lt XOR s` 无 OR-Toffoli；`flip`/`equal`/`CCX` 均自逆，
`eq/lt` 在 T1 未变时（高只动 TH）重算清除，`c1` 在 ADD 经新值 `flip` 清、
在 SUB 经低 Cuccaro 逆 `CX` 清。**证明只管等价性，不管宽度**——宽度由
§2 孤立探针裁决。

## 2. 宽度实测（孤立单行探针，先测量后决策）

探针方法沿用 `a1narrow.md §2`：单行独立成电路，
`extra = num_qubits − base`，全局峰 `= 115 + extra`
（基座 `x22+lz5+coef33+V55=115`）。探针代码在仓库外（tmp，不进产物），
`uv run python` 实测：

| 探针 | qubits / base | extra | 全局等效峰 |
|---|---|---|---|
| 通用 `c-isub22→V[1:45)`（现 A1_J0） | 111 / 67 | **44** | 159（与线上一致） |
| 两级 ADD 22→44（11+11+22，本轮采用） | 94 / 67 | **27** | **142** |
| `flip11×11`（构件） | 33 / 23 | 10 | —（瓶颈，串行复用） |
| `equal11×11`（构件） | 34 / 23 | 11 | — |
| `iadd(1q)→11` / `iadd(1q)→22` | 23/12，45/23 | 11 / 22 | —（高通用 22 为次瓶颈） |
| `iadd11→11`（中通用） | 31 / 22 | 9 | — |
| 窄 R1 ADD 行（校准，S17/T45） | — | 34 | 149（本轮后全局峰） |

决策：**生成器换**（与 A1 同窄否决相反——两级 extra 27 < 44，
44→27 −17，≤30 门限通过；`a1narrow.md §3` 的 `2·nlow<len` 不等式
在此不适用，因低 22 已拆为 11+11，每级 `copy11+flip10` 峰值 22，
`c2` 计算 24，高 22+6=27~28，均 <44）。

## 3. 替换 diff（只做一处：A1 正/逆的 14+14 行）

- `width_opt62.py` 新增 `A1_N0/A1_N1=11` + `_narrow_a1_add_fwd` /
  `_narrow_a1_sub_fwd`（两级专用，注释写明峰值/门数/只换 A1；复用
  `_narrow_maj/_uma/_maj_inv/_uma_inv`，调用时已定义）。
- `build_a1` 的通用 `isub/iadd` → 两级：J0..J12 用 `_sub_fwd`
 （`v[j+1:45)` len44→32，T0/T1 各 11，TH len22→10），J13 用 `_add_fwd`
 （`v[14:45)` len31，TH len9）；`build_a1_rev` 严格镜像（J13 用 `_sub_fwd`，
  J12..J0 用 `_add_fwd`，逆序）。正逆一起换；`build_r1`/S6/QROM/窗口/
  恢复钩子不动。
- 单行结构（ADD 正向）：低 Cuccaro11 置 `c1`（13）→ 中通用 `+Cp1`（22）
  → 中 `+c1`（11）→ 重算 copy + `<`/`equal` 置 `lt/eq` + `CCX` 置 `s` +
  `CX` 置 `c2`（24）→ 高通用 `+c2`（27，峰值）→ `CX` 清 `c2` →
  `CCX` 清 `s` → 重算 copy + `equal`/`flip` 清 `eq/lt`（T1 未变）→
  重算 copy + `flip` 清 `c1`（T0 未变）。SUB 为严格逆序逆操作
  （旧值设进位→高 `isub`→先清 `eq/lt`→中 `isub`→低逆清 `c1`，峰值同 27）。

double-build：`eq True`，两次 SHA 一致（§4 实测）。
Q 断言 `≤160` 通过（149，A1 不再是峰值，见 §4）。

## 4. 成本对比（Q×C 实测，不用旧纸面成本）

| 口径（静态实测） | 上轮（S6 窄后，`s6narrow.md §4`） | 本轮（A1 两级后，实测） | 变化 |
|---|---|---|---|
| Q（`num_qubits`） | 159 | **149** | −10（峰值从 A1_J0 移到 R1_J0；A1 行 159→142，退居次峰以下 7） |
| 文本 SHA | `a0992bc0…5a370d0`（旧 REC_SHA） | `4d43d989…bfe8efd`（新 REC_SHA，`prescreen_width_opt.py` 已同步） | 电路已变，如实记录；**旧 SHA 作废声明：`a0992bc0…5a370d0` 作废** |
| `num_instructions` | 101200 | 124412 | +23212（含 A1 正逆 28 行两级化） |
| CCX / CSWAP / CX | 12352 / 446 / 41022 | 17546 / 446 / 48876 | CCX +5194，CSWAP 0，CX +7854 |
| `toffoli_like`（CCX+CSWAP） | 12798 | 17992 | +5194（每行约 +185×28 行，正逆；A1_J0 toff 109→299） |
| Q×toff（静态） | 159×12798=2,034,882 | 149×17992=2,680,808 | +31.7%（宽度优先，门数涨如实记） |
| A1_J0 行 extra（单行，孤立探针） | 44（峰 159） | 27（峰 142） | −17，胜利 |
| R1_J0 行 extra（单行，孤立探针） | 34（峰 149） | 34（峰 149，未动，现全局峰） | 0 |
| F_A1 段 toff（正向 14 行） | 1253（通用，`width_opt.md`） | 3982 | +2729（行内门换宽） |
| F_R1 段 toff | 1908 | 1908 | 0（R1 不动） |

预筛（16 样本 `1,2,3,8,31,32,63,128,161,888,2047,2048,2097151,2097152,2506015,3133452`，
`prescreen_width_opt.py` 新 REC_SHA 下重跑）：

```
sha1=4d43d989…=sha2=recorded → PRESCREEN-A PASS
checked 16 samples x 149 qubits: x-recovery ok, scratch all zero: True → PRESCREEN-B PASS
16/16 dphase=0，余量全>0，最坏 x=2506015 margin_units=271129065.0（与基线同点同值）→ PRESCREEN-C PASS
x=1 ... OK / ... / x=3133452 ... OK（16/16，t=8…19 全覆盖）→ DUMP-V PASS
```

`width_liveness.py` 已随本轮重跑：`qubits=149`，`liveness_gen2.json`/
`width_report.md` 即对应两级后状态（单线覆盖，见 §0）；first-last 峰值
149 @F_S6 为索引复用假象（`width_opt.md §1` 已记），真峰以
`num_qubits` + 孤立探针为准（R1 149 > A1 142）。

## 5. 完整官方验证 PASS（2026-11-02，seed 20261031，主线程运行）

`artifacts/20261102_generator_v2/invsqrt/verify_a1split_seed20261031.log`（EXIT=0）：

- `status=PASS`，`verified_shots=200540928`，`num_qubits=149`
- `score=2714467.643418115`（Q 降了但门涨，总分高于首版 1847344.58——宽换门如实记）
- `worst_error_over_tolerance=0.6096379373446558` @ x=2506015（与合同一致）
- `circuit_sha256=0cafa2b7…`（kmb 规范哈希）

## 6. 下一步

1. **R1 次窄化评估**：当前峰值 149 @R1_J0（`_narrow_r1_row` extra34）。
   R1 源 17 低 17 已是单级最优（`2·17=34<45`）；再拆 17→9+8 每级
   `copy9/flip8` 峰值约 18+高？预估峰 ~133，但每行 +~100 toff ×24 行，
   Q×C 恶化显著。需独立探针（`extra≤25` 才换）+ 证明 + 门数核算，
   每次只动一处（本轮工作流：先探针再证明再换）。
2. **送完整官方验证建议**：暂不送。送验前需先完成 R1 瓶颈处理并重跑
   B/C + 全阶段 liveness；官方 200M-shot 仍为门禁，不在本轮跑。
3. 位宽截短继续禁止；`btol` 全程 inf；QROM/窗口/恢复钩子不动。
