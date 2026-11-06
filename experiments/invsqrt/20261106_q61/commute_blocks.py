"""Per-peak-block commutation test: can a wire's post-block reads move before the block?

For a peak block [a,b) and a wire w untouched inside it:
  p = last touch of w before a
  the value present during the block ends at the first *pure write* (X/R/HMR) at or after b
  every touch in [b, that write) is a read of the same value; move them all to just after p.

Sufficient (rigorous) condition: each moved gate is unconditional, sits outside any
condition stack, and every *non-moved* gate between p and the moved gate's original
position is disjoint from the moved gate's operands.  Then the gates commute exactly and
the circuit is unitarily identical -- no phase change, no gate added.
"""
from __future__ import annotations

import collections
import json

import common

PURE_WRITE = {"X", "R", "HMR"}


def peak_blocks():
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
    return blocks


def reads_after(gates, touches_w, b, w):
    """Touches of w from b until the first pure write; these all read one value."""
    out = []
    for i in touches_w:
        if i < b:
            continue
        k, qs, p = gates[i]
        if k in PURE_WRITE and qs[0] == w:
            return out, i
        out.append(i)
    return out, None


def try_wire(gates, stacks, w, touches_w, a, b):
    inside = [i for i in touches_w if a <= i < b]
    if inside:
        return None
    before = [i for i in touches_w if i < a]
    if not before:
        return None
    p = before[-1]
    reads, stop = reads_after(gates, touches_w, b, w)
    if not reads:
        return {"wire": w, "free": True, "block": [a, b], "p": p,
                "moved": [], "note": "value already dead after block"}
    moved = set(reads)
    # conditions must be trivial at the moved gates and at the destination
    for i in reads:
        k, qs, pp = gates[i]
        if "if" in pp or stacks[i]:
            return {"wire": w, "free": False, "why": f"conditional read op{i}"}
        if stacks[p + 1] if p + 1 < len(stacks) else ():
            return {"wire": w, "free": False, "why": "destination inside condition stack"}
    # each moved gate must commute past every non-moved gate between p and itself
    blockers = []
    for i in reads:
        mine = set(gates[i][1])
        for j in range(p + 1, i):
            if j in moved:
                continue
            if set(gates[j][1]) & mine:
                blockers.append(j)
                break
    if blockers:
        return {"wire": w, "free": False, "why": "noncommuting",
                "blockers": blockers[:6], "first_blocker_instr": [common.load_ops()[1][j] for j in blockers[:6]],
                "moved_count": len(reads), "p": p}
    return {"wire": w, "free": True, "block": [a, b], "p": p,
            "moved": [[i, common.load_ops()[1][i]] for i in reads],
            "moved_count": len(reads)}


def main():
    _, ops, gates, stacks = common.load_ops()
    touches = common.touches(gates)
    blocks = peak_blocks()
    results = []
    for a, b in blocks:
        per = []
        for w in range(22, 62):
            r = try_wire(gates, stacks, w, touches[w], a, b)
            if r is not None:
                per.append(r)
        free = [r for r in per if r["free"]]
        results.append({"block": [a, b], "len": b - a, "candidates": len(per),
                        "free": free, "blocked": [r for r in per if not r["free"]]})
        print(f"[{a},{b}) len={b-a:>4} untouched_wires={len(per):>3} "
              f"free={[r['wire'] for r in free]}"
              + ("" if free else f"  blocked e.g. {[(r['wire'], r.get('why'), r.get('blockers')) for r in per[:2]]}"))
    covered = set()
    chosen = []
    for r in results:
        if r["free"]:
            w = r["free"][0]
            covered |= set(range(r["block"][0], r["block"][1]))
            chosen.append({"block": r["block"], "wire": w["wire"],
                           "moved_count": w.get("moved_count", 0),
                           "moved": w.get("moved", [])})
    peak = set()
    for a, b in blocks:
        peak.update(range(a, b))
    print(f"\nblocks={len(blocks)} peak_ops={len(peak)}")
    print(f"covered by free commutation: {len(covered & peak)} ops in {len(chosen)} blocks")
    print(f"uncovered: {len(peak - covered)} ops")
    (common.OUT / "commute_blocks.json").write_text(json.dumps(
        {"blocks": results, "chosen": chosen,
         "covered_ops": len(covered & peak), "peak_ops": len(peak),
         "uncovered": sorted(peak - covered)}, indent=1) + "\n")


if __name__ == "__main__":
    main()
