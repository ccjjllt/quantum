"""Count the paid logic in each rotation loading window of the baseline."""
from __future__ import annotations

import io
import json
from fractions import Fraction
from pathlib import Path

import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "artifacts/20261106_syed_v9/invsqrt/syed_v9_nofallback.kmb"
OUT = ROOT / "artifacts/20261106_rot33"
PAID = {"CCX", "CCZ", "CSWAP"}


def classify(t: Fraction) -> str:
    if t % Fraction(1, 2) == 0:
        return "clifford"
    if t % Fraction(1, 4) == 0:
        return "t"
    return "rotation"


def main() -> None:
    c = km.Circuit.from_file(BASE)
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    ops = [l for l in buf.getvalue().splitlines() if not l.startswith(("APPEND", "REGISTER"))]
    rot = [i for i, l in enumerate(ops) if l.startswith("Z_POW")
           and classify(Fraction(l.split()[2])) == "rotation"]
    print("rotations", len(rot))
    # Window: from the previous rotation's HMR+1 (or 120 ops before the first)
    # through the Z_POW itself.  Count paid gates and total ops.
    rows = []
    prev = max(0, rot[0] - 120)
    for k, i in enumerate(rot):
        w = ops[prev:i + 1]
        paid = sum(1 for l in w if l.split()[0] in PAID)
        ccx = sum(1 for l in w if l.split()[0] == "CCX")
        cswap = sum(1 for l in w if l.split()[0] == "CSWAP")
        rows.append({"rot": k, "op": i, "window": [prev, i + 1], "ops": len(w),
                     "paid": paid, "CCX": ccx, "CSWAP": cswap})
        prev = i + 1
    total = sum(r["paid"] for r in rows)
    print("total paid in loading windows", total)
    print("mean paid per rotation", total / len(rows))
    for r in rows:
        print(r)
    # Also count all paid gates between the first and last rotation (both blocks).
    lo, hi = rot[0], rot[-1] + 1
    allpaid = sum(1 for l in ops[lo:hi] if l.split()[0] in PAID)
    print("paid in [first rotation, last rotation)", allpaid)
    (OUT / "gadget_cost.json").write_text(json.dumps(
        {"rows": rows, "total_loading_paid": total,
         "mean_loading_paid": total / len(rows),
         "paid_between_first_and_last_rotation": allpaid}, indent=2) + "\n")


if __name__ == "__main__":
    main()
