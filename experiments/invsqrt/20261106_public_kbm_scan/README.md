# invsqrt：公开 KMB 镜像复核（2026-11-06/07）

本轮用 Kaggle 数据集的**匿名 API**（无需凭据）复核公开 invsqrt 电路，
确认当前本地基线是否仍是最低公开成本，以及是否出现了 61Q 或更低成本的公开文件。

## 方法

```sh
.venv/bin/python experiments/invsqrt/20261106_public_kbm_scan/scan_public.py --list --download
.venv/bin/python experiments/invsqrt/20261106_public_kbm_scan/scan_public.py --inspect
```

- 数据集：`manwithacat/vqcc-apache-public-circuits`（2026-11-06 14:27 更新）。
- 列表接口 `api/v1/datasets/list/...?pageSize=100`，单文件下载
  `api/v1/datasets/download/...?fileName=...`；两者均可匿名访问。
- 共 4,079 个文件，其中 `circuits/invsqrt/*.kmb` **52 个**，全部下载到
  `artifacts/20261106_public_scan/`（gitignored），逐个读 `num_qubits`、
  `static_toffoli_like`、`num_t_like`。
- 另检查了 2026-11-06 15:36/16:00 更新的 `yoyobar/qcc-local-sota-20261031`
  (`submission/invsqrt.kmb`)、`heliosli/qcc-circuits-live` (`invsqrt.kmb`)、
  `isabe11am00re/qcc-v67s9-circuits` (`invsqrt.kmb`)。

## 结果

52 个公开 invsqrt KMB 的 Q 分布：
`62 (30 个), 63 (11), 64 (1), 66 (1), 68 (1), 76 (1), 82 (1), 89 (1), 93 (1), 95 (1), 140 (1), 145 (1), 208 (1), 258 (1)`。
**没有 61Q 文件。**

62Q 公开文件里静态付费门最少的几个：

| 文件 | Q | ops | static paid | T | 备注 |
|---|---:|---:|---:|---:|---|
| `19a0386ae02f` | 62 | 47,532 | 1,476 | 1 | Syed V9 公开文件；作者报告 97,747.22 |
| `556ee4c852f5` | 62 | 47,251 | 1,466 | 28 | T 更多；quick 验证约 98,207，明显更差 |
| `6eea5d218bd0` | 62 | 47,635 | 1,484 | 28 | 同上族 |
| `6707557ed7b2` | 62 | 47,492 | 1,485 | 28 | 同上族 |
| `heliosli_live` / `yoyobar_submission` | 62 | 47,042 | 1,475 | 1 | 2026-11-06 新公开；与 Syed V9 同静态付费，多 22 条指令/30 个经典位；作者线报 97,746.81 |
| `isabe_v67s9` | 62 | 46,844 | 1,475 | 1 | 与 Syed V9 统计一致 |

本地基线的静态付费门是 **1,457**，比所有公开 62Q 文件都低；完整官方本地 PASS
`score=97,700.776777236`。因此在这批公开镜像和新增 live 数据中没有找到
比本地 nofallback 更低成本或 61Q 的电路。

`556ee4c852f5` 的 quick 验证（`--max-x 4096 --shots-per-x 1`）：

```json
{"status":"PASS","score":98207.06552059187,"num_qubits":62,
 "toffoli_count":1285.526611328125,"t_count":14.469970703125,
 "rotation_count":41.0,"verified_shots":4096}
```

`19a0386ae02f` 的 quick 验证：`score=97804.24337703719`，同样高于本地完整读数
（quick 只用于同口径筛选，不是完整官方成绩）。

## 结论与边界

- 公开镜像、yoyobar/heliosli/isabe 的 2026-11-06 新文件都**没有 61Q**，
  也没有静态付费门低于 1,457 的 62Q 文件。
- 新增的 `heliosli_live` / `yoyobar_submission` 是 62Q、1,475 静态付费，
  与 Syed V9 同量级；本地 nofallback 仍低约 46.5 score。
- 本轮没有提交 Kaggle，没有修改基线；quick 验证不是完整官方验证。
- 公开列表/文件可能继续更新；本记录只固定 2026-11-06 14:27–16:00 的版本。
