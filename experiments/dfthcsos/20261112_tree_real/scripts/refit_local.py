"""Short weight refit at fixed words (dfthc_refit's L-BFGS stage, without its jax one-body stage).

Low     python refit_local.py work/tree_<name>.npz --target 19.9 --maxiter 3000 --out work/refit_<name>.npz

Minimizes log lambda_eff over (w, W) with quadratic penalties above the error_2 target and below the
E_gap floor, then regenerates the one-body rows from the final h1' (numpy polish) and reports the
official metrics. Same objective and gradients as `refit_weights.WeightProblem`; the jax progressive
one-body rounding is replaced by `common.onebody_words`.
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import json

import numpy as np
from scipy.optimize import minimize

import common as C
import encode
from paths import SHIFTS, UPPER_ENERGY
from refit_weights import WeightProblem, error_terms
from refine import GAP_FLOOR, Problem, rotate_columns, optimize_offsets
from dfthcsos.scoreinfra.reference import check_fcidump, load_reference
from dfthcsos.verify import native_inputs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('npz')
    ap.add_argument('--out', required=True)
    ap.add_argument('--target', type=float, default=19.9)
    ap.add_argument('--margin', type=float, default=0.002)
    ap.add_argument('--maxiter', type=int, default=3000)
    ap.add_argument('--rounds', type=int, default=2)
    a = ap.parse_args()

    with np.load(a.npz, allow_pickle=False) as z:
        data = {k: np.array(z[k]) for k in z.files}
    edges = np.asarray(data['tree_edges'], np.int64)
    brot = 8
    N = edges.shape[0] + 1
    w0 = np.asarray(data['W'], np.float64)
    W0 = np.asarray(data['H2_I'], np.float64) - w0.sum(axis=1)
    R, B, Cc = w0.shape
    words2 = np.asarray(data['angle_words'], np.int64)[N:]
    u = encode.decode(words2, edges, brot).reshape(R, B, N)
    u /= np.linalg.norm(u, axis=2, keepdims=True)

    ref = load_reference(check_fcidump())
    with np.load(SHIFTS) as z:
        _, _, S, beta = native_inputs({'U': u, 'W': w0, 'H2_I': data['H2_I'], 'H1_I': z['H1_I'],
                                       'Hsym_lower': z['Hsym_lower']})
    K, Q, T2 = error_terms(u, np.asarray(ref['tei'], np.float64), S)
    eta = int(ref['electrons'])
    wp = WeightProblem(u, K, Q, T2, ref['h1_thc'] - 0.5 * eta * S + beta * np.eye(N),
                       float(UPPER_ENERGY - ref['ecore'] + eta * beta))
    target, floor = 1e-3 * a.target, GAP_FLOOR + a.margin

    def objective(x):
        w, W = x[:w0.size].reshape(w0.shape), x[w0.size:].reshape(W0.shape)
        (e2, gap, Lam), (de2, dgap, dLam) = wp.evaluate(w, W)
        rad = gap * (2 * Lam - gap)
        if rad <= 0:
            return 1e12, np.zeros_like(x)
        f = 0.5 * np.log(rad)
        gw, gW = [((Lam - gap) * g + gap * l) / rad for g, l in zip(dgap, dLam)]
        if e2 > target:
            f += 1e6 * (e2 - target) ** 2
            gw = gw + 2e6 * (e2 - target) * de2
        if gap < floor:
            f += 1e5 * (floor - gap) ** 2
            gw, gW = gw - 2e5 * (floor - gap) * dgap[0], gW - 2e5 * (floor - gap) * dgap[1]
        return f, np.concatenate([gw.ravel(), gW.ravel()])

    scale = np.concatenate([np.full(w0.size, np.std(w0)), np.full(W0.size, np.std(W0))])
    res = minimize(lambda y: (lambda f, g: (f, g * scale))(*objective(y * scale)),
                   np.concatenate([w0.ravel(), W0.ravel()]) / scale, jac=True, method='L-BFGS-B',
                   options={'maxiter': a.maxiter, 'maxcor': 30, 'ftol': 1e-15, 'gtol': 1e-10, 'maxls': 50})
    x = res.x * scale
    w, W = x[:w0.size].reshape(w0.shape), x[w0.size:].reshape(W0.shape)
    (e2, gap, Lam), _ = wp.evaluate(w, W)
    print('L-BFGS', res.nit, 'e2', 1e3 * e2, 'gap', gap, 'lam_eff', float(np.sqrt(gap * (2 * Lam - gap))), flush=True)

    best, best_m = None, None
    one_start = np.asarray(data['angle_words'])[:N]
    for k in range(a.rounds + 1):          # k=0 keeps the refit w, W; later rounds add refine.py moves
        if k:
            w, W = rotate_columns(w, W, sweeps=2, seed=k)
            p_ = Problem(u, w, ref, S, beta)
            W = optimize_offsets(p_, W, a.margin)
        p_ = Problem(u, w, ref, S, beta)
        one = C.onebody_words(p_.h1(W), edges, brot, start=one_start, kicks=4, seed=k)
        words = np.vstack([one, words2])
        m = C.metrics(C.load_inputs_from({**{kk: data[kk] for kk in C.KEYS},
                                          'W': w, 'H2_I': W + w.sum(axis=1)}), words, edges, brot)
        print('round', k, json.dumps({kk: float(m[kk]) for kk in ('error_1', 'error_2', 'Lambda', 'E_gap', 'lambda_eff')}),
              flush=True)
        ok = m['error_1'] <= 0.0199 and m['error_2'] <= 0.0200 and m['E_gap'] > GAP_FLOOR
        if ok and (best_m is None or m['lambda_eff'] < best_m['lambda_eff']):
            best, best_m = {'W': w, 'H2_I': W + w.sum(axis=1), 'angle_words': words, 'tree_edges': edges,
                            'U': data['U'], 'H1_I': data['H1_I'], 'Hsym_lower': data['Hsym_lower']}, m
    if best is None:
        print('no refit kept (gate or floor): pass-through')
        best = {kk: data[kk] for kk in ('U', 'W', 'H2_I', 'H1_I', 'Hsym_lower', 'angle_words', 'tree_edges')}
    np.savez(a.out, **best)
    print('saved', a.out, json.dumps({kk: float(best_m[kk]) for kk in ('error_1', 'error_2', 'lambda_eff')}))


if __name__ == '__main__':
    main()
