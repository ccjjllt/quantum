"""Heuristic (state-prep) cost table for candidate (R,B,C) shapes at brot=8, N=76."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, '/Users/zhaohuaxiang/ccjjllt/quantum/data/competition/verifiers')
from dfthcsos.verify import heuristic_costs  # noqa: E402

shapes = [(8, 143, 44), (8, 143, 45), (9, 143, 39), (7, 143, 55), (6, 143, 64),
          (6, 143, 60), (5, 143, 75), (5, 143, 72), (4, 255, 120), (4, 143, 120),
          (6, 255, 64), (6, 200, 64), (6, 180, 64), (5, 255, 75), (5, 200, 75),
          (4, 143, 96), (4, 180, 96), (4, 200, 96), (4, 255, 96), (4, 255, 80)]
print(f"{'shape':>18} {'rows':>5} {'heurT':>6} {'heurQ':>5} {'persist':>7} {'temp':>5}")
for R, B, C in shapes:
    c = heuristic_costs(76, R, B, C, 8)
    print(f"{str((R,B,C)):>18} {76+R*B:5d} {c['toffoli']:6d} {c['qubits']:5d} "
          f"{c['persistent_qubits']:7d} {c['temporary_qubits']:5d}")
