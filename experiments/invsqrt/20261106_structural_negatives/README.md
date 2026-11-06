# invsqrt：大块重综合与条件化的结构负结果

日期：2026-11-06。基线为 `artifacts/20261106_syed_v9/invsqrt/syed_v9_nofallback.kmb`
（62Q，官方本地 PASS，score 97,700.776777236，C=1575.818980278）。
本轮**没有新增候选或收益**；记录的是若干可复现的局部负结果，用来关闭“删门/共享/条件化”
在现有表示内的重复搜索。

## 1. 三个大 X/CX/CCX 块的 AND 数不可由线性共享降低

脚本：[block_rank.py](block_rank.py) 与 [random_rank.py](random_rank.py)，结果：
`artifacts/20261106_structural_negatives/block_rank.json`、`random_rank.json`。

对每个块，把所有 CCX 的乘积函数收集起来，分别计算：

- `formal_span_rank_clean`：只看控制为线性形式的 clean 乘积，在 62 个块输入线变量上的
  二次型 GF(2) 张成维数。若等于 clean 乘积数，则不存在统一的线性组合复用。
- `domain_product_rank`：在实际 3,133,452 个合法 x、全 0 HMR 分支上，全部乘积函数的
  位向量秩；另在 20,000 个随机 x、随机 HMR 分支上复测。

| 块 | 区间 | CCX | clean | 形式张成 | 全域乘积秩 | 随机分支秩 |
|---|---|---:|---:|---:|---:|---:|
| block1 | `[21434,23311)` | 46 | 39 | 39 | 46 | 46,46 |
| block2 | `[33980,36370)` | 59 | 50 | 50 | 59 | 59,59 |
| block3 | `[3429,14081)` | 117 | 110 | 110 | 117 | 117,117 |

结论：在这三个块内，所有乘积在通用测量分支上线性独立；没有“重复乘积/线性组合复用”
可把 CCX 数降下来。全 0 分支上 block3 曾出现 24 的秩，但随机分支恢复为 117，说明那是
测量分支固定造成的假象，不能作为改写依据。该测试只覆盖线性共享；不否定改变算法、
测量纠相或重调度。

## 2. 把 Fredkin 移到 HMR 之后不成立

脚本：[../20261106_deferred_fredkin/deferred_fredkin.py](../20261106_deferred_fredkin/deferred_fredkin.py)。
局部组合检查（5 线、32 个基态、HMR 结果由控制值决定）PASS；生成的真实 KMB 在官方
本地验证器上 **FAIL：x was not restored**（日志
`artifacts/20261106_deferred_fredkin/logs/g0_verify.log`）。

原因：`HMR` 是 X 基测量，测量结果是随机硬币，不是被当控制使用的计算基值；把
`CSWAP(c,a,b)` 移过 `HMR(c)` 后不能用测量结果重建原来的控制。这个方向关闭。

## 3. 条件化/经典化搜索没有稳定命中

脚本与结果：

- [../20261106_cache_search/wire_bit_search.py](../20261106_cache_search/wire_bit_search.py)：
  在随机分支上，没有任何付费门的控制线（或 Fredkin 差值）等于单个现有经典位；
- [../20261106_cache_search/control_span_search.py](../20261106_cache_search/control_span_search.py)：
  没有控制线落在现有测量位的 GF(2) 张成里；
- [../20261106_guard_search/guard_search.py](../20261106_guard_search/guard_search.py)：
  4,000 个样本上找到 31 个“稳定”的守卫候选；
  [../20261106_guard_search/guard_full_domain.py](../20261106_guard_search/guard_full_domain.py)
  在全域 3,133,452 个 x 上逐一检查：**0/31 干净，最少反例 59 个 x**（典型 50–1,000 个）。
  样本法不能代替全域检查。

## 4. 稀有门单删全部失败

脚本：[../20261106_rare_gate_scan/rare_delete_scan.py](../20261106_rare_gate_scan/rare_delete_scan.py)。
在全 0 分支上找出 63 个“乘积非零但支持 <200 个 x”的无条件付费门，逐个删除后用官方
验证器在 `x≤4096` 上检查：**63/63 FAIL**。支持小不等于可删除；典型失败是
`x=1` 或 `x=3` 的相位错误。

## 5. 线性秩与 q28=q50

在 op 3468（首次 62Q 峰值）上，62 条线的函数秩为 62，没有线性关系；在 op 15285/25403
等后段出现秩亏，但 nullspace 基本是 `q28=0`、`q40=0`、`q41=0`（HMR 清零）或
`q28=q50`（显式 `CX q50 q28` 拷贝）。这些是零线/拷贝，不是可免费消除的活动逻辑。

## 复现

```sh
.venv/bin/python experiments/invsqrt/20261106_structural_negatives/block_rank.py
.venv/bin/python experiments/invsqrt/20261106_structural_negatives/random_rank.py
.venv/bin/python experiments/invsqrt/20261106_deferred_fredkin/deferred_fredkin.py --group 0
.venv/bin/python experiments/invsqrt/20261106_cache_search/wire_bit_search.py
.venv/bin/python experiments/invsqrt/20261106_cache_search/control_span_search.py
.venv/bin/python experiments/invsqrt/20261106_guard_search/guard_search.py
.venv/bin/python experiments/invsqrt/20261106_guard_search/guard_full_domain.py
.venv/bin/python experiments/invsqrt/20261106_rare_gate_scan/rare_delete_scan.py
```

官方验证只在明确的候选上手动运行；本记录没有提交 Kaggle，也没有改动基线。
