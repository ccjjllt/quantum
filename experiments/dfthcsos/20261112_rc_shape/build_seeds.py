"""Seed errors for the merge+re-select construction at each target shape (no training)."""
from __future__ import annotations

import time

import numpy as np

import common as C
import seed_rc as S

prob, ref = C.get_target()
src = C.CURRENT
d = C.load(src)

plans = {
    7: [[2, 4], [0], [1], [3], [5], [6], [7]],
    6: [[2, 4], [1, 5], [0], [3], [6], [7]],
    5: [[2, 4], [1, 5], [3, 6], [0], [7]],
    4: [[2, 4], [1, 5], [3, 6], [0, 7]],
}
for R, Cnew in ((7, 50), (7, 52), (7, 55), (6, 60), (6, 64), (6, 72),
                (5, 72), (5, 75), (5, 80), (4, 96), (4, 120)):
    t0 = time.time()
    p = S.build(d, plans[R], Cnew, 143)
    e = C.e2(p['U'], p['W'], prob)
    print('R=%d C=%3d terms %3d  seed float e2 %8.3f mHa  (%.0fs)' % (
        R, Cnew, R * Cnew, 1e3 * e, time.time() - t0), flush=True)
    np.savez(f'artifacts_seed_R{R}_C{Cnew}.npz', **p)
