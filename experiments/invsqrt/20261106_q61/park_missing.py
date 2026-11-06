"""Find a parking cover of the 62-live ops in which every rebuild is cheap.

Rebuild classes at the gap's right end:
  free   : X/R/HMR/init_and/SWAP target, or the value is an XOR of other wires
  cheap  : the value is an AND / OR of two wires (one CCX)  [verified with cheap_expr]
  other  : anything else (not used)
"""
from __future__ import annotations

import collections
import json

import common

ZERO_WRITE = {"X", "R", "HMR"}


def classify(gates, w, i, span_set):
    k, qs, p = gates[i]
    if k in ZERO_WRITE and qs[0] == w:
        return 0, "reinit"
    if k == "CCX" and qs[2] == w:
        return 0, "init_and"
    if k == "SWAP" and w in qs:
        return 0, "swap"
    if i in span_set:
        return 0, "linear"
    return 1, "needs_check"


def main():
    span = {r["q"]: set(r["hit_ops"]) for r in json.loads((common.OUT / "span_test.json").read_text())}
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
    peak_ops = set()
    for (a, l), (b, _) in zip(prof, prof[1:]):
        if l == 62:
            peak_ops.update(range(a, b))
    _, ops, gates, stacks = common.load_ops()
    touches = common.touches(gates)
    options = []
    for w in range(22, 62):
        ts = touches[w]
        for left, right in zip(ts, ts[1:]):
            covered = frozenset(i for i in peak_ops if left < i < right)
            if not covered:
                continue
            c, why = classify(gates, w, right, span[w])
            options.append({"wire": w, "gap": [left, right], "covered": sorted(covered),
                            "cost": c, "why": why, "next_instr": ops[right]})
    free = [o for o in options if o["cost"] == 0]
    covered0 = set()
    for o in free:
        covered0 |= set(o["covered"])
    missing = peak_ops - covered0
    print(f"peak ops {len(peak_ops)}; free options {len(free)}; free cover {len(covered0)}; "
          f"missing {len(missing)}")
    # which expensive options touch the missing ops, and how much of it do they cover
    cand = []
    for o in options:
        if o["cost"] == 0:
            continue
        g = len(set(o["covered"]) & missing)
        if g:
            cand.append((g, o))
    cand.sort(key=lambda t: -t[0])
    print(f"candidate rebuilds for the missing {len(missing)} ops: {len(cand)}")
    for g, o in cand[:25]:
        print(f"  q{o['wire']} gap {o['gap']} covers {g} missing, at {o['gap'][1]}: {o['next_instr']}")
    (common.OUT / "park_missing.json").write_text(json.dumps({
        "peak_ops": sorted(peak_ops), "free_covered": sorted(covered0),
        "missing": sorted(missing),
        "candidates": [{"gain": g, **o} for g, o in cand]}, indent=1) + "\n")


if __name__ == "__main__":
    main()
