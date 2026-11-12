"""Step 7: two direct probes of the group-selection levers, at fixed T/Q.

(A) directions: replace the k weakest rows by greedy residual directions of T outside the current
    1144-dim span, then minimise error_2 at Lambda ~ 290 (the current level).  Current floor: 19.8.
(B) partition: swap k direction pairs between groups (weights carried along), refit with the AL and
    compare lambda_eff.  Current point: 46.900 (same code, same target).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gs_lib as g  # noqa: E402

ART = g.ART

N = 76


def residual_directions(sp, count, log=print):
    """Greedy directions for T's part outside span{p_b}: top eigenvectors of T_out, then of each."""
    T = sp.T
    Q = sp.Q                                           # (5776, 1144)
    Tout = T - Q @ (sp.Ts @ Q.T)
    Tout = 0.5 * (Tout + Tout.T)
    print('  ||T_out|| = %.4f mHa' % (1e3 * np.linalg.norm(Tout)), flush=True)
    dirs = []
    top = 120
    ev, V = np.linalg.eigh(Tout)
    order = np.argsort(-ev)[:top]
    for j in order:
        tj = V[:, j].reshape(N, N)
        lam, W = np.linalg.eigh(0.5 * (tj + tj.T))
        for i in range(2):
            dirs.append(W[:, -1 - i])
        if len(dirs) >= count:
            break
    return np.asarray(dirs[:count]).T, Tout


def weakest_rows(w, count):
    sq = (w ** 2).sum(axis=2).ravel()
    return np.argsort(sq)[:count]


def main() -> None:
    data = g.load_current()
    inp = g.load_inputs(g.SUB)
    sp = g.Space(data['U'], inp)
    R, B, C = sp.R, sp.B, sp.C
    w0, W0 = data['W'], data['H2_I'] - data['W'].sum(axis=1)
    u0 = sp.u.reshape(R * B, N).copy()
    rows = {}

    print('(A) residual-direction fill, error floor at Lambda ~ 290:', flush=True)
    rows['base'] = dict(e2=19.808, Lam=287.2)
    for k, Lam0 in ((32, 290.0), (128, 290.0), (256, 290.0)):
        dirs, Tout = residual_directions(sp, k)
        drop = weakest_rows(w0, k)
        u = u0.copy()
        # replace the weakest rows but keep group sizes: the k weakest may sit in any group, so
        # replace in place (the group structure is unchanged) -- new directions get zero weight.
        u[drop] = dirs.T
        sp2 = g.Space(u.reshape(R, B, N), inp)
        print('  k=%d: outside span %.3f mHa (was %.3f)' % (k, 1e3 * np.sqrt(sp2.outside2),
                                                           1e3 * np.sqrt(sp.outside2)), flush=True)
        wnew = w0.copy()
        flat = wnew.reshape(R * B, C)
        flat[drop] = 0.0
        t0 = time.time()
        w, W, e2, gap, Lam = sp2.fit_error_at_lambda(wnew, W0, Lam0, maxiter=600, log=print)
        rows[f'fill{k}'] = dict(e2=1e3 * e2, Lam=Lam, gap=gap, outside=1e3 * np.sqrt(sp2.outside2))
        np.savez(ART / f'fill{k}.npz', U=u.reshape(R, B, N), W=w, H2_I=W + w.sum(axis=1))
        print('    -> %.3f mHa at Lambda %.2f (%.0f s)' % (1e3 * e2, Lam, time.time() - t0), flush=True)

    print('(B) partition swaps + AL refit:', flush=True)
    rng = np.random.default_rng(3)
    idx = np.arange(R * B)
    for k in (2, 10, 40):
        perm = idx.copy()
        for _ in range(k):
            r1, r2 = rng.choice(R, 2, replace=False)
            a = rng.integers(r1 * B, (r1 + 1) * B)
            b = rng.integers(r2 * B, (r2 + 1) * B)
            perm[a], perm[b] = perm[b], perm[a]
        u = u0[perm].reshape(R, B, N)
        w = w0.reshape(R * B, C)[perm].reshape(R, B, C)
        e2_init = sp.error2(w, perm)
        res = sp.refit(w, sp.init_W(w, perm, w0, W0), perm=perm, target_mha=19.999, outer=8,
                       inner=150, log=lambda *a: None)
        ww, WW, e2, gap, Lam, lam = res
        rows[f'swap{k}'] = dict(e2_init=1e3 * e2_init, e2=1e3 * e2, Lam=Lam, gap=gap, lam_eff=lam)
        print('  swap %d: init %.2f mHa -> refit %.3f mHa  Lambda %.2f  E_gap %.4f  lambda_eff %.4f'
              % (k, 1e3 * e2_init, 1e3 * e2, Lam, gap, lam), flush=True)
        np.savez(ART / f'swap{k}.npz', perm=perm, W=ww, H2_I=WW + ww.sum(axis=1))
    with open(ART / 'step7.json', 'w') as f:
        json.dump(rows, f, indent=1)


if __name__ == '__main__':
    main()
