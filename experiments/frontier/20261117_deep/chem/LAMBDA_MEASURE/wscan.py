"""Scan the offset profile b = c * a (the shipped relationship) for a fitted (U,w).

Validates the parametrisation on the shipped factorization (where the answer is
Lambda = 283.144, lambda_eff = 46.9217) and then measures the same thing at a new
shape. W is chosen anti-aligned with sum_b w, which is the shipped structure.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import fitlib as F
import infra as I
from lamopt import LamProblem

log = F.log


def scan(LP, cs=np.linspace(0.05, 1.6, 156), tag=''):
    sign = -np.sign(LP.s.ravel() + 1e-300)
    rows = []
    for c in cs:
        b = c * LP.a.ravel()
        W = (sign * b).reshape(LP.R, LP.C) - LP.s
        st = LP.stats(W)
        st['c'] = float(c)
        rows.append(st)
    feas = [d for d in rows if np.isfinite(d['lambda_eff']) and d['E_gap'] > I.E_GAP_FLOOR
            and d['Lambda'] > I.LAMBDA_FLOOR]
    gmin = min(rows, key=lambda d: d['E_gap'])
    log(f'{tag}: min E_gap {gmin["E_gap"]:9.6f} at c {gmin["c"]:.3f} '
        f'(Lambda {gmin["Lambda"]:.3f}, lambda_eff {gmin["lambda_eff"]:.5f})  '
        f'feasible {len(feas)}/{len(rows)}')
    if feas:
        best = min(feas, key=lambda d: d['lambda_eff'])
        log(f'{tag}: BEST feasible c {best["c"]:.3f}  Lambda {best["Lambda"]:.4f}  '
            f'E_gap {best["E_gap"]:.9f}  lambda_eff {best["lambda_eff"]:.6f}  '
            f'sumW2 {best["sumW2"]:.2f}')
        return best
    return None


if __name__ == '__main__':
    z = np.load(I.ROOT / 'experiments/frontier/20261117_deep/chem/data/dfthcsos/submission.npz')
    LP = LamProblem(z['U'], z['W'])
    log(f'SHIPPED own W: Lambda {LP.stats(z["H2_I"] - z["W"].sum(axis=1))["Lambda"]:.6f}, '
        f'lambda_eff {LP.stats(z["H2_I"] - z["W"].sum(axis=1))["lambda_eff"]:.9f}')
    scan(LP, tag='SHIPPED')

    # the official baseline (65,60,60) as a second validation
    zb = np.load(I.ROOT / 'data/competition/sample_submission/dfthcsos/submission.npz')
    LPb = LamProblem(zb['U'], zb['W'])
    Wb = zb['H2_I'] - zb['W'].sum(axis=1)
    st = LPb.stats(Wb)
    log(f'BASELINE own W: Lambda {st["Lambda"]:.6f}, lambda_eff {st["lambda_eff"]:.9f}, '
        f'E_gap {st["E_gap"]:.9f}')
    scan(LPb, tag='BASELINE')

    for name in sys.argv[1:]:
        zf = np.load(I.CACHE / name)
        R, B, C = int(zf['R']), int(zf['B']), int(zf['C'])
        x = zf['x']
        w = x[:R * B * C].reshape(R, B, C)
        U = x[R * B * C:].reshape(R, B, I.N)
        LPf = LamProblem(U, w)
        log(f'{name}: fitted w, e2 not measured here (see fit log)')
        scan(LPf, tag=name)
