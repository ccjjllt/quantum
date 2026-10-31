"""Fit integer coefficient tables against the exact truncated arithmetic of model.py.

Per segment: continuous minimax (LP) quadratic in the centered delta, then an integer
neighbourhood search over (C1, C2) with the optimal C0 for each, scored by the max
relative error of Y over exactly the (p, x_n) inputs that occur.
"""
from __future__ import annotations

import sys
import json
import time

import numpy as np
from scipy.optimize import linprog

import model as M


def domains(prm: M.Params | None = None):
    if prm is None:
        prm = M.Params()
    xs = np.arange(1, M.MAX_X + 1, dtype=np.int64)
    _t, xn, p, _s = M.decompose(xs)
    key = np.unique((p << 22) | xn)
    p = key >> 22
    xn = key & ((1 << 22) - 1)
    a = (p << prm.seg_bits) | ((xn >> prm.delta_bits) & ((1 << prm.seg_bits) - 1))
    order = np.argsort(a, kind='stable')
    a, p, xn = a[order], p[order], xn[order]
    bounds = np.searchsorted(a, np.arange(prm.n_segments + 1))
    return a, p, xn, bounds


def ytrue(p, xn):
    return np.where(p == 1, 1.0, 2 ** -0.5) * 2 ** 10.5 / np.sqrt(xn.astype(np.float64))


def lp_fit(dc, y):
    """minimax relative fit y ~ c0 - c1 dc + c2 dc^2."""
    idx = np.unique(np.r_[np.linspace(0, len(dc) - 1, 600).astype(int)])
    d, yy = dc[idx], y[idx]
    # vars c0 c1 c2 e ; minimize e ; |c0 - c1 d + c2 d^2 - y| <= e*y
    A1 = np.c_[np.ones_like(d), -d, d * d, -yy]
    A2 = np.c_[-np.ones_like(d), d, -d * d, -yy]
    A = np.r_[A1, A2]
    bvec = np.r_[yy, -yy]
    r = linprog([0, 0, 0, 1], A_ub=A, b_ub=bvec, bounds=[(None, None)] * 3 + [(0, None)], method='highs')
    return r.x[:3]


def score(C0, R, ytgt, w):
    return np.max(np.abs(C0 + R - ytgt) * w)


def virtual_parity_bits(prm: M.Params) -> list[int]:
    """C2 positions whose rounded-row parities fix the virtual low bit of T.

    This is the same symmetric difference as circuit.parity_indices, evaluated
    on the curvature register of width F2-1. The fit keeps C1's low bit equal
    to that parity, so the integer derivative is even and the omitted wire is 0.
    """
    parity: set[int] = set()
    width = prm.F2 - 1
    for i in prm.rowsA:
        e = prm.eA(i) + 1
        if e < 0:
            continue
        if e < width:
            parity.symmetric_difference_update({e})
        if 0 <= e - 1 < width:
            parity.symmetric_difference_update({e - 1})
    return sorted(parity)


def derivative_parity_matches(c1: int, c2: int, bits: list[int]) -> bool:
    acc = 0
    for k in bits:
        acc ^= (int(c2) >> k) & 1
    return (int(c1) & 1) == acc


def row_obeys_virtual_bits(c0: int, c1: int, c2: int, prm: M.Params) -> bool:
    return (int(c0) & 1) == 0 and derivative_parity_matches(c1, c2, virtual_parity_bits(prm))


def best_C0(R, ytgt, w, top=None):
    """Even constant word. An odd candidate is not scored and not clamped into range."""
    d = R - ytgt
    c = -0.5 * (d.max() + d.min())
    hi = None if top is None else int(top - 1 - R.max())
    best = None
    for C0 in (int(np.floor(c)) + offset for offset in (-2, -1, 0, 1, 2, 3)):
        if C0 & 1:
            continue
        if hi is not None and C0 > hi:
            continue
        sc = score(C0, R, ytgt, w)
        if best is None or sc < best[0]:
            best = (sc, int(C0))
    if best is None:
        return (np.inf, 0)
    return best


def best_C0_g(R, ytgt, w, G0, top):
    d = R - ytgt
    c = int(np.floor(-0.5 * (d.max() + d.min()) + (1 << G0) / 2))
    hi = int(top - 1 - R.max())
    best = None
    for C0 in range(c - (1 << G0), c + (1 << G0) + 1):
        if C0 & 1 or C0 > hi:
            continue
        e = (((C0 + R) >> G0) << G0) - ytgt
        sc = np.max(np.abs(e) * w)
        if best is None or sc < best[0]:
            best = (sc, int(C0))
    if best is None:
        return (np.inf, 0)
    return best


def fit_segment(p, xn, prm: M.Params, rad1=6, rad2=3):
    b = xn & ((1 << prm.delta_bits) - 1)
    center = 1 << (prm.delta_bits - 1)
    dc = (b - (center - 0.5 if prm.sd else center)) * 2.0 ** -21
    y = ytrue(p, xn)
    c0, c1, c2 = lp_fit(dc, y)
    ytgt = (y - 0.5) * 2 ** prm.F0
    w = 1.0 / (y * 2 ** prm.F0) * 2 ** 24   # error / tolerance (approx)
    top = 1 << (prm.F0 - 1)
    zeros = np.zeros(len(b), np.int64)
    cache = {}
    parity_bits = virtual_parity_bits(prm)

    def ev(C1, C2):
        key = (C1, C2)
        if key in cache:
            return cache[key]
        # Virtual low bit of T: the curvature parity has to match C1, and every
        # integer derivative in this segment has to be even. The constant word
        # returned below is already even, so a later +1 adjustment is a no-op.
        if not derivative_parity_matches(C1, C2, parity_bits):
            r = (np.inf, 0)
        else:
            T = M.eval_T(zeros + C1, zeros + C2, b, prm)
            odd_derivative = int(np.max(T & 1)) != 0
            if odd_derivative or T.min() < 0 or T.max() >= (1 << prm.nT) or C1 >= (1 << prm.nT):
                r = (np.inf, 0)
            else:
                R = M.eval_Y(zeros, T, b, prm)
                r = best_C0(R, ytgt, w, top) if prm.G0 == 0 else best_C0_g(R, ytgt, w, prm.G0, top)
                if int(r[1]) & 1:
                    r = (np.inf, 0)
        cache[key] = r
        return r

    k1 = int(round(c1 * 2 ** prm.FT)); k2 = int(round(c2 * 2 ** prm.F2))
    best = None
    for C2 in range(k2 - rad2, k2 + rad2 + 1):
        for C1 in range(k1 - rad1, k1 + rad1 + 1):
            sc, C0 = ev(C1, C2)
            if best is None or sc < best[0]:
                best = (sc, C0, C1, C2)
    # local descent beyond the initial box
    improved = True
    while improved:
        improved = False
        _, _, C1b, C2b = best
        for d2 in (-1, 0, 1):
            for d1 in range(-3, 4):
                sc, C0 = ev(C1b + d1, C2b + d2)
                if sc < best[0] - 1e-12:
                    best = (sc, C0, C1b + d1, C2b + d2); improved = True
    sc, C0, C1, C2 = best
    if not derivative_parity_matches(C1, C2, parity_bits) or (int(C0) & 1):
        alt_sc, alt_c0 = ev(C1 ^ 1, C2)
        if alt_sc < sc:
            sc, C0, C1 = alt_sc, alt_c0, C1 ^ 1
    return (sc, int(C0), int(C1), int(C2))


_D = None


def _work(args):
    seg, prm, rad1, rad2 = args
    a, p, xn, bounds = _D
    lo, hi = bounds[seg], bounds[seg + 1]
    if lo == hi:
        return seg, (0.0, 0, 0, 0)
    return seg, fit_segment(p[lo:hi], xn[lo:hi], prm, rad1, rad2)


def fit_all(prm: M.Params, rad1=6, rad2=3, verbose=False, workers=8):
    global _D
    import multiprocessing as mp
    _D = domains(prm)
    tables = np.zeros((prm.n_segments, 3), dtype=np.int64)
    worst = 0.0
    with mp.get_context('fork').Pool(workers) as pool:
        for seg, (sc, C0, C1, C2) in pool.imap_unordered(_work, [(s, prm, rad1, rad2) for s in range(prm.n_segments)]):
            tables[seg] = (C0, C1, C2)
            worst = max(worst, sc)
    if verbose:
        print('fit worst (approx ratio)', worst)
    return tables, worst


if __name__ == '__main__':
    F0, FT, F2, G0 = map(int, sys.argv[1:5])
    prm = M.Params(F0=F0, FT=FT, F2=F2, G0=G0)
    t0 = time.time()
    tables, w = fit_all(prm, verbose=True)
    print('fit seconds', time.time() - t0)
    res = M.full_check(tables, prm)
    print(json.dumps(res))
    if res['pass']:
        nrot = F0 - G0 + 7
        print('rot T', M.rotation_cost(nrot, res['min_margin']), 'C-eq', M.rotation_cost(nrot, res['min_margin']) / 4)
    np.save(f'../../work/invsqrt/tables_{F0}_{FT}_{F2}_{G0}.npy', tables)
