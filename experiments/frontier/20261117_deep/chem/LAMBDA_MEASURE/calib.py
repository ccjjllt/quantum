"""Step 1: calibrate the fit protocol on the known-good shipped shape.

Warm start from the shipped (8,143,44) table, then alternate least squares on
the exact error_2 objective. This answers: (a) does the protocol move at all,
(b) how much e2 does it reach at 143 bases where the shipped sits at 20.0 mHa,
(c) wall time per round.
"""
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import fitlib as F
import infra as I

z = np.load(I.ROOT / 'experiments/frontier/20261117_deep/chem/data/dfthcsos/submission.npz')
U0, w0 = z['U'], z['W']
R, B, N = U0.shape
C = w0.shape[2]
log = F.log
log(f'shipped shape ({R},{B},{C}) K={R*C} rows={N+R*B}')

pb = F.Problem()
log(f'floor(K=352) {pb.floor(352):.4f}  floor(K=480) {pb.floor(480):.4f}')
x0 = np.concatenate([w0.ravel(), U0.ravel()])
log(f'shipped: reduced {pb.e2_reduced(x0, R, B, C):.4f} mHa   '
    f'full {pb.e2_full(x0, R, B, C):.4f} mHa')

t = time.time()
f, g = pb.fg(x0, R, B, C)
log(f'one fg: {time.time()-t:.3f}s  f {f:.4e}')

x = F.alt_min(pb, x0, R, B, C, rounds=2, itw=80, itu=40, tag='calib')
log(f'calibrated: reduced {pb.e2_reduced(x, R, B, C):.4f}  full {pb.e2_full(x, R, B, C):.4f}')
np.savez_compressed(I.CACHE / 'fit_8_143_44.npz', x=x, R=R, B=B, C=C)
log('DONE')
