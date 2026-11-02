# kickmix API 摸底：生成器可用门原语（primitives）

实测环境：本仓库 `.venv` kickmix 1.0.0（`pyproject.toml`），macOS PyPI 原生包。
所有数字来自 `probe_costs.py` 本机实测（产物
`artifacts/20261102_generator_v2/invsqrt/primitive_probes.json`）或 docstring 原文；
猜测项标**估计**。本文件不含任何基线 KMB 读取。

## 1. 可用原语一览（`CircuitBuilder` 方法 docstring + `hasattr` 实测）

| 原语 | 签名要点 | 相干性 | 备注 |
|---|---|---|---|
| `ccx/cx/cz/ccz/cswap/swap/x/z` | 常规，可 broadcast；`ccx` 遇 bool 控制自动降级为 `CX` | 全相干 | 行写/解码主体 |
| `iadd/isub` | `offset`（经典 int / 经典位 / 量子寄存器）`target` 量子寄存器，`control` 可为量子位，`btol` 默认 inf（精确） | **内部用 R/HMR**（测量式 uncompute） | 首版须按“相干镜像规则”加倍计费（见 §3），调用时断言 `btol=inf` |
| `init_and/del_and` | AND 计算 / HMR+CZ 清理对 | `del_and` 用 HMR，首版禁用 | 首版用裸 `CCX` 进已知零线 + 镜像 `CCX` 撤销代替 |
| `multi_controlled_x` | ≥3 控制时自动分配暂存 + `del_and` 撤销 | 内部用 HMR | 同上，首版只用 2 控制或手写镜像 |
| `unary_iteration` | 8 位地址顺序全扫；首定位 ≤8 Toffoli，相邻移动 `(a^b).bit_length()−1`，关闭 0 Toffoli（docstring） | 内部用 R/HMR（decode AND） | 首版用，关闭按 +254 CCX 相干镜像计（估计） |
| `init_lookup/del_lookup` | 查表进干净目标（内部 reset）、测量式清理 | 内部用 R/HMR + 目标 reset | **首版排除**（违反不用 HMR/R，见 `qrom.md`） |
| `left_rotate/right_rotate` | 常数 shift（一律 free SWAP）；量子 shift（barrel，CSWAP）；`control` 可为量子位 | 全相干 | 变量 t 移位与归一化用 |
| `z_pow` | 指数转 `Fraction`，规范到 [0,2)，**舍入到 2^−127 最近倍数**（docstring） | 全相干 | 36 位相位用，无条件调用 |
| `flip_if_less_than/greater_than/equal` | 无符号比较进目标位，`btol` 默认 inf | 内部用 R/HMR（比较暂存） | lz 比较器用，镜像加倍计 |
| `hmr/bit_store/push_condition/pop_condition/neg/neg_if` | 测量 / 经典位 / 经典条件栈 | — | **首版禁用**（相干性纪律；`push_condition` 只接受经典位，不能做量子条件） |
| `alloc_qubits/free` | workspace 管理；`free` 后由 builder 复用 | — | 复用纪律：只复用相干归零线 |
| `create_quantum_register` | 具名寄存器（`x` 22 位输入等） | — | 确定性命名，固定顺序创建 |
| 无 `h` | `hasattr(builder,'h') == False`（实测） | — | dense-QROM XOR 写法排除的直接理由之一 |

条件能力要点：量子条件只能走 `control=` 参数（`iadd/isub/rotate`）或控制位本身
（`ccx/cswap`）；经典条件栈与量子态无关，生成器禁用。

## 2. 实测成本表（静态门计数；执行口径换算见 §3）

| # | 原语调用形 | CCX | CSWAP | CX | R/HMR（内部，首版须替换） | 来源 |
|---|---|---|---|---|---|---|
| P1 | `unary_iteration` 8 位顺序全扫 + 每值 1×`CX` | 254 | 0 | 511 | 255/255 | 实测 `unary8_seq_1cx` |
| P2 | 同上暂存开销 | +8 qubits（开→16，关→8） | — | — | — | 实测 `unary_temp_qubits` |
| P3 | `init_lookup` 8 位地址（随机表，w=12/22/33） | 254（与 w 无关，纯解码） | 0 | 1771/2993/4478（随表 popcount 变） | R≈267–288 / HMR 255 | 实测 `init_lookup_rand` |
| P4 | `iadd` 量子−量子，w=5/14/22/33/36/55 | w−1（4/13/21/32/35/54） | 0 | ≈6.6/bit | R/HMR/CZ ≈ w−1 | 实测 `iadd_qq`（公式 CCX=w−1） |
| P5 | `isub` 量子−量子，w=5/36/55 | w−1（4/35/54） | 0 | 同上量级 | 同上 | 实测 `isub_qq`（公式 CCX=w−1） |
| P6 | 受控 `iadd`（量子控制+量子 offset），w=14/18/36 | 2w+3（31/39/75） | 0 | 70/94/202 | R/HMR/CZ ≈ w−2 | 实测 `iadd_qq_controlled`（公式 CCX=2w+3） |
| P7 | `right_rotate` V55 × 4 位量子 shift | 0 | 135 | 6 | 无 | 实测 `rot55_by_4q`；CSWAP 计 Toffoli-like（`num_toffoli_like`=135） |
| P8 | `left_rotate` 22 位 × 5 位量子 shift | 0 | 61 | 8 | 无 | 实测 `rot22_by_5q` |
| P9 | `right_rotate` 常数 shift | 0（SWAP 纯 Clifford） | 0 | 0 | 无 | 实测（`SWAP` 54，free） |
| P10 | `z_pow(target, Fraction(1,2**36))` | 0（1×`Z_POW`） | 0 | 0 | 无 | 实测文本 `Z_POW q0 0.0000…1455…`；精度 docstring（2^−127） |
| P11 | double-build 同一电路 | 逐指令相等，SHA-256 一致（demo：`240631b0…`） | — | — | — | 实测 `determinism.equal=True` |

## 3. 执行口径换算（相干镜像规则，估计）

官方 verifier 计 `C = executed Toffoli-like + T/4`（来源 `trackB_discrete.md` §首段；
CSWAP=1 Toffoli 来源同文件 Exp3 与 kickmix `num_toffoli_like` 口径一致）。
首版禁用 HMR/R，故凡内部用测量式 uncompute 的原语（P1/P4/P5/P6 及比较器），
其暂存 AND 必须用 CCX 镜像撤销，**执行成本 ≈ 2× 静态 CCX**（正向计算 + 逆向镜像；
全局逆转已含在内，不另乘）。本规则为**估计**（以生成电路实测峰值为准）：

| 换算 | 公式（估计） | 例 |
|---|---|---|
| 非受控加/减 w 位（执行，正+逆） | 2(w−1) CCX | 55 位：108 |
| 受控加行 w 位（执行，正+逆） | 2(2w+3) = 4w+6 CCX | w=24：102；w=17：74 |
| unary 单扫 256 值（执行，正向） | 254 CCX + 数据 CX（free） | 每表每向 254 |
| unary 相干关闭（估计） | +254 CCX（HMR 关闭的镜像替代） | 每开 pass 一次 |
| barrel 移位（执行，正+逆） | 2× 静态 CSWAP | 55 位×4 位：270 |
| 常数移位 | 0（SWAP free / 索引重标） | — |

旋转合成 T 成本沿用 billing 公式（来源 `trackB_approx.md` §5）：
每旋转 `0.56·log2(1/eps)+5.3` T；eps 取相位余量（待主线程验证），此处只给公式不代数。

## 4. 总表（首版调度执行成本 roll-up，估计；明细见 lz/qrom/arith/round_phase 各文件）

| 阶段 | 执行 Toffoli-like（估计） | 来源 |
|---|---|---|
| lz 求值 + 输入归一化 | ~0.2k（比较器 ~86 + barrel 122） | `lz_norm.md` |
| QROM（单 pass 六扫 + 相干关闭，正+逆） | ~3.6k（6×254+254=1778/向） | `qrom.md` |
| 平方 S=U²（含取绝对值） | ~0.6k | `arith.md` |
| V 组装（B 加 + 2AD 减 + RS 加） | ~3.0k | `arith.md` |
| t 移位 + 舍入加一 + t8 计算 | ~0.4k | `round_phase.md` |
| 36 位相位 | 0 Toffoli-like；T ≈ 0.5k C 正+逆（eps 由主线程余量 1.47e−11 turns grounding，估计） | `round_phase.md` |
| **合计** | **~7.8k Toffoli-like（估计）+ 相位 T ~0.5k C** | 以生成电路为准 |

宽度峰值估计 ~125Q（`qrom.md` §4 复用表），以生成电路为准。
上述合计约为基线执行量级（compute 375 + uncompute 483 静态口径）的 10 倍档——
首版为精确整数 datapath + 全相干付出的诚实代价，**不 claim 任何增益**；
优化钩子（CSD 行裁剪、HMR 重引入、QROM 并行工作区、位宽截短）一律 deferred，
且位宽截短类手段在合同余量验证前禁用（不许擅自截位）。
