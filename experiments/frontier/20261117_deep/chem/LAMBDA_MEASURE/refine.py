"""Continue an alternating fit from a saved checkpoint for MANY rounds."""
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import fitlib as F
import infra as I

name = sys.argv[1]
rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 20
itw = int(sys.argv[3]) if len(sys.argv) > 3 else 200
itu = int(sys.argv[4]) if len(sys.argv) > 4 else 100
log = F.log

z = np.load(I.CACHE / f'{name}.npz')
x, R, B, C = z['x'], int(z['R']), int(z['B']), int(z['C'])
pb = F.Problem()
log(f'{name}: shape ({R},{B},{C}) K={R*C} start {pb.e2_reduced(x, R, B, C):.3f} mHa '
    f'floor {pb.floor(R*C):.3f}')
t0 = time.time()
best = (pb.e2_reduced(x, R, B, C), x.copy())
for rd in range(rounds):
    x = F.alt_min(pb, x, R, B, C, rounds=1, itw=itw, itu=itu, tag=name)
    e = pb.e2_reduced(x, R, B, C)
    if e < best[0]:
        best = (e, x.copy())
        np.savez_compressed(I.CACHE / f'{name}_long.npz', x=x, R=R, B=B, C=C)
    if time.time() - t0 > 3000:
        log('wall stop')
        break
log(f'{name}: FINAL {pb.e2_reduced(best[1], R, B, C):.4f} mHa after {rounds} rounds '
    f'[{time.time()-t0:.0f}s]')
