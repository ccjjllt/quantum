"""Task3b: global recompute cones + cheapest spill candidate vs budget.

Global cone DP over unconditional ops only (X/CX/CCX/SWAP propagate; HMR/R reset
to empty; any conditional write taints the target wire: cone = None = invalid
for simple uncompute/recompute spill).
Spill cost for wire w across [2006,14215] (untouched there):
  cost = |prefix cone @2006| (uncompute) + |full cone @14215| (recompute)  [CCX]
Budget: 1539.2 pts = 25.23 CCX @61Q.
Also: global first-write per wire (are q0..q13 primary inputs?), cheapest
non-input wire by total cone + its in-segment touch density.
"""
import io
import json
from pathlib import Path

import kickmix as km

KMB = Path("artifacts/20261108_public_frontier/release/invsqrt.kmb")
SLO, SHI = 2006, 14215


def parse_ops():
    c = km.Circuit.from_file(str(KMB))
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    return [l for l in buf.getvalue().splitlines()
            if l and not l.startswith(("APPEND", "REGISTER"))]


def main():
    ops = parse_ops()
    cone = [set() for _ in range(62)]
    tainted = [False] * 62
    first_write = {}
    prefix_at_2006 = {}
    depth = 0
    for idx, l in enumerate(ops):
        if idx == SLO:
            prefix_at_2006 = {w: (None if tainted[w] else len(cone[w]))
                              for w in range(62)}
        if l.startswith("PUSH_CONDITION"):
            depth += 1
            continue
        if l.startswith("POP_CONDITION"):
            depth -= 1
            continue
        p = l.split()
        op = p[0]
        cond = (depth > 0) or (" if " in l)
        if op in ("HMR", "R"):
            w = int(p[1][1:])
            if cond:
                tainted[w] = True
            else:
                cone[w] = set()
            first_write.setdefault(w, idx)
        elif op == "X":
            w = int(p[1][1:])
            if cond:
                tainted[w] = True
            first_write.setdefault(w, idx)
        elif op == "CX":
            a, b = int(p[1][1:]), int(p[2][1:])
            if cond:
                tainted[b] = True
            elif not tainted[b]:
                cone[b] |= cone[a]
            first_write.setdefault(b, idx)
        elif op == "CCX":
            a, b, t = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            if cond:
                tainted[t] = True
            elif not tainted[t]:
                cone[t] = cone[t] | cone[a] | cone[b] | {idx}
            first_write.setdefault(t, idx)
        elif op == "CSWAP":
            cc, a, b = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            if cond:
                tainted[a] = tainted[b] = True
            else:
                cone[a], cone[b] = cone[b], cone[a]
            first_write.setdefault(a, idx)
            first_write.setdefault(b, idx)
        elif op == "SWAP":
            a, b = int(p[1][1:]), int(p[2][1:])
            if not cond:
                cone[a], cone[b] = cone[b], cone[a]
        # diagonal/classical ops: no cone change
    full_at_end = {w: (None if tainted[w] else len(cone[w])) for w in range(62)}

    print("first_write q0..q21:", {w: first_write.get(w) for w in range(22)})
    print("prefix cone@2006 q0..q21:",
          {w: prefix_at_2006[w] for w in range(22)})

    # touches in segment
    seg_touch = {w: 0 for w in range(62)}
    for l in ops[SLO:SHI]:
        for t in l.split()[1:]:
            if t.startswith("q") and t[1:].isdigit():
                seg_touch[int(t[1:])] += 1
    rows = []
    for w in range(62):
        pre = prefix_at_2006[w]
        tot = None if (pre is None) else pre + (
            len(cone[w]) if not tainted[w] else 0)
        rows.append((w, first_write.get(w), pre,
                     None if tainted[w] else len(cone[w]), tot,
                     seg_touch[w], tainted[w]))
    rows_ok = [r for r in rows if r[4] is not None]
    rows_ok.sort(key=lambda r: (r[4], r[5]))
    print("wire,first_write,prefix,full,total_cost,seg_touches,tainted "
          "(8 cheapest valid):")
    for r in rows_ok[:8]:
        print("  ", r)
    noninput = [r for r in rows_ok if (r[1] is not None and r[1] >= SLO)
                or (r[1] is not None and r[1] < SLO and r[0] >= 22)]
    print("cheapest wires first-written inside/after segment (recomputable):")
    for r in sorted(noninput, key=lambda r: (r[4], r[5]))[:8]:
        print("  ", r)
    out = {
        "prefix_cone_at_2006": prefix_at_2006,
        "cheapest_valid": [list(r) for r in rows_ok[:12]],
        "budget_ccx_at_61q": 95430.78 / 62 / 61,
    }
    Path("experiments/invsqrt/20261109_cache_borrow_mincut/task3b_cones.json").write_text(
        json.dumps(out, indent=2) + "\n")
    print("wrote task3b_cones.json")


if __name__ == "__main__":
    main()
