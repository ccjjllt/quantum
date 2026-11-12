# 化学 gauge 单行翻转搜索：无收益（2026-11-12）

- 从当前 `f21b8a87` 的 8-bit words 解码单位向量，用官方 unsigned Givens
  编码得到 canonical 表（proxy 5,119，error_1/error_2 仍 0.02）。
- 单行符号翻转只改该行 44 个 words（不是全表）；对 1,220 行做一轮 greedy
  单翻转，proxy 始终 5,119，**0 个改进**（74.5s）。
- 结论：当前 gauge 对 tensor-QROM per_output 代理是单翻转局部最优；gengsr
  303 flips 的 −8 T 已是小量，单翻转搜索不再有空间。
- 范围：静态代理，未构建 loader/未跑 78k verifier。
