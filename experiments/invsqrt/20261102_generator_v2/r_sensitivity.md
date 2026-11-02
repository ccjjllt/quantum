# r_sensitivity.md：R 项 t-条件敏感性 —— 硬约束，无条件可乘（否决）

分支 `invsqrt-generator-rebuild`。对象：BOTH 系表。方法：R 置零后全局 +
分 t（8…19）maxrel 画像（`r_sensitivity.log`，主线程实测，全域，EXIT=0）。

| 口径 | base maxrel | R-zeroed maxrel | fails |
|---|---|---|---|
| 全局 | 0.6168 | 95.5248 | 2,681,414 |
| t=8…19（逐 t） | 0.44–0.62 | 95.44–95.52（全 t） | — |

结论：R 置零在**所有** t 上崩溃（maxrel ~95，2.68M 失败）。
R 不是微调修正项，而是二次形状的承重项（无 R 则模型坍缩）。
t-门控 R 行、R 稀疏化到零、R 表压缩均无空间。
结合 `refit_layout.md` §7（R8 余量 2.6%、DEEP FAIL）：R 精度 ~10 位是本模型族的硬约束；
继续压 R 需换模型族（新拟合思想），非本轮范围。本方向关闭，无电路改动。
