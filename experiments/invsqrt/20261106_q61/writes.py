"""Compact per-wire write/consume summary for the baseline KMB (read-only)."""
from __future__ import annotations

import collections
import json
import sys

import common


def analyse(q, ops, gates, stacks):
    writes = []          # ops that can change q
    paid = []
    controls = collections.Counter()
    phase = collections.Counter()
    per_seg = []
    for i, (k, qs, p) in enumerate(gates):
        if q not in qs:
            continue
        if k in common.PAID:
            paid.append(i)
        if q in common.written(k, qs):
            writes.append(i)
        elif k in {"CX"}:
            controls["CX-control"] += 1
        elif k in {"CZ"}:
            phase["CZ-partner:" + str([x for x in qs if x != q][0])] += 1
        elif k == "CCX" and q in qs[:2]:
            controls["CCX-control"] += 1
        elif k == "CCZ":
            phase["CCZ"] += 1
        elif k in {"Z", "NEG"}:
            phase[k] += 1
    return writes, paid, controls, phase


def show(q, ops, gates, stacks):
    writes, paid, controls, phase = analyse(q, ops, gates, stacks)
    segs = common.conservative_segments(gates, stacks, q)
    print(f"\n===== q{q}: segments {[[a,b] for a,b,_ in segs]}")
    print(f"  writes ({len(writes)}):")
    for i in writes:
        cond = " [cond]" if stacks[i] else ""
        print(f"    {i:6d} {ops[i]}{cond}")
    print(f"  paid ops ({len(paid)}): {paid}")
    print(f"  free controls: {dict(controls)}")
    print(f"  phase uses: {dict(phase)}")


def main():
    targets = [int(a.lstrip("q")) for a in sys.argv[1:]] or [49, 34, 53, 35, 33]
    _, ops, gates, stacks = common.load_ops()
    for q in targets:
        show(q, ops, gates, stacks)

if __name__ == "__main__":
    main()
