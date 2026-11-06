"""Which scratch wires are actually touched inside the 62-value-live operations?

Uses artifacts/20261106_q61/value_liveness.json (produced by value_liveness.py).
"""
from __future__ import annotations

import collections
import json

import common


def main():
    d = json.loads((common.OUT / "value_liveness.json").read_text())
    vl = {int(k[1:]): v for k, v in d["value_liveness"].items()}
    ev = collections.Counter()
    for q, ms in vl.items():
        for a, b in ms:
            ev[a] += 1
            ev[b + 1] -= 1
    pts = sorted(ev)
    live = 0
    counts = []
    for i in pts[:-1]:
        live += ev[i]
        counts.append((i, live))
    peak_ops = set()
    for (a, l), (b, _) in zip(counts, counts[1:]):
        if l >= 62:
            peak_ops.update(range(a, b))
    _, ops, gates, stacks = common.load_ops()
    rows = []
    for q in range(22, 62):
        touched = [i for i in peak_ops if q in gates[i][1]]
        paid = [i for i in touched if gates[i][0] in common.PAID]
        segs = common.conservative_segments(gates, stacks, q)
        # ops in peak set that fall inside one of q's conservative live segments
        interior = [i for i in peak_ops
                    if any(a <= i < b for a, b, _ in segs) and q not in gates[i][1]]
        rows.append({"q": q, "touch_in_62live": len(touched), "paid_in_62live": len(paid),
                     "untouched_but_live_in_62live": len(interior),
                     "paid_ops_in_62live": paid[:40]})
    rows.sort(key=lambda r: (r["touch_in_62live"], r["paid_in_62live"]))
    print(f"62-live ops: {len(peak_ops)}")
    print(f"{'q':>3} {'touched':>8} {'paid':>5} {'untouched_live':>14}")
    for r in rows:
        print(f"{r['q']:>3} {r['touch_in_62live']:>8} {r['paid_in_62live']:>5} "
              f"{r['untouched_but_live_in_62live']:>14}")
    (common.OUT / "peak_touch_profile.json").write_text(json.dumps(rows, indent=1) + "\n")


if __name__ == "__main__":
    main()
