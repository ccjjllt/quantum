# `eae396ba` vs `cd71c482`：52 个 paired seed 的实测（2026-11-12）

## 目的

公开 25.39570 组合把 DQI 从 `cd71c482` 换成 `eae396ba`。此前的拒绝理由是
“换 SHA 重抽 salt，72-salt 15/72 单失败、单失败 +0.46% → 期望惩罚 ~0.1% >
0.083% T 收益”。本轮用同一组 seed 对两个文件做 paired 比较，检验这个判断。

## 方法

- 文件：`cd71c4822aa0`（892Q，local 373,844,684,513.52）与
  `eae396baf0fa`（892Q，local 373,534,939,340.64）。
- 官方 DQI verifier，102,400 shots，`--seed 0..51` 对两个文件各跑一遍；
  同一 seed 下两文件使用相同 RNG 流（paired）。
- 记录 score、value_errors、phase_errors、R、executed Toffoli mean。
- 脚本：`artifacts/20261112_dqi96/run_sweep.py`；原始 JSONL：
  `artifacts/20261112_dqi96/results.jsonl`。

## 结果（52 个 paired seed）

| 指标 | `cd71c482` | `eae396ba` |
|---|---:|---:|
| clean mean score | 373,844,646,921.59 | **373,534,926,459.17** |
| 失败 seed 数 | 18 / 52 | 18 / 52 |
| mean paired relative diff | — | **−0.082843%** |
| paired stderr | — | 0.0000060% |
| 结论 | — | eae 低 0.083%，约 1,100 SE |

失败 seed 相同（两文件在同 seed 下同时出现 value error），说明 eae 没有引入
新的失败模式；它的收益来自确定性的 T 下降（mean Toffoli 394,416.2 → 394,089.3）。

公开 circuits manifest 的 96-draw expected cost 独立给出同一结论：
`eae396ba` 373,856,548,625.22 vs `cd71c482` 374,166,555,017.02（−0.0829%）。

## 结论

之前的 0.1% 期望惩罚估计过于保守；在 96-draw 口径下 eae 的期望成本仍低
0.083%，对应 GM **+0.028%**。已组装候选：
`submissions/20261112_eae_253957/`，本地 GM **25.39570057**（与公开 25.39570
一致），未自动提交。剩余风险是 private draw 命中一次失败（单失败约 −0.153%
GM），但期望值上 eae 优于 cd71。

## 验证范围

52 个 paired seed，单文件 102,400 shots/seed；manifest 的 96-draw 已由公开维护者完成。
未提交 Kaggle；候选提交见 `submissions/20261112_eae_253957/`。
