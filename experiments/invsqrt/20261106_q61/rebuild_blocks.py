"""Rebuild cost for the still-uncovered peak intervals.

For each uncovered interval I and each wire w untouched inside I, the parking plan destroys
w at I and must rebuild its value at the next touch n.  This script prices that rebuild:
    k = 0  affine form of the other 61 wires            (free CX/X)
    k = 1  one product of two affine forms              (1 CCX)
    k = 2  two products (rank-2 quadratic)              (2 CCX)
All arithmetic is full-domain (3,133,452 x) on the given HMR branch; states are cached per
rebuild op so every op is simulated once.
"""
from __future__ import annotations

import collections
import json

import common
import nonlinear_rebuild as nr

MAXX = nr.MAXX


def peak_blocks():
    d = json.loads((common.OUT / "value_liveness.json").read_text())
    vl = {int(k[1:]): [tuple(x) for x in v] for k, v in d["value_liveness"].items()}
    ev = collections.Counter()
    for q, ms in vl.items():
        for a, b in ms:
            ev[a] += 1
            ev[b + 1] -= 1
    pts = sorted(ev)
    live, prof = 0, []
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


def price(masks, w, full):
    covers, info = nr.affine_covers(masks, w, full, cap=48)
    for i, L in enumerate(covers):
        if L == masks[w]:
            return 0, ["affine", info["coeffs"][i]]
    for i in range(len(covers)):
        for j in range(i, len(covers)):
            if covers[i] & covers[j] == masks[w]:
                return 1, [info["coeffs"][i], info["coeffs"][j]]
    # k = 2: XOR of two products built from covers and single wires
    prods = {}
    for i in range(len(covers)):
        for j in range(i, len(covers)):
            prods[covers[i] & covers[j]] = None
    singles = [masks[v] for v in range(len(masks)) if v != w]
    for L in covers:
        for s in singles:
            prods[L & s] = None
    for p in prods:
        if (masks[w] ^ p) in prods:
            return 2, ["two-products"]
    return None, None


def main():
    _, ops, gates, stacks = common.load_ops()
    full = (1 << MAXX) - 1
    touches = common.touches(gates)
    summary = json.loads((common.OUT / "commute_summary.json").read_text())
    merged = []
    for a, b in summary["uncovered_runs"]:
        if merged and a - merged[-1][1] <= 64:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    print(f"uncovered runs {len(summary['uncovered_runs'])} -> merged intervals {len(merged)}")
    # collect (interval, wire, rebuild_op) then simulate each op once
    jobs = []
    for a, b in merged:
        for w in range(22, 62):
            ts = touches[w]
            if any(a <= i < b for i in ts):
                continue
            nxt = [i for i in ts if i >= b]
            if nxt:
                jobs.append((tuple([a, b]), w, nxt[0]))
    by_op = collections.defaultdict(list)
    for iv, w, n in jobs:
        by_op[n].append((iv, w))
    results = collections.defaultdict(list)
    snaps = nr.simulate_snapshots(gates, sorted(by_op), None)
    for n in sorted(by_op):
        masks = snaps[n]
        for iv, w in by_op[n]:
            k, expr = price(masks, w, full)
            results[iv].append({"wire": w, "rebuild_op": n, "next_instr": ops[n], "k": k})
        print(f"  op {n}: {len(by_op[n])} candidates priced", flush=True)
    out = []
    for iv, cands in results.items():
        cands.sort(key=lambda c: (c["k"] if c["k"] is not None else 99, c["rebuild_op"]))
        out.append({"interval": list(iv), "len": iv[1] - iv[0], "cands": cands})
    out.sort(key=lambda r: r["interval"][0])
    print("\ninterval                      untouched  cheapest rebuild")
    for r in out:
        best = r["cands"][0] if r["cands"] else None
        print(f"[{r['interval'][0]},{r['interval'][1]}) len={r['len']:>4} {len(r['cands']):>5}   {best}")
    (common.OUT / "rebuild_intervals.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
