"""Step 2: measure rho(B/C) at FIXED K = 352 by cutting B at R=8, C=44.

The shipped (8,143,44) is the warm start; cutting the basis to B < 143 and
re-solving the weights, then alternating, measures exactly what the Q_AXIS
rho law extrapolates. Every number is the exact full-space error_2.
"""
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import fitlib as F
import infra as I

log = F.log
z = np.load(I.ROOT / 'experiments/frontier/20261117_deep/chem/data/dfthcsos/submission.npz')
U0, w0 = z['U'], z['W']
R, B0, N = U0.shape
C = w0.shape[2]
x_ship = np.concatenate([w0.ravel(), U0.ravel()])
pb = F.Problem()
log(f'warm start {R},{B0},{C} shipped e2 {pb.e2_reduced(x_ship, R, B0, C):.3f}')

out = {}
for B in (143, 129, 96, 76, 62):
    if B == B0:
        x = x_ship
    else:
        x = F.init_truncate(pb, x_ship, R, B0, C, B)
    e0 = pb.e2_reduced(x, R, B, C)
    log(f'B={B}: init e2 {e0:.3f} mHa (B/C {B/C:.3f})')
    x = F.alt_min(pb, x, R, B, C, rounds=3, itw=120, itu=60, tag=f'B{B}')
    e = pb.e2_reduced(x, R, B, C)
    fl = pb.floor(R * C)
    log(f'B={B}: FINAL e2 {e:.3f} mHa  rho {e/fl:.2f}  (law rho '
        f'{1.93*(3.25/(B/C))**1.95:.2f})')
    out[B] = dict(e2=e, rho=e / fl, bc=B / C, rows=N + R * B)
    np.savez_compressed(I.CACHE / f'fit_8_{B}_{C}.npz', x=x, R=R, B=B, C=C)

import json
(I.CACHE / 'ladder.json').write_text(json.dumps(out, indent=1))
log('DONE')
