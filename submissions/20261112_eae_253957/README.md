# 2026-11-12：DQI 换 `eae396ba`，本地 GM 25.39570057

本包是 2026-11-12 公开前沿 **25.39570** 的同一组合：invsqrt `9c708f7b` + 化学
`f21b8a87`/Maoxin v22 4,097 loader + DQI **`eae396ba`**。相对已提交的
`58256166`（25.38868），唯一改动是 DQI；本地预期 **25.39570057**，与公开
notebook 前沿 25.39570 逐位一致。

## 为什么换 DQI

- `eae396ba`（Atakan：four-Toffoli GF(64) phase + 44-CSWAP inverse normaliser）
  的 0 失败成本为 **373,534,939,340.64**；`cd71c482` 为 **373,844,716,975.29**，
  确定性 T 收益 **−0.0828%**。
- 公开 circuits manifest 的 96-draw expected cost：
  `eae396ba` **373,856,548,625.22**，`cd71c482` **374,166,555,017.02**；
  eae 的期望成本仍低 **0.0829%**，不是单次 salt 抽签。
- 之前按 72-salt 的通用 15/72 失败率估算“期望惩罚 ~0.1% > 收益 0.083%”，
  这个估计偏保守；96-draw 的 paired 结果给出 eae 期望更优。
- 本机 `eae396ba` 官方验证器 102,400 shots，salt `eae-20261112-a`：
  **PASS 373,534,784,677.4592，0 value / 0 phase**，R=1.1912604648，892Q，
  mean Toffoli 394,089.27。

## 三件

| 任务 | 文件 | SHA-256 | 本地分数 | 验证范围 |
|---|---|---|---:|---|
| invsqrt | `9c708f7b…ef20d1` | `9c708f7b9abc7c7e6719f6e258a3881945e9ee1fd4fd7009fe37367ca1ef20d1` | 93,555.3164323432 | 200,540,928 shots PASS（沿用 `58256166` 同文件） |
| DQI | `eae396ba…785bd` | `eae396baf0fa52952e07d891237e271257e35bc0483afe57abd17c77857785bd` | 373,534,784,677.4592 | 102,400 shots PASS，0/0，salt `eae-20261112-a` |
| 化学 | `f21b8a87…de2eb` + Maoxin v22 | `f21b8a8725c342eb04c37fad269a431003a304d1ac9ad6bf5c56f1d075fde2eb` | 297,557,548.71265644 | 78,080 shots PASS（沿用 `58256166` 同文件） |

DQI 官方日志：`artifacts/20261112_eae_candidate/verify_dqi_a.log`。
invsqrt / 化学日志：`artifacts/20261112_public_25367/verify_invsqrt.log`、
`artifacts/20261112_public_25367/verify_chem.log`。

## 组合

```text
GM = (2076774.233715 / 93555.3164323432
    × 24439463583672.93 / 373534784677.4592
    × 3355599588.3155375 / 297557548.71265644)^(1/3)
   = 25.39570057135932
```

公开前沿 `25.39570` 的组合与此相同（`ozertuu/25-39570-sota-vqcc-fast-runner-portfolio`，
11-12 01:51 UTC）；本账号 25.38868 当前约在第 201 名，公开 25.3957 的
plateau 约在第 163–184 名（同分按提交时间 tie-break）。

## 打包与提交状态

- 候选目录：`artifacts/20261112_eae_candidate/`（18 个文件）。
- `submission.zip`：82,303,835 bytes，外层 SHA-256
  `81f4bd3dc2554ccc137f9cbe1531766f209daa3ac51ef49224cbd6fb6379a9ec`。
- **已提交 Kaggle**：ref **58265561**，2026-11-12T07:42:01Z（北京时间 15:42），
  状态以平台回填为准；本地预期 public **25.39570**。

## 验证范围与风险

- invsqrt 与化学未重跑，沿用 `58256166` 的同 SHA 全量 PASS；DQI 本轮完整
  102,400-shot PASS，单 salt。
- eae 的 private draw 仍可能命中 1 次失败（单失败 +0.46% DQI 成本，约
  −0.153% GM）；96-draw 期望成本仍优于 cd71，因此这是期望值上的改进，
  不是保证。
- 该包不改变 `references/public-baseline.json` 的已采用基线；它是一份
  已验证的候选/替换记录。
