# 提交回执：14,840-Toffoli 化学 loader swap（ref 58271862）

日期：2026-11-12（北京时间）；用户已批准本次提交。

## 组合

| 任务 | 组件 | SHA-256 | 来源 |
|---|---|---|---|
| invsqrt | `9c708f7b` | `9c708f7b9abc7c7e6719f6e258a3881945e9ee1fd4fd7009fe37367ca1ef20d1` | 当前 best（WCao24 normaliser + Thomas Gamet prefix splice） |
| DQI | `eae396ba` | `eae396baf0fa52952e07d891237e271257e35bc0483afe57abd17c77857785bd` | 当前 best（Atakan h5） |
| dfthcsos | `5d5007a75784`（4,089/pass loader） | npz `e9cffb841c4b8bacec7ae423a931e8b38789ecf74b22011f4e98864521e9a9bd`；verifier `submission_sha256=8cd07c7cbb8dae37077713611b3df017a3ef1110fb446465622bc9371ca0509b` | `manwithacat/vqcc-apache-public-circuits` 2026-11-12 07:48 UTC |

## 本地验证

- 化学件：官方 `dfthcsos` verifier **全量 78,080 shots PASS**（salt `14840-check`）：
  T_total=14,840、Q_total=427、λeff=46.907378146123214、e1=0.01999998、e2=0.019999997、
  Λ=282.97398、E_gap=3.914898003、成本 **297,237,044.95**。
  证据见 `artifacts/20261112_frontier/chem14840/README.md`。
- invsqrt `9c708f7b`、DQI `eae396ba` 沿用已在线验证件（`58265561` 的 25.39570）。
- 组合本地 GM：**25.40482516**（当前 25.39570057，+0.036%）。

## 打包

- 目录：`artifacts/20261112_14840_candidate/`（18 件）。
- ZIP：`submissions/20261112_14840/submission.zip`，**82,261,596 bytes**，
  SHA-256 `67f56f421567e82b5a30bb0c6d4194eb313175e9bd5420bace4f4941fffb1e9b`。
- 上传：resumable，最终 HTTP 200；Kaggle 提交返回
  `{"message":"Successfully submitted ...","ref":58271862}`。
- **线上状态：COMPLETE，public score 25.40482**（与本地幸运值 25.40482516 一致；
  高于上一版 25.39570）。提交后 `submissions.get` 权限被拒，分数由
  `search_competition_submissions` 回填。

## 口径

- 这是公开件内的 0.036% 级 swap，不是 family-level 新算法；本地 GM 与线上不保证逐位一致
  （化学件 salt 不同，但该件在 portfolio 的默认 salt 下也复现过 297,237,044.95）。
- **DQI salt 重抽风险**：上一版 `58265561` 的线上 DQI 成本对应本地幸运 draw
  373,534,784,677.46；eae 的 96-draw 期望成本是 373,856,548,625.22（+0.086%）。
  换 ZIP 会重抽 salt，期望 GM 因此是 **25.39753475**（不是本地 25.40482516）：
  化学 −0.108% 的增益被 DQI 期望 +0.086% 抵消掉大半。若抽到好 salt，可到 25.4048；
  若抽到差 salt，可能低于 25.39570。Kaggle 保留历史最好提交，故 58265561 仍是下限。
- 不覆盖、不删除 `58265561` 的包与回执；本次为独立提交。
