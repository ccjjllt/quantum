"""Diagnostics for the parity expansion: spectrum shape, sanity checks, subspaces.

1. convention sanity check: a linear function of x must be exactly 22 characters.
2. sorted |coefficient| profile and l1 tail (a sufficient K bound).
3. per-octave error profile of the K-term truncation.
4. structured subspaces: popcount(S) <= d (all polynomials of degree d) and
   dyadic-prefix subspaces (functions of the top m bits).
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


def popcounts(n: int) -> np.ndarray:
    v = np.arange(n, dtype=np.uint32)
    c = np.zeros(n, dtype=np.uint8)
    while True:
        c += (v & 1).astype(np.uint8)
        v >>= 1
        if not v.any():
            return c


def main() -> None:
    t0 = time.time()
    target = np.load(ROT33 / "target_units.npy")
    tol = np.load(ROT33 / "tol_units.npy").astype(np.float64) / 2.0**64
    xv = np.arange(1, M + 1, dtype=np.float64)
    g = 1.0 / np.sqrt(xv)
    g[0] = 0.0

    # ---- 1. sanity: linear function x must need exactly 22 characters
    lin = np.zeros(N)
    lin[1:M + 1] = xv
    cl = fwht(lin) / N
    mag = np.abs(cl)
    nz = np.flatnonzero(mag > 1e-9)
    print("SANITY linear x: nonzero coef count", len(nz), "indices", nz.tolist()[:8],
          "| 22 expected (bits 0..21); max |c| =", float(mag.max()))
    rec = fwht(np.where(np.abs(cl) > 1e-9, cl, 0.0))[1:M + 1]
    print("  reconstruction max err:", float(np.abs(rec - xv).max()))

    # ---- 2. spectrum of the natural extension
    f = np.zeros(N)
    f[1:] = 1.0 / np.sqrt(np.arange(1, N, dtype=np.float64))
    f[0] = f[1]
    coef = fwht(f) / N
    mag = np.abs(coef)
    order = np.argsort(mag)[::-1]
    sm = mag[order]
    pc = popcounts(N)
    print("\nspectrum: max", float(sm[0]), "min", float(sm[-1]),
          "energy", float(np.sum(coef**2)))
    print("magnitude at rank (1-based):")
    prof = {}
    for r in (1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192,
              16384, 32768, 65536, 131072, 262144, 524288, 1048576, 2097152,
              3145728, 4000000, 4194304):
        if r <= N:
            prof[r] = float(sm[r - 1])
            print(f"  rank {r:8d}  |c| = {sm[r-1]:.4e}")
    # l1 tail: sufficient condition sum_{S not in F}|c_S| < tol_min
    l1 = np.cumsum(sm[::-1])[::-1]           # l1[K-1] = sum of ranks K..N
    print("\nl1 tail (sum of discarded |c|):")
    for K in (41, 96, 200, 500, 1000, 2000, 10_000, 100_000, 1_000_000,
              4_000_000, 4_190_000, 4_194_000):
        print(f"  K={K:8d}  l1tail = {l1[K-1]:.4e}")
    print("tol_min =", float(tol.min()))

    # l2 tail inside the legal domain for truncation ordering (per octave)
    gm = np.zeros(N)
    gm[1:M + 1] = g
    b = fwht(gm)
    order_legal = np.argsort(np.abs(b))[::-1]
    prof_legal = {r: float(np.abs(b[order_legal[r - 1]]) / N) for r in prof}
    print("\nlegal-domain projection |b|/N at same ranks:",
          {k: f"{v:.3e}" for k, v in prof_legal.items()})

    # ---- 3. per-octave truncation error profile
    rows = []
    for K in (41, 96, 200, 500, 1000, 2000):
        C = np.zeros(N)
        C[order_legal[:K]] = b[order_legal[:K]] / N
        p = fwht(C)[1:M + 1]
        e = p - g
        e -= np.round(e)
        ratio = np.abs(e) / tol
        octs = {}
        for j in range(0, 22):
            lo = max(1, 1 << j)
            hi = min(M, (1 << (j + 1)) - 1)
            if hi <= lo:
                continue
            seg = slice(lo - 1, hi)
            octs[str(j)] = {"max_ratio": float(ratio[seg].max()),
                            "max_abs": float(np.abs(e[seg]).max())}
        rows.append({"K": K, "max_ratio": float(ratio.max()),
                     "worst_x": int(np.argmax(ratio)) + 1, "octaves": octs})
        print(f"\nK={K}: max ratio {ratio.max():.3e} @ x={int(np.argmax(ratio))+1}")
        print("   per-octave max|e|:", {k: f"{v['max_abs']:.2e}" for k, v in octs.items()})

    # ---- 4. structured subspaces
    sub = []
    pcs = popcounts(N)
    for d in (1, 2, 3, 4):
        S = np.flatnonzero(pcs <= d)
        C = np.zeros(N)
        C[S] = b[S] / N
        p = fwht(C)[1:M + 1]
        e = p - g
        e -= np.round(e)
        ratio = np.abs(e) / tol
        sub.append({"family": f"popcount<={d}", "K": int(S.size),
                    "max_ratio": float(ratio.max()),
                    "worst_x": int(np.argmax(ratio)) + 1})
        print(f"\nsubspace popcount<={d}: K={S.size} max ratio {ratio.max():.3e}"
              f" @ x={int(np.argmax(ratio))+1}")
    # dyadic prefix: functions of the top m bits = characters inside low 22-m bits
    for m in (10, 12, 14, 16, 18, 20):
        low = 22 - m
        S = np.arange(1 << low)
        C = np.zeros(N)
        C[S] = b[S] / N
        p = fwht(C)[1:M + 1]
        e = p - g
        e -= np.round(e)
        ratio = np.abs(e) / tol
        sub.append({"family": f"top{m}bits", "K": int(S.size),
                    "max_ratio": float(ratio.max()),
                    "worst_x": int(np.argmax(ratio)) + 1})
        print(f"subspace top{m} bits: K={S.size} max ratio {ratio.max():.3e}"
              f" @ x={int(np.argmax(ratio))+1}")

    (OUT / "diagnostics.json").write_text(json.dumps(
        {"magnitude_profile": prof, "legal_profile": prof_legal,
         "truncation_profile": rows, "subspaces": sub,
         "min_tol": float(tol.min())}, indent=2))
    print(f"\nwrote diagnostics.json ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
