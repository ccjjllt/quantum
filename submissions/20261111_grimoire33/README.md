# 2026-11-11：Grimoire 33 公开前沿组合（三件全本地验证）

用户批准“快速刷新提交”后执行。三件来自 busyaprime 数据集，均在本机官方验证器全量 PASS。

## 提交

- 本账号 `ccjjllt` 提交 **58235797**（`2026-11-11T11:25:28Z` / 北京时间 19:25:28），
  `submission.zip` 81,805,683 bytes，`kaggle competitions submit` 直传文件一次成功。
- 提交时状态 **PENDING**，分数待回填；本地预期 GM **25.331334272**。
- 包内 18 个成员，外层 SHA-256 `7253a154c20df6accfc6d7279804dc948f2a9437833f6e681a68d17701b462d8`。
- 说明：打包脚本 `compresslevel=1`，故 ZIP 比历史包（约 28 MB）大；成员内容不受影响。

## 来源

- Notebook：`busyaprime/lb-25-33133-grimoire-33-every-gate-a-pixel` v20
  （标题自报 25.33133；作者称在盐 A/B 两次实测并附 verifier 报告）。
- Dataset：`busyaprime/33-qcc-v8-members`（apache-2.0，556,808,180 B 的 17 个 `.kmb` +
  2 个 `.npz` + 证据文件）。下载后逐个 SHA-256 与 `SHA256SUMS` 及 notebook 内 PINS 核对一致。
- 组件归属（见 `NOTICE.md` 与作者 notebook）：
  - invsqrt `6c6a734d`：manwithacat（James Barlow）V26/V27 的 HW-25 混合电路——
    gengsr 前 473 个操作 + 两个免费 `Z_POW`（q41 1.0、q47 1.5）+ maoxin `a15b0d73` 从第 329 个操作起的后半段。
  - DQI `cd71c482`：team *i want to run gemma 9b* 的公开件。
  - 化学：Lera 的字表与 12 个 loader（k4–k14、k0），maoxin 的 k1–k3；
    npz `8afd4c67` 为 busyaprime 在固定字下的 R58 refit。

## 三件（全部本地全量验证）

| 任务 | 文件 | SHA-256 | 本地分数 | 口径 |
|---|---|---|---:|---|
| invsqrt | `invsqrt.kmb` | `6c6a734d…89b0666` | **93,863.29319626842** | 200,540,928 shots，PASS，62Q、36,923 ops、41 旋转、eps 2.43404148e-13、worst 0.9993237694@161 |
| DQI | `dqi.kmb` | `cd71c482…90fa671` | **373,844,684,513.5198** | 102,400 shots，PASS，0 value / 0 phase，R=1.1912604648，892Q、60,804,432 ops |
| 化学 | `dfthcsos/submission.npz` | `8afd4c67…e55ae7b` | **298,600,061.555139** | 78,080 shots，PASS，T=14,908、Q=427、λeff=46.9075374326、e1=e2=0.0199999798 Ha |

- 验证 salt：invsqrt `grimoire33-inv-20261111`、DQI `grimoire33-dqi-20261111`、
  化学 `grimoire33-chem-20261111`。日志在 `artifacts/20261111_grimoire33/verify_*.log`。
- 本地 DQI 比作者自报 373,844,569,412 高 115,102（0.00003%），属 salt 抽样下执行 Toffoli 均值的正常量级；
  化学与 invsqrt 与作者数在小数点后 3–5 位一致。
- invsqrt 200M 全量 wall time 约 102 s；DQI 102,400 shots 与化学 78,080 shots 均一次通过，无重跑。

## 组合结果

```text
GM = (2076774.23 / 93863.2932
    × 24439463583672.93 / 373844684513.5198
    × 3355599588.32 / 298600061.555139)^(1/3)
   = 25.331334272
```

相对上一版三件套（`58228252`，25.30340）**+0.02793（+0.110%）**；
各件增量：invsqrt −61.99、DQI −840,321,822、化学 −120,819.74。

## 验证范围

- 三件均为本机官方验证器完整运行（未改 `data/competition` 验证器，未改数据集文件）。
- 未做多 salt 复验（作者称 8 个 salt 的范围为 93,863.29–93,863.36；本轮只跑 1 个 salt）。
- 线上分数尚未回填；本记录的 25.331334272 是本地预期，不是排行榜成绩。
