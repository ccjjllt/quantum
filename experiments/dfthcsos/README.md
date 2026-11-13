# dfthcsos（化学）研究入口

当前采用（main 已提交 `58299045`，Kaggle public **27.00209**）：公开化学件
`6418ec8e…a77f`，**4,074 T/pass**，Q=427，λeff=46.907347493481，T=14,810，
官方 78,080-shot **PASS 296,635,967.5936**（e1=0.0196103713、e2=0.0199987799）。
本线最后一版是 `f21b8a87` + Maoxin v22 4,097 loader，297,557,548.71；更早
Maoxin303 298,720,881.30、Lera 298,942,333.64、P0 299,497,670.48。

## 已关闭方向

训练盆地（R5/R4/R3）、B 轴（143→129/131/135）、7-bit、MBU、形状 (5,129,68)、
synth/synth2、公开集 survey 的完整数字与放弃原因见
[ABANDONED.md](ABANDONED.md)；更早的关闭记录见
[CLOSED_RESEARCH.md](CLOSED_RESEARCH.md)；系统性复盘见
[20261110_arch_review](20261110_arch_review/README.md)。

2026-11-12/13 的 loader 结构搜索（table survey、tree/row/batch/gauge、lowbits、J、
product-set、full-support、ESOP、loader-aware train、R=7、C 截断）全部 no-go，
详细文档与产物已删除；关键数字与放弃原因见 `ABANDONED.md` 和 main
`docs/abandoned-research.md`。其中 loader_aware_train 的结论保留：
结构化 1% loader T 要付 ~10 倍误差门代价；真 loader = 80 缓存 AND + 214 product
CCX/电路 = 4,097，表字 rank 15/15 已是最泛型。

## 可复用载体（保留）

- [20261106_train_r5](20261106_train_r5/README.md)：`seed_numpy.py` 种子生成。
- [20261110_gputrain](20261110_gputrain/README.md)：`slim_train.py` + `fastfit.py` +
  `prob_r5.npz` 训练/拟合栈。

其余失败实验的脚本、候选和中间产物已删除；需要时可从 Git 历史找回。

## 当前判断

- (8,143,44) 的 T/Q/λeff 已接近局部最优；B 轴与 7-bit 都被精度门否决。
- 下一刀只能是新 factorization / 新训练范式，属独立大工程。

## 2026-11-13 停止研究

公开化学件 4,074 T/pass + 296.64M 已优于本线 4,097 loader + 297.56M（+0.31%）。
训练盆地在 38–40 mHa，距 20 mHa 门约 2×；loader 4,089 已逆向到机制层，本仓库
构造器无法在 ≤4,089 落地。继续需要新 factorization / 新训练范式，停止推进。
总览与放弃原因见 main `docs/abandoned-research.md`。
