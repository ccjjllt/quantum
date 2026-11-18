"""Continuation in C at frozen word-U: C=44 -> 43 -> ... , warm-started each step.

!! The C < 44 numbers this script produced before 2026-11-18 01:00 are INVALID:
   `WS.rank_truncate` used to keep a (B, C_old) tensor of rank C, i.e. a
   different model family (44 columns, rank-limited) whose error_2 can come out
   below the span bound -- impossible, which is how the bug was found.  The
   valid, shape-correct C sweep is in RESULT3.md §3 / the Kaggle kernel
   `zhuating/qcc-chem-c-axis-frozen-u` (`kernel_driver.py`, which does its own
   collective truncation).  Keep this script only as the C=44 driver.
"""

Prints, per C, the continuous error_2, the relaxed (block-free) bound and the
"excess" in quadrature -- the number that decides whether the C axis is closable.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import infra as I
import wsolve as WS

N = 76
z = np.load(I.ROOT / 'experiments/frontier/20261117_deep/chem/data/dfthcsos/submission.npz')
U = z['U'].astype(np.float64)
w0 = z['W'].astype(np.float64)
ps = I.cached_pair_space()
H, PA, sqw = ps['H'], ps['PA'], ps['sqw']
R, B, N = U.shape
ps_ev = np.linalg.eigvalsh(H)[::-1]
neg2 = float(np.sum(np.minimum(ps_ev, 0) ** 2))


def floor(K):
    return I.floor_mha(ps_ev, K, neg2)


fu = WS.FixedU(U, H, PA, sqw)

# relaxed bound in the shipped dictionary (block-free), from diag_c2
def relaxed(K):
    P = np.concatenate(fu.Ps, axis=1)
    G = P.T @ P
    A = P.T @ (H @ P)
    g, Vv = np.linalg.eigh(G)
    g = np.maximum(g, 1e-14)
    Wt = Vv / np.sqrt(g)
    M = Wt.T @ A @ Wt
    lam = np.linalg.eigvalsh(0.5 * (M + M.T))[::-1]
    pos = np.maximum(lam, 0)
    return 1e3 * np.sqrt(max(fu.Hfro2 - np.sum(pos[:K] ** 2), 0))


f44 = I.CACHE / 'y_C44_ship.npz'
if f44.exists():
    y = [a for a in np.load(f44)['y']]
else:
    y = fu.y_from_w(w0)
print('start C=44 e2 %.4f' % fu.e2_mha(y), flush=True)

iters = int(sys.argv[1]) if len(sys.argv) > 1 else 12
cgi = int(sys.argv[2]) if len(sys.argv) > 2 else 120
rows = []
for C in [44] + list(range(43, 35, -1)):
    y = WS.rank_truncate(y, C)
    if C == 44:
        y, _ = fu.solve(y, iters=max(iters, 8), cg_iters=cgi, tag='C44', verbose=False)
    else:
        y, _ = fu.solve(y, iters=iters, cg_iters=cgi, tag=f'C{C}', verbose=False)
    e = fu.e2_mha(y)
    rb = relaxed(R * C)
    fl = floor(R * C)
    print(f'C={C:2d} K={R*C:3d}  e2 {e:8.4f}  relaxed-bound {rb:7.4f}  rank-floor {fl:7.4f}'
          f'  excess-vs-relaxed {np.sqrt(max(e**2 - rb**2, 0)):7.4f}  vs-floor {e-fl:8.4f}', flush=True)
    rows.append((C, e, rb, fl))
    np.savez_compressed(I.CACHE / f'y_C{C}.npz', y=np.stack(y), C=C)
print('\nC   e2       vs gate 20.0')
for C, e, rb, fl in rows:
    print(f'{C:2d} {e:8.4f}  {e-20:+.4f}')
