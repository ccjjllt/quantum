# DQI 研究入口

当前采用（main 已提交 `58256166`）：**`cd71c482`**（892Q，60,804,432 ops，
mean T 394,416.2）。本机 102,400-shot **PASS 373,844,684,513.52**（0 value / 0 phase）；
在线 `58235797` / `58256166` 均 0/0。

公开前沿 **`eae396ba`**（Atakan iso-gap h5 + controlled-swap readout windows）本地
**PASS 373,534,939,340.64**（T 低 0.083%）。2026-11-12 的 52 个 paired seed 实测
（`20261112_96salt/`）给出 eae 的 paired mean **−0.08285%**、stderr 0.0000073%，
失败 seed 与 cd71 相同（7/24）；公开 circuits manifest 的 96-draw expected cost
也为 **373,856,548,625.22 vs 374,166,555,017.02（−0.0829%）**。此前按 72-salt
通用 15/72 估计的 ~0.1% 期望惩罚过于保守；eae 在期望值上更优，已组装候选
`submissions/20261112_eae_253957/`（本地 GM 25.39570057，未自动提交）。

## 已关闭方向

全部关闭方向、R 项 72-salt、Q−1/spill/pebbling、qbatch、unextract HMR、template C/A
差分与放弃原因集中在 [ABANDONED.md](ABANDONED.md)；系统性复盘见
[20261110_arch_review](20261110_arch_review/README.md)。
已关闭实验的脚本、候选和中间产物已删除；模板 A/B 方法证据保留在
[20261110_e9diff](20261110_e9diff/README.md)。

## 当前判断

- 892Q 是契约与算法共同决定的局部最优点；Q−1、Q-batching、unextract 清理均已证不可行。
- 单门级 T 收益仍小于 salt 噪声；整件换 DQI 必须用 paired/96-draw 期望成本判断。
  `eae396ba` 已用 52 paired seed + manifest 96-draw 确认 +0.083% 期望收益；更大的
  13%+ 级别仍只能来自换解码器族。
- `20261112_branch_recovery`（paper 原则 (a)/(b) 的剩余空间）：决策机器 57,119 T
  = 14.2%，全部在 n−1 零测试 / 1 CSWAP 下界；无 ≥10k 可替换块。**局部 branch
  recovery no-go**，13.5% 只能来自换族（详见该实验 README）。
