"""Approach B: Walsh-Hadamard transform of exp(2 pi i T(x)) on the 2^22 cube.

A_S = (1/N) sum_x exp(2 pi i T(x)) chi_S(x)   (complex)
keep the K largest |A_S|, reconstruct z(x) = sum_S A_S chi_S(x), and report the
legal-domain phase error of arg(z)/(2 pi) against T.

A real Z_POW parity term can only add a REAL coefficient, so two variants are
reported:
  complex : the phase of the truncated complex sum (an upper bound on what a
            phase-only (unit-modulus) reconstruction can do),
  real    : the linear real-coefficient expansion sum_S Re(A_S) chi_S(x).

Extensions for invalid x are the same three as spectrum.py.
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
KS = [41, 96, 200, 500, 1000, 2000]


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


def build(kind: str) -> np.ndarray:
    """Phase target T(x) in turns on the whole cube."""
    x = np.arange(N, dtype=np.float64)
    t = np.zeros(N)
    t[1:] = 1.0 / np.sqrt(x[1:])
    if kind == "zero":
        t[M + 1:] = 0.0
        t[0] = 0.0
    elif kind == "const":
        t[M + 1:] = t[M]
        t[0] = t[1]
    elif kind == "natural":
        t[0] = t[1]
    else:
        raise ValueError(kind)
    return t


def main() -> None:
    t0 = time.time()
    tol = np.load(ROT33 / "tol_units.npy").astype(np.float64) / 2.0**64
    tgt_units = np.load(ROT33 / "target_units.npy")
    t_legal = tgt_units.astype(np.float64) / 2.0**64      # exact target mod 1
    rows = []
    for kind in ("zero", "const", "natural"):
        T = build(kind)
        ph = np.exp(2j * np.pi * T)
        Ar = fwht(ph.real) / N
        Ai = fwht(ph.imag) / N
        amp = np.hypot(Ar, Ai)
        order = np.argsort(amp)[::-1]
        print(f"\n[{kind}] top |A|: {amp[order[:6]]}  "
              f"rank-2000 |A| = {amp[order[1999]]:.3e}  ({time.time()-t0:.1f}s)")
        amp_sorted = amp[order]
        amp_l1 = np.cumsum(amp_sorted[::-1])[::-1]
        amp_prof = {str(r): float(amp_sorted[r - 1])
                    for r in (1, 10, 100, 1000, 2000, 10_000, 100_000, 1_000_000)}
        for K in KS:
            S = order[:K]
            C = np.zeros(N, dtype=np.complex128)
            C[S] = Ar[S] + 1j * Ai[S]
            z = fwht(C.real) + 1j * fwht(C.imag)
            p = np.angle(z) / (2 * np.pi)                  # in (-0.5, 0.5]
            e = p[:M] - t_legal
            e -= np.round(e)
            ratio = np.abs(e) / tol
            # real-coefficient linear expansion
            Cr = np.zeros(N)
            Cr[S] = Ar[S]
            pr = fwht(Cr)[:M]
            er = pr - t_legal
            er -= np.round(er)
            ratior = np.abs(er) / tol
            rows.append({"ext": kind, "K": K,
                         "amp_profile": amp_prof,
                         "amp_l1_tail_K": float(amp_l1[K - 1]),
                         "complex_max_ratio": float(ratio.max()),
                         "complex_worst_x": int(np.argmax(ratio)) + 1,
                         "abs_max_ratio": float(amp.max()),
                         "real_max_ratio": float(ratior.max()),
                         "real_worst_x": int(np.argmax(ratior)) + 1,
                         "min_modulus": float(np.abs(z[:M]).min())})
            print(f"  K={K:5d} complex phase ratio {ratio.max():.4e}"
                  f" (|z|_min {np.abs(z[:M]).min():.2e})"
                  f"  real-coef ratio {ratior.max():.4e}")
    (OUT / "walsh_phase.json").write_text(json.dumps(rows, indent=2))
    print(f"\nwrote walsh_phase.json ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
