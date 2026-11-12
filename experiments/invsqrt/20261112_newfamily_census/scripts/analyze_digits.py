"""Analyse the per-x digit decomposition: removable rotations and margin headroom.

Model (verified exactly by split_digits.py): the tracked phase is
    phase(x) = sum_k b_k(x) * theta_k + c(x)
with b_k(x) in {0,1} and c(x) the Clifford-only part.  Therefore removing a
rotation changes the error by a known per-x amount, and rescaling the angles is
a linear Chebyshev problem.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np


def load(dirpath: Path):
    z = np.load(dirpath / "digits.npz")
    return z["xs"], z["base_err"].astype(np.int64), z["tol"], z["diffs"].astype(np.int64), z["theta"]


def digits_from_diffs(diffs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (sign*digit matrix as int8, magnitude per rotation)."""
    mags = []
    dig = np.zeros_like(diffs, dtype=np.int8)
    for k, row in enumerate(diffs):
        vals = np.unique(row)
        # vals must be {0, D} or {0, -D}
        nz = vals[vals != 0]
        assert len(nz) == 1, (k, vals[:5])
        d = int(nz[0])
        mags.append(abs(d))
        dig[k] = (row // d).astype(np.int8) if d else 0
    return dig, np.array(mags, dtype=np.int64)


def margins(err: np.ndarray, tol: np.ndarray) -> tuple[int, float, int, int]:
    used = np.abs(err)
    margin = tol.astype(np.int64) - used.astype(np.int64)
    imin = int(np.argmin(margin))
    ratio = used.astype(np.float64) / tol.astype(np.float64)
    imax = int(np.argmax(ratio))
    return int(margin[imin]), float(ratio[imax]), imin, imax


def score(margin: int, n_rot: int, toffoli: float, t_base: float = 1.0, q: int = 62) -> float:
    eps = math.pi * margin / 2**64 / n_rot
    t = t_base + n_rot * (0.56 * math.log2(1 / eps) + 5.3)
    return q * (toffoli + t / 4)


def main() -> None:
    import sys

    d = Path(sys.argv[1])
    xs, base_err, tol, diffs, theta = load(d)
    dig, mags = digits_from_diffs(diffs)
    n = len(xs)
    print(f"x count={n} rotations={len(mags)}")
    print("rotation  theta(half turns)   |D| units      fires/x       max|b*D|/tol")
    for k in range(len(mags)):
        frac = dig[k].mean()
        worst = float(np.max(dig[k] * mags[k] / tol.astype(np.float64)))
        print(f"  {k:2d}  {theta[k]:.6e}  {mags[k]:16d}  {frac:8.4f}  {worst:10.4f}")

    m0, r0, i0, ix0 = margins(base_err, tol)
    print(f"\nbaseline: min margin={m0} @x={int(xs[i0])}  max ratio={r0:.10f} @x={int(xs[ix0])}")
    print(f"baseline score (toffoli 1213.8662) = {score(m0, 41, 1213.8662):.6f}")

    print("\n-- single rotation removal --")
    ok = []
    for k in range(len(mags)):
        err = base_err - dig[k].astype(np.int64) * mags[k]
        mk, rk, ik, ixk = margins(err, tol)
        good = mk > 0 and rk < 1.0
        if good:
            ok.append(k)
        print(f"  drop {k:2d}: min margin={mk:14d} @x={int(xs[ik]):8d} max ratio={rk:.6f}"
              f"{'  OK' if good else '  FAIL'}  score={score(mk, 40, 1213.8662) if good else 0:.1f}")
    print(f"single-removal feasible: {ok}")

    # greedy subsets
    print("\n-- greedy removal --")
    cur = base_err.copy()
    removed: list[int] = []
    while True:
        best = None
        for k in range(len(mags)):
            if k in removed:
                continue
            err = cur - dig[k].astype(np.int64) * mags[k]
            mk, rk, _, _ = margins(err, tol)
            if mk <= 0 or rk >= 1.0:
                continue
            sc = score(mk, 41 - len(removed) - 1, 1213.8662)
            if best is None or sc < best[0]:
                best = (sc, k, err, mk)
        if best is None:
            break
        sc, k, err, mk = best
        removed.append(k)
        cur = err
        m1, r1, i1, ix1 = margins(cur, tol)
        print(f"  add {k:2d} -> removed={sorted(removed)} min margin={m1} @x={int(xs[i1])} "
              f"ratio={r1:.6f} score={score(m1, 41-len(removed), 1213.8662):.1f}")
        if len(removed) >= 12:
            break
    print(f"greedy removed: {sorted(removed)}")


if __name__ == "__main__":
    main()
