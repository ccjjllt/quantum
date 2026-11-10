# 2026-11-10：gengsr 25.2268 公开组合提交

按用户要求采用新的公开最高方案并提交一次，同时更新当前研究比较基线。

## 来源与归属

- 固定公开 notebook：[LB 25.2268 | shifter 46 + own chemistry loaders](https://www.kaggle.com/code/gengsr/lb-25-2268-shifter-46-own-chemistry-loaders)（11-09 运行）。
- 作者保存的 notebook 内验证日志（`verify_results.json`，三项全 PASS）：
  invsqrt 94537.58955971198（62Q，1392 静态，36,686 ops，SHA `26ebf39d…`）；
  DQI 374686873086.94（892Q，静态 395,586，均值 T 395304.76，0/0 失败）；
  化学 299497671.22。
- 本账号 `ccjjllt` 提交 **58181743**（`2026-11-10T01:40:55Z` / 北京时间 09:40:55），
  API 返回 `Successfully submitted`；只读回读确认 `submission.zip`（28,086,422 bytes）。
  未持续监控分数；作者自报 25.2268，非本账号实时成绩。

## 18 个成员文件（原始包未修改）

原始 `submission.zip`（28,086,422 bytes，解压后 536,785,268 bytes）未做任何字节修改直接上传。
SHA-256（`artifacts/20261110_gengsr_252268/release/` 解压核对）：

1. **`invsqrt.kmb`**（`26ebf39df3b13e5fd2d923d1b9988043b107b64f6e21efc5cc9bc76f5d56adec`）：
   62Q，36,686 ops，1392 静态 Toffoli-like；架构与 Syed/Hosen 系不同
   （"shifter 46"，36k vs 53k ops），是 invsqrt 研究线的新 family。
2. **`dqi.kmb`**（`e9f54be304cbdcda7306729c335b1a2314a45d0ca818e05cf60e45ddee969bc4`，
   529,242,404 bytes）：与同期 Özer v91、Maoxin 25.218 三家的 `dqi.kmb`
   字节完全相同（本轮 `artifacts/20261110_public_candidates/` 内三包互相比对确认）；
   相对 Syed 系（`4432ec5f`，529,241,631 bytes）大 773 字节。
3. **`dfthcsos/submission.npz`**（`9c358a8e9a4bba180f7455df777f3a456e68a39b6f7d4de3c485f2bb4554dc13`）
   及 15 个 `angle_k_*.kmb`：形状仍为 `(8, 143, 44)`，与 Syed 系同形，权重不同；
   三家 npz 各不相同。

## 验证范围

- 本机重跑 invsqrt 完整官方验证（200,540,928 shots）：**PASS，
  95430.78→94537.58955971198**，与作者日志小数点后完全一致。
- DQI 与化学沿用作者保存日志的三项 PASS（本机未重跑；DQI 全量为 102,400 shots，
  化学 78,080 shots，按约定不自动触发）。
- GM 估算（作者数）：1.00945 × 1.00013 × 1.00053 开立方 ≈ 25.227，与自报 25.2268 吻合。
- 提交前对比：Özer v91（invsqrt `27977c55…`，36,676 ops/1392）、
  Maoxin 25.218（invsqrt `c6519219…`，36,450 ops/1393）同代，均存于
  `artifacts/20261110_public_candidates/` 作交叉对照，未提交。
- 上一版 Public Frontier 25.14222（`artifacts/20261108_public_frontier/release/`）
  保留为历史对照。
