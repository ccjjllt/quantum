"""Peak blocks vs per-wire value intervals: where could a value be parked and rebuilt?

For every maximal run of ops where the value-liveness count is 62, list the wires that are
live through the whole block and their nearest read/write outside the block.
"""
from __future__ import annotations

import collections
import json

import common


def main():
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
    print("peak blocks (>=200 ops):")
    for a, b in blocks:
        if b - a >= 200:
            print(f"  [{a},{b}) len={b-a}")
    rows = []
    for a, b in blocks:
        if b - a < 50:
            continue
        for q in range(22, 62):
            inside = [i for i in touches[q] if a <= i < b]
            if inside:
                continue
            before = [i for i in touches[q] if i < a]
            after = [i for i in touches[q] if i >= b]
            # is q live across the whole block?
            covering = [iv for iv in vl[q] if iv[0] <= a and iv[1] >= b]
            if not covering:
                continue
            rows.append({
                "block": [a, b], "q": q,
                "prev_touch": before[-1] if before else None,
                "prev_instr": ops[before[-1]] if before else None,
                "next_touch": after[0] if after else None,
                "next_instr": ops[after[0]] if after else None,
                "gap_next": (after[0] - b) if after else None,
                "interval": list(covering[0]),
            })
    rows.sort(key=lambda r: (-(r["block"][1] - r["block"][0]), r["gap_next"] or 0))
    print(f"\n{'block':<18} {'q':>3} {'prev':>7} {'next':>7} {'gap':>6}  prev_instr -> next_instr")
    for r in rows:
        print(f"{str(r['block']):<18} {r['q']:>3} {r['prev_touch']:>7} {r['next_touch']:>7} "
              f"{r['gap_next'] if r['gap_next'] is not None else -1:>6}  "
              f"{r['prev_instr']} -> {r['next_instr']}")
    (common.OUT / "peak_blocks.json").write_text(json.dumps(rows, indent=1) + "\n")


if __name__ == "__main__":
    main()
