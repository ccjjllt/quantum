# tensorqrom lowbits 扫描：lowbits=3 双重否决（2026-11-12）

- 表：`refined_845`（R8/B143/C45，λeff 48.137，error_1 9.72 mHa，
  error_2 19.95 mHa，官方指标可过门）。
- `tensorqrom.build_family(..., lowbits=3)` 给出 ANGLE 静态 T **3,992/pass**
  （当前 Maoxin v22 4,097/pass，−2.6%），Q_total 427，heuristic T 6,741。
- 但官方 score 把 forward+reverse 各算一次，T_total ≈ 2×3,992+6,741 = 14,725
  （当前 14,856，仅 −0.9%）；该表的 λeff 48.137 比当前 46.907 高 2.6%，
  投影成本 ≈ 48.137×14,725×427 = **302.7M**，比当前 297.56M **更差**。
- 另外最大 ANGLE 电路 **195 qubits > 128**，官方 verifier 直接拒绝：
  `an ANGLE_k circuit uses 195 qubits > 128`。lowbits=3 的 high chunk H=153、
  high monomial cache 255 qubits；lowbits=4 的 H=77/cache 127 才是 128 cap 下的
  可行点。high-liveness 峰值实测仍为 152（corrections 需要全部 high monomials），
  懒分配也不能压到 128。
- 结论：不构建候选；当前 4,097/pass + λeff 46.907 已是 cap 与精度约束下的可行点。
