"""B truncation of the public (4,255,120) table, two selections, then weights re-fit.

    python btrunc.py B [--select importance|omp] [--C 120] OUT.npz

The weights are re-solved on the kept atoms against the full group contribution (all 255 atoms),
in the verifier's pair metric, so the truncation only drops what the kept dictionary cannot span.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

import common as C
import seed_rc as S

prob, ref = C.get_target()
i, j = (np.asarray(t) for t in ref['tril'])
dvec = np.sqrt(np.where(i == j, 1.0, 2.0))


def atoms(uu):
    return (uu[:, i] * uu[:, j]) * dvec[None, :]


def select_importance(w, B):
    imp = (np.abs(w).sum(axis=1))
    return np.argsort(-imp)[:B]


def select_omp(uu, w, B):
    A = atoms(uu)                       # (255, P) weighted metric
    X = w.T @ A                         # (C, P)
    sel = S.omp_select(A, X, B)
    return np.sort(sel)


def rebuild(U, w, sel):
    """new atoms = selected rows; weights = weighted LS against the full contribution."""
    uu = U / np.linalg.norm(U, axis=1, keepdims=True)
    A = atoms(uu)
    X = w.T @ A
    As = A[sel]
    G = As @ As.T
    coef = np.linalg.solve(G + 1e-10 * np.trace(G) / len(sel) * np.eye(len(sel)), As @ X.T)
    return uu[sel], coef


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('B', type=int)
    ap.add_argument('out', type=Path)
    ap.add_argument('--select', choices=('importance', 'omp'), default='importance')
    ap.add_argument('--C', type=int, default=120)
    a = ap.parse_args()
    d = C.load(C.PUB4)
    U = np.asarray(d['U'], np.float64)
    w = np.asarray(d['W'], np.float64)
    Un, Wn = [], []
    for r in range(4):
        uu = U[r] / np.linalg.norm(U[r], axis=1, keepdims=True)
        sel = select_importance(w[r], a.B) if a.select == 'importance' else select_omp(uu, w[r], a.B)
        u2, coef = rebuild(U[r], w[r], sel)
        if a.C < w.shape[2]:
            # rank-truncate the copies in the same metric
            Y = coef.T @ atoms(u2)                       # (C, P)
            _, s, Vt = np.linalg.svd(Y, full_matrices=False)
            Y = s[:a.C, None] * Vt[:a.C]
            A2 = atoms(u2)
            G2 = A2 @ A2.T
            coef = np.linalg.solve(G2 + 1e-10 * np.trace(G2) / a.B * np.eye(a.B), A2 @ Y.T)
        Wn.append(coef)
        Un.append(u2)
    p = {'U': np.stack(Un), 'W': np.stack(Wn)}
    p['H2_I'] = p['W'].sum(axis=1)
    np.savez(a.out, **p)
    print('%s B=%d C=%d: float e2 %.3f mHa' % (a.select, a.B, p['W'].shape[2],
                                              1e3 * C.e2(p['U'], p['W'], prob)))


if __name__ == '__main__':
    main()
