# ANGLE 批量参数 J 扫描：J=5 是最优可行点，−2% 需要换构造器（2026-11-12）

## 结论

- **no-go**：在本仓库能找到的 ANGLE loader 构造器（`tensorqrom`，dfthc_refit 版，8-bit 全字输出改型）
  下，**J=5 是最优的可行 J**（`T·Q` 的连续极值在 J≈6.1，但 J=6 在 lowbits=4 下超 128-qubit cap，
  换 lowbits=5 密度立刻差 1.66 倍，见下）。J=5 本身仍比当前成本差 **+14.07%**（339.42M vs 297.56M）。
  J<5 单调更差（J=1 +63.1%，J=2 +33.9%，J=3 +20.4%，J=4 +17.5%）。
- **J 杠杆的解析上限**：`Q_total = 387 + 8J` 严格线性，每加 1 个 J 固定 +8 qubits（+1.874%）；
  而 `T_angles` 的 cache 项是 `75·cache/J`，边际收益 `75·cache/J²`（cache=80、J=5 时 ≈ −240 T，
  折 −1.6% of T_total）。两边相抵的极值在 **J≈6.6（4,089 密度下）**，从 J=5 起累计净收益
  只有 **−1.15%**。用当前最好的单电路密度（Maoxin v22 4089，products≈2889/pass、cache≈80）反推：
  J=7 最优也只有 **−1.15%**（294.13M）；要到 −2%，J=7 上的 `T_angles` 还得再降 1.62%
  （3,746 → 3,685），而那个量已经不属于 J 的自由度。
- 唯一在本轮被官方全量验证且确实更低的产物不是 J 扫描的结果，而是**取回 Maoxin v22 最新公开件
  （4,089 T/pass）**：`PASS 297,237,077.47`，−0.108% vs 当前 297,557,548.71。量级远小于 2%。

## 关键前置事实：当前字表不在 signed gauge，且不能 gauge 变换

`artifacts/20261112_eae_candidate/dfthcsos/submission.npz` 的 `angle_words`（1220×75, brot=8）里
只有 **79.06%** 的字满足 `bit7 == bit6`，即不是 `tensorqrom` 要求的 signed gauge。两条路都试过：

1. **Gauge 化再合成**（`w → ((w+64) % 128) - 64` 再存为 `[0,256)`）：字表全部落入 signed gauge，
   但 `evaluate_words` 的度量**不守恒**：`error_1 0.02 → 14.299 Ha`、`error_2 0.02 → 2.769 Ha`、
   `λeff 46.907 → 181.97`。所以“按 128 取模等于逐节点符号翻转”在这个 Givens 树/DF-THC 度量下不成立
   （`reconstruct_u_vectors` 里 θ→θ+π 只翻转该节点的两个分量，父节点的值随后继续参与其它子节点），
   这条路关闭。
2. **改构造器出全部 8 bit**：把 `tensorqrom.build_circuit` 的 signed-gauge 分支换成 full 模式
   （无 `scratch` 借位、输出 `J*brot` 位），见 `tensorqrom8.py`（对 dfthc_refit
   `tensorqrom.py` 的差异：`anf_tensor(..., full=)`、`build_circuit(..., full=)`、
   `low_groups(lowbits, 1 << (lowbits-2))`、`build_family(..., full=)`、full 模式禁用 scratch）。
   这是本轮所有数值的来源。

`tensorqrom8` 的正确性用两条独立证据锁住：J=5 家族 78,080-shot 官方验证 **PASS**，
且 `static Toffoli 5142 == angles_toffoli_per_pass 5142`（电路里没有条件化 Toffoli，
所以静态计数等于逐 shot 执行计数；当前 4,097 件同样满足 4097 == 4097）。

## 精确 J 表（lowbits=4，full 8-bit，trials=6，K=ceil(75/J)）

每行都由官方 `dfthcsos.verify.resource_costs`/`heuristic_costs`/`evaluate_words` 现算，
`λeff = 46.907383278`，heuristic 部分固定 `T=6662, Q_persist=84, Q_temp=303`。
`cost = λeff · T_total · Q_total`；相对基准 = `297,557,548.71265644`。

| J | K | 每电路 Qmax | angles T/pass | T_total | Q_total | cost | 相对当前 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 75 | 99 | 9,765 | 26,192 | 395 | 485,296,282.21 | +63.09% |
| 2 | 38 | 107 | 7,205 | 21,072 | 403 | 398,338,249.31 | +33.87% |
| 3 | 25 | 115 | 5,958 | 18,578 | 411 | 358,164,045.65 | +20.37% |
| 4 | 19 | 123 | 5,562 | 17,786 | 419 | 349,569,487.25 | +17.48% |
| **5** | **15** | **124** | **5,142** | **16,946** | **427** | **339,419,104.77** | **+14.07%** |

- 五个家族都用 `check_words.py`（1 shot/address）确认**逐 word 等于** `submission.npz` 的
  `angle_words`：`words_equal=True`，J/brot 也正确。所以表里的 T 都是“真能装出这张表”的 T。
- J=5 家族另外做了官方全量（78,080 shots）：**PASS**，`score 339,419,104.77145106`、
  `T 16,946`、`Q 427`、`angles_toffoli_per_pass 5142`、`angles_qubits 124`、
  `λeff 46.90738327801011`、`e1 0.01999998 / e2 0.01999998 Ha`、`submission_sha256 edd85726…b16f`。
  这同时验证了 `tensorqrom8` 的 full-8-bit 改型和“静态 CCX 数 == 验证器执行数”的等价性。
- J=5 的 T_total 有 2×5142 = 10,284 在 ANGLE 上，比当前 8,194 多 2,090（+25.5%）；
  Q 相同（427），所以 +14.07% 全部来自 loader。
- `angles_temporary = Qmax − 11 − 8J`（J=5: 73）恒小于 `heuristic_temporary = 303`，所以
  **Q_total = 387 + 8J 严格线性**，“J 与 303 做权衡”这个次杠杆不存在：J 只会单向加 Q。
- J=6 在 lowbits=4 下需要 `11 + 48 + 69 + 4 = 132 > 128`，不可行（J=5 能到 124 已经靠
  `low_groups(4)` 分块缓存，否则是 131）。
- 换到当前最好的单电路密度（4,089）再看向下方向：J=4 是 **305.6M（+2.7%）**，更差。向上方向
  J=6/7 会更好（−0.98%/−1.15%，见下节解析表），但那套构造代码没有公开（notebook 只内嵌 `.kmb`），
  本轮无法把它做成 J≠5 的电路；能够落地的构造器在 J=6 上直接撞 qubit cap。

## J>5：换 lowbits=5 也不行（乘积项爆炸）

lowbits=5 把高地址缓存从 69 个 ancilla 降到 32（cache 80 → 58），cap 内可以做到 J=9~10。
但同一张表的乘积项大幅变多：单电路搜索（J=5，k=4，trials=2）实测
`sizes=[6,6,6,6,6,6,4] 531 项 / 465 s`、`sizes=[4]*10 510 项 / 61 s`、`sizes=[8]*5 546 项 / 1242 s`，
而 lowbits=4 同电路只有 **239 项 / 11 s**（`time_search.py 5 5 2 4` 与 `time_search.py 5 4 6 4`；
lowbits=4 的三个 sizes 分别是 239 / 254 / 265 项，默认分组最好）。所以 lowbits=5 的每电路
T ≈ 58+510 = 568，是 lowbits=4（80+263）的 1.66 倍；J 每步 ~−240 T 的 cache 摊薄完全被抵消。
按此密度，J=6/lowbits=5 的 T_angles ≈ 13×58 + 510×(48/40)×13 ≈ 8,700，是当前 4,097 的 2.1 倍，
净成本 +65% 量级。

**因此 J>5 没有可用构造**：lowbits=4 超 cap（132 > 128），lowbits=5 乘积项爆炸，
而 J 的净收益上限本来就只有 1% 量级。J=6 的完整家族在 30 分钟内没有建完，未计入验证。

## 解析上限：即使装上最好的单电路 loader，J 也到不了 −2%

用 Maoxin v22 4,089 件的实测密度反推（products_total = 4089 − 15×80 = 2,889，
cache = 80/电路，K = 75/J）：

```
T_angles(J) = 2889 + 6000/J
cost(J)/cost_now = [(2·T_angles(J) + 6662)/14856] · [(387+8J)/427]
```

| J | T_angles | T_total | Q | cost | 相对当前 297,557,548.71 |
|---:|---:|---:|---:|---:|---:|
| 5 | 4,089 | 14,840 | 427 | 297,237,077.47 | −0.108% |
| 6 | 3,889 | 14,440 | 435 | 294,644,037.32 | −0.979% |
| **7** | **3,746** | **14,154** | **443** | **294,125,643.73** | **−1.153%** |
| 8 | 3,639 | 13,940 | 451 | 294,903,904.23 | −0.892% |
| 9 | 3,556 | 13,773 | 459 | 296,546,600.79 | −0.340% |
| 10 | 3,489 | 13,640 | 467 | 298,794,402.59 | +0.416% |

（注意：这是“把当前 4,089 件的单电路密度直接搬到 J”的**上界**，不是实测；实测 tensorqrom8
在 J=5 的 `T_angles` 是 4,089 的 1.258 倍，所以能落地的 cost 曲线整体还要上移 ~14%。）

最优点在 J=7，**−1.15%**。到 −2% 还差多少（每行按 `T_angles` 需要再降的比例）：

| J | Q | −2% 允许的 `T_angles` | 该密度下的 `T_angles` | 还需再降 |
|---:|---:|---:|---:|---:|
| 5 | 427 | 3,948 | 4,089 | −3.44% |
| 6 | 435 | 3,815 | 3,889 | −1.91% |
| **7** | **443** | **3,685** | **3,746** | **−1.62%** |
| 8 | 451 | 3,561 | 3,639 | −2.14% |
| 9 | 459 | 3,441 | 3,556 | −3.23% |
| 10 | 467 | 3,325 | 3,489 | −4.70% |

所以 J 这条轴上“最优 J=7 = −1.15%”，离 −2% 只差 1.6% 的 `T_angles`（≈ 60 T/pass，
即 products 2,889 → 2,829）。**但那个 1.6% 必须来自单电路构造，不是 J**：
本轮实测的 `tensorqrom8` 密度在 J=5 的 `T_angles` 就比 4,089 件差 25.8%，把它搬到 J=7
是 `T_angles 4,904 / T_total 16,471 / Q 443 / 342.3M（+15.0%）`。

## 唯一被官方全量 PASS 且更低的产物：Maoxin v22 最新公开件 4,089 T/pass

步骤 1 去取 Maoxin 的合成代码时发现 v22 已经更新：
`maoxin123/qcc-v22-4089-toffoli-chemistry-loaders`（11-09 12:12 UTC，Apache-2.0，
read-only 取回，未执行其 notebook）。其 notebook 只内嵌 15 个 `.kmb`（zlib+base64），
没有构造代码；解出后即得到与当前**同一张表、同一批 angle words** 的 15 个 loader。

- 逐电路 Toffoli：292, 287, 287, 287, 268×5, 265, 266×4, 267 → **4,089/pass**
  （当前 4,097），Qmax 128，T_total 14,840。
- 1 shot/address 检查：`J=5, brot=8, words_equal=True`。
- 官方全量：`manual_verify.py dfthcsos ... --salt jbatch-v22-4089-a` 与 `…-b` 两个 salt
  → **两次都 PASS**，`score 297,237,077.4701011`（与 salt 无关，符合定义），`T 14,840`，`Q 427`，
  `λeff 46.90738327801011`，`e1=e2=0.01999998 Ha`，各 78,080 shots。
  日志：`verify_v22_4089.log`、`verify_v22_4089_b.log`。
- 收益 **−0.1077%**（化学单项）≈ −0.036% GM。不是 ≥2% 的候选，但比当前包严格更低且已验证。

## 验证范围

- **官方全量（78,080 shots）PASS**：`J5_l4`（tensorqrom8 J=5，339,419,104.77，salt `a`）、
  `cand_v22_4089`（297,237,077.47，salt `a` 与 `b` 两次）。日志：`verify_J5_l4.log`、
  `verify_v22_4089.log`、`verify_v22_4089_b.log`。
- **局部结构检查（1 shot/address，非官方验证）**：J=1,2,3,4,5 五个 tensorqrom8 家族
  `words_equal=True`；4,089 件同样。
- **仅单电路搜索 + 估算**：J>5 方向（lowbits=5）只测了单电路的乘积项数与耗时，没有建完整家族，
  也没有验证；结论是“不可用”而不是“数字更好”。
- 产物路径：`J1_l4_t6`、`J2_l4_t6`、`J3_l4_t6`、`J4_l4_t6`、`J5_l4`（后者未带 `_t6` 后缀）。
- 没有 Kaggle 提交、没有 push；本轮只在 `.worktree/dfthcsos` 内写文件。

## 复现

```bash
cd /Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dfthcsos
uv run python experiments/dfthcsos/20261112_jbatch/build_scan.py 1,4 2,4 3,4 4,4   # J 系列
uv run python experiments/dfthcsos/20261112_jbatch/check_words.py artifacts/20261112_jbatch/J{1,2,3,4}_l4_t6
cd /Users/zhaohuaxiang/ccjjllt/quantum
uv run python scripts/manual_verify.py dfthcsos .worktree/dfthcsos/artifacts/20261112_jbatch/J5_l4 --salt jbatch-J5l4-a
```

产物：`artifacts/20261112_jbatch/J1_l4_t6/`…`J5_l4/`（`angle_k_*.kmb` + `submission.npz`）、
`cand_v22_4089/`、`src_v22/`（公开 notebook 原文 `v22_4089.raw` 与解出的 `.kmb`）、
`scan_*.log`、`verify_*.log`、`time_search.py` 的计时输出。
