"""Parking cover with a rebuild-cost model based on what the gap's right end does to w.

Cost 0 (value re-initialised, previous value irrelevant):
  * X w, R w, HMR w
  * CCX a b w   (init_and requires w = |0>, which the park guarantees)
  * SWAP w v / SWAP v w  (value replaced by the partner's)
  * CX s w      -> NOT free (needs the old value)
Cost 1+ : first touch is a read (control / phase / CZ / CSWAP).
"""
from __future__ import annotations

import collections
import json

import common

ZERO_WRITE = {"X", "R", "HMR"}


def right_cost(gates, w, i):
    k, qs, p = gates[i]
    if k in ZERO_WRITE and qs[0] == w:
        return 0, "reinit"
    if k == "CCX" and qs[2] == w:
        return 0, "init_and"
    if k == "SWAP" and w in qs:
        return 0, "swap"
    if k == "CX" and qs[1] == w:
        return 1, "xor_write"
    return 1, "read"


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
    options = []
    for w in range(22, 62):
        ts = touches[w]
        for left, right in zip(ts, ts[1:]):
            covered = frozenset(i for i in peak_ops if left < i < right)
            if not covered:
                continue
            c, why = right_cost(gates, w, right)
            if right in span[w]:
                c, why = 0, why + "+linear"
            options.append({"wire": w, "gap": [left, right], "covered": sorted(covered),
                            "cost": c, "why": why, "next_instr": ops[right]})
    zero = [o for o in options if o["cost"] == 0]
    covered0 = set()
    for o in zero:
        covered0 |= set(o["covered"])
    print(f"peak ops={len(peak_ops)}  options={len(options)}  zero-cost options={len(zero)}")
    print(f"zero-cost cover: {len(covered0)}/{len(peak_ops)} ops, missing {len(peak_ops - covered0)}")
    # greedy min-cost cover
    remaining = set(peak_ops)
    chosen = []
    while remaining:
        def gain(o):
            return len(set(o["covered"]) & remaining) / (1 if o["cost"] else 0.5)
        best = max(options, key=gain)
        g = len(set(best["covered"]) & remaining)
        if g == 0:
            break
        chosen.append(best)
        remaining -= set(best["covered"])
    print(f"\ngreedy cover: {len(chosen)} parkings, cost {sum(c['cost'] for c in chosen)}, "
          f"uncovered {len(remaining)}")
    for c in chosen:
        print(f"  q{c['wire']} gap {c['gap']} covers {len(c['covered'])} cost={c['cost']} "
              f"({c['why']}) rebuild at {c['gap'][1]}: {c['next_instr']}")
    if remaining:
        print("uncovered sample:", sorted(remaining)[:10])
    (common.OUT / "park_cover_cost.json").write_text(json.dumps(
        {"peak_ops": len(peak_ops), "options": len(options), "zero_covered": len(covered0),
         "chosen": chosen, "uncovered": sorted(remaining)}, indent=1) + "\n")


if __name__ == "__main__":
    main()
