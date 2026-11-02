# hmr_cleanup.md：HMR 清理重引入评估（§4 第三优先）—— A1+R1 窄行 copy 组生效

分支 `invsqrt-generator-rebuild`。基线 `width_opt62.py`（A1 两级分裂版，Q=149，
SHA `4d43d989…bfe8efd`，官方 PASS score 2714467.64，见 `a1split.md §5`）。
本轮只动窄行 copy 清理（相干 `CCX×2` → `init_and + del_and`），不动查表/窗口/
舍入/相位与恢复钩子；不建测试目录/CI；不提交 Kaggle；不改官方 verifier；
不跑官方 200M-shot 验证；不读旧 KMB/tray；不数值拟合、不截位（冻结表
`int_tables_7_8_16_5_trunc.json`，`fit_sha256=72154a80…`）；证明/探针/变体脚本放仓库外
tmp（不进产物）；本目录新增本文一件 + 单线跟踪文件重写（见 §5）；
`artifacts/` 未写新文件（kmb/stats 仍为旧 SHA 产物，待送验时重建）。

## 0. 文件取舍（说明理由）

- **延续 `width_opt62.py` 单线，不新建 `hmr62.py`**：与 `a1split.md §0` 同一理由——
  `width_opt62.py` 已是带 STAGE 标记的工作线，`prescreen_width_opt.py`/
  `width_liveness.py` 均 `import width_opt62`。新建文件需复制 ~900 行并重接三处引用，
  double-build 谱系分叉风险 > 收益。延续单线，SHA 谱系清晰
  （旧 `4d43d989…` 作废声明见 §5，新 `0075e006…`）。
- **证明脚本放仓库外 tmp**：`proof_hmr.py` / `proof_hmr_rev.py` / `var_measure.py` /
  `var_prescreen.py` / `var_multiseed.py` / `var_executed.py` 均为手动证据命令
  （非测试/CI），按 `window_qrom.md` 纪律不进产物；输出粘贴本文件即证据链完整。
- **`liveness_gen2.json` / `width_report.md` 被 `width_liveness.py` 重写**：
  该脚本固定写这两个文件名（单线跟踪当前电路），本轮重跑后它们即对应 HMR 后状态
  （SHA `0075e006…`），不再对应 A1 两级后。这是单线工作流的预期覆盖，如实记录。
- **局部收益不叠加纸面数**：R1-only / A1-only 先各自实测，再合并 BOTH 重测，
  只采用合并后完整电路实测数（§4）。

## 1. 靶子排序（liveness/成本表，按“可证性×收益”）

基线静态（`liveness_gen2.json` A1 两级后，`width_opt62` 实测；Q=149，
toff=17992，Q×toff=2,680,808）：

| 候选清理块 | 静态 toff（基线） | 其中可转相干对（估） | 量子宽度 | 可证性 | 收益 | 排序 |
|---|---|---|---|---|---|---|
| T2a：A1 两级窄行 copy 组（Cp0a/Cp1a~1e/Cp0b 11位×7组 + s=`c1&eq` 1位，正逆28行向） | F_A1 3982 + R_A1 3718 = 7700（含 A1 段全部） | ~156/行向 ×28 ≈ 4368 CCX（占 A1 段 ~57%） | 组内现配现释，峰值27不变 | **高**：每位为 `ctl&S[i]`（或 `c1&eq`）标准 AND，`del_and` 的 HMR + `CZ` 即论文 Thm.2 块形修正；s 的 CZ 作用于 temps 且 LIFO 先清；NEG=0（块文本无 NEG）；态全程基态（无 H，见下） | **高**：50% copy CCX，预估 ~2100 | **第1，做深** |
| T2b：R1 窄行 copy 组（Cp/Cp2 17位×2组，正逆24行向） | F_R1 1908 + R_R1 1908 = 3816 | 68/行向 ×24 = 1632 CCX（占 R1 段 ~43%） | 同 temps，峰值149不变 | **高**：同上标准 AND（共享 ctl 但各 `CZ(ctl,S[i])` 互易独立）；NEG=0；基态论证同 | **中高**：~816 | **第2，做深** |
| T3：温度计 hot 编码（S1，`h^=c_{i+1}&~c_i`，21 值） | F_S1 922 + R_S1 1762 = 2684 | ~42 CCX（hot 对），其余为 flip 比较器内部（已是 HMR，不可转） | 2+1 线滑动 | 中：含取反控制，需额外 X 处理且会扰动滑动窗口活位；证明负担 > 收益 | 低：~21 | 第3，defer（不等式：可转占比 ~1.6%，先做 T2） |
| T1：QROM decode 对 / 卸载镜像（10 扫 ×254，§1 2540；`window_qrom.md §5` 靶子） | 10 扫 decode 2540（load+unload 对 508/表·方向） | 0（无相干对可转） | extra 8 | 低：`unary_iteration` 关闭已是 HMR（`primitives.md` P1：开 254 CCX + 关 0 Toffoli，实测 close 段 `HMR+CZ`），decode 254 是 init 侧非对易解码非简单 AND；卸载改 `del_lookup` 需把 load 换 `init_lookup`（R reset 语义变 + 新解码器证明），超出本轮预算 | 名义大（若 del_lookup 成立 ~1270）但不可兑现 | 否决（已 HMR 最优 + 重设计阻断，转 §6 未来工作） |

基态论证（T2a/T2b 证明前提，沿用 `window_qrom.md §5`）：用户代码全程无叠加产生门
（`hasattr(builder,'h')==False` 实测；`z_pow` 对角只加相位；`iadd/isub/flip/unary`
内部 HMR 只做测量式 uncompute 且每 shot 输入为基 `|x>|0>`）——每 shot 清理前态恒为
计算基态，测量塌缩不破坏分支相干，剩下相对相位恰为论文式 (4) 的
`(-1)^{k·λ}`，由 `del_and` 的 `CZ` 修正覆盖（见 §2）。

QROM 否决补充证据（`unary` 关闭已 HMR，关闭 0 Toffoli）：
`2位地址全扫` 探针文本含 `HMR q4 b0 / CZ q5 q0 if b0` 关闭段，静态 `CCX=2` 全为
open 侧（见本轮手动探针；`primitives.md §2 P1` 同）。故 T1 无相干镜像税可省，
`window_qrom.md §5` 的“卸载半价趋零”须经 `del_lookup` 重设计实现，不在本轮冒充。

决策：**T2a + T2b 做深**（各取 2–8 位小切片先证，后全宽进生成器变体）；
T3 defer（可转占比过小）；T1 否决（已 HMR + 重设计阻断）。

## 2. 第一名 T2b（R1 copy）：证明（先证后进生成器）

结构（论文映射）：每位 `Cp[i]=ctl&S[i]` 即 Thm.2 式 (8) 块形
`U_φ=Σ|branch><branch|⊗X^{λ}` 的单比特实例（λ 为 AND 结果）；
`del_and` = X 基测量（syndrome `k∈{0,1}`）+ 非零 syndrome 适配修正 `CZ(ctl,S[i])^k`
（§IV.2 outcome-adapted；零 syndrome 无修正）。各 `CZ` 互易且只作用于基态控制位，
联合修正为张量积，`2^k` 联合 pattern 覆盖由单比特覆盖 × 独立性得到；
常数 NEG=0（块文本无 `NEG`，实测断言）。

证明脚本仓库外（tmp，不进产物）：`/tmp/hmr_cleanup/proof_hmr.py`（fwd+pattern）、
`/tmp/hmr_cleanup/proof_hmr_rev.py`（rev/sub）：

- `single-and`：`c1,c2∈{0,1}` 全 4 输入 × 4 seed × batch8 = 128 shots，
  HMR 两种结果均观测到（`{0:52, 1:76}`），输出（控制保留、T 归零）+ 恢复 + 总相位 0
  全对，`NEG_in_block=False`。
- `r1-hmr-slice noff=2 nlow=2 nhigh=2`（R1 形状，copy 2 位组，`del_and` 生成器等价版）：
  `ctl×sv×tv` 全 `128/128 ok`（oracle `(tv+(sv if ctl)) mod 2^ntgt`，相位恒 0）。
- `r1-pattern-coverage k=2`（显式 distinct-bit 手工版 `hmr+push/CZ/pop`，与 `del_and` 同语义，
  每 temp 独立 bit 可读）：固定 `ctl=1,sv=0b11`，8 seed × 16 shots = 128 shots，
  4 种联合 pattern 全观测到 `{(1,1):37,(0,1):32,(0,0):33,(1,0):26}`，
  每 pattern 下 Cp 归零 + 相位 0（`bad=0`）。`del_and` 版（bit 复用 b0）因每次 HMR 后
  紧跟 `CZ` 即时消费（无跨读，版本化 hazard 无；对比 `evidence_fix2_joint.md` 的
  b341 66-writer 教训，本块每写后立即修正，无 last-write-wins 歧义），同 pattern 下等价，
  生成器采用 `del_and`（指令更少，bit 复用）。
- `r1-hmr-rev`：和态出发逆切片 `128/128 ok`（输出回 tv，相位 0）。

```text
single-and: patterns seen [0, 1] counts {0: 52, 1: 76} NEG_in_block=False fails=0
r1-hmr-slice noff=2 nlow=2 nhigh=2: 128/128 ok (del_and, single-seed)
r1-pattern-coverage k=2: patterns {(1, 1): 37, (0, 1): 32, (0, 0): 33, (1, 0): 26} total=128 bad=0 (need all 4 patterns, bad=0)
r1-hmr-rev 2/2/2: 128/128 ok
HMR-PROOF PASS
HMR-REV-PROOF PASS
```

孤立全宽行探针（`W_S=17`，证据：`var_measure.py` 前后对比）：
coherent `CCX=170 → hmr CCX=136`（−34/行向 = 68 copy 的一半），qubits 同 97，
bits 同 1（bit 复用，无新增）。

## 3. 第二名 T2a（A1 copy + s-AND）：证明（先证后进生成器）

结构：7 组 11 位 copy（Cp0a/Cp1a/Cp1b/Cp1c/Cp1d/Cp1e/Cp0b）同 §2 标准 AND；
`s=c1&eq` 为 temps 上的 AND，其 `CZ(c1,eq)` 在 `eq/lt/c1` 清除前 LIFO 即时执行
（add 正向：置 s → 用 s 置 c2 → 高加 → 清 c2 → 清 s → 再清 eq/lt/c1；
sub 正向：旧值置 s/c2 → 高减 → 清 s → 再清 eq/lt → 中减 → 低逆清 c1），
嵌套顺序安全；NEG=0。

- `a1-hmr-add 2+2+2`（A1 两级形状，全部 copy + s 均 `init/del`，`del_and` 版）：
  `ctl×sv(16)×tv(64)` 全 `2048/2048 ok`（oracle `(tv+(sv if ctl)) mod 2^ntgt`，相位 0）。
- `a1-hmr-sub 2+2+2`：全 `2048/2048 ok`（oracle `(tv-(sv if ctl)) mod 2^ntgt`，相位 0）。
- 联合 pattern 覆盖由 §2 的 k=2 显式覆盖 + 各组独立互易 CZ 推广（组间控制对
  `(ctl,S*)` 与 `(c1,eq)` 不交或 LIFO 有序，无交叉 syndrome）；
  全电路多种子预筛（§4，5 seed × 16 样本）为联合大 pattern 下的端到端确认。

```text
a1-hmr-add 2+2+2: 2048/2048 ok (del_and incl s-AND)
a1-hmr-sub 2+2+2: 2048/2048 ok
```

孤立全宽行（A1_J0 形 `S22/T44`，`var_measure`）：`CCX=299 → 221`（−78/行向；
7 组 154 + s 对 2 的一半），与 R1 行同 qubits/bits 不变。

## 4. 生成器变体：单线合并，完整电路实测（不用纸面叠加）

变体方法（仓库外 tmp，`import width_opt62` 后 monkey-patch 四个行函数，
其余调度/表/寄存器不动；Q_CAP 断言保留以暴露真峰值；double-build `eq` 检查）：

| 变体（完整电路实测） | Q | toff | Q×toff | SHA（前12） | double-build |
|---|---|---|---|---|---|
| 基线（A1 两级后） | 149 | 17992 | 2,680,808 | `4d43d989b9f9` | eq=True |
| R1-only（§2 全宽） | 149 | 17176（−816） | 2,559,224（−4.5%） | `68e2a20dac0b` | eq=True |
| A1-only（§3 全宽） | 149 | 15962（−2030） | 2,378,338（−11.3%） | `6a71bb062284` | eq=True |
| **BOTH（合并后重测，采用）** | **149** | **15146（−2846 = 816+2030，加和成立无交叠）** | **2,256,754（−15.8%）** | `0075e006a67e` | eq=True |

```text
BASE Q=149 toff=17992 CCX=17546 instr=124412 sha=4d43d989b9f9 bits=1
R1-only: eq=True Q=149 bits=1 instr=126044 CCX=16730 CSWAP=446 CX=48876 HMR=8642 R=8642 CZ=9544 toff=17176 Qxtoff=2559224 sha=68e2a20dac0b
A1-only: eq=True Q=149 bits=1 instr=128472 CCX=15516 CSWAP=446 CX=48876 HMR=9856 R=9856 CZ=10758 toff=15962 Qxtoff=2378338 sha=6a71bb062284
BOTH: eq=True Q=149 bits=1 instr=130104 CCX=14700 CSWAP=446 CX=48876 HMR=10672 R=10672 CZ=11574 toff=15146 Qxtoff=2256754 sha=0075e006a67e
```

执行口径确认（verifier 按 executed Toffoli-like 计，`CZ/HMR/R` 非 Toffoli-like 免费；
4 样本 `counting_operations` 实测）：base `(71968/4=17992)` vs both `(60584/4=15146)`，
seed 1/42 同值——静态节约 = 执行节约，无数据依赖分支。

```text
base static 17992 executed (71968, 4)
both static 15146 executed (60584, 4)
```

阶段表（`width_liveness.py` 重跑，BOTH 后）：F_A1 3982→2901，R_A1 3718→2769
（A1 段合计 −2030）；F_R1 1908→1500，R_R1 1908→1500（R1 段合计 −816）；
A1_J0 `CCX 299→221 / HMR 65→143 / CZ 90→168`；R1_J0 `CCX 170→136 / HMR 18→52 /
CZ 33→67`；Q 峰值仍 R1_J0（149 不变，HMR 不增量子宽度）；`num_instructions`
124412→130104（+5692：`R`/`HMR`/`CZ` 修正指令如实涨，Toffoli-like 降）。

预筛（16 样本 `1,2,3,8,31,32,63,128,161,888,2047,2048,2097151,2097152,2506015,3133452`，
新 REC_SHA 下 `prescreen_width_opt.py` 重跑；B/C/DUMP-V 沿用同文件）：

```text
sha1=0075e006a67e30a54ad82083cd1a19434bfa85e026f4182788beea9feb80235d
sha2=0075e006a67e30a54ad82083cd1a19434bfa85e026f4182788beea9feb80235d
recorded=0075e006a67e30a54ad82083cd1a19434bfa85e026f4182788beea9feb80235d
PRESCREEN-A PASS
checked 16 samples x 149 qubits: x-recovery ok, scratch all zero: True
PRESCREEN-B PASS
16/16 dphase=0，余量全>0，最坏 x=2506015 margin_units=271129065.0（与基线同点同值）
PRESCREEN-C PASS
x=1 ... OK / ... / x=3133452 ... OK（16/16，t=8…19 全覆盖）
DUMP-V PASS
```

多种子鲁棒（HMR 不同 pattern，`/tmp`，非预筛文件）：seed 0/1/42/12345/999 × 16 样本，
x 恢复 + scratch 归零 + dphase=0 全 `bad=0 PASS`。`narrow_proof.py` 原证明未动，
重跑仍 `NARROW-PROOF PASS`（HMR 只换 copy 清理，不碰加法正确性）。

## 5. 生成器状态：单线已换，REC_SHA 已同步

- `width_opt62.py`：`_narrow_r1_row_fwd/rev`（2×17 copy 对）+
  `_narrow_a1_add/sub_fwd`（7×11 copy 对 + s 对）`CCX×2` → `init_and + del_and`，
  注释写明 HMR/峰值/行 toff；`build_a1/rev`、`build_r1/rev` 调度不动；
  MAJ/UMA 内核、`flip` 比较器、`unary`、S6、QROM、窗口不动。
- `prescreen_width_opt.py`：`REC_SHA` → `0075e006a67e30a54ad82083cd1a19434bfa85e026f4182788beea9feb80235d`。
- **旧 SHA 作废声明：`4d43d989b9f9520fec11991b90f7bd511aa76a6df7bfd3a60822ed755bfe8efd` 作废**
  （A1 两级 + 相干 copy 时代终结；官方 PASS 记录 `verify_a1split_seed20261031.log`
  仍对应旧 SHA 存档，不删）。
- Q/门数记录：Q149 不变 / toff15146 / Q×toff 2,256,754（−15.8%）；`liveness_gen2.json`/
  `width_report.md` 已随本轮重跑（单线覆盖，见 §0）。
- `git status`：`width_opt62.py`、`prescreen_width_opt.py`、`liveness_gen2.json`、
  `width_report.md` 四件修改 + 本文一件新增（`hmr_cleanup.md`）。

## 6. 下一步

1. **送完整官方验证（建议送）**：本轮 toff −15.8% 且 Q 不变，score 必降
   （静态预估 `149×(15146+T/4)` vs 旧 `2714467.64`；T 侧 36×z_pow 未动）。
   送验前只需重建 kmb（`width_opt62.main()`，artifacts 未跟踪）并跑官方 verifier
   （200M-shot 门禁：本轮未跑，仍为门禁）。
2. **T3 温度计 hot（defer，非否决）**：可转 ~42 CCX（~0.3%），且取反控制需 X 包裹证明；
   待 HMR 送验 PASS 后作为顺手优化（与 S6 `gated` 1-CCX 对同批），不单独立项。
3. **T1 QROM `del_lookup`（否决维持）**：需 `init_lookup` 重设计 + 新解码器证明 +
   fixup 表编译（论文 §E.2 `O(L)→O(√L)` 线），立项条件为独立证明文件 + 全电路集成预算，
   不在窄行线内冒充。
4. 位宽截短继续禁止；`btol` 全程 inf；CSD 精确重编码（常数加屈指可数处）可作 HMR 后
   顺手优化，不单独立项（沿用 `window_qrom.md §5` 结论）。

---

证据命令索引（本轮全部手动运行，非测试/CI）：
`uv run python /tmp/hmr_cleanup/proof_hmr.py`（§2）、
`uv run python /tmp/hmr_cleanup/proof_hmr_rev.py`（§2–§3）、
`uv run python /tmp/hmr_cleanup/var_measure.py`（§4 变体表）、
`uv run python /tmp/hmr_cleanup/var_prescreen.py`（§4 预筛等价）、
`uv run python /tmp/hmr_cleanup/var_multiseed.py`（§4 多种子）、
`uv run python /tmp/hmr_cleanup/var_executed.py`（§4 执行口径）、
`uv run python experiments/invsqrt/20261102_generator_v2/prescreen_width_opt.py --a/--b/--c/--dump-v`（§4）、
`uv run python experiments/invsqrt/20261102_generator_v2/narrow_proof.py`（§4）、
`uv run python experiments/invsqrt/20261102_generator_v2/width_liveness.py`（§4–§5）。
官方 200M-shot 验证：**PASS**（2026-11-02，主线程运行，seed 20261031）：
`artifacts/20261102_generator_v2/invsqrt/verify_hmr_seed20261031.log`（EXIT=0）——
`score=2290413.643418115`（相对 A1 分裂版 2714467.64 **−15.6%**，与静态预测 −15.8% 吻合；
约为基线 100568.50 的 22.8 倍），`toffoli_equivalent=15371.90`，`num_qubits=149`，
`worst_error_over_tolerance=0.6096379373446558` @ x=2506015（合同点不变），
`circuit_sha256=0b4ce332…`。
