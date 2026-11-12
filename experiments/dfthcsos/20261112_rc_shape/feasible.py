"""Which (R,B,C) shapes can clear cost < 292M at a plausible lambda_eff, before accuracy?"""
from __future__ import annotations

import sys

sys.path.insert(0, '/Users/zhaohuaxiang/ccjjllt/quantum/data/competition/verifiers')
from dfthcsos.verify import heuristic_costs  # noqa: E402

LOADER_PER_ROW = 6.70   # total (both passes) Toffolis per loaded row at brot 8, from the manifest
J_BROT = 40             # 5 words per circuit x 8 bits
CODED = 375             # ~25/pass x 15 circuits saved by the coded bit 0 (measured on the current table)

rows_out = []
for R in range(4, 10):
    for B in (129, 135, 143, 150, 160, 170, 180, 190, 200, 220, 255):
        for C in (40, 44, 48, 52, 56, 60, 64, 68, 72, 75, 80, 88, 96, 104, 112, 120):
            rows = 76 + R * B
            h = heuristic_costs(76, R, B, C, 8)
            T = LOADER_PER_ROW * rows + h['toffoli'] - CODED
            Q = h['qubits'] + J_BROT
            rows_out.append((R, B, C, rows, h['toffoli'], Q, T, T * Q))

for lam in (46.9, 48.0, 50.0, 52.0):
    ok = [x for x in rows_out if lam * x[7] < 292e6]
    print(f'\nlambda_eff {lam}: {len(ok)} feasible shapes, best 12 by cost')
    for x in sorted(ok, key=lambda z: z[7])[:12]:
        print('  %2d %3d %3d rows %4d heurT %5d Q %3d T %6.0f cost %6.1fM' % (
            x[0], x[1], x[2], x[3], x[4], x[5], x[6], lam * x[7] / 1e6))
