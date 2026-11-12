"""Build a (R, 143, C) seed from a trained table by merging groups and re-selecting atoms.

A group's contribution is sum_c x_c (x) x_c with x_c = sum_b w_bc u_b u_b^T (packed pair vectors).
Merging two groups gives 2B atoms and C1+C2 terms; to reach (R-1, B, C) we
  1. keep the cluster's top-C SVD term directions (the rest cannot fit under C copies),
  2. choose B atoms from the 2B candidates by greedy OMP on those directions,
  3. solve the weights by least squares on the chosen atoms.
Singles keep their atoms and terms (zero-padded copies).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import common as C

prob, ref = C.get_target()
i, j = (np.asarray(t) for t in ref['tril'])


def atoms_of(U):
    u = U / np.linalg.norm(U, axis=2, keepdims=True)
    return (u[:, :, i] * u[:, :, j])          # (R, B, P)


def omp_select(A, Y, k):
    """Greedy select k rows of A (n, P) to span the rows of Y (m, P); returns indices."""
    n = A.shape[0]
    R = Y.copy()
    sel = []
    used = np.zeros(n, bool)
    an = np.einsum('np,np->n', A, A)
    for _ in range(k):
        proj = A @ R.T                     # (n, m)
        score = (proj ** 2).sum(axis=1) / np.maximum(an, 1e-30)
        score[used] = -1.0
        b = int(np.argmax(score))
        sel.append(b)
        used[b] = True
        As = A[sel]
        G = As @ As.T
        coef = np.linalg.solve(G + 1e-12 * np.eye(len(sel)), As @ Y.T)   # (len(sel), m)
        R = Y - (coef.T @ As)
    return np.array(sel)


def compress_cluster(Uc, wc, B, Cnew):
    """Uc (b, N), wc (b, c) -> atoms (B, P), weights (B, Cnew)."""
    A = atoms_of(Uc[None])[0]                       # (b, P)
    X = (wc.T @ A)                                  # (c, P) term vectors
    # best rank-Cnew directions of the cluster's contribution
    if X.shape[0] > Cnew:
        _, s, Vt = np.linalg.svd(X, full_matrices=False)
        Y = s[:Cnew, None] * Vt[:Cnew]              # (Cnew, P) top directions
    else:
        Y = X
    sel = omp_select(A, Y, B)
    As = A[sel]
    G = As @ As.T
    coef = np.linalg.solve(G + 1e-10 * np.trace(G) / len(sel) * np.eye(len(sel)), As @ Y.T)
    W = np.zeros((B, Cnew))
    W[:, :Y.shape[0]] = coef
    return As, W, sel


def build(d, plan, Cnew, Bnew, verbose=True):
    """plan: list of clusters, each a list of old group indices."""
    U = np.asarray(d['U'], np.float64)
    w = np.asarray(d['W'], np.float64)
    off = np.asarray(d['H2_I'], np.float64) - w.sum(axis=1)     # identity offsets
    Un, Wn, On = [], [], []
    for cl in plan:
        if len(cl) == 1:
            r = cl[0]
            Un.append(U[r][:Bnew])
            W = np.zeros((Bnew, Cnew))
            W[:, :w.shape[2]] = w[r][:Bnew]
            Wn.append(W)
            On.append(np.zeros(Cnew))
        else:
            Uc = np.concatenate([U[r] for r in cl], axis=0)
            wc = np.concatenate([w[r] for r in cl], axis=0)      # (sum b, c)
            A, W, sel = compress_cluster(Uc, wc, Bnew, Cnew)
            # atoms: recover unit vectors of the selected atoms
            uu = Uc / np.linalg.norm(Uc, axis=1, keepdims=True)
            Un.append(uu[sel])
            Wn.append(W)
            On.append(np.zeros(Cnew))
    U2 = np.stack(Un)
    W2 = np.stack(Wn)
    O2 = np.stack(On)
    return {'U': U2, 'W': W2, 'H2_I': O2 + W2.sum(axis=1)}


def pair_costs(d, Bnew):
    """Residual of compressing each pair at Cnew=min(C,64) (relative, on the cluster)."""
    U = np.asarray(d['U'], np.float64)
    w = np.asarray(d['W'], np.float64)
    R = w.shape[0]
    out = {}
    for a in range(R):
        for b in range(a + 1, R):
            A = atoms_of(np.concatenate([U[a], U[b]])[None])[0]
            wc = np.concatenate([w[a], w[b]], axis=0)
            X = wc.T @ A
            _, s, Vt = np.linalg.svd(X, full_matrices=False)
            k = min(64, len(s))
            Y = s[:k, None] * Vt[:k]
            sel = omp_select(A, Y, Bnew)
            As = A[sel]
            G = As @ As.T
            coef = np.linalg.solve(G + 1e-10 * np.trace(G) / len(sel) * np.eye(len(sel)), As @ Y.T)
            res = Y - coef.T @ As
            out[(a, b)] = float(np.sum(res ** 2) / np.sum(Y ** 2))
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('src', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('--plan', type=str, required=True, help='e.g. "0,1|2,3|4|5|6|7"')
    ap.add_argument('--C', type=int, required=True)
    ap.add_argument('--B', type=int, default=143)
    ap.add_argument('--pairs-only', action='store_true')
    a = ap.parse_args()
    d = C.load(a.src)
    plan = [[int(x) for x in part.split(',')] for part in a.plan.split('|')]
    if a.pairs_only:
        pc = pair_costs(d, a.B)
        for k, v in sorted(pc.items(), key=lambda kv: kv[1]):
            print(k, '%.6f' % v)
        raise SystemExit
    p = build(d, plan, a.C, a.B)
    np.savez(a.out, **p)
    e = C.e2(p['U'], p['W'], prob)
    print('plan', plan, 'shape', p['W'].shape, 'float e2 %.4f mHa' % (1e3 * e))
