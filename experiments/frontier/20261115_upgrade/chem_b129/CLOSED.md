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

## 5. 一个尚未关闭的子问题（在跑，不影响上面的判决）

上游的 6–8 mHa 是"merged shapes"的泛化说法，没有给 `(8,R,44)` coded-word 这一族的实测值。
若这一族的 8-bit rounding 代价其实远小于 6 mHa，那么 B=139 的 16.173 mHa 有可能量化到
≤20 mHa（对应 GM 27.42），B=129 仍不够。

已启动 `qingyu1232/qcc-chem-rounding-calibration`（T4 GPU）做直接标定：

1. 同一 seed 的 `(8,143,44)` 做 full-U L-BFGS refit（不剪枝）→ 这一族的连续地板 `e2_c(143)`；
2. `quantize.py --brot 8` 量化同一 fit → `e2_q(143)`；两者之差就是**这一族的真实 rounding 代价**；
3. 对 `(8,129,44)`（已知 `e2_c = 19.830`）做同样的量化 → `e2_q(129)`。

判读：
- 若 `e2_c(143)` 落在 ~12–13 mHa → 说明本轮的 shrink 管线是够强的，`e2_c(129)=19.830`
  就是真实水位，B=129 判死成立；
- 若 `e2_c(143)` 也停在 ~19–20 mHa → 说明本轮的 10⁴ 级 L-BFGS 远没到该族地板（公开表来自
  数万 Adam epoch + 59 段冻结量化），那么 `19.830` 不能当作 B=129 的地板，B=129 属于
  **未决**，必须重跑长程 Adam 才能判。
- 两种情况下 B=129 都不会因为这次标定变成可提交件：只有当 `e2_q(129) ≤ 20 mHa` 才会
  进入 loader build 与官方 78,080-shot 验证。

## 6. 已完成的对照标定：这一族的真实 rounding 代价 = 5.22 mHa

`qingyu1232/qcc-chem-rounding-calibration`（T4，COMPLETE）。同一 seed、**同一形状 (8,143,44)、
不剪枝**，只做 full-U L-BFGS refit：

```
start (8, 143, 44)
    8x143x44: error_2   20.000 ->   20.000 mHa  D 0.15  (3 s)     # 已 8-bit 的公开表
 143x44 x0.5: error_2   20.000 ->   16.727 mHa  D 1.25  (23 s)
 143x44 x0.2: error_2   16.727 ->   16.178 mHa  D 1.32  (43 s)
    8x143x44: error_2   16.178 ->   14.777 mHa  D 2.14  (166 s)   # 连续地板
```

于是：

| 量 | 值 |
|---|---:|
| 连续地板 `e2_c(143)` | **14.777 mHa** |
| 已发布 8-bit 表 `e2_q(143)` | 20.000 mHa |
| **这一族的 rounding 代价** | **5.22 mHa** |
| 连续地板 `e2_c(139)` | 16.173 mHa |
| 连续地板 `e2_c(129)` | 19.830 mHa |
| 每减 1 个 B 的误差代价 | ≈ −0.361 mHa/B（141→15.5、137→16.9、135→17.7） |

把它加到 20 mHa 闸门上，得到 B<143 的**逐点判死表**（预测，非实测）：

| B | e2_c | e2_c + 5.22 | ≤20 mHa |
|--:|--:|--:|---|
| 143 | 14.777 | 20.0 | PASS（就是现用的形状） |
| 141 | ~15.48 | 20.7 | FAIL |
| 139 | 16.173 | 21.4 | FAIL |
| 135 | 18.408 | 23.6 | FAIL |
| 129 | 19.830 | 25.1 | FAIL |

**只有 B=143 本身能过 20 mHa 闸门**；任何 ≥1 个基函数的削减都会越过边界（每减 1 个 B
只省 42.4 T = 0.29% 成本 = +0.10 GM，却要付 0.36 mHa 误差）。这解释了为什么公开件里
根本不存在 B<143 的化学表：不是没人试，而是这条路在 20 mHa 闸门下不可行。

重要副产品：**本轮的 shrink 管线是够强的**（166 s 就把该族从 20.000 压到 14.777，
仅比作者数万 epoch 的连续地板差 ~2 mHa），所以 `e2_c(129)=19.830` 不是"欠训练"的假象，
它就是这个形状的真实水位。

直接量化 `e2_q(143)`/`e2_q(129)` 的确认跑在
`qingyu1232/qcc-chem-roundcost-b143-vs-b129`（T4）；结论不依赖它——上面的预测
已经全部 >20 mHa，量化只会更差。

## 7. 第二次独立复现 + 129 的直接 fit（2026-11-15）

`qingyu1232/qcc-chem-roundcost-b143-vs-b129`（T4，COMPLETE）：

```
== shrink143
        8x143x44: error_2   20.000 ->   20.000 mHa  (3 s)
     143x44 x0.5: error_2   20.000 ->   16.726 mHa  (23 s)
     143x44 x0.2: error_2   16.726 ->   16.185 mHa  (41 s)
        8x143x44: error_2   16.185 ->   14.779 mHa  (161 s)     # 与 14.777 一致
== shrink129  (直接从 143 seed fit，不走 139/135/131 链)
     129x44 x0.5: error_2  187.479 ->   24.431 mHa  (25 s)
     129x44 x0.2: error_2  138.987 ->   30.362 mHa  (43 s)
        8x129x44: error_2  100.732 ->   21.134 mHa  (176 s)     # 比链式 19.830 更差
```

两个新事实：

1. `e2_c(143) = 14.779` **重复出现**（两次独立 run：14.777 / 14.779），说明这一族的连续地板
   稳定在 ~14.78 mHa，rounding 代价 5.22 mHa 是可靠的。
2. `e2_c(129)` 取决于起点：链式（139→135→131→129，每步热启动）给 19.830；
   直接从 143 seed 单步 cut 给 **21.134**。两者都远离 ≤12.5，所以结论与起点的强弱无关。

注：该 run 的 `quantize.py` 因 `dfthcsos.scoreinfra` 不在 PYTHONPATH 而 rc=1（未产出
`e2_q`）。修正版 `qingyu1232/qcc-chem-measured-e2q` 把比赛 `verifiers/` 树加进
PYTHONPATH 后重跑，专为拿到直接量化的 `e2_q(143)` / `e2_q(129)`。

## 8. 最后一条未试路径已上线：Adam 重训 (8,135,44)（Kaggle CPU）

上游 `adam_train.py` 的 docstring 明确指出这是"the one lever not yet pulled"：

> The L-BFGS seeds plateau where they start (random 19, DF 6.8 at (9,180,90), 19 at a scoring
> shape); the public seeds came out of tens of thousands of Adam epochs and prune far better,
> so this is the one lever not yet pulled.

所以上面所有 19.8/21.1 的连续 e2 都是 **L-BFGS/shrink 路径** 的上限，不等于该形状的真实地板。
为把这个变量单独测掉，已启动：

- `qingyu1232/qcc-chem-adam-b135-cpu`（CPU，`JAX_PLATFORMS=cpu`；GPU 两个槽位被卡住的
  reservation 占满、GPU 时间冻结在 3,551.975 s，故走 CPU）
- 第 1 步：full-U shrink 到 `(8,135,44)`（`--fade 300 --fit 1200 --final 4000`）
- 第 2 步：`adam_train.py --steps 8000 --lr 1e-3 --lr-final 1e-5 --kappa 5e-5
  --report 250 --save 1000 --chunk 50`，每 250 步打印一次 error_2 轨迹
- 闸门：连续 `error_2 ≤ 12.5 mHa`（现有实测 rounding 代价 5.22 mHa），且量化后 ≤20 mHa
- 选 `B=135` 的理由：`T=14,389` → chem cost 288.20 M → GM **27.525**，本身就能过 27.50；
  而且它的连续地板（18.408）比 B=129（19.830/21.134）更接近目标

判读：如果 8,000 步后仍停在 ≳16 mHa 且趋势平坦，则"129/135 维基组不可能过量化闸门"
被实测确认，化学线彻底关闭；如果掉到 ≤12.5，则进入 quantize/refine/refit + 15 loader
build + 官方 78,080-shot 验证。

### 8.1 闸门的更精确形式（为什么 B=135 值得跑）

先前把"rounding 代价 5.22 mHa"当成常数，推出所有 B<143 都需要连续 ≤12.5。但 5.22 是
**B=143 这一形状**的实测值（14.777 连续 → 20.000 8-bit），它随角度数变化：

- 角度总数 ∝ `R·B·(N-1)`；B=143 是 1,144 行，B=135 是 1,080 行（−5.6%）；
- 若量化误差近似随机叠加（∝√角度数）→ 代价 ≈ 5.22×√(1080/1144) ≈ **5.07 mHa**；
  若系统性（∝角度数）→ ≈ **4.93 mHa**。

于是"量化后 ≤20 mHa"对应的连续门槛是：

| B | T | GM | rounding 估计 | 需要的连续 e2 |
|--:|--:|--:|--:|--:|
| 143 | 14,728 | 27.3119 | 5.22 | ≤14.8（已达，14.78） |
| 135 | 14,389 | **27.5247** | ~5.0 | **≤15.0** |

所以 B=135 的目标不是 12.5，而是 **≈15.0 mHa**，而 shrink 路径已给 18.408 —— 差 3.4，
这正是 Adam 重训要补的洞。这也解释了为什么这一步值得实测而不是直接关闭。
