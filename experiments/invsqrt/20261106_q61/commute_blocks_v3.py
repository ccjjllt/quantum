"""Per-block read-move with the *block start* as destination (v3).

To make wire w dead inside peak block [a,b) it is enough to consume all reads of the value
at or before a (not at the previous touch p).  So the move distance is only the part inside
the block, which is far shorter than in v2.

Also handles wires that *are* touched inside the block: such a wire can still cross the
block if every inside touch can be pushed out (before a or after b) while preserving order.

Commutation is the exact basis-state test in commute.py; HMR/R are barriers; classical
conditions are checked for bit stability.
"""
from __future__ import annotations

import collections
import functools
import json

import common
from commute import commutes

PURE_WRITE = {"X", "R", "HMR"}


@functools.lru_cache(maxsize=None)
def _cached(k1, q1, e1, k2, q2, e2):
    return commutes((k1, list(q1), ["", e1]), (k2, list(q2), ["", e2]))


def commutes_i(gates, i, j):
    k1, q1, p1 = gates[i]
    k2, q2, p2 = gates[j]
    e1 = p1[1] if k1 == "Z_POW" else ""
    e2 = p2[1] if k2 == "Z_POW" else ""
    return _cached(k1, tuple(q1), e1, k2, tuple(q2), e2)


def peak_blocks():
    d = json.loads((common.OUT / "value_liveness.json").read_text())
    vl = {int(k[1:]): [tuple(x) for x in v] for k, v in d["value_liveness"].items()}
    ev = collections.Counter()
    for q, ms in vl.items():
        for x, y in ms:
            ev[x] += 1
            ev[y + 1] -= 1
    pts = sorted(ev)
    live = 0
    prof = []
    for i in pts[:-1]:
        live += ev[i]
        prof.append((i, live))
    blocks = []
    for (x, l), (y, _) in zip(prof, prof[1:]):
        if l == 62:
            if blocks and blocks[-1][1] == x:
                blocks[-1][1] = y
            else:
                blocks.append([x, y])
    return blocks


def bit_writes(gates):
    out = collections.defaultdict(list)
    for i, (k, qs, p) in enumerate(gates):
        if k in {"BIT_STORE0", "BIT_STORE1", "BIT_INVERT"}:
            out[p[1]].append(i)
        elif k == "HMR":
            out[p[-1]].append(i)
    return out


def bits_stable(writes, bits, lo, hi):
    import bisect
    for b in bits:
        lst = writes.get(b, [])
        k = bisect.bisect_right(lst, lo)
        if k < len(lst) and lst[k] < hi:
            return False
    return True


def move_free(gates, stacks, writes, i, lo, hi):
    """Can op i move to position lo (relative to its current position) commuting past [lo,hi)?"""
    k, qs, p = gates[i]
    bits = set()
    bits.update(stacks[i])
    if "if" in p:
        bits.add(p[-1])
    if not bits_stable(writes, bits, lo, i):
        return False, "cond"
    for j in range(lo, hi):
        if j == i:
            continue
        if not commutes_i(gates, i, j):
            return False, j
    return True, None


def reads_after(gates, ts, b, w):
    out = []
    for i in ts:
        if i < b:
            continue
        k, qs, p = gates[i]
        if k in PURE_WRITE and qs[0] == w:
            return out, i
        out.append(i)
    return out, None


def main():
    _, ops, gates, stacks = common.load_ops()
    writes = bit_writes(gates)
    touches = common.touches(gates)
    blocks = peak_blocks()
    results, chosen, covered = [], [], set()
    print(f"{'block':<18} {'len':>4} {'untouched':>9} {'free':>5}  detail")
    for a, b in blocks:
        per = []
        for w in range(22, 62):
            ts = touches[w]
            inside = [i for i in ts if a <= i < b]
            before = [i for i in ts if i < a]
            if not before:
                continue
            reads, stop = reads_after(gates, ts, b, w)
            if any(not move_free(gates, stacks, writes, i, a, i)[0] for i in reads):
                per.append({"wire": w, "free": False, "why": "post-read",
                            "bad": [i for i in reads if not move_free(gates, stacks, writes, i, a, i)[0]][:3]})
                continue
            ok = True
            for i in inside:
                lt = move_free(gates, stacks, writes, i, a, i)[0]
                rt = move_free(gates, stacks, writes, i, i + 1, b)[0]
                if not (lt or rt):
                    ok = False
                    break
            if not ok:
                per.append({"wire": w, "free": False, "why": "inside"})
                continue
            per.append({"wire": w, "free": True, "moved_post": len(reads),
                        "moved_inside": len(inside)})
        free = [r for r in per if r["free"]]
        results.append({"block": [a, b], "len": b - a, "tested": len(per),
                        "free": free, "blocked": [r for r in per if not r["free"]]})
        if free:
            w = free[0]
            covered |= set(range(a, b))
            chosen.append({"block": [a, b], "wire": w["wire"], **w})
        print(f"[{a},{b})".ljust(18) + f" {b-a:>4} {len(per):>9} "
              f"{len(free):>5}  {[(r['wire'], r['moved_post'], r['moved_inside']) for r in free][:4]}")
    peak = set()
    for a, b in blocks:
        peak.update(range(a, b))
    print(f"\nblocks={len(blocks)} peak_ops={len(peak)}")
    print(f"covered: {len(covered & peak)} ops in {len(chosen)} blocks; "
          f"uncovered {len(peak - covered)}")
    print(f"covered blocks: {[c['block'] for c in chosen]}")
    (common.OUT / "commute_blocks_v3.json").write_text(json.dumps(
        {"blocks": results, "chosen": chosen, "covered_ops": len(covered & peak),
         "peak_ops": len(peak), "uncovered": sorted(peak - covered)}, indent=1) + "\n")


if __name__ == "__main__":
    main()
