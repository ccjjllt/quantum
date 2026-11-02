# gen2 独立整数生成器：首版构建记录

分支 `invsqrt-generator-rebuild`。实现文件 `generator62_v2.py`（新建，
骨架 `generator62_v2_skeleton.py` 未改），预筛脚本 `prescreen_gen2.py`
（手动运行，非测试文件）。系数表调用方注入
（`artifacts/20261102_generator_v2/invsqrt/int_tables_7_8_16_5_trunc.json`，
`fit_sha256=72154a80…`，主线程已验证；生成器内无硬编码大表、无数值拟合、
不读旧 KMB/tray/嵌入指令串）。

## 1. 调度（S0–S10 → 函数）

| 阶段 | 函数 | 内容 |
|---|---|---|
| S0 | `assert_tables` | 形状 + B/A/R 位宽 + min(B) 非负下界；不多断言 |
| S1 | `build_lz_norm` / `_rev` | 温度计 21 比较（`flip_if_less_than`，`btol=inf`，滑动窗口 2 线+1 编码线）+ 优先编码（`hot_i=c_{i+1}&~c_i`，`lz^=Σhot_i·(21-i)`）；x 不变期 XOR 重放即撤销 |
| S2 | `build_normalize[_rev]` | 原地 `left/right_rotate(x, lz)`（rotl=逻辑左移，顶零保证） |
| D | 内联 | `isub/iadd 8192` 原地于 `x[0:14)` |
| S4 | `mini_pass` + `qrom_sweep` | 每表 load-mini / 算术 / unload-mini（addr 每 mini 现配现释，`range(256)` + `move_to`，LSB-first CX；同 pattern 重放即卸载） |
| B | `mini_pass(→v[12:45))` | B 跳过 coef 与 B1 加法器，直装进零初态 V（逆向回放即卸载） |
| A1 | `build_a1[_rev]` | 14 行：`V-=A<<(j+1) if D_j`（j=13 变加），目标止于 bit45 |
| S3' | `build_square2[_rev]` | U 由 D 重建 → 取 `\|U\|` → 9 全加行进 `S=coef[16:33)`（见 §3 bug-1） |
| R1 | `build_r1[_rev]` | 12 行：`V+=S<<j if R_j`，目标止于 bit45 |
| S6 | `build_shift_round_phase[_rev]` | t 全 5 位 → `right_rotate(V,t)` → `V[54]` 受控 +1 进 `V[0:36)` → 36×`z_pow(Fraction(2^k,2^35))`；逆向只逆数据、不碰 z_pow（见 §3 bug-2） |
| S7/S8 | `build_forward` / `build_reverse` | 正：S0→S1→S2→D→B→A×3→S3'→R×3→S6；逆：严格镜像 |
| S9 | `build_circuit` + `create_regs` | 固定顺序具名寄存器；`num_qubits ≤ 160` 断言 |
| S10 | `main` | 同表 double-build 逐指令比对 + SHA；写 kmb + stats JSON |
| 地址 | `build_addr` | `addr[0:7]=x[14:21]`，`addr[7]^=lz[0]`，8×CX，自逆 |

与 §3–§4 设计文档的偏离（D1–D7，正确但较贵，见 `generator62_v2.py` 模块注）：
D1 温度计+编码代替二分（22 值域非 2 的幂；84 flip，可审计）；
D2 S 进 `coef[16:33)`、平方推迟到 A 卸载后、U 由 D 重建（33 线无空闲窗口）；
D3 全 t 5 位 barrel（跳过 const-8 重标；V=55 不可缩，循环正确需 t+36≤55）；
D4 逆向不重放 z_pow（相位是输出；同/负指数重放分别致加倍/抵消）；
D5 行控制经 `coef[15]` 中转 + 平方行先取 `\|U\|`（control/offset 防 collision；
slice 零扩展修正，见 §3）；
D6 mini-pass 拆分 + 算术期释放 addr + 行目标止于 bit45（V<2^45 精确）；
D7 B 直装 V（省 B1 加法器）；kickmix 原语暂存实测 `≈len(target)`
（`qrom.md` §4 的 ~125Q 估计漏计了此项，首版以实测为准）。

## 2. 位宽表（并发峰值审计）

| 寄存器 | 位宽 | 寿命 |
|---|---|---|
| x（输入+归一化+D 原地） | 22 | 全程 |
| lz | 5 | S1→S2 逆 |
| coef（B/A/R/U/S/t 分时；S=`[16:33)`，U=`[0:9)`，t=`[0:5)`，sgn=`[9]`，crow=`[15]`） | 33 | D 后→S3'逆 |
| V（55 容器；行目标止于 45；barrel/相位用全 55） | 55 | B 装→B 卸 |
| addr（mini 内现配现释） | 8 | mini 内 |
| unary 暂存 | 8 | sweep 内 |
| lz 比较/编码线 | 2+1 | S1 内 |
| iadd/isub/flip 内部 ripple 暂存 | ≈len(target)，最大 45（R1-j0 `V[0:45)`） | 调用内 |
| **峰值** | **115 + 45 = 160（余量 0）** | R1/A1 算术期（addr、unary 均已释放） |

## 3. 资源（`gen2_stats.json`，静态门计数）

`qubits=160`，`num_instructions=94442`，`sha256=2296e16c…89115d4`，
`int_tables_sha256=5db0c303…`。
`ops: CCX 10874 / CSWAP 446 / CX 38368 / CZ 6430 / R 6584 / HMR 6584 /
X 13696 / Z 148(+NEG 124) / Z_POW 36 / PUSH/POP_CONDITION 2764 /
INFO_TAG 5624`；`toffoli_like=11320`，`num_z_pow=36`。（2026-11-02 主线程复跑确认与 `gen2_stats.json` 一致。）
说明：R/HMR/CZ/PUSH-POP 为 `iadd/isub/flip/unary` 内部测量式 uncompute
（首版直接调用这些原语，内部残留如实计入；“不用 HMR/R”纪律指不直接调用，
相干镜像 ×2 换算见 `primitives.md` §3，执行口径 ~2× 静态 CCX + 相位 T）。
与基线对照（只读，不复用）：基线 62Q/47258 ops/静态 CCX 1153；
首版约 10 倍门量级——精确整数 datapath + 全相干 + 通用 ripple 的诚实代价，
**不 claim 任何增益**。

## 4. 预筛结果（手动运行命令 + 输出）

- `uv run python experiments/invsqrt/20261102_generator_v2/generator62_v2.py`
  → double-build SHA 一致（`2296e16c…`），写
  `artifacts/20261102_generator_v2/invsqrt/gen2_invsqrt.kmb`（kmb 回读 SHA 一致）
  + `gen2_stats.json`。S0 断言通过，Q≤160 断言通过（恰 160）。
- `prescreen_gen2.py --a` → PRESCREEN-A PASS（重建双 SHA = 记录值）。
- `prescreen_gen2.py --b` → PRESCREEN-B PASS（16 样本 × 160 线：
  `1,2,3,8,31,32,63,128,161,888,2047,2048,2097151,2097152,2506015,3133452`；
  x 逐 shot 恢复，`q0..159` 除 x 位外全零；真输入，无 padding）。
- `prescreen_gen2.py --c` → PRESCREEN-C PASS（16 样本实际相位 vs
  `contract62.model_phase` 差值全为 0；vs 官方 `reference_values` 余量全 >0，
  最小余量 271129065 units（x=2506015）与合同全域最坏点一致）。
- `--dump-v`（诊断）：16 样本前向 V 与模型逐位一致（含 t=8…19 全覆盖）。

## 5. 首版修过的两个真 bug（证据链）

- bug-1 平方零扩展：slice 加法 offset 短于 target 时按零扩展，有符号 U
  为负的行加错整整 2^16（x=3133452：S 多 65536，V 差 R×65536；
  x=1 因 U=-256 仅 MSB 行点火而侥幸通过）。修：取 `|U|` 后全加行。
  教训：凡“量子有符号数进窄 offset”一律先取绝对值或显式符号扩展。
- bug-2 相位放进镜像：逆向重放 z_pow（负指数）把正向相位完全抵消
  （总相位恒为偶整数），`--c` 初版全 FAIL 而余量全 >0。修：逆向只逆数据。
  `round_phase.md`“Z_POW 对角自逆”说法删除；正向数据通路相位中性由
  fwd-only 电路精确验证（相位 = P/2^35 半 turns，分毫不差）。

## 6. 已知缺口与下一步（钩子不动）

- 官方 verifier **0 shots**（本阶段止于 directed 样本模拟；不跑 200M-shot）。
- Q 余量 0（160/160）：kickmix 通用 ripple 按 `len(target)` 吃暂存是主因；
  真降宽需换加法器架构（手写窄 ripple / 进位暴露原语），deferred。
- 降门钩子（deferred）：二分 lz（31 比较+修正 vs 温度计 84）、CSD 行裁剪、
  QROM 并行工作区、HMR 重引入、位宽截短（需合同余量先行验证，禁擅自截位）。
- 下一步：主线程定首次完整官方 PASS 计划；本生成器只改 bug，不做优化。
