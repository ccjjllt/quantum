# Public Frontier dfthcsos (`c1321df2`)：谱折点约束审计与解析切空间重拟合

日期：2026-11-08（北京时间）；分支 `codex/dfthcsos-research`。
固定输入为主仓库下载的 Public Frontier 25.14222 化学产物，本工作区只读链接 `artifacts/20261108_public_frontier/release/dfthcsos/`。

## 1. 公开前沿 `c1321df2` 相比 Syed V9 (`c76d568c`) 的精确差异

Public Frontier 使用的 15 个 `angle_k_0.kmb` .. `angle_k_14.kmb`、`U`（形状 `(8, 143, 76)`）、`tree_edges`（形状 `(75, 2)`）、`angle_words`（形状 `(1220, 75)`）、`H1_I` 和 `Hsym_lower` 与 Syed V9 **逐字节完全一致**（$Q = 427$，$T = 14,966.0$）。全部成本下降（$\lambda_{\text{eff}}$ 从 `46.893662078701` 降至 `46.891275464716`，官方本地分数从 `299,673,103.43` 降至 `299,657,851.81`，净降 **15,251.61**）仅来自 `submission.npz`（SHA-256 `c1321df252e15ccd92f5086048ad6e4c376862bec5a4dd58d603edbbc3623cf1`，源自 Maoxin123 V2）中的权重张量 `W` 与 `H2_I`：

1. **稀疏支撑扩展**：
   - `W`（形状 `(8, 143, 44)`，共 50,336 项）：精确零元数从 Syed V9 的 `9,498` 增加到 `9,787`（平滑非零坐标 `40,549` 项）。
   - `H2_I`（即 $w_B = W_{\rho, c} + \sum_b w_{b, \rho, c}$，形状 `(8, 44)`，共 352 项）：有 `3` 项被精确钉在 $|w_B| \le 2.22 \times 10^{-16}$ 的 L1 折点上（平滑非零坐标 `349` 项）。
2. **一阶算符 $h_1'$ 的零特征值折点钉扎（Spectral Kink Pinning）**：
   - 由于 $\lambda_{H_1} = \sum_{j=0}^{75} |\lambda_j(h_1')|$ 在 $\lambda_j = 0$ 处具有非光滑绝对值折点，`c1321df2` 将第 59 个特征值 $\lambda_{58}(h_1')$ 精确推到了零点（$\lambda_{58} = +1.143816 \times 10^{-13}\text{ Ha}$，次小特征值 $|\lambda_j| = 2.572 \times 10^{-3}\text{ Ha}$）。
3. **三道不等式门限裕度收紧**：
   - 将 Syed V9 的 `1.0e-8 Ha`（`error_1`, `error_2`）与 `1.0e-7 Ha`（`E_gap`）裕度收紧至 `[2.361e-10, 2.239e-10, 2.392e-10] Ha`。

## 2. 精确解析 Jacobian、KKT 乘子与切空间重拟合（已实现并官方本地验证 PASS）

在 [`nullspace_refit.py`](nullspace_refit.py) 中，我们针对 `40,549` 个 `W` 平滑坐标与 `349` 个 `H2_I` 平滑坐标推导并实现了 $(\lambda_{\text{eff}}, \text{error}_1, \text{error}_2, E_{\text{gap}}, \lambda_{58}(h_1'))$ 的精确解析梯度（利用 Hellmann-Feynman 定理处理 $h_1'$ 特征值与 QROM 特征向量匹配算子）：

- **四重约束流形上的精确 KKT 乘子**：
  $$\nabla \lambda_{\text{eff}} \approx -0.248931\,\nabla(\text{error}_1) - 345.150121\,\nabla(\text{error}_2) + 5.591391\,\nabla(E_{\text{gap}}) + 0.160913\,\nabla(\lambda_{58})$$
  - 每放宽 $1\text{ Ha}$ 的 $\text{error}_2$ 可降低 $345.15$ 的 $\lambda_{\text{eff}}$，每降低 $1\text{ Ha}$ 的 $E_{\text{gap}}$ 可降低 $5.591$ 的 $\lambda_{\text{eff}}$。
  - 在四重约束切空间上，`c1321df2` 仍存在非零投影梯度 $\|\text{Proj}_{\ker J}(\nabla \lambda_{\text{eff}})\|_2 = 0.129558$。
- **切空间步进 + Newton 流形回缩（Retraction）实验结果**：
  1. **严守 `c1321df2` 原有门限裕度**（仅沿切空间方向步进 `step = 4.0e-7` 并做 4 步精确 Newton 回缩）：$\lambda_{\text{eff}}$ 降至 `46.891275419343`（$\Delta \lambda_{\text{eff}} = -4.537 \times 10^{-8}$，$\Delta\text{score} = -0.2900$）。
  2. **切空间步进 + 安全裕度收紧至 `2.5e-11 Ha`**（仍大于 `float64` 机器精度 $10^5$ 倍，且通过 `verify.py` 内置 100 位 `Decimal` 复核）：生成候选 `artifacts/20261108_public_frontier/dfthcsos_refit/submission.npz`（SHA-256 `b9eced3e7f19811bcbd4587f72a28533aa7d19ecf379d3565a7254bdfffe4163`）。

| 指标 | Syed V9 (`c76d568c`) | Public Frontier (`c1321df2`) | 同裕度切空间步 | 本轮 Refit (`b9eced3e`) |
|---|---:|---:|---:|---:|
| `error_1` (mHa) | 19.999989995 | 19.999999764 | 19.999999764 | **19.999999975** |
| `error_2` (mHa) | 19.999989995 | 19.999999776 | 19.999999776 | **19.999999975** |
| `E_gap` (Ha) | 3.914898100 | 3.914898000239 | 3.914898000239 | **3.914898000028** |
| $\lambda_{58}(h_1')$ (Ha) | $-1.19 \times 10^{-4}$ | $+1.144 \times 10^{-13}$ | $+1.117 \times 10^{-13}$ | **$-8.523 \times 10^{-16}$** |
| `Lambda` | 282.809656049 | 282.781076407 | 282.781075863 | **282.781075042** |
| `lambda_eff` | 46.893662078701 | 46.891275464716 | 46.891275419343 | **46.891275349493** |
| `T` / `Q` | 14,966 / 427 | 14,966 / 427 | 14,966 / 427 | **14,966 / 427** |
| 官方本地 78,080-shot score | 299,673,103.4280 | 299,657,851.8143 | 299,657,851.5244* | **299,657,851.0780** |

\*注：`同裕度切空间步` 为 `metrics.json` 中的精确算术评估值；`Public Frontier (c1321df2)` 与 `本轮 Refit (b9eced3e)` 均在同一本地 salt `local-frontier-refit-20261108` 下完成完整 78,080-shot 官方本地验证 **PASS**（日志分别保存在 `artifacts/20261108_public_frontier/dfthcsos_refit/verify_baseline.log` 与 `verify.log`），净降 **0.7363** 分。这同时证明：在固定当前 15 个 `angle_k_*.kmb` 角度字（`8/143/44`）的前提下，`c1321df2` 距离光滑子流形上的局部 KKT 极小值仅剩约 $10^{-7}$ 量级的微调空间。

## 3. 下一步实质降本方向

既然固定 `(8, 143, 44)` 角度字的连续权重 refit 已逼近 KKT 理论极限，后续化学分数的实质跃升（$>1\%$）只能来自改变 $T \times Q$ 或改变已量化的 `angle_words`：

1. **训练紧凑秩形状 `R5/B135/C70`（首选）与 `R4/B131/C83`**：
   - 按 `SpinFreeData_V1` 精确成本模型，将 `R=8, B=143, C=44`（$A=1220$，11 位地址，$T=14,966, Q=427$）改为 `R=5, B=135, C=70`（$A=751$，10 位地址，$RC=350$，PSD 下界 `7.552 mHa`），$T$ 降至约 `14,177`（$T \times Q$ 降 **5.27%**），允许 $\lambda_{\text{eff}}$ 上升达 **+5.57%**（打平线 $\lambda_{\text{eff}} \le 49.50$）。
2. **多折点（Multi-Kink）一阶特征值钉扎与角度字离散坐标下降**：
   - `c1321df2` 通过将 1 个 $h_1'$ 特征值（$\lambda_{58}$）钉在 0 获得了显著的 $\lambda_{H_1} - E_{\text{SOS}}$ 折点收益；当前次小特征值 $|\lambda_j|$ 为 `2.57 mHa`、`3.29 mHa`。若结合离散 `angle_words` 的 $\pm 1\text{ LSB}$ 坐标搜索（只挑不影响 shared planner 195 products 的自由位）与上述解析 Jacobian 投影回缩，可将第 2、第 3 个小特征值推向 0 折点。

## 4. 手动复现命令

```bash
# 1. 运行解析切空间重拟合生成 dfthcsos_refit/submission.npz 与 metrics.json
/Users/zhaohuaxiang/ccjjllt/quantum/.venv/bin/python \
  experiments/dfthcsos/20261108_frontier_refit/nullspace_refit.py

# 2. 手动运行完整 78,080-shot 官方本地验证
/Users/zhaohuaxiang/ccjjllt/quantum/.venv/bin/python \
  scripts/manual_verify.py dfthcsos \
  artifacts/20261108_public_frontier/dfthcsos_refit \
  --salt local-frontier-refit-20261108
```
