"""Chebyshev re-fit of the 41 ladder angles on the exact per-x digit model.

phase(x) = sum_k b_k(x) theta_k + c(x).  Refitting theta is linear in the
digits, so the minimax problem is an LP.  Here we use IRLS on a working set of
x (the near-binding ones) and validate exactly on all x.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np


def load(dirpath: Path):
    z = np.load(dirpath / "digits.npz")
    return (z["xs"], z["base_err"].astype(np.int64), z["tol"].astype(np.int64),
            z["diffs"].astype(np.int64), z["theta"])


def digits_from_diffs(diffs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    dig = np.zeros_like(diffs, dtype=np.int8)
    mags = np.zeros(len(diffs), dtype=np.int64)
    for k, row in enumerate(diffs):
        vals = np.unique(row)
        nz = vals[vals != 0]
        assert len(nz) == 1, (k, vals[:5])
        d = int(nz[0])
        mags[k] = abs(d)
        dig[k] = (row // d).astype(np.int8)
    return dig, mags


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", type=Path)
    ap.add_argument("--iters", type=int, default=60)
    ap.add_argument("--exponent", type=float, default=8.0)
    args = ap.parse_args()

    xs, base_err, tol, diffs, theta = load(args.dir)
    dig, mags = digits_from_diffs(diffs)
    n = dig.shape[1]
    # e(x) in units; X columns are b_k * mags_k (the phase change per unit theta_k)
    X = (dig.astype(np.float64) * mags[:, None]).T   # n x 41, columns = D_k b_k
    e = base_err.astype(np.float64)
    w0 = 1.0 / tol.astype(np.float64)

    # least squares first
    XtX = X.T @ X
    Xte = X.T @ e
    delta_ls = np.linalg.solve(XtX, -Xte)
    res_ls = e + X @ delta_ls
    print("least squares: max|res|/tol =", np.max(np.abs(res_ls) * w0),
          " rms|res|/tol =", np.sqrt(np.mean((res_ls * w0) ** 2)))
    print("baseline     : max|e|/tol   =", np.max(np.abs(e) * w0),
          " rms|e|/tol   =", np.sqrt(np.mean((e * w0) ** 2)))
    print("std(e)/tol =", np.std(e * w0), " mean(e)/tol =", np.mean(e * w0))

    # IRLS minimax
    delta = delta_ls.copy()
    r = e + X @ delta
    for it in range(args.iters):
        s = np.abs(r) * w0
        s = s / s.max()
        w = w0 * (s + 1e-3) ** (args.exponent - 2.0)
        W = w * w
        XtWX = X.T @ (X * W[:, None])
        XtWe = X.T @ (e * W)
        delta = np.linalg.solve(XtWX + 1e-18 * np.eye(len(delta)), -XtWe)
        r = e + X @ delta
        mx = float(np.max(np.abs(r) * w0))
        if it % 10 == 0 or it == args.iters - 1:
            print(f"  irls {it:3d}: max|r|/tol={mx:.8f}  min margin={int(np.min(tol - np.abs(r)))}")
    print("\nfinal delta (in units, = change in D_k b_k):")
    for k in range(len(delta)):
        if abs(delta[k]) > 1:
            print(f"  k={k:2d} delta={delta[k]:+.3f} units  ({delta[k]/2**64:+.6e} turns) "
                  f"rel={delta[k]/mags[k]:+.6e}")
    print("max ratio after:", float(np.max(np.abs(r) * w0)))
    margin = tol - np.abs(r)
    imin = int(np.argmin(margin))
    print(f"min margin={int(margin[imin])} @x={int(xs[imin])}")
    n_rot = dig.shape[0]
    eps = math.pi * float(margin[imin]) / 2**64 / n_rot
    t = 1.0 + n_rot * (0.56 * math.log2(1 / eps) + 5.3)
    print(f"eps={eps:.6e}  score={62*(1213.8662 + t/4):.4f}  (baseline 93555.34)")


if __name__ == "__main__":
    main()
