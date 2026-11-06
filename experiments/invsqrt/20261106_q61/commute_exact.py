"""Exact-commutation rescheduling analysis (v2: classically conditioned gates included).

A conditional gate `G if b` may move to a position where b has the same value (no write of b
in between) and the underlying gate G commutes with every gate it passes.  Condition stacks
are checked the same way.  Commutation of G is the exact basis-state test in commute.py;
HMR/R stay barriers.

Part A: for every scratch wire touched in [16731,18483), can each touch move out of the
        region (before LO / after HI)?
Part B: for every 62-value-live block and every wire untouched inside it, can all reads of
        the value spanning the block move before the block?
"""
from __future__ import annotations

import collections
import functools
import json

import common
from commute import commutes

LO, HI = 16731, 18483
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


def cond_of(gates, i):
    p = gates[i][2]
    return p[-1] if "if" in p else None


def bit_write_ops(gates):
    """bit -> sorted list of ops writing it (HMR output, BIT_STORE*, BIT_INVERT)."""
    out = collections.defaultdict(list)
    for i, (k, qs, p) in enumerate(gates):
        if k in {"BIT_STORE0", "BIT_STORE1", "BIT_INVERT"}:
            out[p[1]].append(i)
        elif k == "HMR":
            out[p[-1]].append(i)
    return out


def last_write_before(writes, bit, i):
    import bisect
    lst = writes.get(bit, [])
    j = bisect.bisect_left(lst, i) - 1
    return lst[j] if j >= 0 else -1


def cond_ok(writes, gates, i, dest):
    """Is the classical condition of op i unchanged over [min(dest,i), max(dest,i))?"""
    b = cond_of(gates, i)
    if b is not None:
        lw = last_write_before(writes, b, i)
        if dest < i:
            if lw >= dest:
                return False
        else:
            # moving right: no write of b in (i, dest)
            import bisect
            lst = writes.get(b, [])
            k = bisect.bisect_right(lst, i)
            if k < len(lst) and lst[k] < dest:
                return False
    return True


def blockers(gates, writes, i, lo, hi):
    out = []
    for j in range(lo, hi):
        if j == i:
            continue
        if not commutes_i(gates, i, j):
            out.append(j)
    return out


def part_a(gates, writes):
    touches = common.touches(gates)
    print(f"== Part A: region [{LO},{HI}) ==")
    print(f"{'q':>3} {'touches':>7} {'left':>5} {'right':>6} {'both':>5}  first blocked touch (op, blocker)")
    rows = []
    for w in range(22, 62):
        ts = [i for i in touches[w] if LO <= i < HI]
        if not ts:
            continue
        nl = nr = nb = 0
        first = None
        for i in ts:
            bl = blockers(gates, writes, i, LO, i)
            canl = (not bl) and cond_ok(writes, gates, i, LO)
            br = blockers(gates, writes, i, i + 1, HI)
            canr = (not br) and cond_ok(writes, gates, i, HI)
            nl += canl
            nr += canr
            nb += (canl and canr)
            if not (canl or canr) and first is None:
                first = (i, (bl[0] if bl else None), (br[0] if br else None),
                         "cond" if (not bl and not br) else "commute")
        rows.append({"wire": w, "touches": len(ts), "left": nl, "right": nr,
                     "both": nb, "first_blocked": first})
        print(f"{w:>3} {len(ts):>7} {nl:>5} {nr:>6} {nb:>5}  {first}")
    print(f"\nwires with every region touch movable: "
          f"{[r['wire'] for r in rows if r['both'] == r['touches']]}")
    return rows


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


def part_b(gates, stacks, writes):
    touches = common.touches(gates)
    blocks = peak_blocks()
    print(f"\n== Part B: per-block read-move ==")
    results, chosen, covered = [], [], set()
    for a, b in blocks:
        per = []
        for w in range(22, 62):
            ts = touches[w]
            if any(a <= i < b for i in ts):
                continue
            before = [i for i in ts if i < a]
            if not before:
                continue
            p = before[-1]
            reads, stop = reads_after(gates, ts, b, w)
            if not reads:
                per.append({"wire": w, "free": True, "moved": [], "p": p})
                continue
            if tuple(stacks[p + 1]) or any(tuple(stacks[i]) for i in reads):
                per.append({"wire": w, "free": False, "why": "stack"})
                continue
            moved = set(reads)
            bad = []
            cbad = []
            for i in reads:
                if not cond_ok(writes, gates, i, p + 1):
                    cbad.append(i)
                for j in range(p + 1, i):
                    if j in moved:
                        continue
                    if not commutes_i(gates, i, j):
                        bad.append((i, j))
                        break
            if bad or cbad:
                per.append({"wire": w, "free": False,
                            "why": "noncommuting" if bad else "cond bit",
                            "pairs": bad[:4], "cond_bad": cbad[:4],
                            "moved_count": len(reads), "last_read": reads[-1]})
            else:
                per.append({"wire": w, "free": True, "p": p,
                            "moved": [[i, gates[i][0], gates[i][2][-1] if "if" in gates[i][2] else None]
                                      for i in reads],
                            "moved_count": len(reads)})
        free = [r for r in per if r["free"]]
        results.append({"block": [a, b], "len": b - a, "untouched": len(per),
                        "free": free, "blocked": [r for r in per if not r["free"]]})
        if free:
            w = free[0]
            covered |= set(range(a, b))
            chosen.append({"block": [a, b], "wire": w["wire"],
                           "moved_count": w.get("moved_count", 0),
                           "moved": w.get("moved", []), "p": w.get("p")})
        print(f"[{a},{b}) len={b-a:>4} untouched={len(per):>3} "
              f"free={[r['wire'] for r in free]}"
              + ("" if free else f"  why={dict(collections.Counter(r['why'] for r in per if not r['free']))}"))
    peak = set()
    for a, b in blocks:
        peak.update(range(a, b))
    print(f"\nblocks={len(blocks)} peak_ops={len(peak)}")
    print(f"covered by free rescheduling: {len(covered & peak)} ops in {len(chosen)} blocks")
    print(f"uncovered: {len(peak - covered)} ops")
    (common.OUT / "commute_exact.json").write_text(json.dumps(
        {"blocks": results, "chosen": chosen,
         "covered_ops": len(covered & peak), "peak_ops": len(peak),
         "uncovered": sorted(peak - covered)}, indent=1) + "\n")


def main():
    _, ops, gates, stacks = common.load_ops()
    writes = bit_write_ops(gates)
    part_a(gates, writes)
    part_b(gates, stacks, writes)


if __name__ == "__main__":
    main()
