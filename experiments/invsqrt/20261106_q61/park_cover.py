"""Minimum park-and-rebuild cover of the 62-value-live operations.

A wire w can be reset for free at any point inside a gap between two consecutive touches
(its value is untouched there).  Resetting frees w's register for the whole gap; the value
must be rebuilt at the gap's right end (the next touch), costing >=1 C when it is not an
XOR of the other live wires.

Cover all ops with 62 live values by such gap-parkings; report the minimum number of
parkings and the sum of the cheapest rebuild costs.
"""
from __future__ import annotations

import collections
import json

import common


def main():
    span = {r["q"]: set(r["hit_ops"]) for r in json.loads((common.OUT / "span_test.json").read_text())}
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
    _, ops, gates, stacks = common.load_ops()
    touches = common.touches(gates)

    options = []   # (covered frozenset, wire, gap, next_op, cheap?)
    for w in range(22, 62):
        ts = touches[w]
        for left, right in zip(ts, ts[1:]):
            covered = frozenset(i for i in peak_ops if left < i < right)
            if not covered:
                continue
            cheap = right in span[w]
            options.append({"wire": w, "gap": [left, right], "covered": sorted(covered),
                            "next_instr": ops[right], "cheap": cheap})
    print(f"peak ops {len(peak_ops)}, parking options {len(options)}")
    # greedy cover
    remaining = set(peak_ops)
    chosen = []
    while remaining:
        best = max(options, key=lambda o: len(set(o["covered"]) & remaining), default=None)
        gain = len(set(best["covered"]) & remaining) if best else 0
        if gain == 0:
            print("cannot cover", len(remaining), "ops")
            break
        chosen.append(best)
        remaining -= set(best["covered"])
    print(f"greedy parkings: {len(chosen)}, uncovered {len(remaining)}")
    cost = 0
    for c in chosen:
        cost += 0 if c["cheap"] else 1
        print(f"  q{c['wire']} gap {c['gap']} covers {len(c['covered'])} ops, "
              f"cheap={c['cheap']}, rebuild at {c['gap'][1]}: {c['next_instr']}")
    print(f"sum of cheap-rebuild costs >= {cost} C")
    (common.OUT / "park_cover.json").write_text(json.dumps(
        {"peak_ops": len(peak_ops), "options": len(options),
         "chosen": chosen, "uncovered": len(remaining), "cost_lower_bound": cost}, indent=1) + "\n")


if __name__ == "__main__":
    main()
