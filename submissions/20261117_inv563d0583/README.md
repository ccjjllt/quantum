# 候选包：invsqrt `563d0583`（+0.0297 GM）

**状态：2026-11-18 修正。** 原回执把 integrator 的 DQI 成员写成了 `575b043f`，实测不是。

## 更正（2026-11-18 00:55 Beijing）

核对内核 `qingyu1232/qcc-integrator-inv563d0583` v2 的 `receipt.json` 后发现：

* zip `cd24b38a…` 里的 `dqi.kmb` 是 **`957d6733`**（480,416,017 B），不是 `575b043f`。
* 官方 DQI verifier 对该成员：`PASS`，但 **value_errors = 1**（默认 salt）→ cost
  **348,246,849,661.48**，GM **28.1310187**。
* 因此该 zip **不能提交**（低于当前榜单 28.15094）。此前“本地 salt 假警报”的解释不成立：
  这是 manifest 里 DQI 成员选错（`members_2818066.json` 的 dqi sha 就是 `957d6733`）。

## 修正后的目标包

* 同一 chem（`a73b25d2` + 15 loaders，官方 294,643,137.73，λ_eff 46.9217168，4,022/pass）
* 同一 invsqrt `563d0583`（74,560.90687312803）
* **DQI `575b043f`**（sha `575b043f4fee91a0fc3a9fd6fc1e9290e7b2a0669cae79886be2bf999f7ec155`，
  479,128,738 B；来源 `grantprater/vqcc-dqi-61c8348d-merged-closings : dqi_575b043f.kmb.xz`）
* 新 integrator：`qingyu1232/qcc-integrator-281806` v1（manifest
  `integration/members_281806_correct.json`，expected GM 28.180659）。

按官方公式，DQI `575b043f` 在 0 错误抽样下 cost = **346,409,762,292.72**（该值已在
2026-11-17 的榜单提交 58464076 上验证），于是

```
GM = (2076774.233715/74560.90687 × 24439463583672.93/346409762292.72 × 3355599588.3155375/294643137.73)^(1/3)
   = 28.18066
```

DQI 若抽样掉 1 shot，cost ≈ 348.0e9 ⇒ GM ≈ 28.131；这正是榜单 salt 抽样的风险，
提交前以 integrator 的实测 JSON 为准。

## 提交（名额重置后）

```bash
kaggle competitions submit -c google-verifiable-quantum-circuit-compilation \
  -k qingyu1232/qcc-integrator-281806 -v 1 -f submission.zip
```

提交前必须确认：receipt 里 `dqi.circuit_sha256 = 575b043f…`、`value_errors = 0`。
