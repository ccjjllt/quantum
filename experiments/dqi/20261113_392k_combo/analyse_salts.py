"""Analyse the DQI 392k salt sweep: failure statistics, expected cost, expected GM.

Uses the official verifier's Clopper-Pearson / R functions unmodified.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.stats import beta

VERIFIER_DIR = Path('/Users/zhaohuaxiang/ccjjllt/quantum/data/competition/verifiers/dqi')
sys.path.insert(0, str(VERIFIER_DIR))
import verify_submission_dqi as V  # noqa: E402

N = 102_400
Q = 892
# Reference costs (main repo, verified against sample submission).
REF = {'invsqrt': 2_076_774.2337, 'dqi': 24_439_463_583_672.93, 'chem': 3_355_599_588.3155}
INVSQRT = 93_555.2627
CHEM = 297_237_044.9509761
EAE_T = 394_089.4627734375
EAE_Q = 892
EAE_ZERO = 373_534_939_340.64


def R_of(k: int, n: int = N, log2_delta: float = -128.0) -> float:
    eps = V.clopper_pearson_upper_bound(k, n, log2_delta=log2_delta)
    return float(V.repetition_overhead(eps))


def gm(cost_dqi: float) -> float:
    return (REF['invsqrt'] / INVSQRT * REF['dqi'] / cost_dqi * REF['chem'] / CHEM) ** (1 / 3)


def main() -> None:
    d = Path(sys.argv[1])
    rows = [json.loads(p.read_text()) for p in sorted(d.glob('verify_salt_*.json'))]
    rows.sort(key=lambda r: r['salt'])
    print(f'salts: {len(rows)}')
    print(f"{'salt':<20}{'ve':>4}{'pe':>4}{'R':>12}{'cost':>20}")
    ks, costs = [], []
    for r in rows:
        k = r['value_errors'] + r['phase_errors']
        ks.append(k)
        costs.append(r['score'])
        print(f"{r['salt']:<20}{r['value_errors']:>4}{r['phase_errors']:>4}"
              f"{r['repetition_factor']:>12.9f}{r['score']:>20.2f}")
    k = np.array(ks)
    total_shots = len(rows) * N
    p_hat = k.sum() / total_shots
    # Clopper-Pearson 95% on per-shot failure probability.
    lo = beta.ppf(0.025, k.sum(), total_shots - k.sum() + 1) if k.sum() > 0 else 0.0
    hi = beta.ppf(0.975, k.sum() + 1, total_shots - k.sum()) if k.sum() < total_shots else 1.0
    lam = p_hat * N
    print(f'\ntotal errors {k.sum()} / {total_shots} shots')
    print(f'p_hat = {p_hat:.3e}  (95% CI {lo:.3e} .. {hi:.3e})')
    print(f'lambda per 102,400-shot draw = {lam:.3f} (95% CI {lo*N:.3f} .. {hi*N:.3f})')
    print(f'observed k histogram: {dict(zip(*np.unique(k, return_counts=True)))}')

    T = np.mean([r['toffoli_count'] for r in rows])
    print(f'\nT mean over salts = {T:.6f} (min {min(r["toffoli_count"] for r in rows):.6f})')
    print(f'\n{"k":>3}{"R_k":>15}{"cost(k)":>22}{"GM(k)":>14}{"GM gain":>10}')
    tab = {}
    for kk in range(0, 8):
        rk = R_of(kk)
        c = rk * Q * Q * T
        tab[kk] = (rk, c, gm(c))
        print(f'{kk:>3}{rk:>15.9f}{c:>22.2f}{gm(c):>14.8f}{gm(c)/gm(EAE_ZERO)-1:>10.4%}')

    # Poisson mixture, plus a conservative negative-binomial-free check.
    for lam_use, tag in ((lam, 'p_hat'), (hi * N, 'CP upper'), (lo * N, 'CP lower')):
        w = [math.exp(-lam_use) * lam_use ** kk / math.factorial(kk) for kk in range(0, 40)]
        # renormalise over the truncated tail
        s = sum(w)
        w = [x / s for x in w]
        ec = sum(wi * tab[min(kk, 7)][1] for kk, wi in enumerate(w))
        eg = sum(wi * tab[min(kk, 7)][2] for kk, wi in enumerate(w))
        p0 = w[0]
        print(f'\n[{tag}] lambda={lam_use:.3f}  P(0 fail)={p0:.4f}  E[cost]={ec:,.2f}  E[GM]={eg:.8f}')
        print(f'  vs eae zero-failure cost {EAE_ZERO:,.2f}: {(EAE_ZERO/ec-1):+.4%} cheaper')
        print(f'  vs eae expected (48-draw) 373,856,548,625.22: {(373856548625.22/ec-1):+.4%} cheaper')
        print(f'  E[GM] gain vs eae zero-failure GM {gm(EAE_ZERO):.8f}: {eg/gm(EAE_ZERO)-1:+.4%}')

    # Empirical bootstrap over the observed draws.
    rng = np.random.default_rng(20261113)
    boots = []
    for _ in range(20000):
        s = rng.choice(k, size=len(k), replace=True)
        lam_b = s.sum() / (len(k) * N) * N
        w = np.array([math.exp(-lam_b) * lam_b ** kk / math.factorial(kk) for kk in range(0, 40)])
        w /= w.sum()
        boots.append(sum(w[kk] * tab[min(kk, 7)][1] for kk in range(40)))
    boots = np.array(boots)
    print(f'\nbootstrap E[cost]: median {np.median(boots):,.0f}  90% [{np.percentile(boots,5):,.0f}, '
          f'{np.percentile(boots,95):,.0f}]')
    print(f'bootstrap E[GM]:   median {gm(np.median(boots)):.8f}  '
          f'90% [{gm(np.percentile(boots,95)):.8f}, {gm(np.percentile(boots,5)):.8f}]')

    out = {'salts': len(rows), 'total_errors': int(k.sum()), 'total_shots': total_shots,
           'p_hat': p_hat, 'p_ci': [lo, hi], 'lambda': lam, 'T_mean': T,
           'P0': math.exp(-lam), 'E_cost': sum(math.exp(-lam) * lam ** kk / math.factorial(kk)
                                               * tab[min(kk, 7)][1] for kk in range(40)) / math.exp(-lam) / sum(
               lam ** kk / math.factorial(kk) for kk in range(40)),
           'cost_by_k': {str(kk): tab[kk][1] for kk in tab},
           'GM_by_k': {str(kk): tab[kk][2] for kk in tab}}
    (d / 'analysis.json').write_text(json.dumps(out, indent=2))
    print('\nGM(eae zero) =', f'{gm(EAE_ZERO):.8f}')
    print('GM(eae expected) =', f'{gm(373856548625.22):.8f}')


if __name__ == '__main__':
    main()
