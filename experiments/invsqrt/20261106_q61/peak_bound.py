"""Final quantitative bound: for each scratch wire, cost of reproducing its value at the
62-value-live operations, using the span-test linearity screen.

Lower-bound argument: producing a non-linear value in this gate set requires a Toffoli-like
gate (CCX/CSWAP/CCZ are the only deterministic non-linear gates), so each non-linear use
inside a 62-live operation costs >= 1 C unless the value can be stored in another wire --
which is impossible there because all 62 wires already carry distinct live values.
"""
from __future__ import annotations

import collections
import json

import common


def main():
    span = {r["q"]: set(r["hit_ops"]) for r in json.loads((common.OUT / "span_test.json").read_text())}
    peak = json.loads((common.OUT / "peak_touch_profile.json").read_text())
    _, ops, gates, stacks = common.load_ops()
    d = json.loads((common.OUT / "value_liveness.json").read_text())
    vl = {int(k[1:]): [tuple(x) for x in v] for k, v in d["value_liveness"].items()}
    ev = collections.Counter()
    for q, ms in vl.items():
        for a, b in ms:
            ev[a] += 1
            ev[b + 1] -= 1
    pts = sorted(ev)
    live = 0
    prof = []
    for i in pts[:-1]:
        live += ev[i]
        prof.append((i, live))
    peak_ops = set()
    for (a, l), (b, _) in zip(prof, prof[1:]):
        if l == 62:
            peak_ops.update(range(a, b))

    rows = []
    for r in peak:
        q = r["q"]
        uses = [i for i in sorted(peak_ops) if q in gates[i][1]]
        lin = [i for i in uses if i in span[q]]
        paid = [i for i in uses if gates[i][0] in common.PAID]
        rows.append({"q": q, "peak_uses": len(uses), "peak_paid": len(paid),
                     "peak_linear": len(lin), "peak_nonlinear": len(uses) - len(lin),
                     "linear_ops": lin, "peak_use_ops": uses})
    rows.sort(key=lambda r: r["peak_nonlinear"])
    print(f"{'q':>3} {'peak_uses':>9} {'paid':>5} {'linear':>6} {'nonlin':>7}   lower-bound C")
    for r in rows:
        print(f"{r['q']:>3} {r['peak_uses']:>9} {r['peak_paid']:>5} {r['peak_linear']:>6} "
              f"{r['peak_nonlinear']:>7}   >={r['peak_nonlinear']} C")
    (common.OUT / "peak_bound.json").write_text(json.dumps(rows, indent=1) + "\n")


if __name__ == "__main__":
    main()
