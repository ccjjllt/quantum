# 20261115 公开 27.31 升级

## 提交回执

| ref | 内容 | 状态 | Public Score |
|---:|---|---|---:|
| 58349843 | `maoxin123/qcc-v27-4033-toffoli-coded-word-chemistry` v2 的 Kaggle 输出 | COMPLETE | **27.30661** |
| 58350759 | HW-26 invsqrt `1ba197b02771` + DQI `821bf8d1` + maoxin 4,033 chemistry | COMPLETE | **27.31193** |

两版 ZIP 均为 18 文件。MCP 名次：提交时 159 / 3053，2026-11-15 复核 175 / 3055。`58349843` 大小 49,292,293 B；`58350759` 大小
49,292,319 B，SHA-256
`46d53bde0a8b3e6e6aed2693df3a12f540eeb258da75588cbfb99c21f369c933`。

## 58349843（COMPLETE，27.30661）

来源：`maoxin123/qcc-v27-4033-toffoli-coded-word-chemistry` v2 的 Kaggle 运行输出
（Apache-2.0，credit 见原 notebook）。三件：

| Task | 文件 | Q | 官方验证 | cost |
|---|---|---:|---|---:|
| invsqrt | `e46d90c3`（Asterios/Heliosli free-CZ，Syed 46Q 线） | 46 | PASS | 78,719.529147 |
| DQI | `821bf8d1`（Syed v12 + Ertugrul cutoff18 + Areeb 241 retained products） | 889 | PASS，0/0 errors，102,400 shots | 360,209,905,486.02 |
| chemistry | 4,033-Toffoli/pass coded-word loaders + weights | 427 | PASS，78,080 shots | 294,991,455.82 |

本机默认 salt GM 27.306613；实际 public **27.30661**（COMPLETE），比上一版
58299045（27.00209）高 **+0.30452**。

## 58350759（COMPLETE，27.31193）

只把 invsqrt 换成 **HW-26 `1ba197b02771`**（manwithacat/vqcc-hedge-wizardry v27，
46Q，78,673.569211），DQI 和化学保持不变。

- HW-26 独立官方验证（自建 Kaggle notebook `qcc-hw-26-invsqrt-verify`）：
  未修改 `verifier.py`，**200,540,928 shots PASS**，score 78,673.56921101942，
  worst/tol 0.9986660009，circuit SHA-256 与源件一致。
- 组合 GM **27.31193**（+0.00532），MCP 回执 **COMPLETE，public_score 27.31193**。
- 公开可复现上限为 27.31214（再把化学 npz 换成 `e52b7cdd`，仅 +0.0002）。

## 验证范围

- `58349843`：由 maoxin123 notebook 的 Kaggle 运行完成三件官方验证；本仓库未重跑
  三件全量。
- `58350759`：invsqrt HW-26 由本仓库在 Kaggle 上独立重跑官方 verifier；DQI 和化学
  直接复用同一字节的 `821bf8d1` / `3f864a7a`，其官方 PASS 记录来自 maoxin 运行。
- 未在本机运行大电路模拟；所有组装/验证/提交均在 Kaggle 或 Kaggle API 上完成。

## 来源与归属

- 46Q invsqrt：Syed Asad Ali 的 own-circuit builder，Ali Haydar Özdağ 64-row table，
  Asterios/Heliosli dead-write/free-CZ，manwithacat HW-26。Apache-2.0。
- DQI：Syed Asad Ali v12 decoder，Ertugrul Ozer cutoff 18，Areeb Ali retained products。
  Apache-2.0。
- chemistry：maoxin123 4,033 coded-word loaders/table，Lera (marculera) 表和
  prvsiyan/Atakan/Heliosli 权重线。Apache-2.0/CC0，具体见原数据集。
- 完整来源、版本和讨论链接见
  `experiments/frontier/20261115_upgrade/frontier_scan.md`。
