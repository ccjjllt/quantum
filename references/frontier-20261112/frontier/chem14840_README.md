# 公开 14,840-Toffoli 化学 loader（`5d5007a75784`）

日期：2026-11-12；来源：`manwithacat/vqcc-apache-public-circuits`（2026-11-12 07:48 UTC
manifest），tiraJoon 的 `5d5007a75784` 组合；同一 4,089-Toffoli loader 也出现在
maoxin123 的 `92fef6dd17f2`（其 npz 与本仓库 `f21b8a87` 逐字节相同）。

## 内容

- `angle_k_0.kmb` … `angle_k_14.kmb`：15 个 ANGLE 电路，每电路 Q=128。
- `submission.npz`：`factorizations/5d5007a75784.npz`（R8/B143/C44、同一张
  `8afd4c67` 表、75 个角度字）。

## 实测（本机官方验证器，全量）

命令：

```bash
uv run python scripts/manual_verify.py dfthcsos artifacts/20261112_frontier/chem14840 \
    --salt 14840-check
```

结果（`uv run` 退出码 0，即 PASS；78,080 shots）：

| 量 | 值 |
|---|---:|
| `status` | PASS |
| `angles_toffoli_per_pass` | 4,089.0 |
| `angles_toffoli` | 8,178.0 |
| `heuristic_toffoli` | 6,662 |
| `toffoli`（T_total） | **14,840.0** |
| `qubits`（Q_total） | **427** |
| `lambda_eff` | **46.907378146123214** |
| `error_1` | 0.019999980000000313 Ha |
| `error_2` | 0.019999997000000033 Ha |
| `Lambda` | 282.9739815978877 |
| `E_gap` | 3.914898003000417 |
| `gp_in_domain` | true |
| `submission_sha256` | `8cd07c7cbb8dae37077713611b3df017a3ef1110fb446465622bc9371ca0509b` |
| **score（成本）** | **297,237,044.95** |

## 相对当前 `f21b8a87`（4,097 loader）

- T_total 14,856 → 14,840（−16，−0.108%）；T_angles 8,194 → 8,178。
- λeff 46.907383278 → 46.907378146（−5.1e-6）。
- 成本 297,557,548.71 → **297,237,044.95**（−320,503.76，−0.108%）。
- 组合（invsqrt 9c708f7b + DQI eae396ba + 本件）本地 GM：
  **25.40482516**（当前 25.39570057，+0.036%）。

## 验证范围

- 本机官方 verifier **全量 78,080 shots PASS**，e1/e2/Λ/E_gap/λeff 逐项记录。
- 未提交 Kaggle；是否以本件替换当前化学件、以及新的提交，需按 main 治理另行确认。
- `E_gap` 3.914898003 仅比门限 3.914898 高 3e-9；该值与是否换 loader 无关
  （由表/角度字决定），当前 `f21b8a87` 同表，风险相同。
