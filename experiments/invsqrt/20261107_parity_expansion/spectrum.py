"""Walsh (parity) spectrum of T(x) = 1/sqrt(x) in turns on the 22-bit cube.

Phase target and tolerance are read from the rot33 experiment artifacts, which
were validated against the official error profile (worst ratio 0.9993237694 @161).

Legal domain x = 1..M, M = 3,133,452 out of N = 2^22 = 4,194,304 cube points.
The extension for invalid x only fixes which characters get *selected*; the
coefficients are refit on the legal domain in fit.py.

  zero    : f(x) = 0 for x = 0 and x > M
  const   : f(0) = f(1), f(x) = f(M) for x > M
  natural : f(x) = 1/sqrt(x) for all x >= 1 (mathematical continuation), f(0)=f(1)

Reconstruction uses the inverse WHT of the sparse coefficient array: exactly the
sum a real K-term parity expansion builds in hardware.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
ROT33 = ROOT / "artifacts/20261106_rot33"
OUT = ROOT / "artifacts/20261107_parity_expansion"
N = 1 << 22
M = 3_133_452
ORDER = 40_000
KS = [1, 8, 22, 41, 96, 200, 500, 1000, 2000, 5000, 10_000, 20_000, 40_000]


def fwht(a: np.ndarray) -> np.ndarray:
    """Unnormalised WHT: A[S] = sum_x a[x] (-1)^popcount(S&x); self-inverse up to N."""
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


def build_full(kind: str) -> np.ndarray:
    x = np.arange(N, dtype=np.float64)
    f = np.zeros(N, dtype=np.float64)
    f[1:] = 1.0 / np.sqrt(x[1:])
    if kind == "zero":
        f[M + 1:] = 0.0
        f[0] = 0.0
    elif kind == "const":
        f[M + 1:] = f[M]
        f[0] = f[1]
    elif kind == "natural":
        f[0] = f[1]
    else:
        raise ValueError(kind)
    return f


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    target = np.load(ROT33 / "target_units.npy")
    tol = np.load(ROT33 / "tol_units.npy").astype(np.float64) / 2.0**64
    assert target.shape == (M,)
    f_legal = target.astype(np.float64) / 2.0**64
    model = 1.0 / np.sqrt(np.arange(1, M + 1, dtype=np.float64))
    print("float model vs 64-bit target: max |diff| =",
          float(np.abs(model - f_legal).max()), "turns; tol(min) =", float(tol.min()))

    summary: dict = {"M": M, "N": N, "tolerance_min": float(tol.min()),
                     "tolerance_max": float(tol.max()), "extensions": {}}
    for kind in ("zero", "const", "natural"):
        f = build_full(kind)
        coef = fwht(f) / N
        mag = np.abs(coef)
        order = np.argsort(mag)[::-1][:ORDER]
        rows = []
        got = 0
        for K in KS:
            got = K
            C = np.zeros(N)
            C[order[:K]] = coef[order[:K]]
            recon = fwht(C)[:M]
            err = np.abs(f_legal - recon)
            ratio = err / tol
            rows.append({"K": int(K), "trunc_max_ratio": float(ratio.max()),
                         "trunc_worst_x": int(np.argmax(ratio)) + 1,
                         "trunc_max_abs": float(err.max())})
        above = {f"{t:.0e}": int((mag > float(t)).sum())
                 for t in (1e-6, 1e-7, 1e-8, 1e-9, 1e-10, 1e-11, 1e-12)}
        summary["extensions"][kind] = {
            "top_magnitudes": [float(v) for v in mag[order[:20]]],
            "top_indices": [int(v) for v in order[:20]],
            "order_head": [int(v) for v in order[:64]],
            "truncation": rows,
            "coef_energy": float(np.sum(coef**2)),
            "count_above": above,
        }
        np.savez_compressed(OUT / f"coef_{kind}.npz",
                            order=order.astype(np.int64),
                            coef=coef[order].astype(np.float64))
        print(kind, "top |c|:", [f"{v:.3e}" for v in mag[order[:6]]])
        print("   count |c|>:", above)
        for r in rows:
            print(f"   K={r['K']:6d} trunc ratio {r['trunc_max_ratio']:.4e}"
                  f"  maxabs {r['trunc_max_abs']:.3e}  x={r['trunc_worst_x']}")
        print(f"   ({time.time()-t0:.1f}s)")
    (OUT / "spectrum.json").write_text(json.dumps(summary, indent=2))
    print("wrote", OUT / "spectrum.json", f"total {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
