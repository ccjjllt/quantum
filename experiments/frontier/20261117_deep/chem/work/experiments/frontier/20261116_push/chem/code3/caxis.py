"""C axis at fixed words: how low does error_2 go with C = 44, 43, 42, 41 copies per group?

Dropping a copy sets one column of w (R,B,C) to zero (and one offset) and refits the rest; the
ANGLE word table does not depend on C, so the 15 shipped loaders stay byte-identical and only
submission.npz changes (T_heur drops 76 inner + 2 outer per copy).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from evalkit import Eval, load_pkg  # noqa: E402
from refine import GAP_FLOOR  # noqa: E402

PKG = ('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push'
       '/bdae_dataset/submission.npz')


def fit(ev, w0, keep, target_mha=None, maxiter=3000, lam_weight=1.0, log=print):
    """Minimise lambda_eff (or pure error_2) over the surviving columns of (w, W)."""
    w_full = np.asarray(w0, np.float64).copy()
    W_full = ev.H2_I - ev.w0.sum(axis=1)
    R, B, C = w_full.shape
    act = [(r, c) for r in range(R) for c in keep[r]]
    mask = np.zeros((R, C), bool)
    for r, c in act:
        mask[r, c] = True
    W_full = np.where(mask, W_full, 0.0)
    w_full = np.where(mask[:, None, :], w_full, 0.0)
    wp = ev.problem()
    target = 1e-3 * target_mha if target_mha is not None else 0.0

    def unpack(x):
        n = len(act)
        w = np.zeros((R, B, C))
        W = np.zeros((R, C))
        for i, (r, c) in enumerate(act):
            w[r, :, c] = x[i * B:(i + 1) * B]
            W[r, c] = x[n * B + i]
        return w, W

    def objective(x):
        w, W = unpack(x)
        (e2, gap, Lam), (de2, dgap, dLam) = wp.evaluate(w, W)
        gw = np.zeros_like(w)
        gW = np.zeros_like(W)
        if lam_weight == 0.0:
            f = e2
            gw += de2
        else:
            rad = gap * (2 * Lam - gap)
            if rad <= 0:
                return 1e12, np.zeros_like(x)
            f = 0.5 * np.log(rad)
            a = ((Lam - gap) * dgap[0] + gap * dLam[0]) / rad
            b = ((Lam - gap) * dgap[1] + gap * dLam[1]) / rad
            gw += a
            gW += b
            if e2 > target:
                f += 1e6 * (e2 - target) ** 2
                gw = gw + 2e6 * (e2 - target) * de2
            if gap < GAP_FLOOR:
                f += 1e5 * (GAP_FLOOR - gap) ** 2
                d0, d1 = dgap
                gw = gw - 2e5 * (GAP_FLOOR - gap) * d0
                gW = gW - 2e5 * (GAP_FLOOR - gap) * d1
        g = np.zeros_like(x)
        for i, (r, c) in enumerate(act):
            g[i * B:(i + 1) * B] = gw[r, :, c]
            g[len(act) * B + i] = gW[r, c]
        return f, g

    x0 = np.zeros(len(act) * (B + 1))
    for i, (r, c) in enumerate(act):
        x0[i * B:(i + 1) * B] = w_full[r, :, c]
        x0[len(act) * B + i] = W_full[r, c]
    sw = max(np.std(x0[:len(act) * B]), 1e-12)
    sW = max(np.std(x0[len(act) * B:]), 1e-12)
    scale = np.concatenate([np.full(len(act) * B, sw), np.full(len(act), sW)])

    def fun(y):
        f, g = objective(y * scale)
        return f, g * scale

    t0 = time.time()
    res = minimize(fun, x0 / scale, jac=True, method='L-BFGS-B',
                   options={'maxiter': maxiter, 'maxcor': 30, 'ftol': 1e-16, 'gtol': 1e-12,
                            'maxls': 50})
    w, W = unpack(res.x * scale)
    (e2, gap, Lam), _ = wp.evaluate(w, W)
    lam_eff = float(np.sqrt(gap * (2 * Lam - gap))) if 0 < gap < 2 * Lam else float('nan')
    log(f'   C={len(keep[0])} target {target_mha} lam_w {lam_weight}: e2 {1e3*e2:.5f} mHa  '
        f'E_gap {gap:.10f}  Lambda {Lam:.5f}  lam_eff {lam_eff:.8f}  '
        f'({res.nit} it, {time.time()-t0:.0f}s)')
    return w, W, dict(e2_mha=1e3 * e2, gap=gap, Lam=Lam, lam_eff=lam_eff)


def main():
    d = load_pkg(PKG)
    ev = Eval(d)
    w44 = ev.w0
    u = ev.uvec()
    X = np.einsum('tjp,tjq,tjl->tlpq', u, u, w44, optimize=True)
    imp = np.linalg.norm(X.reshape(8, 44, -1), axis=2)
    order = np.argsort(imp, axis=1)
    out = {}
    for drop in (0, 1, 2, 3):
        keep = [list(np.sort(order[r, drop:])) for r in range(8)]
        print(f'\n=== C={44-drop} ({drop} dropped; weakest {[order[r,0] for r in range(8)]}) ===')
        w, W, m0 = fit(ev, w44, keep, None, lam_weight=0.0)
        out[f'C{44-drop}_e2floor'] = m0
        for tgt in (19.99, 19.9):
            _, _, m = fit(ev, w, keep, tgt)
            out[f'C{44-drop}_tgt{tgt}'] = m
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
