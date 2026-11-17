# 2026-11-18 候选包：invsqrt `563d0583` + DQI `575b043f` + chem（18 成员官方 PASS）

**状态：已端到端官方验证 PASS，等待提交名额（UTC 00:00 = 北京 08:00 重置）。**
内核 `qingyu1232/qcc-integrator-281806` v1，manifest
`experiments/frontier/20261117_deep/integration/members_281806_correct.json`。

## 三条腿（installer 实测 JSON，未改动官方 verifier）

| 腿 | 件 | 官方 cost | Q | T | 错误 |
|---|---|---:|---:|---:|---|
| invsqrt | `563d0583` | **74,560.90687312803** | 44 | 1,454.0008 + T/4 | 200,540,928 shots PASS |
| DQI | `575b043f` | **346,409,762,292.7187** | 890 | 367,116.057 | 0 value / 0 phase |
| chem | `a73b25d2` + 15 loaders | **294,643,137.73357135** | 427 | 14,706 | PASS, λ_eff 46.9217168 |

几何平均 **GM = 28.18065942104198**（`scripts/gm.py` 复核 28.18066）。

zip：85,016,504 B，sha256
`2271b861eb44628f45e2bcbf836c1f41b8bc34446389849776817328ba800eb5`
18 成员；`dqi.kmb` sha `575b043f4fee91a0fc3a9fd6fc1e9290e7b2a0669cae79886be2bf999f7ec155`。

## 提交

```bash
kaggle competitions submit -c google-verifiable-quantum-circuit-compilation \
  -k qingyu1232/qcc-integrator-281806 -v 1 -f submission.zip
```

提交前确认 receipt 中 `dqi.value_errors == 0`（本包已满足）。

## 更正说明

前一份回执（`submissions/20261117_inv563d0583/`）声称 GM 28.1806，但实测 zip 里装的是
`957d6733`（默认 salt 1 个 value error，GM 28.1310）。本包才是真正的 28.1806。
