# §3–§4 独立整数生成器：原语与调度设计索引

本文件为 §3–§4 子任务（原语与调度）的设计索引。数值合同由主线程独立验证通过
（本目录 `README.md` §定点合同独立验证：全域 3,133,452 输入失败 0，
maxrel 0.6096，最小余量 271129065×2⁻⁶⁴ turns ≈ 1.47e−11 turns，
V∈(12439556932177,24879107506176)⊂(0,2^45)；整数表
`artifacts/20261102_generator_v2/invsqrt/int_tables_7_8_16_5_trunc.json`）。
以下设计引用该结论，不复验。基线只读对照
`artifacts/20261102_hw06_opt/invsqrt/baseline_hw06.kmb`（`bce2948f…`，62Q，
47258 ops，静态 CCX 1153 / HMR 897 / Z_POW 68；B 区新索引 `20738:25687`），
生成器最终入口不得读旧 KMB/tray/嵌入指令串。

首版约束：55 位 V 容器、相干恢复、不用 HMR/R、预期约 136Q；不许为压 62Q 擅自截位；
不写最终生成器实现，不做数值拟合，不跑官方验证。

## 文档索引

| 文件 | 任务 | 内容 |
|---|---|---|
| `primitives.md` | §5 | kickmix API 摸底 + 逐原语成本表 + 总表 |
| `lz_norm.md` | §1 | lz 归一化可逆方案 + 门数/宽度估计 |
| `qrom.md` | §2 | 8 位地址 unary QROM 装载方案 + 成本估计 + dense-QROM 排除理由 |
| `arith.md` | §3 | 精确相干加减 + 学校式平方 + V 各步位宽/Toffoli |
| `round_phase.md` | §4 | 变量 t 移位 + 舍入 + 36 位相位 + 全逆转调度 |
| `generator62_v2_skeleton.py` | §6 | 生成器骨架（签名 + 调度 + 断言），未填实现 |
| `probe_costs.py` | 证据 | 原语成本实测脚本（手动运行） |

## 产物与验证范围

- `artifacts/20261102_generator_v2/invsqrt/primitive_probes.json`：本机实测原语成本。
- 验证范围：仅 kickmix 本地构造级实测（门计数、double-build 哈希一致）；
  **官方 verifier 0 shots**，无 gain claimed。
- 首版诚实成本（估计）：执行 Toffoli-like ~7.8k + 相位 T ~0.5k C @ 峰值 ~125Q，
  约为基线 10 倍量级——首版只求语义独立与正确，不计增益；优化钩子 deferred。
