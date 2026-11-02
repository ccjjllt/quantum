# width_opt.md：实测降宽第一步（R1 窄化，只做一处）

分支 `invsqrt-generator-rebuild`。基线只读对照（`generator62_v2.py`、`prescreen_gen2.py`、
`artifacts/.../gen2_invsqrt.kmb`、`gen2_stats.json`、`int_tables_7_8_16_5_trunc.json`
`fit_sha256=72154a80…` 均未改；本轮不送完整官方验证，不跑 200M-shot）。
原文件保留为对照；新文件：`width_opt62.py`（`generator62_v2.py` 的复制+标记+一处窄化）、
`width_liveness.py`、`narrow_proof.py`、`prescreen_width_opt.py`（REC_SHA 已同步新值）、
`liveness_gen2.json`（通用标记版实测）/`width_report.md`、`liveness_narrow.json`/
`width_report_narrow.md`。不读旧 KMB/tray；不做数值拟合；本轮不截位（截位禁令遵守）。

## 1. 实测表（先测量）

实测命令：

```
uv run python experiments/invsqrt/20261102_generator_v2/width_liveness.py
# 通用标记版：qubits=160 peak_firstlast=160 @43177 stage=F_S6 comp={'x':22,'temp':45,'lz':5,'v':55,'coef':33}
# 窄化版（重跑）：qubits=159 peak_firstlast=159 @46393 stage=F_S6 comp={'x':22,'temp':44,'lz':5,'v':55,'coef':33}
```

真峰值修正（`width_report.md` 已记）：first-last 落在 F_S6 是索引复用假象；
真值以 `circuit.num_qubits` + 孤立探针为准（`num_allocated_qubits` 在 iadd 前后恒 115，
ripple 暂存走内部 workspace，`probe_cnt` 实测）。

| 调用点 | target len | 孤立探针 extra（=len） | 真 live（115+extra） |
|---|---|---|---|
| R1_J0 `V[0:45)` | 45 | 45 | **160（全局峰值，正/逆 R1_J0/R1R_J0）** |
| A1_J0 `V[1:45)` | 44 | 44 | 159（次峰） |
| S6 `iadd(1)→V[0:36)` | 36 | 35 | 150 |
| square 最大 `S[j:17)` | 17 | 17 | 132 |
| sweep（addr+unary） | — | 8+8 | 131 |
| S1（flip22） | — | 21 | ~51（基座小） |

阶段 toff（通用标记版，`width_report.md` 阶段表，CCX+CSWAP）：F_S1 922 / F_A1 1253
（A1_J0 109 … A1_J13 70）/ F_S3P 302 / F_R1 1206（R1_J0 117 … R1_J11 84）/ F_S6 214 /
逆向 R_S1 1762 / R_A1 1253 / R_R1 1206 / R_S3P 302 / 各 QROM 段 254。
峰值构成：基座 x22+lz5+coef33+V55=115 + R1_J0 行暂存 45 = 160（余量 0）。

## 2. 替换 diff（只做一处：R1 正/逆，A1/S6/查表/窗口/恢复钩子不动）

- `build_r1` / `build_r1_rev` 的通用
  `b.iadd(S, target=v[j:45), control=coef[j])` /
  `b.isub(S, target=v[j:45), control=coef[j])`
  → `_narrow_r1_row_fwd` / `_narrow_r1_row_rev`
  （`width_opt62.py` 新增 `_narrow_maj/_uma/_maj_inv/_uma_inv` + 单行 fwd/rev）。
- 单行结构（S 17 位，Tslice=V[j:45) len≥34；Tlow=前 17，Thigh=剩余）：
  正向：copy17（CCX）→ MAJ×17 → CX 置 cout → UMA×17 → 解 copy（carry/cout 外留 cout，
  峰值 134）→ 高 `b.iadd(cout→Thigh)`（通用，copy 已释，峰值 144）→ 重算 copy →
  `b.flip_if_less_than(Tlow, Cp→cout)` 清 cout（`cout=(Tnew<C)` 恒等式，峰值 149）→ 解 copy。
  逆向为严格逆序逆操作（copy→flip 置 cout→解 copy→高 `isub`→重算 copy→UMA逆正序→CX 清 cout→
  MAJ逆倒序→解 copy，峰值同 149）。copy 做两次以错开 high/flip 峰值（门换宽）。
- 语义证明先行（`narrow_proof.py`，全 Simulator 穷举）：
  `uncontrolled n=3: 64/64 ok`；`controlled-via-copy n=3: 128/128 ok`；
  `split noff=2/nlow=2/nhigh=3: 256/256 ok`；
  `split-reverse: 256/256 ok` → `NARROW-PROOF PASS`。
  MAJ/UMA 由 `CX(c,b);CX(c,a);CCX` 推导（`c'=ab⊕ac⊕bc=maj`），UMA 为其逆+和，
  小例逐位等价已证；`cout=(Tnew<C)` 充要性已证（`Told+C=Tnew+c·2^n`）。

## 3. 成本对比（Q×C 实测，不用旧纸面成本）

| 口径（静态实测） | 通用基线（`gen2_stats.json`） | 窄化（`width_opt62` 实测） | 变化 |
|---|---|---|---|
| Q（`num_qubits`） | 160 | **159** | −1（峰值从 R1_J0 移到 A1_J0） |
| 文本 SHA | `4fe00ee7…`（REC_SHA，原 prescreen） | `55b829c9…4341`（新 REC_SHA，`prescreen_width_opt.py` 已同步，A PASS） | 电路已变，如实记录 |
| `num_instructions` | 94442 | 100618 | +6176（含 STAGE 标记行；标记本身不占线不改语义） |
| CCX / CSWAP / CX | 10874 / 446 / 38368 | 12278 / 446 / 41020 | CCX +1404 |
| `toffoli_like`（CCX+CSWAP） | 11320 | 12724 | +1404（窄行每行约 +53×24 行，正逆） |
| Q×toff（静态） | 160×11320=1,811,200 | 159×12724=2,023,116 | +11.7%（宽度优先，门数涨如实记） |
| 行 toff（R1_J0） | 117（distinct 109） | 170（distinct 97） | 行内宽换门 |
| F_R1 段 toff | 1206 | 1908 | +702（正向 12 行） |
| tracker max（alloc 口径） | 123（基座+addr） | 134（基座+copy17+carry1+cout1） | 窄分配可见，内部 ripple 仍走 workspace |

double-build：`eq True`，两次 SHA 一致（`probe_opt` 实测）。
Q 断言 `≤160` 通过（159）。

预筛（16 样本 `1,2,3,8,31,32,63,128,161,888,2047,2048,2097151,2097152,2506015,3133452`）：

```
prescreen_width_opt.py --a → PRESCREEN-A PASS（双 SHA=55b829c9…=recorded）
--b → checked 16 samples x 159 qubits: x-recovery ok, scratch all zero: True → PASS
--c → 16/16 dphase=0，余量全>0，最坏 x=2506015 margin_units=271129065.0（与基线同点同值）→ PASS
```

`--dump-v` 未重跑（R1 在 V 组装段，B 已覆盖 V 值正确性；如下一步动 A1 再补）。

## 4. 下一步（查表/窗口/恢复钩子不动）

- 当前峰值 159 在 A1_J0（`isub off22→tgt44`）。下一步按同一窄架构处理 A1
  （offset 22，低 22 Cuccaro + 高通用 + flip，行峰值预估 ~150），预期全局 159→~150；
  再处理 S6 经典增量（35→窄），再评估 square/比较器。本轮 A1/S6 不动。
- QROM（mini-pass/unary）、barrel 窗口、z_pow 恢复钩子（逆向不重放相位 D4）均不动。
- 位宽截短继续禁止（无整数误差分析+全域检查前不截位）；`btol` 全程 inf。
- 本轮不送完整官方验证（门禁）；送验前需先完成 A1 窄化并重跑 B/C + 全阶段 liveness。
