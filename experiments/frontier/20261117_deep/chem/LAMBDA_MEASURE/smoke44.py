"""Smoke test: LM/CG w-solve at C=44 from the shipped weights (fixed word-U)."""
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import infra as I
import wsolve as WS

z = np.load(I.ROOT / 'experiments/frontier/20261117_deep/chem/data/dfthcsos/submission.npz')
U = z['U'].astype(np.float64)
w0 = z['W'].astype(np.float64)
ps = I.cached_pair_space()
H, PA, sqw = ps['H'], ps['PA'], ps['sqw']

fu = WS.FixedU(U, H, PA, sqw)
y0 = fu.y_from_w(w0)
print('start e2 %.4f mHa' % fu.e2_mha(y0))
t = time.time()
f, g = fu.fg(y0)
print('fg time %.3f s' % (time.time() - t))
t = time.time()
fu.A(y0, [0.01 * a for a in y0])
print('A  time %.3f s' % (time.time() - t))

y, hist = fu.solve(y0, iters=int(sys.argv[1]) if len(sys.argv) > 1 else 10,
                   cg_iters=int(sys.argv[2]) if len(sys.argv) > 2 else 100,
                   tag="C44", exact_every=1)
print('final e2 %.4f mHa' % fu.e2_mha(y))
np.savez_compressed(I.CACHE / 'y_C44_smoke.npz', y=np.stack(y), C=y[0].shape[1])
