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
