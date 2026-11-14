# B < 143 关闭记录（2026-11-15，带实测数字）

状态：**CLOSED**。B<143 这条线在本轮被实测否证，不再投入。
当前最佳仍是 **27.31193（ref 58350759，rank 159/3053）**。

## 1. 判决依据

### 1.1 全 U/W refit 的连续 error_2（Kaggle GPU 实测）

`qingyu1232/qcc-chem-b129-full` **v1** 已 COMPLETE。上游 Apache-2.0
`dfthc_refit/experiments/shrink.py`，seed = `maoxin123/qcc-chemistry-4033-toffoli-loaders`
`submission.npz`（`(8,143,44)`，SHA-256 `3f864a7a…`），`--select impact --device --kappa 5e-5`，
`139x44,135x44,131x44,129x44`，`--fade 500 --fit 2500 --final 8000`。日志原文（每行是
"fade 后 ×0.5 / ×0.2 / 最终 fit"）：

```
start (8, 143, 44)
    8x143x44: error_2   20.000 ->   20.000 mHa  D 0.15  (4 s)      # 已量化的公开 seed
 139x44 x0.5: error_2   54.913 ->   18.754 mHa  D 3.33  (77 s)
 139x44 x0.2: error_2   39.209 ->   19.342 mHa  D 4.14  (148 s)
    8x139x44: error_2   30.085 ->   16.173 mHa  D 2.71  (968 s)
 135x44 x0.5: error_2   67.001 ->   18.260 mHa  D 5.69  (1044 s)
 135x44 x0.2: error_2   46.414 ->   19.642 mHa  D 6.60  (1115 s)
    8x135x44: error_2   35.259 ->   18.408 mHa  D 3.93  (1389 s)
 131x44 x0.5: error_2   83.188 ->   21.003 mHa  D 8.71  (1465 s)
 131x44 x0.2: error_2   56.758 ->   22.477 mHa  D 8.98  (1535 s)
    8x131x44: error_2   41.909 ->   20.713 mHa  D 5.25  (1809 s)
 129x44 x0.5: error_2   69.642 ->   21.698 mHa  D 7.40  (1886 s)
 129x44 x0.2: error_2   48.618 ->   22.355 mHa  D 7.57  (1957 s)
    8x129x44: error_2   37.063 ->   19.830 mHa  D 4.07  (2775 s)
out files [8x129x44.npz, last.npz, 8x143x44.npz, 8x139x44.npz]
```

（另一条独立复现：`qcc-chem-b139-quick`，同样 seed，`--fade 100 --fit 100 --final 300`，
8x139x44 = **25.478 mHa**，说明 16.17 需要足量迭代，不是欠收敛的假象。）

结论：**B=129 的连续 error_2 = 19.830 mHa**，B=139 最好也只有 16.173 mHa。

### 1.2 通过门槛是 ≤12.5 mHa，不是 20 mHa

上游 `dfthc_refit/recipes/finish_merged_b8.toml` 的原文（Apache-2.0）：

```
# The rounding is the hybrid schedule used on the (9,176,84) fit on 2026-10-28 ...
# Rounding has cost 6-8 mHa on merged shapes, so the fit should be <= ~12.5 mHa.
```

所以 8-bit 量化的验收门槛是**连续 error_2 ≤ ~12.5 mHa**（而不是 20 mHa）：

- B=129：19.830 mHa，比门槛高 **7.3 mHa**（约 1.6×）；
- B=135：18.408 mHa，高 5.9 mHa；
- B=139（最好点）：16.173 mHa，高 3.7 mHa。

按作者给出的 6–8 mHa rounding 代价，B=129 量化后会落在 **26–28 mHa**，远超 20 mHa
硬闸门，且无法靠 refit 补回（refit 只能收敛到连续最优，而连续最优本身已经贴死 20）。

### 1.3 为什么"只有 B≤135 才有意义"

`dT/dB = −42.40`（由 Stage A 的 T(139)=14,558.4 与 T(143)=14,728 定出；与
`T = 2×loader + inner + outer + Givens` 的分解一致）。用 λeff、Q 不变换算：

| B | T | chem cost | 预期 GM | 实测连续 e2 (mHa) | 门槛 ≤12.5 |
|--:|--:|--:|--:|--:|---|
| 143 | 14,728 | 294.99 M | 27.3119 | 20.000（已量化 seed） | FAIL |
| 139 | 14,558 | 291.59 M | 27.4176 | **16.173** | FAIL |
| 135 | 14,389 | 288.20 M | **27.5249** | **18.408** | FAIL |
| 131 | 14,219 | 284.80 M | 27.6339 | 20.713 | FAIL |
| 129 | 14,134 | 283.10 M | **27.6890** | **19.830** | FAIL |

**GM ≥ 27.50 需要 chem cost ≤ 288.98 M，即 T ≤ 14,428，即 B ≤ 135。**
而 B=135 的连续 e2 是 18.408 mHa —— 全部 B<143 点都离 12.5 mHa 门槛差 3.7–8.2 mHa。
B=139 虽然 e2 最接近，但只给到 27.42，不够 27.5。

因此：**B<143 在两个约束（e2 门槛、GM 门槛）下同时被否证**，不是靠时间盒或猜测关闭。

## 2. 与"廉价 Stage A"的关系

`stage_a.py`（只 refit W/H2_I、冻结 U/words）给出 B=139 e2 = 64.31 mHa、B=129 = 138.07 mHa，
`C=48` 也救不回 —— 说明截断列后再只调权重是死路。本次 full-U 把 e2 从 138 压到 19.8，
证明"瓶颈是 U 不是 W"，但 19.8 仍远离 12.5。两条证据方向一致：**B<143 需要的是重新
训练一个 129 维的基组，而不是修剪 143 维的基组。**

## 3. 重新打开的唯一条件（留档）

若将来要重开 B<143，必须先满足：

1. 从**新 seed** 或 Adam 长训（`dfthc_refit/experiments/adam_train.py`，"tens of thousands of
   Adam epochs"，上游 README 明确说这是"the one lever not yet pulled"）在 B≤135 得到
   **连续 error_2 ≤ 12.5 mHa**；
2. 再做 8-bit rounding（`quantize.py`，`--brot 8` + `finish_merged_b8` 的 33 段冻结表）、
   `refine.py`、`refit.py`，量化后 e2 ≤ 20 mHa；
3. 然后才 build 15 个 loader、跑官方 78,080-shot verifier；
4. 最后只有 chem cost ≤ 288.98 M 才打包提交。

本轮实测（19.830 mHa）距离第 1 步的门槛还差 7.3 mHa，且这是从 143 维 SVD 修剪来的；
没有任何证据表明 Adam 长训能把 129 维基组做到 12.5 mHa 以内。按"不把未执行的验证
写成通过"的约定，此项记为**未验证的开放问题**，不作为可提交路径。

## 4. 验证范围

- 本节所有 error_2 都来自 Kaggle 上的 full-U L-BFGS（`--device --f32`，T4），**不是本机**。
- 没有跑 8-bit rounding、没有 build loader、没有跑官方 78,080-shot verifier（因为
  第 1 步就没过门槛，后续步骤无意义）。
- 本机只做了两件轻量事：读 Kaggle 日志、做上面的 T/GM 换算（纯算术）。
- 早期 `stage_a.py` 的 W/H2_I-only 结果是在本机跑的，已在此标注为不同口径，未与本节混用。
