# J=5/6 tensorqrom on the signed refined_845 table：更差（2026-11-12）

- 表：`refined_845`（R8/B143/C45，λeff 48.137，error_1 9.72 mHa，
  error_2 19.95 mHa，官方指标可过门）。
- `tensorqrom.build_family(..., lowbits=4, J=5)`：15 circuits，ANGLE **4,611 T/pass**，
  Qmax 119，heuristic T 6,741，T_total 15,963，投影 score **328.1M**，
  比当前 `f21b8a87` + Maoxin v22（4,097/pass，297.56M）差 **10.3%**。
- J=6 构建在 30 分钟超时内未完成；即便完成，J=5 已落后 10.3%，且 J=6 需要
  128-qubit cap 内多 8 个 persistent qubits，不具竞争力。
- 原因：tensorqrom 的 signed-gauge 表 λeff 48.137 比当前 46.907 高 2.6%，
  且其 loader 4,611/pass 比 Maoxin v22 4,097 高 12.5%；loader 重综合不是收益点。
- 结论：chemistry 的 ≥20% loader T 削减不能靠现有公开 loader 构造；必须换
  factorization/训练范式（circuit-aware factorization）。
- 范围：静态 `circuit_costs` + 官方 metrics；J=5 未跑 78,080-shot verifier
  （投影已差，未继续）。
