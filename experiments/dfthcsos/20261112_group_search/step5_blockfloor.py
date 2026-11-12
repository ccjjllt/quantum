"""Step 5: what the 8x143x44 block structure costs -- the ideal coefficient matrix is not block diagonal.

The unconstrained best rank-RC fit inside the current 1144-dim span has error 13.977 mHa.  Its
coefficient matrix M* is obtained by M* = C^-1 A* C^-T (C = Q^T P, A* = the top-RC eigenpairs of
Ts = Q^T T Q).  M* is the exact minimum of error^2 = tr(M G M G) - 2 tr(M Q0) + ||T||^2, so
keeping only its block-diagonal part (the only part the model can use) and cutting each block to
rank C measures how much the group structure itself costs.
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


def main() -> None:
    data = g.load_current()
    inp = g.load_inputs(g.SUB)
    sp = g.Space(data['U'], inp)
    R, B, C = sp.R, sp.B, sp.C
    ev, V = np.linalg.eigh(sp.Ts)
    order = np.argsort(-ev)[:R * C]
    A_star = (V[:, order] * ev[order]) @ V[:, order].T
    Cinv = np.linalg.inv(sp.Cmat)
    M = Cinv @ A_star @ Cinv.T
    M = 0.5 * (M + M.T)
    print('ideal rank-%d fit in span: %.4f mHa (outside %.3f)'
          % (R * C, 1e3 * np.sqrt(np.linalg.norm(A_star - sp.Ts) ** 2 + sp.outside2),
             1e3 * np.sqrt(sp.outside2)), flush=True)
    print('M*: ||M|| %.4f, block-diagonal share %.3f, error of the full M* %.4f mHa'
          % (np.linalg.norm(M), sum(np.linalg.norm(M[r * B:(r + 1) * B, r * B:(r + 1) * B]) ** 2
                                    for r in range(R)) / np.linalg.norm(M) ** 2, 1e3 * sp.error2_M(M)),
          flush=True)
    Mb = np.zeros_like(M)
    ranks = []
    for r in range(R):
        s = slice(r * B, (r + 1) * B)
        Mb[s, s] = M[s, s]
        e = np.linalg.eigvalsh(0.5 * (M[s, s] + M[s, s].T))
        ranks.append(int((e > e.max() * 1e-6).sum()))
    print('block-diagonal part: %.4f mHa' % (1e3 * sp.error2_M(Mb)), flush=True)
    Mc = np.zeros_like(M)
    for r in range(R):
        s = slice(r * B, (r + 1) * B)
        e, Vb = np.linalg.eigh(0.5 * (M[s, s] + M[s, s].T))
        keep = np.argsort(-e)[:C]
        Mc[s, s] = (Vb[:, keep] * np.maximum(e[keep], 0.0)) @ Vb[:, keep].T
    print('block-diagonal + rank-%d cut: %.4f mHa' % (C, 1e3 * sp.error2_M(Mc)), flush=True)
    print('per-block rank of M* (tolerance 1e-6 of the block top eigenvalue):', ranks, flush=True)
    w0 = data['W']
    Mtr = np.zeros_like(sp.G)
    for r in range(R):
        s = slice(r * B, (r + 1) * B)
        Mtr[s, s] = w0[r] @ w0[r].T
    out = {'ideal_in_span': 1e3 * np.sqrt(np.linalg.norm(A_star - sp.Ts) ** 2 + sp.outside2),
           'outside': 1e3 * np.sqrt(sp.outside2), 'M_star_full': 1e3 * sp.error2_M(M),
           'M_star_blockdiag': 1e3 * sp.error2_M(Mb), 'M_star_blockdiag_rankcut': 1e3 * sp.error2_M(Mc),
           'trained': 1e3 * sp.error2_M(Mtr), 'block_ranks': ranks}
    with open(ART / 'step5.json', 'w') as f:
        json.dump(out, f, indent=1)
    print('trained M: %.4f mHa' % (1e3 * sp.error2_M(Mtr)), flush=True)


if __name__ == '__main__':
    main()
