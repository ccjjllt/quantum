"""Fit one (R,B,C) shape on the exact error_2 objective and save (U, w).

Usage: fit_shape.py R B C [--init ship|spec] [--rounds N] [--itw N] [--itu N]
                       [--seed N] [--tag str] [--extra K]
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import fitlib as F
import infra as I

ap = argparse.ArgumentParser()
ap.add_argument('R', type=int)
ap.add_argument('B', type=int)
ap.add_argument('C', type=int)
ap.add_argument('--init', default='ship')
ap.add_argument('--rounds', type=int, default=4)
ap.add_argument('--itw', type=int, default=150)
ap.add_argument('--itu', type=int, default=80)
ap.add_argument('--seed', type=int, default=0)
ap.add_argument('--tag', default='')
ap.add_argument('--wall', type=float, default=0.0)
a = ap.parse_args()
log = F.log

pb = F.Problem()
R, B, C = a.R, a.B, a.C
K = R * C
rows = F.N + R * B
log(f'shape ({R},{B},{C}) K {K} rows {rows} B/C {B/C:.3f} floor {pb.floor(K):.4f} mHa')

x0 = None
if a.init == 'ship':
    z = np.load(I.ROOT / 'experiments/frontier/20261117_deep/chem/data/dfthcsos/submission.npz')
    Xs0 = F.shipped_Xs(z)
    t = time.time()
    tg = F.targets_from_shipped_plus_residual(pb, Xs0, K)
    log(f'targets: {len(tg)} columns ({len(Xs0)} shipped + {len(tg)-len(Xs0)} residual) '
        f'[{time.time()-t:.0f}s]')
    x0 = F.init_from_targets(pb, tg, R, B, C, seed=a.seed)
else:
    # pure spectral targets: the top-K eigenvectors of H
    ev, evec = np.linalg.eigh(pb.H)
    order = np.argsort(ev)[::-1][:K]
    tg = []
    for k in order:
        v = evec[:, k]
        M = np.zeros((F.N, F.N))
        M[pb.PA[:, 0], pb.PA[:, 1]] = v / pb.sqw
        M = np.triu(M) + np.triu(M, 1).T
        tg.append(np.sqrt(max(ev[k], 0.0)) * M)
    x0 = F.init_from_targets(pb, tg, R, B, C, seed=a.seed)

log(f'init e2 {pb.e2_reduced(x0, R, B, C):.3f} mHa (floor {pb.floor(K):.3f})')
x = F.alt_min(pb, x0, R, B, C, rounds=a.rounds, itw=a.itw, itu=a.itu,
              tag=a.tag or 'fit', wall=(a.wall or None))
e2 = pb.e2_reduced(x, R, B, C)
log(f'FINAL ({R},{B},{C}) init={a.init} seed={a.seed}: e2 {e2:.4f} mHa '
    f'= {e2/pb.floor(K):.2f}x floor')

name = a.tag or f'fit_{R}_{B}_{C}_{a.init}_s{a.seed}'
np.savez_compressed(I.CACHE / f'{name}.npz', x=x, R=R, B=B, C=C, e2=e2,
                    floor=pb.floor(K))
(I.CACHE / f'{name}.json').write_text(json.dumps(
    dict(R=R, B=B, C=C, K=K, rows=rows, e2=e2, floor=pb.floor(K),
         rho=e2 / pb.floor(K), init=a.init, seed=a.seed,
         rounds=a.rounds, itw=a.itw, itu=a.itu), indent=1))
log('DONE')
