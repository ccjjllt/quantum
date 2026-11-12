"""Step 6: construct the ideal coefficient matrix and measure what the 8x143 block structure loses.

M is a coefficient matrix in the p-basis: A = P M P^T, error^2 = tr(M G M G) - 2 tr(M Q0) + ||T||^2.
The unconstrained best rank-RC model in the span has error 6.93 mHa; converting it to the p-basis
and keeping only its block-diagonal part (then rank-C truncating each block) gives a *feasible*
model of the current shape.  Its error says how much the group structure itself costs, and the
same construction on a co-clustered partition tests whether another grouping is better.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gs_lib as g  # noqa: E402

ART = g.ART


def to_w(M, R, B, C, trunc=True):
    w = np.zeros((R, B, C))
    for r in range(R):
        s = slice(r * B, (r + 1) * B)
        blk = 0.5 * (M[s, s] + M[s, s].T)
        ev, V = np.linalg.eigh(blk)
        order = np.argsort(-ev)[:C]
        lam = np.maximum(ev[order], 0.0)
        w[r] = (V[:, order] * np.sqrt(lam)).T.T if False else (V[:, order] * np.sqrt(lam))
    return w


def measure(sp, M, R, B, C, label, log=print):
    e_full = 1e3 * sp.error2_M(M)
    w = to_w(M, R, B, C)
    e_rank = 1e3 * sp.error2(w)
    log('  %-28s block-diag M: %.3f mHa ; rank-%d cut: %.3f mHa' % (label, e_full, C, e_rank))
    return w, e_full, e_rank


def main() -> None:
    data = g.load_current()
    inp = g.load_inputs(g.SUB)
    sp = g.Space(data['U'], inp)
    R, B, C = sp.R, sp.B, sp.C
    log = print
    # ideal rank-RC fit of Ts in coordinates, mapped back to the p-basis
    ev, V = np.linalg.eigh(sp.Ts)
    order = np.argsort(-ev)[:R * C]
    A_ideal = (V[:, order] * ev[order]) @ V[:, order].T
    Cinv = np.linalg.inv(sp.Cmat)
    M_ideal = Cinv @ A_ideal @ Cinv.T
    M_ideal = 0.5 * (M_ideal + M_ideal.T)
    log('ideal rank-%d fit: %.3f mHa in coordinates; ||M_ideal|| %.3f, min eig %.3e'
        % (R * C, 1e3 * np.sqrt(np.linalg.norm(A_ideal - sp.Ts) ** 2 + sp.outside2),
           np.linalg.norm(M_ideal), np.linalg.eigvalsh(M_ideal).min()))
    log('current partition:')
    Mc = np.zeros_like(M_ideal)
    for r in range(R):
        s = slice(r * B, (r + 1) * B)
        Mc[s, s] = M_ideal[s, s]
    measure(sp, Mc, R, B, C, 'M_ideal block-diag')
    # trained M for reference
    w0 = data['W']
    Mtr = np.zeros_like(sp.G)
    for r in range(R):
        s = slice(r * B, (r + 1) * B)
        Mtr[s, s] = w0[r] @ w0[r].T
    log('  trained M: %.3f mHa' % (1e3 * sp.error2_M(Mtr)))

    # co-clustering of the ideal M: rows of the weighted eigenvector matrix
    Uw = (V[:, order] * np.sqrt(np.maximum(ev[order], 0.0))).T     # (RC, 1144)
    rng = np.random.default_rng(0)
    best = None
    for seed in range(6):
        cent = Uw[:, rng.choice(Uw.shape[1], R, replace=False)].T  # (R, RC)
        for _ in range(60):
            d = ((Uw.T[:, None, :] - cent[None, :, :]) ** 2).sum(-1)
            lab = d.argmin(axis=1)
            for r in range(R):
                if np.any(lab == r):
                    cent[r] = Uw.T[lab == r].mean(axis=0)
        blocks = [np.where(lab == r)[0] for r in range(R)]
        # rebalance to exactly B per group by moving the weakest members
        while max(len(b) for b in blocks) > B:
            big = max(range(R), key=lambda r: len(blocks[r]))
            small = min(range(R), key=lambda r: len(blocks[r]))
            v = blocks[big][np.argmin(np.abs(Uw[:, blocks[big]]).sum(0))]
            blocks[big] = np.delete(blocks[big], np.where(blocks[big] == v)[0][0])
            blocks[small] = np.append(blocks[small], v)
        perm = np.concatenate(blocks)
        Mp = np.zeros_like(M_ideal)
        for r in range(R):
            idx = perm[r * B:(r + 1) * B]
            Mp[np.ix_(idx, idx)] = M_ideal[np.ix_(idx, idx)]
        w, e_full, e_rank = measure(sp, Mp, R, B, C, 'co-cluster seed %d' % seed)
        if best is None or e_rank < best[0]:
            best = (e_rank, perm, w)
        np.savez(ART / f'idealM_seed{seed}.npz', perm=perm, W=w, H2_I=w.sum(axis=1))
    log('best co-cluster rank-cut: %.3f mHa' % best[0])
    np.savez(ART / 'idealM_best.npz', perm=best[1], W=best[2])


if __name__ == '__main__':
    main()
