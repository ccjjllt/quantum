"""Exact packed error_2 from the competition verifier's own reference data (no starter kit).

error_2^2 = sum over orbital pairs (i>=j) of m_i m_j (sum_rc X_rc[i,j] X_rc[r,s] - T_ij,rs)^2
with X_rc = sum_b w[r,b,c] u[r,b] u[r,b]^T and T the symmetry-shifted target.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0, str(ROOT/'data/competition/verifiers'))


def target(inputs):
    """(T, M, i, j): packed target, pair multiplicity product, pair indices."""
    ref = inputs.ref
    N = int(ref['orbitals'])
    S = np.asarray(inputs.S, np.float64)
    tei = np.asarray(ref['tei'], np.float64)
    i, j = np.tril_indices(N)
    # T[p,q] = tei[i_p, j_p, i_q, j_q] + shift on the diagonal pairs
    T = tei[i[:, None], j[:, None], i[None, :], j[None, :]].copy()
    # 0.5 S[i,j] delta_{i',j'} + 0.5 S[i',j'] delta_{i,j}
    T += 0.5 * S[i, j][:, None] * (i == j)[None, :]
    T += 0.5 * S[i, j][None, :] * (i == j)[:, None]
    m = np.where(i == j, 1.0, 2.0)
    return T, np.outer(m, m), i, j


def error2(U, w, inputs, prob=None, chunk=1 << 22):
    T, M, i, j = prob if prob is not None else target(inputs)
    R, B, N = U.shape
    R2, C = w.shape[0], w.shape[2]
    u = U / np.linalg.norm(U, axis=2, keepdims=True)
    pairs = (u[:, :, i] * u[:, :, j]).reshape(R, B, -1)          # (R, B, P)
    A = np.einsum('rbc,rbp->rcp', w, pairs).reshape(R*C, -1)      # (R*C, P)
    P = A.shape[1]
    tot = 0.0
    for s in range(0, P, chunk):
        e = min(P, s + chunk)
        H = A[:, s:e].T @ A - T[s:e]
        tot += float(np.sum(M[s:e] * H * H))
    return float(np.sqrt(tot))
