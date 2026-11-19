# 比赛契约与研究约束速查

权威契约位于 `data/competition/verifiers/` 与 [官方 Evaluation](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/overview/evaluation)。

## 评分与三任务硬门槛

总分为三项相对官方参考成本改善倍数的几何平均（参考基准见 `scripts/gm.py`）：

```text
improvement_b = reference_cost_b / candidate_cost_b
overall_score = (improvement_invsqrt * improvement_dqi * improvement_dfthcsos) ** (1/3)
```

| 任务 | 成本公式 | 核心契约与已确认边界 |
|---|---|---|
| `invsqrt` | `Q × (Toffoli-like + T/4)` | `x=1..3,133,452`（每输入 64 shots，共 200,540,928 shots），相位误差 ≤ `2^-24 / sqrt(x)` turns；必须恢复输入并清空 scratch。`kickmix` 无 `H` 与 Z 基测量，只有 X 基 `HMR`。 |
| `dqi` | `R(ε+) × Q² × mean_T` | GF(2¹²) 上 RS(4095, 4025) 可逆解码，默认 102,400 shots；`value_errors + phase_errors` 的上置信界 `ε+ < 1/16`，失败惩罚 `R(ε+)` 呈阶跃放大（0 失败时 `R=1.19126`）。 |
| `dfthcsos` | `lambda_eff × T_total × Q_total` | `lambda_eff = sqrt(E_gap·(2·Lambda − E_gap))`。硬门：`error_1 ≤ 20 mHa`、`error_2 ≤ 20 mHa`、`Lambda > 49.0`、`E_gap > 3.914898`。每个 ANGLE 电路 ≤ 128 qubits；官方 `_check_state` 在每个 circuit 后强制非公共 workspace 清回 `\|0>`。 |

## 工程与验证约束

- **macOS 本地环境**：使用 PyPI 原生 `kickmix`（`uv sync` 安装），禁止导入 `data/competition/kickmix/kickmix.so`（Kaggle Linux 专用）。
- **验证分级**：严格区分静态计数、局部子电路检查、默认 salt 官方 verifier 全量 PASS 与 Kaggle 线上提交分数（线上使用秘密 salt，榜单显示截断/舍入至 5 位小数）。
- **获奖源码要求**：主办方要求最终获奖方案能够提供复现同一电路的生成器代码。
- **详细停研复盘**：各研究线历史数据、已否证方向与磁盘清理记录见 [abandoned-research.md](abandoned-research.md)；公开前沿现状见 [public-frontier.md](public-frontier.md)。
