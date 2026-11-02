# th_tail.md：行 TH 长尾整数先行验证 —— 通过（A/R 行恒不触 V[36:45)）

分支 `invsqrt-generator-rebuild`。对象：BOTH 系表（sA=sR=2）。
方法：全域逐行加数 `>>36` 最大值与触及数（`throw_tail.log`，主线程实测，EXIT=0）。

- A1sub j=0..13：max_hi36 全 0，n_touch 全 0。
- A1add J13：max_hi36=0，n_touch=0。
- R1 j=0..11：max_hi36 全 0，n_touch 全 0。
- 唯一触及者：B（(B<<12)>>36 最大 361）。

结论：V[36:45)（即 Vn[20:29)）的非零贡献只来自 B 直接装载；
A1/R1 任意行加数恒 < 2^36。行 TH（覆盖 Vn[20:29) 的高位通用加法）可缩为
仅算进 bit36 的 carry（含 borrow），B 高位静态装载后只需在 bit36 加一次 carry。
注意：carry 本身不可删（低位和可向 bit36 进位），删的是 36..44 的全加器链。

预期：峰值 134（`iadd(c2→TH)` 暂存 ~23 主导）降 ~5~8Q；门数同降。
下一步专线实现：两级行 TH 收窄 + B 高位直装 + carry36 合并。
