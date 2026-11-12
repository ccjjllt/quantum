"""Step 8 (B): partition swaps -- move k direction pairs between groups, carry the weights, AL refit.

Regrouping costs nothing in T/Q (row order only, same directions and words).  This is the direct
test of the "local exchange" group-selection idea: if a swap plus refit beats lambda_eff 46.900,
the group assignment is a lever; if not, it is closed.
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

N = 76


def main() -> None:
    data = g.load_current()
    inp = g.load_inputs(g.SUB)
    sp = g.Space(data['U'], inp)
    R, B, C = sp.R, sp.B, sp.C
    w0, W0 = data['W'], data['H2_I'] - data['W'].sum(axis=1)
    u0 = sp.u.reshape(R * B, N).copy()
    rows = {'refit_identity': 46.8996}

    print('AL refit from the untouched table (control):', flush=True)
    res = sp.refit(w0, W0, target_mha=19.999, outer=8, inner=200, log=lambda *a: None)
    _, _, e2, gap, Lam, lam = res
    print('  e2 %.3f mHa  Lambda %.2f  E_gap %.5f  lambda_eff %.4f' % (1e3 * e2, Lam, gap, lam), flush=True)
    rows['control'] = dict(e2=1e3 * e2, Lam=Lam, gap=gap, lam_eff=lam)

    rng = np.random.default_rng(3)
    idx = np.arange(R * B)
    for k in (1, 2, 5, 10, 40):
        best = None
        for trial in range(2):
            perm = idx.copy()
            for _ in range(k):
                r1, r2 = rng.choice(R, 2, replace=False)
                a = int(rng.integers(r1 * B, (r1 + 1) * B))
                b = int(rng.integers(r2 * B, (r2 + 1) * B))
                perm[a], perm[b] = perm[b], perm[a]
            u = u0[perm].reshape(R, B, N)
            w = w0.reshape(R * B, C)[perm].reshape(R, B, C)
            e2_init = sp.error2(w, perm)
            r2res = sp.refit(w, sp.init_W(w, perm, w0, W0), perm=perm, target_mha=19.999,
                             outer=6, inner=150, log=lambda *a: None)
            ww, WW, e2, gap, Lam, lam = r2res
            cand = (lam, e2, gap, Lam, perm, ww, WW)
            if best is None or lam < best[0]:
                best = cand
        lam, e2, gap, Lam, perm, ww, WW = best
        rows[f'swap{k}'] = dict(e2=1e3 * e2, Lam=Lam, gap=gap, lam_eff=lam)
        print('  swap %2d: init %.2f mHa -> %.3f mHa  Lambda %.2f  E_gap %.5f  lambda_eff %.4f'
              % (k, 1e3 * e2_init, 1e3 * e2, Lam, gap, lam), flush=True)
        np.savez(ART / f'swap{k}.npz', perm=perm, W=ww, H2_I=WW + ww.sum(axis=1))
    with open(ART / 'step8.json', 'w') as f:
        json.dump(rows, f, indent=1)


if __name__ == '__main__':
    main()
