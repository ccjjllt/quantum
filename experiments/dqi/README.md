# DQI 研究入口

当前采用（main 已提交 `58256166`）：**`cd71c482`**（892Q，60,804,432 ops，
mean T 394,416.2）。本机 102,400-shot **PASS 373,844,684,513.52**（0 value / 0 phase）；
在线 `58235797` / `58256166` 均 0/0。

公开前沿 **`eae396ba`**（Atakan iso-gap h5 + controlled-swap readout windows）本地
**PASS 373,534,939,340.64**（T 低 0.083%），但它是新 SHA，换件会重抽 salt；
按 72-salt 15/72 单失败、单失败 +0.46%，期望惩罚 ~0.1% 大于 0.083% 收益，未采用。

## 已关闭方向

全部关闭方向、R 项 72-salt、Q−1/spill/pebbling、qbatch、unextract HMR、template C/A
差分与放弃原因集中在 [ABANDONED.md](ABANDONED.md)；系统性复盘见
[20261110_arch_review](20261110_arch_review/README.md)。
已关闭实验的脚本、候选和中间产物已删除；模板 A/B 方法证据保留在
[20261110_e9diff](20261110_e9diff/README.md)。

## 当前判断

- 892Q 是契约与算法共同决定的局部最优点；Q−1、Q-batching、unextract 清理均已证不可行。
- 单门级 T 收益小于 salt 噪声（0.46%/失败），只有 >0.2% 的整段换算法才值得重提。
