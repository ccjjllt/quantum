"""Diagnostics of the current (8,143,44) DF-THC table: where Lambda and the error budget sit.

Reads the verified submission npz, prints the official metrics at 8 bits, the continuous
(no angle rounding) metrics of the same U/W, and per-group / per-basis statistics used to
design new group selections.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
SUB = ROOT / 'artifacts/20261112_eae_candidate/dfthcsos/submission.npz'
sys.path.insert(0, str(ROOT / 'data/competition/verifiers'))
sys.path.insert(0, str(ROOT / 'artifacts/20261112_chem_pipeline/dfthc_refit'))

from dfthcsos.scoreinfra.dfthc_math import evaluate_dfthc_vectors  # noqa: E402
from dfthcsos.verify import evaluate_words, load_inputs  # noqa: E402


def continuous_metrics(inp, U):
    u = np.asarray(U, np.float64)
    u = u / np.linalg.norm(u, axis=2, keepdims=True)
    N = u.shape[2]
    # one-body rows: exact eigenvectors of h1_prime built from these U/W
    from dfthcsos.scoreinfra.dfthc_math import build_h1_prime, reconstruct_x
    X = reconstruct_x(u, inp.w)
    h1p = build_h1_prime(inp.ref['h1_thc'], inp.S, inp.beta_1, inp.ref['electrons'], inp.W, X)
    _, vecs = np.linalg.eigh(h1p)
    u_all = np.vstack([vecs.T, u.reshape(-1, N)])
    m = evaluate_dfthc_vectors(u_all, inp.w, inp.W, inp.S, inp.beta_1, inp.ref,
                               energy_upper=inp.energy_upper)
    return {k: float(v) for k, v in m.items() if not isinstance(v, bool)}, h1p


def main() -> None:
    with np.load(SUB, allow_pickle=False) as z:
        words = np.asarray(z['angle_words'], np.int64)
        tree = np.asarray(z['tree_edges'], np.int64)
        U = np.asarray(z['U'], np.float64)
    inp = load_inputs(SUB)
    R, B, C = inp.w.shape
    print('shape', (R, B, C), 'N', inp.num_orbitals)
    m8 = evaluate_words(inp, words, tree, 8)
    print('8bit', json.dumps({k: float(m8[k]) for k in ('error_1', 'error_2', 'Lambda', 'E_gap', 'lambda_eff')}))
    mc, h1p = continuous_metrics(inp, U)
    print('cont', json.dumps({k: mc[k] for k in ('error_1', 'error_2', 'Lambda', 'E_gap', 'lambda_eff')}))

    w, W = inp.W, inp.W  # placeholder
    w = inp.w
    W = inp.W  # W^(rho c) = H2_I - sum_b w
    lam = np.linalg.eigvalsh(h1p)
    l1 = np.abs(w).sum(axis=1)              # (R,C) sum_b |w_b|
    s = w.sum(axis=1)                       # (R,C)
    wB = W + s                              # H2_I
    m = l1 + np.abs(wB)
    Lam = np.abs(lam).sum() + 0.25 * np.sum(m ** 2)
    print('Lambda split: one-body |lam| %.6f  two-body 1/4 sum m^2 %.6f' %
          (np.abs(lam).sum(), 0.25 * np.sum(m ** 2)))
    print('lambda_j: n %d, sum %.6f, sum|.| %.6f, min %.6f max %.6f' %
          (lam.size, lam.sum(), np.abs(lam).sum(), lam.min(), lam.max()))
    print('|wB| max %.6f  sum %.6f ; sum_b|w| sum %.6f' % (np.abs(wB).max(), np.abs(wB).sum(), l1.sum()))

    u = U / np.linalg.norm(U, axis=2, keepdims=True)
    contrib = np.linalg.norm(w, axis=2)                   # (R,B) weight-vector norm per basis
    # exact Frobenius contribution of a basis vector is not separable, use squared weight
    sq = (w ** 2).sum(axis=2)                             # (R,B)
    order = np.argsort(sq.ravel())
    print('basis squared-weight quantiles (R*B=%d):' % sq.size,
          np.round(np.quantile(sq, [0, .01, .05, .1, .25, .5, .75, .9, 1.0]), 12))
    print('weakest 12 (group,index,sq,||w_b||):')
    for flat in order[:12]:
        r, b = divmod(int(flat), B)
        print('   r%d b%d sq %.3e norm %.3e' % (r, b, sq[r, b], contrib[r, b]))
    print('group importance (sum_c ||X_rc||^2):')
    from structure import importance
    imp = importance(U, w)
    print('  ', np.round(imp / imp.sum(), 5))
    # cross-group overlap of basis sets: max |<u_i,u_j>| between different groups
    G = np.einsum('rbp,sdp->rbsd', u, u)
    worst = []
    for r in range(R):
        for s in range(r + 1, R):
            a = np.abs(G[r, :, s, :])
            worst.append((float(a.max()), r, s, int(np.unravel_index(a.argmax(), a.shape)[0]),
                          int(np.unravel_index(a.argmax(), a.shape)[1])))
    worst.sort(reverse=True)
    print('cross-group max |overlap| top5:', [(round(v, 6), r, s, b1, b2) for v, r, s, b1, b2 in worst[:5]])


if __name__ == '__main__':
    main()
