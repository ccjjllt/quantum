# Fix5: approxB62 digit 搜索双 break 修复（invsqrt §2-5）

范围：只修 `fit_segment` 坐标 digit 搜索的 add-digit 候选循环控制流
（两处 `break` 删除）；不改拟合语义（模型、口径、caps、相位装配、
billing 全不动），不重跑 108 配置网格。主线程定点合同验证不受影响
（合同读 `trackB_fit` 系数表，不读搜索代码）。

复现（2026-11-02 实测）：

```
git diff -- experiments/invsqrt/20261102_hw06_opt/approxB62.py
uv run python -m py_compile experiments/invsqrt/20261102_hw06_opt/approxB62.py
uv run python -c "<Fix5-count 段：同一 cur 下旧 1 候选 vs 新 46 候选>"
```

## 1. diff 位置（`approxB62.py` `fit_segment`，原 279–284 行）

```diff
             for q in range(lo, hi + 1):
                 if q not in used:
                     for s in (1, -1):
                         cands.append(cur + [(q, s)])
-                        break
-                    break
```

第一处 `break` 跳出 `for s`（每位置只试 `s=+1`，`-1` 永不尝试）；
第二处 `break` 跳出 `for q`（只试首个空位）。双 break 叠加后，
每轮每系数只产生 **1 个** add-digit 候选（首个空位、`+1` 符号），
其余位置×符号的改进方向被静默丢弃。修复后候选集为全部空位×`{+1,-1}`。
`git diff --stat`：2 deletions，其他零改动；`py_compile` 通过。

影响量化（同 `cur=[(-30,1),(-12,-1)]`，`lo=-34, hi=-10`）：

```
old add-digit candidates: 1 [[(-30, 1), (-12, -1), (-34, 1)]]
new add-digit candidates: 46
new signs at first q: [(-34, 1), (-34, -1)]
```

`len(c) > cap → skip` 行未动：digit 预算 caps（Pm∈{7,8,9}、
Pr∈{16,17,18}）约束与旧完全一致，搜索只变完整、不变口径。
`fit_segment` 的 move/shift/delete 候选分支本就无 break，不受牵连。

## 2. 为什么两个数值候选不受该 bug 影响

- `7_8_16_5_trunc`：`trackB_full` pass=true，maxrel 0.6096，
  margin 271129065 units，n_rot 37，3 seeds 哈希逐位一致
 （`742d300ee848c494`×3）；`trackB_fit` max digits nM=8/nR=16，
  caps 8/16/16 逐项满足（`rect maxrel` 0.431×TOL）。
- `7_9_18_5_trunc`：full pass=true，maxrel 0.5793，
  margin 314568102 units，3 seeds 哈希逐位一致
  （`59ace6aa7e840b07`×3）；digits nM=9/nR=18，caps 满足。
- 有效性链条：`--full` 从**已存档系数表**出发做整数模型全域检查
  （3,133,452 真输入、batch framing、padding 分开、3 seeds），
  不经过 digit 搜索路径。bug 只决定“搜索是否可能错过更优 digit 集”
  （最优性），不决定“已找到 digit 集是否满足 caps 并通过全域检查”
  （有效性）。两候选的有效性由独立全域检查背书，与搜索最优性无关。
- 网格 108 行 rect 结论标注更新：rect 数字是 bug 版搜索的产物
  （可能次优：真实最优只会更好不会更差），其“通过/不通过”标签保持，
  但 S=6 死 / r0=7 死 / round 劣等结构性结论在重跑完整搜索前改记
  “bug 版搜索下成立，待完整搜索确认”；两候选的 angles/full/billing
  文件不动（输入系数表未变，`sha256 trackB_fit_7_8…=72154a80…`、
  `trackB_fit_7_9…=310364b7…` 实测未变）。

拟合语义冻结确认：本次只删两行 `break`，模型公式、IRLS、`quantize_cap`、
`tread_reps`、相位装配、`full_eval`、`billing_hypothesis` 均未触碰；
网格暂不重跑（待生成器原语开发排期）。

官方验证：0 shots（未运行；引用的 full 检查是模型级整数检查，
非 verifier 电路验证）。Kaggle 提交：无。
