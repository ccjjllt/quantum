"""Probe (R,136,96) from the shipped table: drop 7 basis vectors, matched-filter
the extra 52 columns per group against the residual in the group's span, refine.

This isolates B=136 + C=96 (the target's accuracy parameters) at the proven R.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import fitlib as F
import infra as I

log = F.log
R = int(sys.argv[1]) if len(sys.argv) > 1 else 8
B = int(sys.argv[2]) if len(sys.argv) > 2 else 136
C = int(sys.argv[3]) if len(sys.argv) > 3 else 96
rounds = int(sys.argv[4]) if len(sys.argv) > 4 else 6
pb = F.Problem()
z = np.load(I.ROOT / 'experiments/frontier/20261117_deep/chem/data/dfthcsos/submission.npz')
U0, w0 = z['U'], z['W']
B0, C0 = w0.shape[1], w0.shape[2]
assert R == U0.shape[0]
U = np.zeros((R, B, F.N))
w = np.zeros((R, B, C))
for r in range(R):
    use = np.abs(w0[r]).sum(axis=1)
    keep = np.argsort(-use)[:B]
    U[r] = U0[r][keep] / np.linalg.norm(U0[r][keep], axis=1, keepdims=True)
    w[r, :, :C0] = w0[r][keep]
Y0 = pb.Y_of(U, w[:, :, :C0])
Res = pb.H - Y0 @ Y0.T
for r in range(R):
    P = pb.proj(U[r])
    M = P.T @ (Res @ P)
    M = 0.5 * (M + M.T)
    lam, vec = np.linalg.eigh(M)
    order = np.argsort(lam)[::-1]
    n_new = C - C0
    for j, i in enumerate(order[:n_new]):
        if lam[i] <= 0:
            break
        v = vec[:, i]
        Pv = P @ v
        w[r, :, C0 + j] = np.sqrt(lam[i]) * v / np.linalg.norm(Pv)
x = np.concatenate([w.ravel(), U.ravel()])
log(f'({R},{B},{C}) K {R*C} rows {F.N+R*B} B/C {B/C:.2f} floor {pb.floor(R*C):.3f}')
log(f'   init e2 {pb.e2_reduced(x, R, B, C):.3f} mHa')
x = F.alt_min(pb, x, R, B, C, rounds=rounds, itw=250, itu=120, tag=f'probe{R}_{B}_{C}')
e = pb.e2_reduced(x, R, B, C)
log(f'   FINAL ({R},{B},{C}): {e:.3f} mHa = {e/pb.floor(R*C):.2f}x floor')
np.savez_compressed(I.CACHE / f'fit_{R}_{B}_{C}.npz', x=x, R=R, B=B, C=C)
