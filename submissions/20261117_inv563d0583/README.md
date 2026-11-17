# 候选包：invsqrt `563d0583`（+0.0297 GM）

**状态：已端到端官方验证 PASS，尚未提交。** 今日提交名额已用满（5/5），UTC 00:00 重置。

## 三条腿（本地 integrator 全量官方 verifier，18/18 成员）

| 腿 | 件 | 官方 cost | 备注 |
|---|---|---|---|
| invsqrt | **`563d0583`** | **74,560.90687312803** | 新；旧 `0af21cb8` 为 74,797.365357 |
| DQI | `575b043f` | 348,246,849,661.48 | **本地 salt 抽样**；榜单口径该项仍是 346,409,762,292.72 |
| chem | `a73b25d2` | 294,643,137.73357135 | 未改动 |

zip：85,200,406 B，sha256 `cd24b38a5a022dbe7db5e4d8498c0480e93fbbe9de5f1ea109405d65f1ebc992`
（内核 `qingyu1232/qcc-integrator-inv563d0583` v2，`decision: DO_NOT_SUBMIT` 是本地/榜单 salt 不同造成的假警报，见
`experiments/frontier/20261117_deep/SUMMARY2.md` §17）。

## 预期榜单分数

DQI tape 完全没动 ⇒ 榜单那一项保持原值，只应用 invsqrt 的 delta：

```
(74,560.90687 / 74,797.365357)^(-1/3) = ×1.001054
28.15094 × 1.001054 ≈ 28.1806      (+0.0297)
```

## 为什么这是本代能拿到的几乎全部

见 `experiments/frontier/20261117_deep/SUMMARY2.md`：DQI 峰值 liveness 恰好 890（0 dead wire，
任何 k 无「可恢复覆盖」）、invsqrt 44Q 是 liveness 峰值且旋转 ε 被容差钉死、
chem 的 Q(427)/rows(1,220)/loader(4,025)/λ(46.92) 四轴全部实测到顶。
金线 28.71339 需要 DQI ≤ 864（合同地板 840），那是换一代 EEA 工作集，不是重排字节。

## 提交（名额重置后）

```bash
kaggle competitions submit -c google-verifiable-quantum-circuit-compilation \
  -k qingyu1232/qcc-integrator-inv563d0583 -v 2 -f submission.zip
```
