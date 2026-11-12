"""Public (4,255,120) as a seed: float level, B truncation, split to R=5."""
from __future__ import annotations

import numpy as np

import common as C
import seed_rc as S

prob, ref = C.get_target()
d = C.load(C.PUB4)
U = np.asarray(d['U'], np.float64)
w = np.asarray(d['W'], np.float64)
print('pub4 U', U.shape, 'W', w.shape, 'float e2 %.3f mHa' % (1e3 * C.e2(U, w, prob)))
if 'continuous_U' in d:
    Uc = np.asarray(d['continuous_U'], np.float64)
    print('continuous_U float e2 %.3f mHa' % (1e3 * C.e2(Uc, w, prob)))
    print(' U vs continuous_U max diff %.4f' % np.abs(U - Uc).max())



def truncate_B(U, w, B):
    """per group: choose atoms by importance sum_c|w|, keep B, LS-refit weights (same C)."""
    R, B0, C = w.shape
    Un, Wn = np.zeros((R, B, 76)), np.zeros((R, B, C))
    for r in range(R):
        imp = np.abs(w[r]).sum(axis=1)
        sel = np.argsort(-imp)[:B]
        uu = U[r] / np.linalg.norm(U[r], axis=1, keepdims=True)
        Un[r] = uu[sel]
        A = S.atoms_of(uu[sel][None])[0]
        G = A @ A.T
        X = (w[r][sel].T @ A)          # (C, P) keeping only the selected atoms' contribution
        coef = np.linalg.solve(G + 1e-10 * np.trace(G) / B * np.eye(B), A @ X.T)
        Wn[r] = coef
    return Un, Wn


def split_group(U, w, r, Cnew):
    """split group r's copies into two groups with the same atoms (exact)."""
    U1 = np.concatenate([U[:r], U[r:r + 1], U[r:r + 1], U[r + 1:]])
    c = w.shape[2]
    h = c // 2
    W1 = np.zeros((w.shape[0] + 1, w.shape[1], Cnew))
    for g in range(w.shape[0] + 1):
        if g < r:
            W1[g, :, :c] = w[g]
        elif g == r:
            W1[g, :, :h] = w[r][:, :h]
        elif g == r + 1:
            W1[g, :, :c - h] = w[r][:, h:]
        else:
            W1[g, :, :c] = w[g - 1]
    return U1, W1


for B in (255, 200, 180, 160, 143):
    Un, Wn = truncate_B(U, w, B)
    print('B=%3d: float e2 %.3f mHa' % (B, 1e3 * C.e2(Un, Wn, prob)))

Un, Wn = truncate_B(U, w, 143)
for r in range(4):
    U1, W1 = split_group(Un, Wn, r, 75)
    print('split group %d -> (5,143,75): float e2 %.3f mHa' % (r, 1e3 * C.e2(U1, W1, prob)))
