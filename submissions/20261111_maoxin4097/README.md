# 2026-11-11：Maoxin v22 4,097-Toffoli 化学 loader（同一字表，纯 loader 增益）

用户批准“继续提高分数”后执行。只更换化学的 15 个 ANGLE loader；invsqrt、DQI、化学字表全部不变。

## 提交

- 本账号 `ccjjllt` 提交 **58239559**（`2026-11-11T13:42:15Z` / 北京时间 21:42:15），
  `submission.zip` 29,934,135 bytes，外层 SHA-256
  `92a81300433c8eb0517bbf11e03da760db0950761130eb80d101a03f6b034c16`，18 个成员。
- 状态 **PENDING**；本地预期 GM **25.360855367**（+0.029525 vs 25.33133）。
- 来源：`maoxin123/qcc-v22-4097-toffoli-chemistry-loaders` v1（notebook 输出时间 11-11 12:38 UTC，
  作者自报约 25.361）。`kaggle kernels output` 取回的 `submission.zip` 原样提交。

## 包内容（18 文件）

| 成员 | SHA-256 | 说明 |
|---|---|---|
| `invsqrt.kmb` | `6c6a734d…89b0666` | 与 58235797 完全相同 |
| `dqi.kmb` | `cd71c482…90fa671` | 与 58235797 完全相同 |
| `dfthcsos/submission.npz` | `8afd4c67…e55ae7b` | 与 58235797 完全相同 |
| `dfthcsos/angle_k_0..14.kmb` | 本轮新件 | 4,097 Toffoli/pass（原 4,123） |

## 本地验证

- 化学 `manual_verify.py dfthcsos artifacts/20261111_maoxin4097/dfthcsos --salt maoxin4097-main-20261111`：
  **PASS**，78,080 shots，score **297,558,526.5939861**，
  T=14,856、Q=427、`lambda_eff=46.90753743257459`、
  `error_1=error_2=0.01999997980003125 Ha`、
  `angles_toffoli_per_pass=4097`、`angles_toffoli=8194`、
  `submission_sha256=7efa20c2ebe1ad4bfe3cbdf508e4f18d0560a1324626f5927e9f305acd354737`。
  日志：`artifacts/20261111_maoxin4097/verify_chem.log`。
- invsqrt 与 DQI 与 58235797 逐字节相同，沿用该次全量验证：
  invsqrt 200,540,928 shots PASS 93,863.29319626842；
  DQI 102,400 shots PASS 373,844,684,513.52（0/0）。
- 化学误差门只由字表决定，字表未变，故 e1/e2 与 298,600,061.56 版本逐位相同；
  本次收益全部来自 loader T（14,908→14,856，−52）。

## 组合

```text
GM = (2076774.233715 / 93863.29319626842
    × 24439463583672.93 / 373844684513.5198
    × 3355599588.3155375 / 297558526.5939861)^(1/3)
   = 25.360855367
```

相对 58235797（25.33133）**+0.02953（+0.1166%）**；化学单项 −0.349%。

## 验证范围

- 化学完整官方验证 1 次（78,080 shots，单 salt）；invsqrt/DQI 未重跑，沿用 58235797 的 PASS。
- 外层 ZIP 为作者原包，未重打包；成员 SHA 与本地验证文件一致。
- 线上分数待回填；25.360855367 是本地预期，不是排行榜成绩。
