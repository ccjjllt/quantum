"""Sound commutation cover (v4).

A wire w is provably dead inside peak block [a,b) if, after reordering, it is untouched in
[a,b) and every read of the value it carries into the block happens before a.

Allowed moves (all gate-free): move a *read* of that value from inside the block, or from
after the block, to just before a, keeping their relative order.  Conditions:
  * every moved gate commutes exactly with the gates it passes (commute.py, exhaustive),
  * no classical bit used by a moved gate is written on the way,
  * wires that are *written* inside the block are not used (write moves are excluded).

Cost: zero paid gates; the only change is gate order.
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
    if tuple(stacks[dest]) != tuple(stacks[i]):
        return False, "stack-mismatch"
    bits = set(stacks[i])
    if "if" in p:
        bits.add(p[-1])
    if not bits_stable(writes, bits, dest, i):
        return False, "cond"
    for j in range(dest, i):
        if not commutes_i(gates, i, j):
            return False, j
    return True, None


def is_read(gates, i, w):
    """A touch reads w's current value unless it is a pure overwrite.

    X / R / HMR overwrite without reading; SWAP replaces the value with another wire's.
    CX / CCX / CSWAP targets are accumulate/read-modify-write, so they DO read the value.
    """
    k, qs, p = gates[i]
    if k in PURE_WRITE and qs[0] == w:
        return False
    return True


def reads_until_write(gates, ts, start, w):
    out = []
    for i in ts:
        if i < start:
            continue
        if not is_read(gates, i, w):
            return out, i
        out.append(i)
    return out, None


def main():
    _, ops, gates, stacks = common.load_ops()
    writes = bit_writes(gates)
    touches = common.touches(gates)
    blocks = peak_blocks()
    rows, chosen, covered = [], [], set()
    print(f"{'block':<18} {'len':>4} {'cand':>5} {'sound':>6}  wires (moved reads)")
    for a, b in blocks:
        cands = []
        for w in range(22, 62):
            ts = touches[w]
            inside = [i for i in ts if a <= i < b]
            if any(not is_read(gates, i, w) for i in inside):
                continue
            before = [i for i in ts if i < a]
            if not before:
                continue
            post, _ = reads_until_write(gates, ts, b, w)
            moved = inside + post
            bad = [i for i in moved if not move_ok(gates, stacks, writes, i, a)[0]]
            cands.append({"wire": w, "moved": len(moved), "inside": len(inside),
                          "post": len(post), "ok": not bad, "bad": bad[:4]})
        ok = [c for c in cands if c["ok"]]
        rows.append({"block": [a, b], "len": b - a, "cands": cands, "ok": ok})
        if ok:
            covered |= set(range(a, b))
            chosen.append({"block": [a, b], "wire": ok[0]["wire"],
                           "moved": ok[0]["moved"], "inside": ok[0]["inside"],
                           "post": ok[0]["post"]})
        print(f"[{a},{b})".ljust(18) + f" {b-a:>4} {len(cands):>5} {len(ok):>6}  "
              f"{[(c['wire'], c['moved']) for c in ok][:5]}")
    peak = set()
    for x, y in blocks:
        peak.update(range(x, y))
    print(f"\nblocks={len(blocks)} peak_ops={len(peak)}")
    print(f"soundly covered: {len(covered & peak)} ops in {len(chosen)} blocks, added C = 0")
    print(f"uncovered: {len(peak - covered)}")
    (common.OUT / "commute_v4.json").write_text(json.dumps(
        {"rows": rows, "chosen": chosen, "covered_ops": len(covered & peak),
         "peak_ops": len(peak), "uncovered": sorted(peak - covered)}, indent=1) + "\n")


if __name__ == "__main__":
    main()
