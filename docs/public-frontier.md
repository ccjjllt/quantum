# 公开前沿与预算（2026-11-19）

## 当前最佳方案与榜单位置

- **本账号最佳 COMPLETE**：ref **`58522779`**（2026-11-18T19:20:43Z），Public Score **`28.23162`**，**rank 183 / 3,355**（2026-11-19 快照；本地 `scripts/gm.py` 复算 GM **`28.231630`**）。
- **三腿配置与官方验证（默认 salt，未改官方 verifier）**：
  - `invsqrt` **`d0227f3c`**：44Q，**`74,405.67238374705`**（200,540,928 shots PASS，`worst/tol = 0.9994556 @ x=231`，33 rotations，`eps = 2.0054e-13`）。
  - `DQI` **`15a4b740`**：890Q，**`345,256,821,433.9815`**（102,400 shots 0/0 PASS，mean T `365,894.2005`，max `366,216`，`num_bits = 74,545`；含 CSWAP converter + 32 GF(2^24) closings + MBUC + PW4 + HW-30）。
  - `dfthcsos` **`4d63be3d` + 15 loaders**：427Q，**`294,642,170.565169`**（78,080 shots PASS，`T = 14,706` = `2×4,022 + 6,662`，`Lambda = 283.143964`，`lambda_eff = 46.921563`）。
- **榜单差距**：榜首 `Z³C¹oherence` **`31.74002`**、#2 `ThemBones` **`31.62236`**、#10 `yu4u` **`29.23215`**。≥ 28.24 分段未见公开对应包，属于私有电路代际。

## 提分成本预算（从 `28.231630` 出发）

仅改单腿（其余两腿与 DQI `Q=890, R=1.19126` 固定）或三腿均摊的成本门槛：

| 目标 GM | 仅改一项降幅 | 三项均摊各降 | 仅改 invsqrt 上限 | 仅改 DQI mean T 上限 | 仅改化学成本上限 |
|---:|---:|---:|---:|---:|---:|
| 29.00 | 7.74% | 2.65% | 68,647 | 337,574 | 271.84M |
| 30.00 | 16.66% | 5.89% | 62,008 | 304,930 | 245.55M |
| 31.50 | 28.01% | 10.38% | 53,565 | 263,410 | 212.11M |
| 31.74 | 29.63% | 11.05% | 52,359 | 257,479 | 207.34M |

## 固定公开来源与验证证据

- **现役 28.23162 组合**：`ozertuu/28-23163-sota-verified-compilation-top-portfolio` v3（回执见 [20261118_sota2823](../submissions/20261118_sota2823/README.md)）。
- **公开电路汇总与基准数据集**：`manwithacat/vqcc-apache-public-circuits`、`asteriospanoras/qcc-circuit-atlas`、`ratnachand/vqcc-verified-public-floor`、`junmiaotiao/qcc-frontier-20261118w`（combo W 三腿完整官方验证 JSON 保存在 [evidence/20261118b](evidence/20261118b/)）。
- **公开源码参考（Apache-2.0 / 论文数据）**：[QVC v0.4.0](https://github.com/Agnuxo1/qvc-chemistry-compiler/releases/tag/v0.4.0)（46Q invsqrt 与 889Q DQI 生成器源码）、[marculera v7](https://www.kaggle.com/datasets/marculera/dfthc-merge-pipeline/versions/7)、[BLISS-THC v1](https://doi.org/10.5281/zenodo.14712662)。
