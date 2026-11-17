"""Does K growth at the proven B=143 work? (8,143,44) -> (8,143,88).

The shipped basis is kept; the 44 new columns per group are initialised by a
matched filter on the residual *in the group's span*:

    M = P^T (H - Y0 Y0^T) P ,  M v_i = lam_i v_i  ->  y_i = sqrt(lam_i) P v_i/||P v_i||

which is the exact best rank-|new| update if the residual is diagonal in that
span. This isolates "more columns at fixed basis" from "smaller basis".
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
R, B, N = U0.shape
C0 = w0.shape[2]
pb = F.Problem()
U = U0 / np.linalg.norm(U0, axis=2, keepdims=True)

for C in (88, 128):
    log(f'== grow to ({R},{B},{C}) K={R*C} rows={N+R*B} B/C {B/C:.2f} '
        f'floor {pb.floor(R*C):.3f}')
    w = np.zeros((R, B, C))
    w[:, :, :C0] = w0
    Y0 = pb.Y_of(U, w[:, :, :C0])
    Res = pb.H - Y0 @ Y0.T
    for r in range(R):
        P = pb.proj(U[r])
        RP = Res @ P
        M = P.T @ RP
        M = 0.5 * (M + M.T)
        lam, vec = np.linalg.eigh(M)
        order = np.argsort(lam)[::-1][:C - C0]
        for j, i in enumerate(order):
            if lam[i] <= 0:
                break
            v = vec[:, i]
            nrm = np.linalg.norm(P @ v)
            w[r, :, C0 + j] = np.sqrt(lam[i]) * v / nrm
    x = np.concatenate([w.ravel(), U.ravel()])
    log(f'   init e2 {pb.e2_reduced(x, R, B, C):.3f} mHa')
    x = F.alt_min(pb, x, R, B, C, rounds=6, itw=200, itu=100, tag=f'grow{C}')
    e = pb.e2_reduced(x, R, B, C)
    log(f'   FINAL ({R},{B},{C}): {e:.3f} mHa = {e/pb.floor(R*C):.2f}x floor')
    np.savez_compressed(I.CACHE / f'fit_8_{B}_{C}.npz', x=x, R=R, B=B, C=C)
