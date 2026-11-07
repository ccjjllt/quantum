"""Genuine Chebyshev (min-max) parity fit on the legal domain, via LP exchange.

Variables: K coefficients c_S and t; minimise t subject to
    |T(x) - sum_S c_S chi_S(x)| <= t * tol(x)
over an active set that is expanded with the worst violators each round.
This is the *best possible* max error over the chosen K-dimensional parity
span, i.e. approach A in its strongest form.  Reported number: the achieved
worst error/tolerance over all 3,133,452 legal x.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

ROOT = Path(__file__).resolve().parents[3]
ROT33 = ROOT / "artifacts/20261106_rot33"
OUT = ROOT / "artifacts/20261107_parity_expansion"
N = 1 << 22
M = 3_133_452


def fwht(a: np.ndarray) -> np.ndarray:
    a = np.array(a, dtype=np.float64, copy=True)
    n = a.size
    h = 1
    while h < n:
        b = a.reshape(-1, 2, h)
        u = b[:, 0, :].copy()
        v = b[:, 1, :].copy()
        b[:, 0, :] = u + v
        b[:, 1, :] = u - v
        h *= 2
    return a


def chars(S: np.ndarray, x: np.ndarray) -> np.ndarray:
    """(len(S), len(x)) matrix of chi_S(x) = (-1)^popcount(S&x)."""
    prod = np.bitwise_and(S[:, None].astype(np.uint32), x[None, :].astype(np.uint32))
    return 1.0 - 2.0 * (np.bitwise_count(prod) & 1).astype(np.float64)


def main() -> None:
    t0 = time.time()
    K = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    tol_all = np.load(ROT33 / "tol_units.npy").astype(np.float64) / 2.0**64
    g = 1.0 / np.sqrt(np.arange(1, M + 1, dtype=np.float64))
    g[0] = 0.0

    gm = np.zeros(N)
    gm[1:M + 1] = g
    Wg = fwht(gm)
    S = np.argsort(np.abs(Wg))[::-1][:K].astype(np.int64)

    # seed active set: dyadic boundaries, a domain-spanning grid, worst points
    bnd = set()
    for j in range(0, 23):
        for d in (-2, -1, 0, 1, 2):
            v = (1 << j) + d
            if 1 <= v <= M:
                bnd.add(v)
    bnd |= set(range(1, 129))
    grid = set(np.unique(np.round(np.geomspace(1, M, 600)).astype(np.int64)).tolist())
    rng = np.random.default_rng(20261107)
    rand = set(rng.integers(1, M + 1, size=600).tolist())
    C0 = np.zeros(N)
    C0[S] = Wg[S] / N
    e0 = fwht(C0)[1:M + 1] - g
    e0 -= np.round(e0)
    worst0 = np.argsort(np.abs(e0) / tol_all)[::-1][:1000] + 1
    active = np.array(sorted(bnd | grid | rand | set(worst0.tolist())), dtype=np.int64)
    print(f"K={K} seed active={len(active)}")

    best = None
    for rnd in range(8):
        xa = active.astype(np.float64)
        A = chars(S, active)                       # (K, n)
        fa = 1.0 / np.sqrt(xa)
        fa[xa == 1] = 0.0
        ta = tol_all[active - 1]
        n = len(active)
        # minimise t:  -A^T c - t*ta <= -fa ;  A^T c - t*ta <= fa
        # t is ~1e7, so the t column is rescaled by SC to keep the LP well scaled.
        SC = 1.0e7
        A_ub = np.vstack([np.hstack([-A.T, -(SC * ta)[:, None]]),
                          np.hstack([A.T, -(SC * ta)[:, None]])])
        b_ub = np.concatenate([-fa, fa])
        cobj = np.zeros(K + 1)
        cobj[K] = 1.0
        bounds = [(None, None)] * K + [(0, None)]
        res = linprog(cobj, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")
        if not res.success:
            print("  LP failed:", res.message)
            break
        c = res.x[:K]
        t_lp = float(res.x[K]) * SC
        C = np.zeros(N)
        C[S] = c
        e = fwht(C)[1:M + 1] - g
        e -= np.round(e)
        ratio = np.abs(e) / tol_all
        mx = float(ratio.max())
        print(f"  round {rnd}: t_lp={t_lp:.4e} true max ratio={mx:.4e} "
              f"@ x={int(np.argmax(ratio))+1} active={n} ({time.time()-t0:.1f}s)")
        if best is None or mx < best["max_ratio"]:
            best = {"K": K, "max_ratio": mx,
                    "worst_x": int(np.argmax(ratio)) + 1,
                    "t_lp": t_lp, "active": n, "rounds": rnd + 1,
                    "rms_ratio": float(np.sqrt(np.mean(ratio**2)))}
        newpts = np.argsort(ratio)[::-1][:max(1000, K)] + 1
        added = np.setdiff1d(newpts, active)
        if added.size == 0:
            break
        active = np.union1d(active, added)
    print("best:", json.dumps(best))
    f = OUT / "cheb.json"
    old = json.loads(f.read_text()) if f.exists() else {}
    old[str(K)] = best
    f.write_text(json.dumps(old, indent=2))


if __name__ == "__main__":
    main()
