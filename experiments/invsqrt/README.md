# invsqrt 研究入口

当前采用（main 已提交 `58256166`）：公开前沿 **`9c708f7b`**——WCao24 44-CSWAP normaliser
（`94b29cc5`）+ Thomas Gamet early prefix（`5ec4f516`）的 splice，62Q。
官方 **93,555.26**，本机 200,540,928 shots **PASS 93,555.3164**（mean Toffoli 1,213.866、
static 1,375、41 rotations、worst 0.99932377@161）。
来源：`asteriospanoras/lb-25-367-verified-portfolio-dqi-readout-fix` 的 `receipt.json`。

上一版 `6c6a734d` 93,863.36（manwithacat HW-25），此前 gengsr `26ebf39d` 94,537.59、
Public Frontier `7c10edba` 95,430.78、Syed V9 约 97,747.22。

## 已关闭方向

2026-11-11/12 及更早的全部关闭方向、关键数字和放弃原因集中在
[ABANDONED.md](ABANDONED.md)（唯一详细记录）；系统性复盘见
[20261110_arch_review](20261110_arch_review/README.md)。
已关闭实验的脚本、候选电路和中间产物已删除；需要时可从 Git 历史找回。

## 当前判断

- 62Q 的局部优化面（单删/辛秩/HMR/脏借用/T 融合/重排序/跨守卫缓存/均值条件化/splice）
  已全部饱和，公开前沿只剩跨 family splice 与整段重写。
- 61Q 的纯重标号不可能；值级“重算代替存值”与 S1 shift-select 降级仍是独立大工程。
