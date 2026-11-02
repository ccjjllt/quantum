# idesc.md：直接整数坐标下降 —— 有效但救不了 R8（记录，不集成）

分支 `invsqrt-generator-rebuild`。新拟合思想（未试过）：跳过浮点 CSD，
直接在存储整数上贪心（B/A/R 三表，步长 4/2/1，逐地址精确更新全局 max，
`integer_descent62.py`）。冻结表只读；每次运行结束全域复核。

## 1. 结果

| 基线 | sweep 后 | 全域确认 | verdict |
|---|---|---|---|
| BOTH 0.616827 | 0.596225（3 moves） | 0 fails | 有效（新能力成立） |
| R8 0.973847 | 0.920781（3）→ 0.913699（2）→ 0 moves 收敛 | 0 fails | 抢救 0.06，仍高于 0.85 集成线 |

## 2. 不集成的理由

- BOTH-idesc（0.5962）：同宽度同移位，代入后 CCX/CSWAP/T 逐项相同，
  score 严格不变（CX 免费口径）——只涨余量，不集成，表留档
 （`int_tables_R10_A20_idesc.json`）。
- R8-idesc（0.9137）：未达 0.85 集成线，不集成，表留档
 （`int_tables_R8_idesc.json` / `int_tables_R8_idesc2.json` 同值）。
- R 侧结论维持：R8 是可验证的极限附近（0.91），DEEP 已 FAIL；
  R 精度硬约束成立，整数下降把 R8 从 0.97 抢到 0.91 即是本法在此的极限。

## 3. 过程 bug（已修，均在文件中注释）

- 全局界低估（局部 max 误作全局）→ 逐地址 maxima 数组精确更新。
- `reshape(256,-1)` 分组错误（xs 交错地址）→ `np.maximum.at`。
- 输出缺 candidate 字段致文件名误标 → 已补；误名文件已删，无数据丢失。
- 门禁：harness 先过 base 对照再谈候选（row_round 教训重申）。

R 侧新拟合到此为止（直接整数优化已是第三种拟合范式：float-CSD → 量化邻域 →
直接整数，三种都指向同一 R 精度墙）。下一步只有换模型族。

## 4. R8I 官方验证 PASS（2026-11-02，主线程，seed 20261031）—— 余量纪律重写

`verify_r8i_seed20261031.log`（EXIT=0）：`status=PASS`，200,540,928 shots，
`score=2133173.374036213`（149Q，宽 V 线；比 BOTH 的 2141088 好 −0.37%），
`worst_error_over_tolerance=0.9136991113709051`（与合同一致），
`circuit_sha256=41bd98bf…`。

原则确证：应用相位是确定性的（TH 双 seed 逐位一致已证），maxrel<1 精确即 PASS，
与 seed 无关。0.85 集成保守线作废——余量只决定抗实现噪声能力，
不决定 PASS/FAIL。R8（0.91）与 A18 同为合法候选；R 精度墙теперь指
“R8 可用、R 更窄需重证”，而非“R8 禁用”。
