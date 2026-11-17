# 2026-11-17 深度轮提交：28.15093（DQI 换 4 个 Toffoli 的 closings）

## 结论

| 项 | 值 |
|---|---|
| 提交 ref | **58464076** |
| 提交时间 | 2026-11-17 09:2x UTC |
| 路径 | code competition：kernel `qingyu1232/qcc-deep-2815093-575b043f` version **1**，输出 `submission.zip` |
| 状态 | **COMPLETE，public 28.15094** |
| 本地官方 GM | **28.150932035980528**（前值 28.15082863，**+0.00010**） |

## 三件（全部由未修改官方 verifier 在本账号复核，full shots）

| task | 件 | 状态 | 官方 cost | Q | T |
|---|---|---|---:|---:|---:|
| invsqrt | `0af21cb8` | PASS | 74,797.36535717871 | 44 | 1,459.3748803 |
| DQI | **`575b043f`** | PASS | **346,409,762,292.7187** | 890 | **367,116.0572168** |
| chemistry | `a73b25d2` + 15 SMALL loader | PASS | 294,643,137.73357135 | 427 | 14,706 |

DQI 的改动：`575b043f` 是 `61c8348d` 加上 **4 个已证明的 product-retention closings**，
静态 Toffoli 367,993 → **367,989**，均值 367,120.00 → **367,116.06**（−3.94）。
来源：`grantprater/vqcc-dqi-61c8348d-merged-closings` v4 的 `dqi_575b043f.kmb.xz`
（xz 20,858,792 B → kmb 479,128,738 B，sha256 `575b043f4fee91a0fc3a9fd6fc1e9290e7b2a0669cae79886be2bf999f7ec155`）。

## 证据

- Kernel：`qingyu1232/qcc-deep-2815093-575b043f` v1 **COMPLETE**，`receipt.json`：
  三腿 `PASS`，`gm = 28.150932035980528`，`decision = SUBMIT`，
  `submission.zip` sha256 `cddfb0bb9140b90bf3c73dabe3144e146b55ba013f0add8a915248d862c4cc50`（85,016,715 B，18 成员）。
- 复现命令：
  ```bash
  cd experiments/frontier/20261117_deep/integration
  python3 make_main.py --members members_2815093.json \
      --label "28.15093 candidate" --expected-gm 28.15093204 --min-gm 28.15082863 \
      --invsqrt-b64 ../../20261116_push/pipeline/invsqrt_0af21cb8.kmb.b64 --out main_2815093.py
  ```
- 独立证据：`royalacecat/qcc-28-1509587-e8-submission` 的发布记录声称同一套件 local GM
  28.1509587233（API 提交 58460103，score PENDING_API），与本包同一 DQI 字节。
- 风险：该 DQI 在 **default salt** 下 3/3 salt PASS 中 2 clean / 1 lost-shot
  （丢 1 shot 时 cost 348,000,563,990.93）。若公开/私有盐抽到丢 shot，本包公开分为
  ≈28.1079，**不会**低于当前最佳 28.15083 的账上记录（榜单取本团队最好一次）。

## 回执

```
Submission Ref : 58464076
Status         : COMPLETE
Public Score   : 28.15094          (前最佳 28.15083, +0.00011)
Leaderboard    : rank 156 / 3,250+  (28.15094 档, 同分还有 rank 153-155)
```

`kaggle competitions submission 58464076` 的读回即上表。榜上 `28.15083` 这一档现在是 **0 队**
（原 29 队并列在 05:30 时位于 rank 87–115），说明整个公开包在当天 02:32–04:52 的
grantprater closings 发布后集体上移；我们这次换 `575b043f` 把自己也抬到 **28.15094**，
现位于 **silver 线（top 5% ≈ rank 162）以内但只剩 6 名余量**。

## 与 05:30 快照的对比（重要）

| 项 | 05:30 快照 | 现在（58464076 之后） |
|---|---|---|
| 本账号 public | 28.15083 | **28.15094** |
| `28.15083` 这一档 | 29 队并列（rank 87–115） | **0 队** |
| 本账号 rank | 87–115 | **156** |
| silver 线 | 28.14702 / rank 161 | top 5% ≈ rank 162 |

**结论：分数涨了 +0.00011，但名次掉了约 40 名** —— 因为同行在 4 小时内把同一档整体抬到了
28.15086/28.15094。要守住 silver 需要继续挖同量级的小项（每 −122 Toffoli（DQI）、
−5 T（chem）、−0.55 C（invsqrt）各约 +0.011 GM）。
