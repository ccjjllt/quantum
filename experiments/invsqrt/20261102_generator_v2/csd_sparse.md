# csd_sparse.md：CSD 稀疏性回收 —— 技术 PASS、记分否决（side branch 留档）

分支 `invsqrt-generator-rebuild`。对象：BOTH 系表
`int_tables_R10_A20_quant.json`（合同 maxrel 0.6168270944）。
冻结表只读对照、未覆盖；官方 verifier 未动、官方 200M-shot 未跑（本轮止于预筛）。
产物：`experiments/.../csd_sparse62.py`、`artifacts/.../int_tables_R10_A20_sparse62.json`
及同目录 `csd_sparse_search*.log`、`csd_sparse_verify.log`、
`prescreen_refit_both_sparse.log`。

> 与已提交 veto 版（719c03d）的关系：记分结论（CX 免费、score 不动）经本轮实证确认成立；
> 但 veto 版有两处事实错误需订正：(1) QROM 系数不是 4×，而是 **2B+4A+4R**
> （ablation 实测 §1）；(2) 搜索进程并未被杀掉，`csd_sparse_search.log` 非空，
> 搜索成功并产出唯一候选（§2）。本版为完整证据记录，替代 veto 版的“搜索失败/叫停”叙述；
> **记分否决本身维持**（§4）。

## 1. 任务 1：表示检查 —— 已最小（唯一性，无重编码）

`csd_sparse62.py --recount` 实测：B pop=4189 / A pop=2528 / R pop=1087，合计 7804
（B 宽 33、A 宽 20、R 宽 10；entry pop 均值 16.36/9.88/4.25）。
存储 JSON 为纯整数（无 CSD digit 字段）；电路 `qrom_sweep`
（`width_opt62.py:293`）按二进制位做条件 CX，目标线零初值、256 slot 共享、
同 pattern 重放卸载。固定整数值的二进制展开唯一，故每 sweep CX = popcount
强制最小，不存在“值不变、CX 更少”的精确等价重编码。结论：已最小，转任务 2。

**QROM 系数订正（veto 版 4×7804=31216 错误）**：B 表直接装入 V 累加器（免卸载），
A/R 表经 coef 工作区（装载+卸载）。零表 + 单表 ablation（fwd+rev 全电路 CX 差值）：

| 实验 | CX 差值 | 表 pop | 系数 |
|---|---|---|---|
| 全零表 | 22838 | 7804 | 2.926（混合） |
| 仅 B 置零 | 8378 | 4189 | **2.0** |
| 仅 A 置零 | 10112 | 2528 | **4.0** |
| 仅 R 置零 | 4348 | 1087 | **4.0** |

真模型：全电路 QROM CX = **2·popB + 4·popA + 4·popR**；基线 = 8378+10112+4348 = **22838**。
每 sweep CX = pop（B 4189 / A 2528 / R 1087）不受影响，任务 1 最小性结论不变。

## 2. 任务 2：稀疏加压搜索 —— 成功（1 个候选）

方法（`csd_sparse62.py --search`）：BOTH 当前值为起点，segment 独立
（V/P 只依赖本地址表项）；每地址对 B/A/R 逐项试严格更少 1-bit 的邻居
（单比特清零、±1..16、向 2^k 取整），接受条件 = 总 pop 严格下降 **且**
seg maxrel ≤ BUDGET_GLOBAL = 0.6168270944+0.02 = **0.6368270944**；
选择 = 省位数最多、次选 rel 最小；2 遍坐标下降。搜索确定性（RAB 三轮复现比特一致）。

| order | budget | saved bits | 新 pop（B/A/R） | maxrel（@x） | margin units | verdict |
|---|---|---|---|---|---|---|
| BAR | +0.005 | 1290 | 6514 | 0.6216370895 @2441152 | 243452919 | PASS（未留档） |
| BAR | +0.01 | 1304 | 6500 | 0.6262727350 @2130016 | 235736264 | PASS（未留档） |
| BAR | +0.02 | 1319 | 6485（3294/2207/984） | 0.6350391942 @1965983 | 235736264 | PASS（曾落盘，后被 RAB 替代） |
| **RAB** | **+0.02** | **1323** | **6481（3379/2154/948）** | **0.6362060779 @1114240** | **243452919** | **PASS，采用** |

采用理由：RAB 在两项稀疏性指标上同时最优（bits 1323 > 1319；真 CX 3672 > 3486，
因 A/R 位权重 4×、B 位 2×，RAB 把预算优先花在高权重位），且满足全部约束
（fails=0、Δmaxrel=+0.01938 ≤ 0.02、V 全程 ∈ (12439557194768, 24879107407872) ⊂ (0, 2^45)）。
代价透明：maxrel 距 band 上沿仅 0.0006，但绝对余量仍 2.43e8 units，且整数合同是精确全域检查、
无采样不确定性。`--verify-cand` 独立复核：fails=0、maxrel 与落盘值逐位一致，VERIFY-CAND PASS。

候选真 QROM CX = 2×3379+4×2154+4×948 = **19166**（基线 22838，**−3672 / −16.1%**）。

## 3. 任务 3：集成 —— 延续 `refit_variant62` 系（BOTH_SPARSE）+ 预筛全 PASS

新文件理由不成立（与 BOTH 同宽 wA=20/wR=10、同移位 sA=sR=2，builder 对
(wA,wR,nR,sA,sR) 完全通用），故系内加 `CANDS["BOTH_SPARSE"]` 一项
（`refit_variant62.py` +7 行），旧候选零触碰。证据：

| 变体 | eq | Q | toff | N | Q×N | CX | SHA12 |
|---|---|---|---|---|---|---|---|
| BOTH（回归） | True | 149 | 14144 | 122388 | 18235812 | 45030 | da9d9491f920（**不变**） |
| BOTH_SPARSE | True | 149 | 14144 | 118716 | 17688684 | 41358 | 7f9d8b2234c0 |

关键一致性：实测 ΔCX = −3672 **精确等于** §2 预测的真 QROM CX 节省（3672），
ΔN = ΔCX（每省一 CX 即少一条指令）——证明除 QROM pattern 外电路其余 gate
与表值完全无关，集成干净。Q/toff 不变（QROM CX 系 Clifford，预期内）。
REC_SHA（新系）：`7f9d8b2234c0249e9a42c54430c701cd8fdb9082880ace7186cda9e24e8fc4cf`；
BOTH `da9d9491…` 与基线 `0075e006…` 谱系地位不变。

预筛（`prescreen_refit.py --cand BOTH_SPARSE --a --b --c --dump-v`，16 样本，
`prescreen_refit_both_sparse.log`，EXIT=0）：A（double-build SHA 一致）PASS；
B（x 恢复 + 149×16 scratch 全零）PASS；C（16/16 dphase=0、margin 全 >0）PASS；
DUMP-V（16/16 V 逐位一致）PASS。

## 4. 记分 verdict：技术 PASS，记分否决（同意 veto 版结论，实证补强）

ΔQ=0、Δtoffoli-like=0（14144 实测逐位一致）→ 官方 score（Q×(toff+T/4) 口径，
CX 不计费）**严格不变**。因此：BOTH_SPARSE 不送官方 200M-shot 验证、不替 BOTH 主力，
记为 side branch 证据留档（复现：`prescreen_refit.py --cand BOTH_SPARSE`；
RAB/BAR 搜索行可用 `--budget-add/--order/--no-write` 复现，不写盘）。
保留理由：N −3672（−3.0%）/ QROM CX −16.1% 是真实指令减少（QROM 时间），
且 ablation 钉牢了 2/4/4 系数模型；删除将销毁已验证证据，保留零成本
（无 CI、无官方运行、无 KMB/tray 接触）。

## 5. 下一步

- 本分支确定性收益项已穷尽（位宽量化 → 本轮稀疏回收记分归零）。
- R 侧精度仍是硬瓶颈（R8/DEEP 结论不变）；继续压 R 需新拟合思想，
  或结构性重设计（流式相位/小表/免大 V 容器，非本轮范围）。
- 权重感知联合搜索（2/4/4 加权 + B/A/R 联合步）为已记录未做项：预期再省
  ~1% QROM CX，但同样记分归零——除非记分口径变化，否则不做。
