# dfthcsos（化学）研究入口

当前采用（main 已提交 `58256166`）：**`f21b8a87` + Maoxin v22 4,097-Toffoli/pass loaders**，
字表 `8afd4c67`，形状 `(8,143,44)`；T=14,856、Q=427、λeff=46.9073833，
本机 78,080-shot **PASS 297,557,548.71**，e1=e2=0.01999998 Ha。

上一版 `8afd4c67` + Maoxin v22 4,097 为 297,558,526.59；更早 Maoxin303 298,720,881.30、
Lera 298,942,333.64、P0 299,497,670.48。

## 已关闭方向

训练盆地（R5/R4/R3）、B 轴（143→129/131/135）、7-bit、MBU、形状 (5,129,68)、
synth/synth2、公开集 survey 的完整数字与放弃原因见
[ABANDONED.md](ABANDONED.md)；更早的关闭记录见
[CLOSED_RESEARCH.md](CLOSED_RESEARCH.md)；系统性复盘见
[20261110_arch_review](20261110_arch_review/README.md)。

## 可复用载体（保留）

- [20261106_train_r5](20261106_train_r5/README.md)：`seed_numpy.py` 种子生成。
- [20261110_gputrain](20261110_gputrain/README.md)：`slim_train.py` + `fastfit.py` +
  `prob_r5.npz` 训练/拟合栈。

其余失败实验的脚本、候选和中间产物已删除；需要时可从 Git 历史找回。

## 当前判断

- (8,143,44) 的 T/Q/λeff 已接近局部最优；B 轴与 7-bit 都被精度门否决。
- 下一刀只能是新 factorization / 新训练范式，属独立大工程。
