# dfthcsos — `quantize.py --coded2` 对现表 14,840 的检验（no-go）

日期：2026-11-12。工作区 `.worktree/dfthcsos`，分支 `codex/dfthcsos-research`。
产物：`artifacts/20261112_coded2/`（管线副本、npz、日志、venv）。未提交 Kaggle、未 push。

## 问题

当前最优化学件：公开字表 `8afd4c67`（R8/B143/C44）+ 公开 4,089-Toffoli/pass ANGLE loader，
T=14,840（角度 8,178 + heuristic 6,662）、Q=427、λeff=46.907378146、
e1=19.99998 mHa、e2=19.999997 mHa、cost 297,237,044.95。两条误差门各只剩 ~2e-5 mHa。

检验 `quantize.py --coded2`（每 16 地址块内 bit 0 **和** bit 1 都是 4 个低地址位的仿射函数，
即余数 mod 4 约束）能否压低 ANGLE loader T，把成本做到 <292M。

## 结论：no-go（两条独立理由，任一都足以否决）

1. **精度**：coded2 的 mod-4 约束在现表上极贵。用管线自己的 progressive rounding 跑
   **最小子集 8-14（35 列）**，e2 收敛到 **34.60 mHa**（门限 20.0），e1 在最终 h1′ 上
   **22.65 mHa**（门限 20.0）。3-14 ⊇ 8-14，其 e2 ≥34.6 且 e1 实测已 23.28。全部超门。
2. **成本口径**：本仓库 `tensorqrom.py` 复现不出公开的 4,089/pass。把 `8afd4c67` 转成
   signed gauge 后（指标逐位不变）建出 **4,612/pass**，T=15,886、Q=427、cost
   **318,187,850.14**。coded2 在 11 个电路上的**收益上限**约 264 T/pass（528 T），
   最好也只到 **~307.6M**；要 <292M 需再降 1,307 T（−653.5/pass，−14% loader；break-even T=14,578.5）。
   **先补 loader 差距，coded2 才谈得上收益。**

## 已完成（全部为实测）

### 1. 基线复现（官方 `evaluate_words`，与 14,840 回执逐位一致）

`base/current_14840.npz` = main 的 `artifacts/20261112_frontier/chem14840/submission.npz`。

| 量 | 实测 |
|---|---:|
| e1 | 19.999980000 mHa |
| e2 | 19.999997000 mHa |
| Λ | 282.973981598 |
| E_gap | 3.914898003 |
| λeff | 46.907378146 |
| 官方电路 T（`num_toffoli_like` 合计） | 4,089 /pass |
| 官方 cost | 297,237,044.95 |

官方 15 个 `.kmb` 的逐电路 Toffoli：
`292, 287, 287, 287, 268, 268, 268, 268, 268, 265, 266, 266, 266, 266, 267`（合计 4,089，
等于 verifier 的 `angles_toffoli_per_pass`）。

### 2. 静态检查：coded2 不是现成的

`scan.py` 对 75 列、76 个 16-地址块逐列检查仿射性：

- **bit 0 仿射列 = 15…74（恰好 60 列，连续）**，与 `--coded 3-14` 一致；
- **bit 1 仿射列 = 0**（每列最多 1/76 个块偶然成立）。

所以 coded2 必须重新取整，不能"顺带"获得。

### 3. 自有 builder 的基线（成本口径的关键）

`8afd4c67` 的 91,500 个字中有 **19,161 个违反 signed gauge（bit7≠bit6）**，`tensorqrom`
的 `build_circuit` 直接断言失败。用 `onebody.signed_gauge` 转换（改 19,313 个字，
逐行向量不变：最小 |overlap| = 0.9999999999999997；e1/e2/Λ/E_gap/λeff 与转前完全一致）后：

| 表 | T_angles/pass | 逐电路 T | T_total | Q | cost |
|---|---:|---|---:|---:|---:|
| 公开电路（外部 loader） | **4,089** | 292/287/287/287/268×5/265…267 | 14,840 | 427 | 297,237,044.95 |
| signed gauge + `tensorqrom` | **4,612** | 325×4, 301×9, 302, 301 | 15,886 | 427 | **318,187,850.14** |

（heuristic 部分两者相同：6,662 T、Q 贡献相同；差 1,046 T 全在 ANGLE。）
本仓库自己的 (8,143,45) 表同样是 4,613/pass —— 这是 builder 与公开实现的结构差距，
不是这张表的特例。

### 4. coded2 的 one-body 代价（管线自己的 `onebody_quant.quantize_coded`）

每子集单独重算：33 段 progressive freezing，L-BFGS 300 iters/stage，coded bit 0 + coded2，
在现 h1′ 上重建 76 行 one-body 字；e1 由官方 `evaluate_words` 复核。

| coded2 子集 | 列数 | 覆盖电路 | e1 (mHa) | ≤19.9？ |
|---|---:|---|---:|---|
| 无（仅 coded bit 0） | 0 | — | **10.54** | 是 |
| 5-10 | 30 | 6–10 | **17.33** | 是 |
| 8-14 | 35 | 9–14 | **19.01 / 19.34**（两次，`following` 块不同） | 勉强 |
| 3-14 | 60 | 4–14 | **23.28** | **否** |

### 5. coded2 的 two-body 代价（真正的 `quantize.py`，子集 8-14）

命令（见"复现"）：`--brot 8 --coded 3-14 --coded2 8-14`，33 段 fine schedule，
400 Adam steps/stage + 800 final，κ=5e-5，f32，CPU。日志 `logs/c2_8-14_v2.log`：

| 阶段 | frozen | error_2 (mHa) |
|---|---:|---:|
| 0 | 0.05% | 328.28 → 45.22 |
| 2 | 0.25% | 64.41 → 35.08 |
| 6 | 3.5% | 64.36 → 32.66 |
| 10 | 14% | 50.67 → 33.31 |
| 17 | 52% | 35.50 → 34.32 |
| 33 | 100% | 34.62 → **34.60** |

stages 5–32 一直平在 32.6–34.6，已经是约束地板（不是步数不够）。D(w) 0.02 → 5.81，
说明 refit 同时在用权重吸收误差。

### 6. 合并候选（8-14）的官方指标

one-body 行用最终 h1′（= quantize 输出的 w）重建，与两-body 字拼接后 `evaluate_words`：

| 量 | 实测 | 门限 |
|---|---:|---|
| e1 | **22.653 mHa** | ≤20 |
| e2 | **34.602 mHa** | ≤20 |
| Λ | 290.583 | >49 |
| E_gap | 9.5737 | >3.914898 |
| λeff | 73.975 | （≈46.9 才持平） |

λeff 高是因为**没有跑 `refine.py`**（偏移 W 未重新优化；w 的 refit 把 E_gap 从 3.9149 抬到
9.57 是已知效应）。由于 e1/e2 已双双超门，refine 不影响结论，故未执行。

## 未完成（明确记录，不当作通过）

- **coded2 表的 loader T 未实测**：`finalize.py` 的电路构建被中止（按要求）。因此 coded2 的
  真实 T 只有设计上的**上限**：coded2 把 5 个字的 bit 1 加进 coded 输出组，参考本仓库
  `finish_845.log` 的 245→221 products（5 个 coded 输出省 24 T/电路），8-14（6 个电路）
  ≤144 T/pass ≤288 T；3-14（11 个电路）≤264 T/pass ≤528 T。
- **5-10、3-14 的 e2 未跑**。3-14 ⊇ 8-14 ⇒ e2(3-14) ≥34.6（约束集嵌套，严格）。
  5-10 与 8-14 互不包含，其 e2 未测，但 e1 已 17.33，且它无法解决成本口径问题。
- **`--coded 2-14` / `4-14` 平移对照未跑**：解析上界已否决 —— 平移最多把电路 3 纳入
  coded 组（~24 T/pass = 48 T = 0.3% of T），远低于 1.7%；`4-14` 去掉 batch 3 反而更差。
- **官方全量 verifier 未跑**：没有任何候选同时过 e1/e2；自有 builder 基线已在 318M。
- **refine.py / refit_weights.py 未跑**（见上）。

## 复现

```bash
cd .worktree/dfthcsos
# 基线指标 + 静态检查（bit0/bit1 仿射列）
artifacts/20261112_coded2/venv/bin/python artifacts/20261112_coded2/scan.py \
    artifacts/20261112_coded2/base/current_14840.npz
# signed gauge + 自有 builder 的逐电路 T
uv run python artifacts/20261112_coded2/build_count.py \
    artifacts/20261112_coded2/base/current_14840_signed.npz --coded 3-14
# one-body 的 coded2 代价
artifacts/20261112_coded2/venv/bin/python artifacts/20261112_coded2/onebody_probe.py \
    artifacts/20261112_coded2/base/current_14840_signed.npz --coded2 8-14 \
    --out artifacts/20261112_coded2/runs/c2_8-14/onebody.npy
# 真正的 coded2 取整 schedule（约 24 min，CPU）
DFTHC_DATA=$PWD/data/competition artifacts/20261112_coded2/venv/bin/python \
    artifacts/20261112_coded2/pipeline/quantize.py \
    artifacts/20261112_coded2/base/current_14840_signed.npz \
    artifacts/20261112_coded2/runs/c2_8-14/q.npz --brot 8 --coded 3-14 --coded2 8-14 \
    --free "0.9995,0.999,0.9975,0.995,0.99,0.98,0.965,0.95,0.925,0.9,0.86,0.82,0.77,0.72,0.66,0.6,0.54,0.48,0.42,0.36,0.3,0.25,0.2,0.16,0.12,0.09,0.065,0.045,0.03,0.02,0.012,0.006,0.0" \
    --stage-steps 400 --final-steps 800 --kappa 5e-5 --lbfgs-until 0
# 合并 + 官方指标（e1/e2/Λ/E_gap/λeff）
DFTHC_DATA=$PWD/data/competition artifacts/20261112_coded2/venv/bin/python \
    artifacts/20261112_coded2/assemble.py \
    artifacts/20261112_coded2/base/current_14840_signed.npz \
    artifacts/20261112_coded2/runs/c2_8-14/q.npz \
    artifacts/20261112_coded2/runs/c2_8-14/onebody2.npy \
    artifacts/20261112_coded2/runs/c2_8-14/candidate.npz
```

## 环境与管线差异（必须记录）

- 本机无 starter kit（`dfthc.df_thc_sga`、`dfthc.train_df_thc_sga.Initialize`）、无 jax。
  为离线运行，在 `artifacts/20261112_coded2/pipeline/dfthc/` 放两个**替身**：
  `df_thc_sga`（按官方 verifier 的 error_2 定义用 jnp 实现 `Compute_H2_sqrt` /
  `Compute_H2_residual_after_symmetry_shift`）与 `train_df_thc_sga.Initialize`
  （`load_reference` + 固定 shift + `tril`）。验证：现表上 20.000007 mHa（官方 19.999997，
  f32），x64 下逐位一致；coded2 表上替身与官方 `evaluate_words` 相差 0.001 mHa（f32 舍入）。
- `quantize.py` 原本硬编码 `encode.log_depth_tree(N)`；`8afd4c67` 的树是**同一棵树的另一种边序**
  （边集合相同、顺序不同）。副本改为优先读结构 npz 的 `tree_edges` —— 不改的话角度会被重编码到
  另一棵树，整轮结果无效（本次踩过一次，已作废并重跑）。
- 独立 venv `artifacts/20261112_coded2/venv`（jax 0.12.0.1 + optax 0.2.9 + kickmix 1.0.0，CPU），
  不改共享 `.venv`。
- 预算：GPU 日志为 1000 steps/stage + L-BFGS 到 18%；本机用 400 steps/stage、纯 Adam。
  这是**缩短的预算**：只影响 recovery 的绝对水平，不影响"约束地板 ≈34.6 mHa"的结论
  （stages 5–32 平坦）。

## 产物

- `base/current_14840.npz`、`base/current_14840_signed.npz`：现表原样 / signed-gauge 版本。
- `runs/c2_8-14/{q.npz, onebody.npy, onebody2.npy, stage1.npz, candidate.npz}`。
- `runs/probe_{3-14,5-10,8-14}.npz`：一次性（无 refit）投影的对照表（e2 657–953 mHa，
  只作"约束有多贵"的上界参考，不是管线结果）。
- `logs/`：`signed_count.json`、`c2_8-14_v2.log`、`cold_none.log` 等全部日志。
- 脚本：`scan.py`（指标 + 仿射列）、`build_count.py`（逐电路 T）、`onebody_probe.py`
  （one-body coded2 代价）、`probe.py`（一次投影）、`round_c2.py`（曲率加权一次投影 + w refit）、
  `cold_round.py`（连续 refit → 投影，失败的口径实验，保留作记录）、`assemble.py`、`finalize.py`。
