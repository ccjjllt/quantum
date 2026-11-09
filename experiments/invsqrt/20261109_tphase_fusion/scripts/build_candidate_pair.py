"""Build candidate B: merge rotation pair (op 25860 + op 25903) into one.

Keeps Z_POW @25860 with exact summed angle, deletes Z_POW @25903.
Writes artifacts/20261109_tphase_fusion/candidate_pair_merge.kmb.
"""
from __future__ import annotations

import io
from fractions import Fraction
from pathlib import Path

KMB = "artifacts/20261108_public_frontier/release/invsqrt.kmb"
OUT = "artifacts/20261109_tphase_fusion/candidate_pair_merge.kmb"
KEEP, DROP = 25852, 25903  # placeholder, overwritten below
KEEP, DROP = 25860, 25903


def frac_to_decimal(fr: Fraction) -> str:
    assert fr >= 0
    assert fr.denominator & (fr.denominator - 1) == 0  # power of two
    digits = []
    rem = fr.numerator
    den = fr.denominator
    while rem:
        rem *= 10
        digits.append(str(rem // den))
        rem %= den
    return "0." + "".join(digits)


def main() -> None:
    import kickmix as km
    c = km.Circuit.from_file(KMB)
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    hdr = [l for l in lines if l.startswith(("APPEND", "REGISTER"))]
    ops = [l for l in lines if l and not l.startswith(("APPEND", "REGISTER"))]
    assert ops[KEEP].startswith("Z_POW q28 "), ops[KEEP]
    assert ops[DROP].startswith("Z_POW q28 "), ops[DROP]
    a1 = Fraction(ops[KEEP].split()[2])
    a2 = Fraction(ops[DROP].split()[2])
    total = a1 + a2
    dec = frac_to_decimal(total)
    assert Fraction(dec) == total, (dec, total)
    print("sum =", total, "->", dec)
    ops[KEEP] = f"Z_POW q28 {dec}"
    del ops[DROP]
    kmx = "\n".join(hdr + ops) + "\n"
    c2 = km.Circuit.from_file(io.StringIO(kmx), format="kmx")
    assert len(c2) == len(ops), (len(c2), len(ops))
    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    c2.to_file(OUT, format="kmb")
    print("wrote", OUT, "ops", len(c2), "qubits", c2.num_qubits)


if __name__ == "__main__":
    main()
