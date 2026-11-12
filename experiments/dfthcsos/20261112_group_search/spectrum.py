"""Spectrum of the verifier target T and what the (8,143,44) table actually represents.

error_2 = || sum_rc x_rc x_rc^T - T ||_F with x_rc = vec(X_rc), T = tei + (S x I + I x S)/2.
Prints T's spectrum, the best rank-R*C tail, the part of T outside span{p_b} and the best
rank-352 approximation inside that span: the ceiling of any weight refit at fixed directions.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
SUB = ROOT / 'artifacts/20261112_eae_candidate/dfthcsos/submission.npz'
sys.path.insert(0, str(ROOT / 'data/competition/verifiers'))
sys.path.insert(0, str(ROOT / 'artifacts/20261112_chem_pipeline/dfthc_refit'))

from dfthcsos.verify import load_inputs  # noqa: E402


def target(inp):
    N = inp.num_orbitals
    T = np.asarray(inp.ref['tei'], np.float64).reshape(N * N, N * N).copy()
    eye = np.eye(N).ravel()
    T += 0.5 * (np.outer(inp.S.ravel(), eye) + np.outer(eye, inp.S.ravel()))
    return T


def main() -> None:
    inp = load_inputs(SUB)
    N = inp.num_orbitals
    T = target(inp)
    ev = np.linalg.eigvalsh(T)[::-1]
    print('T: trace %.6f, ||T||_F %.6f, min eig %.3e' % (np.trace(T), np.linalg.norm(T), ev.min()))
    for k in (44, 88, 352, 704, 1144, 1408):
        print('  rank %4d tail %.6f Ha (%.3f mHa)' % (k, np.sqrt(np.sum(ev[k:] ** 2)), 1e3 * np.sqrt(np.sum(ev[k:] ** 2))))

    z = np.load(SUB)
    u = np.asarray(z['U'], np.float64)
    u /= np.linalg.norm(u, axis=2, keepdims=True)
    R, B, _ = u.shape
    p = np.einsum('rbp,rbq->rbpq', u, u).reshape(R, B, N * N)
    x = np.einsum('rbc,rbm->rcm', inp.w, p).reshape(-1, N * N)
    G = x @ x.T
    Tx = T @ x.T
    e2 = np.sqrt(max(np.sum(G ** 2) - 2 * np.sum(x * Tx.T) + np.linalg.norm(T) ** 2, 0.0))
    print('represented: trace %.6f, error_2 %.6f Ha (%.3f mHa)' % (np.trace(G), e2, 1e3 * e2))

    Q, _ = np.linalg.qr(p.reshape(R * B, N * N).T)   # (N^2, R*B) orthonormal, span{p_b}
    Bm = Q.T @ T @ Q
    ev_in = np.linalg.eigvalsh(Bm)[::-1]
    outside = np.sqrt(max(np.linalg.norm(T) ** 2 - np.linalg.norm(Bm) ** 2, 0.0))
    print('T outside span{p_b}: %.6f Ha (%.3f mHa)' % (outside, 1e3 * outside))
    print('best rank-352 inside span tail: %.6f Ha' % np.sqrt(np.sum(ev_in[352:] ** 2)))
    print('=> fuzzy ceiling at fixed directions: %.3f mHa'
          % (1e3 * np.sqrt(outside ** 2 + np.sum(ev_in[352:] ** 2))))


if __name__ == '__main__':
    main()
