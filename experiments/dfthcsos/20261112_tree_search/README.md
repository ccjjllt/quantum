# Givens 树搜索：当前树已最优（2026-11-12）

- 输入：`artifacts/20261112_public_25367/dfthcsos/submission.npz` 的 1,220×75
  `angle_words` 与 `tree_edges`。
- 方法：把当前 words 解码成单位向量，用官方 unsigned Givens 编码
  (`encode.tree_angles`/`to_words`) 在候选树上重编码；按 J=5 形成 15 个批次
  XOR delta，用 `tensorqrom.per_output` 的 Toffoli 代理求和。当前树先把 words
  逐位复现（代理 5,119，和 5,120 的舍入一致）。
- 候选：path、star、heap + 24 棵随机递归树（seed 20261112）。
- 结果：当前树 **5,119**；其余 5,311–5,400（path 5,397、star 5,400、heap 5,378），
  全部更差。没有找到换树收益。
- 范围：静态代理，未构建 128-qubit loader、未跑 78,080-shot verifier。
