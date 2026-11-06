"""Can any scratch wire be commuted out of [16731,18483) ?

Model
-----
Two gates whose operand sets are disjoint commute exactly (they are tensor factors), and
classical conditions only matter if a condition bit is written in between.  So a touch
g at op i can move *left* past [lo, i) iff every gate j in that range has an operand set
disjoint from O(g) and the condition stack / condition bit is unchanged.  Likewise right.

This is a *sufficient* condition (it ignores extra commutations such as CZ-CZ or CX-CX on
the same pair), so a "can move" result is a proof and a "cannot move" result is only a
blocker witness for this criterion.
"""
from __future__ import annotations

import collections
import json
import sys

import common

LO, HI = 16731, 18483


def cond_key(stacks, gates, i):
    """Classical condition identity at op i: stack contents plus the trailing `if` bit."""
    k, qs, p = gates[i]
    bit = p[-1] if "if" in p else None
    return (tuple(stacks[i]), bit)


def bit_writes_between(gates, stacks, i, j):
    out = set()
    for t in range(i, j):
        k, qs, p = gates[t]
        if k in {"BIT_STORE0", "BIT_STORE1", "BIT_INVERT"}:
            out.add(p[1])
        elif k == "HMR":
            out.add(p[-1])
    return out


def move_blockers(gates, stacks, i, dest, ops_set):
    """Gates in the open interval between i and dest that share an operand with op i.

    dest == -1 means "before the region": blockers are ops in [region_lo, i).
    dest == +1 means "after the region": blockers are ops in (i, region_hi).
    """
    k, qs, p = gates[i]
    mine = set(qs)
    lo, hi = (LO, i) if dest < 0 else (i + 1, HI)
    bad = []
    for j in range(lo, hi):
        if set(gates[j][1]) & mine:
            bad.append(j)
    return bad


def main():
    _, ops, gates, stacks = common.load_ops()
    census = collections.Counter(gates[i][0] for i in range(LO, HI))
    print(f"region [{LO},{HI}) ops={HI-LO}")
    print("gate kinds:", dict(census))

    touches = common.touches(gates)
    rows = []
    for w in range(22, 62):
        ts = [i for i in touches[w] if LO <= i < HI]
        if not ts:
            print(f"q{w}: untouched in region")
            continue
        info = []
        for i in ts:
            lb = move_blockers(gates, stacks, i, -1, None)
            rb = move_blockers(gates, stacks, i, +1, None)
            info.append({"op": i, "instr": ops[i], "kind": gates[i][0],
                         "can_left": not lb, "left_blockers": lb[:4],
                         "can_right": not rb, "right_blockers": rb[:4]})
        allmove = all(x["can_left"] or x["can_right"] for x in info)
        rows.append({"wire": w, "touches": len(ts), "all_can_move": allmove,
                     "detail": info})
        kinds = dict(collections.Counter(x["kind"] for x in info))
        nleft = sum(x["can_left"] for x in info)
        nright = sum(x["can_right"] for x in info)
        print(f"q{w}: {len(ts):>4} touches {kinds}  can_left={nleft} can_right={nright}"
              f"{'  <-- FULL' if allmove else ''}")
    rows.sort(key=lambda r: (-r["all_can_move"], r["touches"]))
    (common.OUT / "commute_region.json").write_text(json.dumps(rows, indent=1) + "\n")

    full = [r for r in rows if r["all_can_move"]]
    print(f"\nwires whose every region touch can move out: {[r['wire'] for r in full]}")
    # For the best few wires, show why the others cannot move.
    for r in rows[:3]:
        print(f"\nq{r['wire']} blockers:")
        for x in r["detail"][:12]:
            print(f"  op{x['op']} {x['kind']}: left={x['can_left']} right={x['can_right']} "
                  f"{x['instr']}" + ("" if x["can_left"] or x["can_right"]
                                     else f" left_block={x['left_blockers']}"))


if __name__ == "__main__":
    main()
