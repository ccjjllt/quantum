"""Blocker table for the region [16731,18483): which gate stops each wire's touches moving out.

For every scratch wire touched inside the region, report per touch whether it can move left
of LO / right of HI under exact commutation, and name the first blocking gate.  Then
aggregate the blocking gates to get the minimal set that blocks every candidate.
"""
from __future__ import annotations

import collections
import functools
import json

import common
from commute import commutes

LO, HI = 16731, 18483


@functools.lru_cache(maxsize=None)
def _cached(k1, q1, e1, k2, q2, e2):
    return commutes((k1, list(q1), ["", e1]), (k2, list(q2), ["", e2]))


def commutes_i(gates, i, j):
    k1, q1, p1 = gates[i]
    k2, q2, p2 = gates[j]
    return _cached(k1, tuple(q1), p1[1] if k1 == "Z_POW" else "",
                   k2, tuple(q2), p2[1] if k2 == "Z_POW" else "")


def main():
    _, ops, gates, stacks = common.load_ops()
    touches = common.touches(gates)
    rows = []
    blocker_count = collections.Counter()
    print(f"{'q':>3} {'touches':>7} {'L':>4} {'R':>4}  first blocked touch | blocker")
    for w in range(22, 62):
        ts = [i for i in touches[w] if LO <= i < HI]
        if not ts:
            continue
        nl = nr = 0
        first = None
        detail = []
        for i in ts:
            bl = [j for j in range(LO, i) if not commutes_i(gates, i, j)]
            br = [j for j in range(i + 1, HI) if not commutes_i(gates, i, j)]
            canl, canr = (not bl), (not br)
            nl += canl
            nr += canr
            if not (canl or canr):
                b = bl[0] if bl else br[0]
                blocker_count[b] += 1
                if first is None:
                    first = (i, ops[i], b, ops[b])
            detail.append({"op": i, "instr": ops[i], "can_left": canl, "can_right": canr,
                           "left_blocker": bl[0] if bl else None,
                           "right_blocker": br[0] if br else None})
        rows.append({"wire": w, "touches": len(ts), "left": nl, "right": nr,
                     "first_blocked": first, "detail": detail})
        print(f"{w:>3} {len(ts):>7} {nl:>4} {nr:>4}  {first}")
    print(f"\nwires fully movable out of region: "
          f"{[r['wire'] for r in rows if r['left'] + r['right'] == 2 * r['touches']]}")
    print("\nmost frequent blocking gates (gate -> #wire-touches it blocks):")
    for b, n in blocker_count.most_common(15):
        print(f"  op{b:>6} {ops[b]:<16} blocks {n}")
    print(f"\ndistinct blocking gates: {len(blocker_count)}")
    (common.OUT / "commute_blockers.json").write_text(json.dumps(
        {"rows": rows, "blocker_counts": {str(k): v for k, v in blocker_count.items()},
         "blocker_instr": {str(k): ops[k] for k in blocker_count}}, indent=1) + "\n")


if __name__ == "__main__":
    main()
