# R5/R4 训练栈搭建与首批拟合轨迹

2026-11-06，分支 `codex/dfthcsos-research`。目标：按上一轮结论，
搭建官方 starter-kit + Lera V7 的 U/W 训练栈，尝试把 R5/B135/C70
或 R4/B131/C83 从成本预算变成可量化候选。

**结论：训练栈已搭好，但本机 CPU 上的首批拟合没有达到 20 mHa 门限，
因此本轮仍没有新的可提交候选。** 这不是算法否证；它说明需要公开
Lera 配方中的 60k–240k 次迭代/GPU 级算力，当前会话只有 CPU。

## 1. 已搭好的环境

- 官方 starter kit V4：`artifacts/20261106_high_yield/starter_kit/`
  （Kaggle `sohier/verifiable-circuit-compilation-starter-kit`，
  161 MB；`dfthc`、`starter`、`verifier` 可用）。
- Lera V7 完整源码：`artifacts/20261106_high_yield/lera_data/dfthc_refit/`
  （含 `compact_seed.py`、`shrink.py`、`quantize.py`、`refine.py`、
  `fastfit.py`、`tensorqrom.py`）。
- JAX CPU 0.12.0.1 + optax，通过
  `uv run --no-project --with jax --with optax ...` 的临时环境使用，
  未改共享 `.venv`。
- 已确认 `dfthc.train_df_thc_sga.Initialize` 和
  `fastfit.problem/error2/lbfgs` 在本机可导入、可运行；目标矩阵
  构建耗时约 0.4 s，单次 error2 约 0.29 s。

## 2. 首批 seed 与精确合并

NumPy 版 Lera `df_init.seed`（pivoted-Cholesky leaves + balanced
k-means + simultaneous OMP）在目标形状上的初始 error_2：

| 形状 | seed error_2 |
|---|---:|
| 5/135/70 | 793.6 mHa |
| 5/143/70 | 748.5 mHa |
| 7/143/50 | 518.2 mHa |
| 6/143/59 | 510.6 mHa |
| 5/135/70（eig leaves, roundrobin） | 1849.7 mHa |

这些是**共享基初始化**的误差，不是候选。Lera 公开配方需要先用
240k 次预拟合把 compact seed 降下来；本机没有跑完这个量级。

另一条路径是精确合并当前 V9 的 8 个组到 7 个组：
`merge_seed.py` 输出 `7x286x90`，用 starter 的 packed target 复算
error_2 = **19.99999 mHa**，与 V9 完全一致。该形状 A=2078，
超过 11 位地址和 128 比特限制，只能作为 shrink 的中间态。

## 3. Lera shrink 的首批轨迹

命令（短预算，仅用于看趋势）：

```sh
DFTHC_DATA=... DFTHC_STARTER=... \
uv run --no-project --with jax --with optax --with numpy --with scipy --with h5py \
python .../dfthc_refit/experiments/shrink.py \
  merged_7x286x90.npz shrink7 286x90,250x80,220x70,180x60,143x50 \
  --merged --pre 100 --fade 20 --fit 60 --final 100 --save 143x50
```

实际输出（每步 20–100 次 refit，远低于公开配方的 60k）：

```text
start 7x286x90: 20.000 -> 18.019 mHa
286x90 fades: 17.918 -> 17.667 mHa
250x80: 306.477 -> 51.994 mHa
220x70: 481.123 -> 81.793 mHa
180x60: 626.693 -> 84.548 mHa
143x50: 716.515 -> 82.741 mHa
```

短预算下 143x50 只到 82.74 mHa；随后又跑了一次更长的 shrink
（每步 2,000 次、最后 4,000 次）：

```text
7x286x90 pre-fit: 20.000 -> 14.345 mHa
250x80: 334.054 -> 17.306 mHa
220x70: 438.669 -> 21.104 mHa
180x60: 583.312 -> 25.844 mHa
143x50: 598.923 -> 29.357 mHa
```

250x80/220x70/180x60 的 A 分别为 1826/1616/1336，加上 cache 后
超过 128 qubit，**不是合法最终形状**；唯一合法的 143x50 仍为
29.357 mHa，离 20 mHa 还差 9.4 mHa。对保存的 7x143x50 再做
连续 L-BFGS 也只能到 28.4 mHa（6,000 次）；把 C 从 50 加到 55
（rank 385）训练 3,000 次也只到 27.65 mHa。量化只会在这个连续
误差上再加误差，所以没有继续跑 `quantize.py`。

R7/B143/C50 的预算收益只有 1.86%，即使训成，λ 稍升就可能打平；
当前这个“精确合并 + shrink”的 seed 盆地也不够好。公开 Lera
配方从 compact seed 或公共 seed 出发，用 60k–240k 次迭代和
A100 才能到 13–20 mHa；本机 CPU 的 6 it/s 无法在本轮达到。

## 4. 当前阻塞

- 公开 Lera 成功路径使用 A100；本机 CPU JAX 在 7x143x50 上约
  6 it/s。60k 次迭代约 3 小时/步，且我们的 seed 仍差 8 mHa。
- 更激进的 R5/B135/C70、R4/B131/C83 需要 compact seed 的
  240k 预拟合或更强的 GPU 训练；本机没有完成。
- 这不是用户决策问题，而是算力/训练时长问题。若要在本会话内
  产出真实候选，需要 GPU 环境或允许数小时到一天的 CPU 训练。

## 5. 下一步（有算力时）

1. 用 `compact_seed.py` 在 R5/B135/C70 上跑 240k 预拟合，或把
   公开 `refit_845.npz` 精确合并到 R7/R5 后按 Lera 配方
   （60k 级）shrink。
2. 对连续结构跑 `quantize.py`（8-bit，staged rounding + Adam/LBFGS）
   和 `refine.py`（one-body polish + λ refit）。
3. 用 `build.py`/`tensorqrom.py` 发射 15 个 loader，手动跑官方
   78,080-shot 验证；只有 PASS 且 score < 299,672,935.08 才算
   新候选。
4. R5/B135/C70 仍是首选（PSD 7.55，预算 5.27%，λ 可升 5.57%）；
   R4/B131/C83 是激进目标。

## 6. 证据文件

- `experiments/dfthcsos/20261106_train_r5/seed_numpy.py`：NumPy seed。
- `experiments/dfthcsos/20261106_train_r5/merge_seed.py`：8→7 精确合并。
- `experiments/dfthcsos/20261106_train_r5/fit_probe.py`：连续 packed-pair
  L-BFGS。
- `artifacts/20261106_high_yield/train_r5/`：seed、merge、shrink、
  fit 的 NPZ 与日志。
- 本文件中的数值均为局部训练诊断；没有新的官方验证 PASS。

## 7. R6/B143/C59 追加结果与 Pareto 结论（2026-11-07）

按评审建议，继续在 R6/B143/C59（A=934，合法）上训练，并试了三种 seed：

| seed | 最终 6x143x59 连续 error_2 |
|---|---:|
| V9 8 组两两精确合并（6x286x90） | 未跑完；144x50 同级路径 29.36 mHa（R7） |
| Lera `eigen_9x180x90` 合并到 6 组（6x360x180） | **33.30 mHa**（30k 连续 L-BFGS） |
| Lera `cluster_27x60x30` 合并到 6 组（6x300x150） | **37.41 mHa**（shrink 到 143x59 + 6k final） |

`cluster` 路径的逐级连续 error_2（括号内为 A 和 qubit 可行性）：

```text
6x300x150: 7.184 mHa   (A=1876, 超 128Q)
6x260x130: 10.234 mHa  (A=1636, 超 128Q)
6x220x110: 15.019 mHa  (A=1396, 超 128Q)
6x180x90:  23.744 mHa  (A=1156, 128Q 恰好可行，但 T≈15.5k，比当前更差)
6x150x75:  35.355 mHa  (A=976, 116Q 可行，T≈14.8k，仅约 1.3% 预算)
6x143x59:  37.410 mHa  (A=934, 108Q 可行，T≈14.6k，约 2.5% 预算)
```

**Pareto 结论**：20 mHa 连续门限在 180x90 附近才达到（23.7 mHa，仍差
3.7 mHa），而该形状的 T 比当前更大，没有资源收益；真正有收益的
150x75/143x59 已经在 35–37 mHa，离 20 mHa 差 15 mHa 以上。
在 8-bit、公开 seed 和本机 CPU 预算内，**R6/R5 的 T×Q 预算与
20 mHa 连续门限没有交集**；这不是再跑几次 L-BFGS 能补上的差距。

公开 Lera 的 8-bit 成功形状是 (9,143,46)，A=1363，本身大于当前
1220，不能带来地址/cache 收益。R6/R5 需要新的 seed/训练方法或
不同的误差分配，而不是继续同一 shrink。

因此本轮仍没有新候选；唯一已验证收益仍是 C44 refit 的 168.35 分
（0.000056%）。R5/B135/C70、R4/B131/C83 的 5.3%/8.8% 仍是
**未实现预算**，且当前证据表明同一 8-bit 训练路线难以兑现。

## 8. 形状成本敏感性：更保守的 B160/C70 并不是收益

评审建议的“更保守形状”需要先核对官方成本，否则会训练一个
**比当前更差**的分解。R6 的 B/C 扫描（`Tprep` 用官方
`SpinFreeData_V1`，ANGLE products 固定 3010/遍，低 cache 取完整 11）：

| R/B/C | A | T | T×Q 相对当前 |
|---|---:|---:|---:|
| 6/143/59 | 934 | 14,592 | **+2.50% 收益** |
| 6/143/60 | 934 | 14,651 | +2.10% |
| 6/143/62 | 934 | 14,768 | +1.32% |
| 6/143/65 | 934 | 14,946 | +0.13% |
| 6/160/59 | 1,036 | 15,484 | **−3.46%（更差）** |
| 6/160/70 | 1,036 | 16,263 | −8.92% |
| 6/170/59 | 1,096 | 15,624 | −4.40% |
| 6/180/59 | 1,156 | 16,114 | −7.92% |
| 6/143/70 | 934 | 15,239 | −1.82% |

原因：B=143 处在 cache 阶梯的低位；B→160 使 A 从 934 到 1036，
cache 增加 5 个/槽（约 150 T/遍），同时 C 增加 prepare，直接把
2.5% 的收益吃光。**只有 B≤144、C≤65 的窄区域有正收益**；
B160/C59、C70/C80 都不是收益目标。

而训练 Pareto 显示：C≈90/B180 才接近 20 mHa（23.74），
C≤65 的收益区域在 30–37 mHa。**收益区域与 20 mHa 门限没有交集**，
这不是换一个更保守的 B/C 就能解决的；需要新的训练方法/更强
seed，或接受“无收益但可过门”的形状（R9/B143/C46 等）。

因此本轮不再把 CPU 时间投入到 B160/C70 这类负收益形状。

## 9. “Grow-then-refit” 也不同：局部盆地没有逃出

作为与 shrink 不同的方法，把已训练的 6x143x59（33.30 mHa）用随机
U 向量和零权重扩到 6x180x90（更大的容量），再跑连续 L-BFGS：

```text
start 33.303 mHa
1,000 iter: 32.773 mHa
2,000 iter: 32.616 mHa
```

零权重扩展不改变函数；L-BFGS 仍停在同一个局部盆地，没有出现
向 20 mHa 的快速下降。要继续只能做随机 kick/多 seed 重启，但
180x90 本身 T 比当前更大，没有资源收益；它只能作为中间态，而
当前证据不支持它能稳定降到 20 mHa 再 shrink 到收益形状。

因此本轮不再把 CPU 时间投入到同一 8-bit 训练路线的 grow/shrink。

## 10. Compact-seed 长预拟合：17k 次后仍 35.3 mHa

按评审建议，换用 Lera compact seed（NumPy 版 `df_init.seed`，
R6/B143/C59 初始 510.63 mHa）做连续 L-BFGS：

```text
start 510.631 mHa
1,000 iter:  97.718 mHa
5,000 iter:  50.074 mHa
9,000 iter:  41.724 mHa
13,000 iter: 37.631 mHa
17,000 iter: 35.305 mHa
20,000 iter: 34.144 mHa  (完成)
```

下降在 13k 后明显变慢（约 0.0005 mHa/iter）。20k 实际为 34.14 mHa，240k 也未必能稳定到 20 mHa 以下；而 240k 在本机
CPU（约 3.7 it/s）需要约 **18 小时**。Lera 公开的 240k 预拟合是
在 A100 上、且形状为 (9,180,90) 的更大容量结构；R6/B143/C59
的 B/C 更紧，不能直接套用其收敛结论。

至此，四条合法训练路线（V9 合并、eigen、cluster、compact seed）
在 R6/B143/C59 上都停在 33–37 mHa（compact 17k 为 35.3），
离 20 mHa 门限 13 mHa 以上。没有一条能在本机 CPU 预算内完成
quantize.py → refine.py → build.py → 官方 78,080-shot 验证。

## 11. Grow-then-50k 的后续：6x180x90 到 25.80 mHa

上一节 2k 时的 grow-then-refit 只到 32.62 mHa，但继续跑到 50k
（约 3.7 小时）后实际到达：

```text
start 33.303 mHa
2,000 iter:  32.616 mHa
50,000 iter: 25.800 mHa
```

这是目前合法（128Q）形状上最低的连续误差，但 6x180x90 的 T 比
当前更大，本身没有资源收益；它只能作为继续 shrink 到
R6/B143/C59 的更好 seed（25.8 而不是 29–37）。下一步用细粒度
curriculum（180x90→170x85→160x80→150x75→143x59）尝试把它带到
20 mHa 以下。

## 12. 25.8 mHa 的 180x90 seed 也不能承受 shrink

用 `--kappa 0`（只优化 error2）从 25.80 mHa 的 6x180x90 继续
细粒度 shrink：

```text
6x180x90: 25.800 -> 25.697 mHa
170x85 x0.5: 32.460 -> 28.775 mHa
170x85 x0.2: 34.237 -> 31.370 mHa   (下一步 fit 前停止)
```

仅仅 180x90→170x85 的 fade 就把误差从 25.8 推到 28.8–31.4 mHa；
到 143x59 还要再减 B 17%、C 30%。因此即使 180x90 达到 25.8 mHa
（合法但 T 比当前更大、无收益），它也不能作为到收益形状的 seed。
R6/B143/C59 在 8-bit 下仍没有 <20 mHa 的可行路径。
