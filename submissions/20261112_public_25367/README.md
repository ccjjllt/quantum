# 2026-11-12：采用 25.367 公开前沿的 invsqrt + 化学 refit，保留原 DQI

公开前沿更新后（2026-11-12 凌晨）的安全组合：只换 invsqrt 与化学，DQI 保持已在线上 0/0 的
`cd71c482`，避免新 DQI SHA 的 salt 重抽。

## 公开前沿变化

| 项 | 旧 | 新（2026-11-11 晚） |
|---|---|---|
| LB 榜首 | 29.30100（11-08） | **29.45296**（Entangled Team，11-11 22:02 UTC） |
| LB 第二 | 29.18459 | **29.30643**（Schrödinger's cat lived，11-11 20:48 UTC） |
| 公开 notebook 最高 | 25.33133 / 25.36085 | **25.36727**（pramitdas 19:44；asteriospanoras 22:44） |

25.367 组合：invsqrt `9c708f7b`（新 splice）或 `6c6a734d`、DQI Atakan `bb4287e7`/iso-gap h5
（+ readout windows，作者本地 PASS 373,534,939,340.64）、化学 `f21b8a87` + Maoxin v22 4,097 loader。

## 本次采用/拒绝

- **采用 invsqrt `9c708f7b`**：asteriospanoras 的 splice（WCao24 44-CSWAP normaliser `94b29cc5`
  + Thomas Gamet early prefix `5ec4f516`，接在 maoxin/manwithacat 62Q 线上）。
  作者官方 93,555.2627；本机全量 **PASS 93,555.3164323432**（salt `25367-inv-20261112`），
  比 `6c6a734d` 的 93,863.2932 **低 307.98（−0.328%）**。
- **采用化学 `f21b8a87` + Maoxin v22 loader**：prvsiyan 的约束 refit，字表仍 `8afd4c67`，
  loader 4,097/pass。本机 78,080-shot **PASS 297,557,548.71265644**，
  λeff 46.90738327801011（比 Maoxin v22 版 46.9075374 低），T=14,856、Q=427、e1/e2=0.01999998。
- **拒绝 Atakan DQI `eae396ba`**：作者本地 PASS 373,534,939,340.64（比 cd71 低 0.0828%），
  但换 SHA 会重抽 salt；按 72-salt 15/72 单失败、单失败 +0.46%，期望惩罚 ~0.1% 大于 0.083% 收益。
  保留 `cd71c482`（58235797 已在线 0/0）。

## 提交

- 本账号 `ccjjllt` 提交 **58256166**（`2026-11-12T01:10:18Z` / 北京时间 09:10:18），
  `submission.zip` 81,590,723 bytes，外层 SHA-256
  `81dab8c834db478b14a8bffa22670c665d5d9b61ea590fdeecaa36f1b1e30aca`，18 成员。
- 回填（2026-11-12 01:39 UTC）：**COMPLETE，public_score 25.38868**，与本地预期
  GM **25.388681347** 一致（+0.027836 vs 25.36085）。

## 三件

| 任务 | 文件 | SHA-256 | 本地分数 |
|---|---|---|---:|
| invsqrt | `9c708f7b…ef20d1` | `9c708f7b9abc7c7e6719f6e258a3881945e9ee1fd4fd7009fe37367ca1ef20d1` | **93,555.3164323432** |
| DQI | `cd71c482…90fa671` | 与 58235797 相同 | 373,844,684,513.52（0/0，沿用） |
| 化学 | `f21b8a87…de2eb` | `f21b8a8725c342eb04c37fad269a431003a304d1ac9ad6bf5c56f1d075fde2eb` | **297,557,548.71265644** |

化学 `submission_sha256=478fae1c151118700284bb6412d1fc7971a0b5fbe6943a3520fc073bd7cedd64`；
invsqrt 200,540,928 shots，62Q、mean Toffoli 1,213.8659、static 1,375、41 rotations、
worst 0.9993237694@161。

## 组合

```text
GM = (2076774.233715 / 93555.3164323432
    × 24439463583672.93 / 373844684513.5198
    × 3355599588.3155375 / 297557548.71265644)^(1/3)
   = 25.388681347
```

## 验证范围

- invsqrt 与化学各 1 次完整官方验证（200,540,928 / 78,080 shots，单 salt）；
  DQI 未重跑，沿用 58235797 的全量 PASS（同文件 SHA）。
- 未采用 25.367 组合中的新 DQI；未跑该 DQI 的本地验证（作者 receipt 已给 0/0 PASS）。
- 线上分数已回填为 25.38868；25.388681347 是本地验证预期，两者一致。
