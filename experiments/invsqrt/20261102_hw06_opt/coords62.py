"""Full-domain input coordinates for the 62Q invsqrt baseline.

Mathematical model (complete decomposition, bit20 included):
    lz     = number of leading zeros of x in 22 bits (x>=1, so lz in 0..21)
    m      = x << lz            (22-bit mantissa window, top bit set)
    parity = lz & 1
    a      = (parity << 7) | ((m >> 14) & 127)
    delta  = m & 16383          (low 14 bits)

Physical on-wire address encodings are modelled separately (see
wire_addr62, a placeholder hook filled by Track A as stages align).
Non-contiguous registers are allowed; there is no forced contiguous
19-bit T and no zero-coefficient Horner placeholder check.

Usage:
    uv run python experiments/invsqrt/20261102_hw06_opt/coords62.py --roundtrip
"""

from __future__ import annotations

import argparse
import sys

WIDTH = 22
X_MAX = 3_133_452  # official domain 1..3133452


def decompose(x: int):
    """Return (lz, m, parity, a, delta) for 1 <= x <= X_MAX."""
    if not 1 <= x <= X_MAX:
        raise ValueError(f"x out of domain: {x}")
    lz = WIDTH - x.bit_length()
    m = (x << lz) & ((1 << WIDTH) - 1)
    parity = lz & 1
    a = (parity << 7) | ((m >> 14) & 127)
    delta = m & 16383
    return lz, m, parity, a, delta


def roundtrip(x: int) -> bool:
    """Rebuild x from (lz, m); a/delta are derived views, checked for range."""
    lz, m, parity, a, delta = decompose(x)
    if not (0 <= a <= 255 and 0 <= delta <= 16383):
        return False
    if (m >> 21) != 1:  # normalized top bit must be set
        return False
    if ((m >> 14) & 127) != (a & 127) or (lz & 1) != (a >> 7):
        return False
    if (m & 16383) != delta:
        return False
    return (m >> lz) == x


def wire_addr62(x: int) -> dict:
    """Hook for the physical on-wire address encoding (Track A fills in).

    The math model above is authoritative for fitting; wire encodings must
    be modelled separately and never silently substituted for (a, delta).
    """
    lz, m, parity, a, delta = decompose(x)
    return {"lz": lz, "m": m, "parity": parity, "a": a, "delta": delta,
            "note": "wire encoding not yet aligned; do not use as circuit ground truth"}


def full_roundtrip(xs=None) -> dict:
    xs = range(1, X_MAX + 1) if xs is None else xs
    bad = [x for x in xs if not roundtrip(x)]
    # x=2/3 collision watch: same lz, adjacent mantissas must stay distinct
    watch = {x: decompose(x) for x in (2, 3)}
    distinct = watch[2][:2] != watch[3][:2] or watch[2][1] != watch[3][1]
    return {"checked": len(list(xs)) if not isinstance(xs, range) else len(xs),
            "failures": bad[:10], "n_fail": len(bad),
            "x2": watch[2], "x3": watch[3], "x2_x3_distinct": distinct}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roundtrip", action="store_true")
    ap.add_argument("--x", type=int, default=None)
    args = ap.parse_args()
    if args.x is not None:
        lz, m, parity, a, delta = decompose(args.x)
        print(f"x={args.x} lz={lz} m={m:#08x} parity={parity} a={a} delta={delta} "
              f"roundtrip={roundtrip(args.x)}")
        return 0
    if args.roundtrip:
        res = full_roundtrip()
        print(f"checked={res['checked']} n_fail={res['n_fail']}")
        print(f"x=2 -> {res['x2']}")
        print(f"x=3 -> {res['x3']} distinct={res['x2_x3_distinct']}")
        if res["n_fail"]:
            print(f"first failures: {res['failures']}")
            return 1
        print("ROUNDTRIP PASS over full domain 1..3133452 (bit20 included)")
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
