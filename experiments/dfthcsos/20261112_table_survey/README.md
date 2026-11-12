# Lera 量化表 survey：当前 (8,143,44) 最低（2026-11-12）

- 用官方 `dfthcsos.verify.load_inputs`/`evaluate_words` 和
  `heuristic_costs` 评估 `dfthc-compact-pipeline` 的 R8/R9 量化表；
  ANGLE T 用 `tensorqrom.per_output` 代理按当前 loader 的 4097/5119 比例校准。
- 下表是 **per-pass 代理**（`λeff × (angle_proxy + heuristic_T) × Q`），
  不是官方 score；官方会再把 ANGLE 计一次 reverse，所以绝对值约为 2×。
  只用于同口径排序。
- 关键结果（λeff / heuristic T / Q / per-pass 代理）：
  - 当前 `f21b8a87` R8/B143/C44：**46.9074 / 6,662 / 427 / 215.51M**。
  - `refined_845` R8/B143/C45：48.1371 / 6,741 / 427 / 222.75M。
  - `final_refit_44` R9/B143/C44：47.0742 / 7,094 / 428 / 227.60M。
  - `coded_refined_40` R9/B143/C40：49.0477 / 6,741 / 428 / 229.82M。
- 结论：当前表的 λeff 最低，R9 变体的 heuristic T/Q 更高；没有找到可替换的
  Lera 表。官方口径下当前表约 297.56M，`refined_845` 约 306.9M（+3.1%）。
- 范围：静态代理，未跑 78,080-shot verifier。
