# csd_sparse.md：CSD 稀疏性回收 —— 否决（CX 免费，提不动分）

分支 `invsqrt-generator-rebuild`。对象：BOTH 系表
`int_tables_R10_A20_quant.json`（合同 maxrel 0.6168270944）。
生成器零改动；冻结表未动；官方验证未跑。

## 1. 任务 1：已最小（实测确认）

`csd_sparse62.py --recount`（主线程实测）：B pop=4189 / A pop=2528 / R pop=1087，
合计 7804；全电路 QROM CX = 4×7804 = 31216。存储 JSON 为纯整数（无 CSD digit 字段），
电路 `qrom_sweep` 按二进制位做条件 CX——固定整数值的二进制展开唯一，
故每 sweep CX = popcount 强制最小，不存在“值不变、CX 更少”的精确重编码。

## 2. 任务 2：否决（记分口径原因，非搜索失败）

CX 是 Clifford 门，官方成本 `Q × (Toffoli-like + T/4)` 不计 CX
（`evidence_fix4_costing.md` 已立口径；`gen2_stats.json` toffoli_like=CCX+CSWAP 可佐证）。
故任何只减 popcount、不改动 CCX/CSWAP/T/宽度的重编码，**score 严格不变**。
稀疏加压搜索（不同整数值换稀疏性）已无记分意义——叫停，不写候选表。
（已杀掉遗留搜索进程；`csd_sparse_search.log` 为空，无残留产物。）

## 3. 结论

CSD 稀疏性回收在当前电路架构下对官方分数无杠杆。QROM 相关优化只在
“窄位宽（已做 A20/R10/A18）→ 窄加法器/窄行”链条上有意义，该链条已走完。
下一步：R 侧精度需新拟合思想（`refit_layout.md` §7），或承认当前架构距 5% 目标
仍 ~21 倍、需结构性重设计（流式相位/小表/免大 V 容器，非本轮范围）。
