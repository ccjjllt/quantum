"""K-ladder: truncation error up to K = N, and the official cost ledger.

For each K the support is the K largest |Walsh coefficient| of the natural
extension; the reconstruction is the inverse WHT of the sparse coefficient
array, which is exactly the phase a real K-term parity circuit applies.  The
error is compared to tol(x) = 2^-24/sqrt(x) after reduction mod 1.

Cost model (official, verify_submission_invsqrt.py):
  eps       = pi * min_margin / n_rot          (min_margin in turns)
  T(eps)    = 0.56 log2(1/eps) + 5.3
  C_rot     = T(eps) / 4
  C         = K * C_rot                        (+ 0 for the free CX parity fan-in)
  Q         = 22 x + 1 ancilla = 23
score = Q * C.

Also reports the L1 sufficient bound: dropping a set with sum |c| = L guarantees
error <= L at every x.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
ROT33 = ROOT / "artifacts/20261106_rot33"
OUT = ROOT / "artifacts/20261107_parity_expansion"
N = 1 << 22
M = 3_133_452
BASE_SCORE = 97_700.776777236
BASE_C = 1_575.818980278
FRONT_ROT = 694.840824


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


def rot_cost(n_rot: int, margin: float) -> float:
    """Official per-rotation C at the given absolute minimum margin (turns)."""
    eps = math.pi * margin / n_rot
    return (0.56 * math.log2(1.0 / eps) + 5.3) / 4.0


def main() -> None:
    t0 = time.time()
    tol = np.load(ROT33 / "tol_units.npy").astype(np.float64) / 2.0**64
    xv = np.arange(1, M + 1, dtype=np.float64)
    g = 1.0 / np.sqrt(xv)
    g[0] = 0.0
    tol_min = float(tol.min())

    f = np.zeros(N)
    f[1:] = 1.0 / np.sqrt(np.arange(1, N, dtype=np.float64))
    f[0] = f[1]
    coef = fwht(f) / N
    mag = np.abs(coef)
    order = np.argsort(mag)[::-1]
    sm = mag[order]
    l1 = np.cumsum(sm[::-1])[::-1]

    ks = [41, 96, 99, 200, 500, 584, 590, 1000, 2000, 5000, 10_000, 20_000, 50_000, 100_000,
          200_000, 500_000, 1_000_000, 1_500_000, 2_000_000, 2_500_000,
          3_000_000, 3_500_000, 3_900_000, 4_100_000, 4_150_000, 4_180_000,
          4_190_000, 4_193_000, 4_194_000, N]
    near = [0, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10_000]
    rows = []
    for K in ks + [N - m for m in near if m]:
        C = np.zeros(N)
        C[order[:K]] = coef[order[:K]]
        p = fwht(C)[1:M + 1]
        e = p - g
        e -= np.round(e)
        ratio = np.abs(e) / tol
        margin = float((tol - np.abs(e)).min())
        j = int(np.argmax(ratio))
        row = {"K": int(K), "drop": int(N - K),
               "max_ratio": float(ratio.max()), "worst_x": j + 1,
               "max_abs": float(np.abs(e).max()),
               "rms_ratio": float(np.sqrt(np.mean(ratio**2))),
               "min_margin": margin, "l1_tail": float(l1[K - 1]),
               "pass": bool(ratio.max() <= 1.0)}
        if row["pass"]:
            cr = rot_cost(K, margin)
            row.update(c_rot=cr, n_rot=K + 1, C=(K + 1) * cr, Q=23,
                       score=23 * (K + 1) * cr)
        rows.append(row)
        print(f"K={K:8d} drop={N-K:8d} ratio={ratio.max():.4e} "
              f"maxabs={np.abs(e).max():.3e} worst_x={j+1} "
              f"margin={margin:+.3e} l1={l1[K-1]:.3e}"
              + ("  PASS" if row['pass'] else ""))
    (OUT / "ladder.json").write_text(json.dumps(
        {"rows": rows, "tol_min": tol_min, "N": N, "M": M,
         "base_score": BASE_SCORE, "base_C": BASE_C, "front_rot_C": FRONT_ROT,
         "min_coef": float(sm[-1])}, indent=2))
    print(f"\ntol_min={tol_min:.4e}  min|c|={sm[-1]:.4e}  "
          f"min|c|/tol_min={sm[-1]/tol_min:.1f}")
    print("budget: K*7.19 < 694.84 -> K <= 96;  Q-aware 24C<97700 -> C<4070.9"
          " -> K <= 566")
    print(f"wrote ladder.json ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
