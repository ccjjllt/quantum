"""Park-and-rebuild accounting over every maximal 62-value-live block.

To reach 61 registers, at each op where 62 values are live, one value must be destroyed and
rebuilt later.  The cheapest unit is a whole block: destroy an untouched wire at the block
start and rebuild it at the block end.  Rebuild is free only if the wire's value there is an
XOR of other live wires (span test, 512-x screen, 2 HMR branches).
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
    blocks = []
    for (a, l), (b, _) in zip(prof, prof[1:]):
        if l == 62:
            if blocks and blocks[-1][1] == a:
                blocks[-1][1] = b
            else:
                blocks.append([a, b])
    _, ops, gates, stacks = common.load_ops()
    touches = common.touches(gates)
    total = 0
    infeasible = 0
    rows = []
    for a, b in blocks:
        cands = []
        for q in range(22, 62):
            if any(a <= i < b for i in touches[q]):
                continue
            if not any(iv[0] <= a and iv[1] >= b for iv in vl[q]):
                continue
            # value at block end is used at the next touch; check linearity at that op
            nxt = [i for i in touches[q] if i >= b]
            if not nxt:
                cands.append({"q": q, "free": True, "next": None})
                continue
            n = nxt[0]
            cands.append({"q": q, "next": n, "free": n in span[q], "instr": ops[n]})
        best = min([0 if c["free"] else 1 for c in cands], default=None)
        if best is None:
            infeasible += 1
        else:
            total += best
        rows.append({"block": [a, b], "len": b - a, "candidates": cands, "best_cost": best})
    print(f"blocks={len(blocks)}  with no untouched-live wire={infeasible}  "
          f"sum of per-block best rebuild cost >= {total} C")
    for r in sorted(rows, key=lambda x: -x["len"]):
        free = [c["q"] for c in r["candidates"] if c["free"]]
        print(f"  [{r['block'][0]},{r['block'][1]}) len={r['len']:>5} "
              f"candidates={len(r['candidates'])} free={free[:8]} best={r['best_cost']}")
    (common.OUT / "block_park_bound.json").write_text(json.dumps(
        {"blocks": len(blocks), "infeasible": infeasible, "sum_best_cost": total,
         "rows": rows}, indent=1) + "\n")


if __name__ == "__main__":
    main()
