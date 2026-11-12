"""Step 3: how good can 1144 projector directions be?  Cheap measurement, no training.

T = sum_k sigma_k t_k t_k^T (t_k symmetric 76x76).  Each t_k = sum_i lam_ki v_ki v_ki^T, so the
one-body leaves {v_ki v_ki^T} are the natural projector pool.  Prints, for several selections of
1144 leaves, the mass of T outside their span and the best 352-term error inside it -- the number
to beat is the current table's 12.14 mHa outside / 13.98 mHa total ceiling.
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


def outside_and_tail(p, T, k_terms=352, rcond=1e-9):
    """(outside mass, best k-term tail inside span{p_b}) for a projector set p (D, M)."""
    Q, _ = np.linalg.qr(p)
    TQ = T @ Q
    Ts = Q.T @ TQ
    outside2 = max(float(np.linalg.norm(T)) ** 2 - float(np.linalg.norm(Ts) ** 2), 0.0)
    ev = np.linalg.eigvalsh(0.5 * (Ts + Ts.T))[::-1]
    tail2 = float(np.sum(ev[k_terms:] ** 2))
    return np.sqrt(outside2), np.sqrt(max(tail2, 0.0))


def main() -> None:
    data = g.load_current()
    inp = g.load_inputs(g.SUB)
    T = g.target(inp)
    cache = ART / 'T_eigh.npz'
    if cache.exists():
        z = np.load(cache)
        ev, vecs = z['ev'], z['vecs']
    else:
        ev, vecs = np.linalg.eigh(T)
        order = np.argsort(-ev)[:1200]
        ev, vecs = ev[order], vecs[:, order]
        np.savez(cache, ev=ev, vecs=vecs)
    print('T top eigenvalue %.4f, 352-tail %.3f mHa' % (ev[0], 1e3 * np.sqrt(np.sum(ev[352:] ** 2))), flush=True)

    N = 76
    # leaves of the top eigenvectors, scored by sigma_k * lam^2 (mass of t_k t_k^T along the leaf)
    cand_u, cand_s, cand_k = [], [], []
    for k in range(len(ev)):
        tk = vecs[:, k].reshape(N, N)
        lam, V = np.linalg.eigh(tk)
        for i in range(N):
            cand_u.append(V[:, i])
            cand_s.append(ev[k] * lam[i] ** 2)
            cand_k.append(k)
    cand_u = np.asarray(cand_u).T          # (N, ncand)
    cand_s = np.asarray(cand_s)
    cand_k = np.asarray(cand_k)
    print('pool %d leaves from %d eigenvectors' % (cand_u.shape[1], len(ev)), flush=True)

    def pmat(idx):
        uu = cand_u[:, idx]
        return np.einsum('ic,jc->ijc', uu, uu).reshape(N * N, -1)

    chosen = np.argsort(-cand_s)[:1144]
    out, tail = outside_and_tail(pmat(chosen), T)
    print('top-1144 leaves by sigma*lam^2: outside %.3f mHa, in-span 352-tail %.3f mHa, total %.3f'
          % (1e3 * out, 1e3 * tail, 1e3 * np.hypot(out, tail)), flush=True)

    # diversity-controlled: at most 8 leaves per eigenvector, so the span covers many t_k
    for per in (2, 4, 8, 16):
        cnt = {}
        sel = []
        for j in np.argsort(-cand_s):
            k = int(cand_k[j])
            if cnt.get(k, 0) >= per:
                continue
            cnt[k] = cnt.get(k, 0) + 1
            sel.append(j)
            if len(sel) == 1144:
                break
        out, tail = outside_and_tail(pmat(np.asarray(sel)), T)
        print('  max %2d leaves/eigvec (%3d eigvecs): outside %.3f mHa, in-span tail %.3f, total %.3f'
              % (per, len(cnt), 1e3 * out, 1e3 * tail, 1e3 * np.hypot(out, tail)), flush=True)

    # current table for reference
    u = np.asarray(data['U'], np.float64)
    u = u / np.linalg.norm(u, axis=2, keepdims=True)
    p_cur = np.einsum('rbp,rbq->rbpq', u, u).reshape(-1, N * N).T
    out, tail = outside_and_tail(p_cur, T)
    print('current 1144 rows: outside %.3f mHa, in-span 352-tail %.3f, total %.3f'
          % (1e3 * out, 1e3 * tail, 1e3 * np.hypot(out, tail)), flush=True)


if __name__ == '__main__':
    main()
