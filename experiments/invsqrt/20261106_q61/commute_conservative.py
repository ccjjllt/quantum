"""Conservative commutation cover: wire untouched inside the block, all reads of the
spanning value moved to just before the block (destination = block start a).

Why destination a: the register only has to be free *inside* [a,b), so the reads may stay
after the gates that precede the block.  This is strictly easier than v2 (which used the
previous touch p as destination).

Soundness: after the move the wire is untouched inside [a,b) and every read of the value it
carries there has been moved before a, so no gate in [a,b) can depend on it.
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
    return _cached(k1, tuple(q1), p1[1] if k1 == "Z_POW" else "",
                   k2, tuple(q2), p2[1] if k2 == "Z_POW" else "")


def peak_blocks():
    d = json.loads((common.OUT / "value_liveness.json").read_text())
    vl = {int(k[1:]): [tuple(x) for x in v] for k, v in d["value_liveness"].items()}
    ev = collections.Counter()
    for q, ms in vl.items():
        for x, y in ms:
            ev[x] += 1
            ev[y + 1] -= 1
    pts = sorted(ev)
    live, prof = 0, []
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


def move_ok(gates, stacks, writes, i, dest):
    k, qs, p = gates[i]
    bits = set(stacks[i])
    if "if" in p:
        bits.add(p[-1])
    if not bits_stable(writes, bits, dest, i):
        return False, "cond"
    for j in range(dest, i):
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
    rows, chosen, covered = [], [], set()
    print(f"{'block':<18} {'len':>4} {'untouched_in':>12} {'read-movable':>12}  wires")
    for a, b in blocks:
        cands = []
        for w in range(22, 62):
            ts = touches[w]
            if any(a <= i < b for i in ts):
                continue
            before = [i for i in ts if i < a]
            if not before:
                continue
            reads, _ = reads_after(gates, ts, b, w)
            if not reads:
                cands.append({"wire": w, "reads": 0, "ok": True})
                continue
            bad = [i for i in reads if not move_ok(gates, stacks, writes, i, a)[0]]
            cands.append({"wire": w, "reads": len(reads),
                          "last_read": reads[-1], "ok": not bad,
                          "blocked_reads": bad[:4]})
        ok = [c for c in cands if c["ok"]]
        rows.append({"block": [a, b], "len": b - a, "cands": cands, "ok": ok})
        if ok:
            covered |= set(range(a, b))
            chosen.append({"block": [a, b], "wire": ok[0]["wire"],
                           "reads_moved": ok[0]["reads"]})
        print(f"[{a},{b})".ljust(18) + f" {b-a:>4} {len(cands):>12} {len(ok):>12}  "
              f"{[(c['wire'], c['reads']) for c in ok][:4]}")
    peak = set()
    for a, b in blocks:
        peak.update(range(a, b))
    print(f"\nblocks={len(blocks)} peak_ops={len(peak)}")
    print(f"covered by pure read-move commutation: {len(covered & peak)} ops in {len(chosen)} blocks")
    print(f"uncovered: {len(peak - covered)}")
    (common.OUT / "commute_conservative.json").write_text(json.dumps(
        {"rows": rows, "chosen": chosen, "covered_ops": len(covered & peak),
         "peak_ops": len(peak), "uncovered": sorted(peak - covered)}, indent=1) + "\n")


if __name__ == "__main__":
    main()
