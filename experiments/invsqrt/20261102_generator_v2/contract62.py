"""Independent check of the fixed-point contract for candidate 7_8_16_5_trunc.

Model side is pure integer math (no floats): CSD tables are exact sums of
signed powers of two, evaluated with Fraction, then RH(z)=floor(z+1/2).
Target/tolerance side uses the official verifier's reference_values
(authoritative contract, not model).

Contract (frozen):
    B[a] = RH(B0[a] x 2^32)    unsigned 33 bit
    A[a] = -RH(M[a] x 2^29)    unsigned 22 bit, sign outside rounding
    R[a] = RH(Rcoef[a] x 2^26) unsigned 12 bit
    lz = 22 - bit_length(x); m = x << lz; p = lz & 1
    a = (p << 7) | ((m >> 14) & 127); delta = m & 16383
    D = delta - 8192            signed 14 bit
    U = (delta >> 5) - 256      signed 9 bit
    S = U^2                     unsigned 17 bit
    V = (B[a] << 12) - 2*A[a]*D + R[a]*S
    e = (lz >> 1) + p - 11; t = 8 - e        # 8..19
    P = RH(V / 2^t) mod 2^36; phase = P / 2^36 turns

Expected checks: 0 failures over all 3,133,452 inputs, max rel 0.6096379373,
min margin 271128766 x 2^-64 turns, 0 < V < 2^45.

Usage:
    uv run python experiments/invsqrt/20261102_generator_v2/contract62.py [--tables-only | --full]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data/competition/verifiers"))

from invsqrt import verify_submission_invsqrt as official  # noqa: E402

FIT = ROOT / "artifacts/20261102_hw06_opt/invsqrt/trackB_fit_7_8_16_5_trunc.json"
TABLES = ROOT / "artifacts/20261102_generator_v2/invsqrt/int_tables_7_8_16_5_trunc.json"
X_MAX = 3_133_452
TOL_POW = 24  # official: phase error budget 2^-24/sqrt(x)


def csd_value(digits) -> Fraction:
    return sum(Fraction(s) * Fraction(2) ** p for p, s in digits)


def RH(z: Fraction) -> int:
    # floor(z + 1/2); Python // on positive denominator already floors,
    # including for negative numerators (halves round toward +inf).
    return (z.numerator * 2 + z.denominator) // (2 * z.denominator)


def build_tables():
    doc = json.loads(FIT.read_text())
    coef = doc["coef"]
    B, A, R = [], [], []
    for a in range(256):
        p, seg = a >> 7, a & 127
        c = coef[f"{p}_{seg}"]
        b0, m, r = (csd_value(c[k]) for k in ("B0", "M", "R"))
        B.append(RH(b0 * 2**32))
        A.append(-RH(m * 2**29))
        R.append(RH(r * 2**26))
    assert all(0 <= v < 2**33 for v in B), "B width"
    assert all(0 <= v < 2**22 for v in A), "A width"
    assert all(0 <= v < 2**12 for v in R), "R width"
    return B, A, R


def serialize(B, A, R) -> bytes:
    buf = bytearray()
    for v in B:
        buf += struct.pack("<Q", v)
    for v in A:
        buf += struct.pack("<I", v)
    for v in R:
        buf += struct.pack("<H", v)
    return bytes(buf)


def model_phase(x: int, B, A, R):
    lz = 22 - x.bit_length()
    m = x << lz
    p = lz & 1
    a = (p << 7) | ((m >> 14) & 127)
    delta = m & 16383
    D = delta - 8192
    U = (delta >> 5) - 256
    S = U * U
    V = (B[a] << 12) - 2 * A[a] * D + R[a] * S
    e = (lz >> 1) + p - 11
    t = 8 - e
    P = ((V + 2 ** (t - 1)) >> t) & (2**36 - 1) if V >= 0 else None
    return V, t, P


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tables-only", action="store_true")
    ap.add_argument("--full", action="store_true")
    args = ap.parse_args()

    fit_hash = hashlib.sha256(FIT.read_bytes()).hexdigest()
    B, A, R = build_tables()
    blob = serialize(B, A, R)
    thash = hashlib.sha256(blob).hexdigest()
    TABLES.write_text(json.dumps(
        {"fit_sha256": fit_hash, "tables_sha256": thash, "B": B, "A": A, "R": R},
        indent=0) + "\n")
    print(f"fit_sha256={fit_hash}")
    print(f"tables_sha256={thash} (format: 256x<u64 B + 256x<u32 A + 256x<u16 R, LE)")
    print(f"B range [{min(B)},{max(B)}] A range [{min(A)},{max(A)}] R range [{min(R)},{max(R)}]")
    if args.tables_only:
        return 0

    import numpy as np
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    tgt_all, tol_all = official.reference_values(
        spec, np.arange(1, X_MAX + 1, dtype=np.uint64))
    tgt = np.asarray(tgt_all, dtype=np.float64) / 2**64
    tol = np.asarray(tol_all, dtype=np.float64) / 2**64

    fails, maxrel, min_margin, worst, vmin, vmax = 0, 0.0, None, None, None, None
    for x in range(1, X_MAX + 1):
        V, t, P = model_phase(x, B, A, R)
        assert 8 <= t <= 19, (x, t)
        vmin = V if vmin is None else min(vmin, V)
        vmax = V if vmax is None else max(vmax, V)
        if not (0 < V < 2**45):
            fails += 1
            if fails < 5:
                print(f"V RANGE FAIL x={x} V={V}")
            continue
        err = (P / 2**36 - tgt[x - 1] + 0.5) % 1.0 - 0.5
        ae = abs(err)
        rel = ae / tol[x - 1]
        if rel > maxrel:
            maxrel, worst = rel, (x, ae)
        margin = (tol[x - 1] - ae) * 2**64
        min_margin = margin if min_margin is None else min(min_margin, margin)
        if ae > tol[x - 1]:
            fails += 1
            if fails < 5:
                print(f"FAIL x={x} ae={ae:.3e} tol={tol[x-1]:.3e} rel={rel:.6f}")
        if x % 1_000_000 == 0:
            print(f"... {x} done, fails={fails}, maxrel={maxrel:.6f}", flush=True)
    print(f"checked={X_MAX} fails={fails} maxrel={maxrel:.10f} "
          f"worst={worst} min_margin_units={min_margin:.1f} V_range=({vmin},{vmax})")
    print("CONTRACT FULL " + ("PASS" if fails == 0 else "FAIL"))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
