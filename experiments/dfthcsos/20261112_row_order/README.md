# 化学行序搜索：canonical 序最优（2026-11-12）

- 化学 verifier 对行序不变：76 个 one-body 行可任意排；每个 rho 内的 B 个
  two-body 行可排（`w`/`U` 同步），rho 组也可整体排（`W`/`H2_I` 同步）。
- 在 canonical words 上比较：
  - 当前 canonical 序：proxy **5,119**，error_1/error_2 0.02，λeff 46.907。
  - Hamming 最近邻（one-body + 每组 rho）：proxy 5,279，指标不变。
  - 最近邻 + rho 组序：proxy 5,280，指标不变。
  - 字典序：proxy 5,257，但 rho/w 置换不匹配，指标失败（仅记录，不采用）。
- 结论：当前训练产生的行序已优于简单最近邻/字典序；行序不是免费收益点。
- 范围：静态代理，未构建 loader/未跑 78k verifier。
