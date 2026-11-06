"""Shared read-only helpers for the 61Q investigation (baseline KMB, no edits)."""
from __future__ import annotations

import collections
import io
import json
from pathlib import Path

import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "artifacts/20261106_syed_v9/invsqrt/syed_v9_nofallback.kmb"
OUT = ROOT / "artifacts/20261106_q61"
PAID = {"CCX", "CCZ", "CSWAP"}
WRITES_ONE = {"X", "R", "HMR"}
WRITES_LAST = {"CX", "CCX"}
WRITES_TWO = {"SWAP", "CSWAP"}
NQ = 62


def load_ops():
    """Return (circuit, ops, gates, stacks).

    ops[i]   raw KMX line, register declarations removed
    gates[i] (kind, [qubit indices], token list)
    stacks[i] condition-stack contents live *before* operation i
    """
    circuit = km.Circuit.from_file(BASE)
    buf = io.StringIO()
    circuit.to_file(buf, format="kmx")
    ops = [l for l in buf.getvalue().splitlines() if not l.startswith(("APPEND", "REGISTER"))]
    gates = [(p[0], [int(t[1:]) for t in p[1:] if t.startswith("q")], p) for p in map(str.split, ops)]
    stack, stacks = [], []
    for k, qs, p in gates:
        stacks.append(tuple(stack))
        if k == "PUSH_CONDITION":
            stack.append(p[-1])
        elif k == "POP_CONDITION":
            stack.pop()
    assert not stack
    return circuit, ops, gates, stacks


def written(kind, qs):
    if kind in WRITES_ONE:
        return qs[:1]
    if kind in WRITES_LAST:
        return qs[-1:]
    if kind in WRITES_TWO:
        return qs[-2:]
    return []


def touches(gates):
    """touches[q] = list of op indices that mention q (read or write)."""
    t = [[] for _ in range(NQ)]
    for i, (_, qs, _) in enumerate(gates):
        for q in qs:
            t[q].append(i)
    return t


def conservative_segments(gates, stacks, q):
    """Census model: touch -> next unconditional HMR/R (conditional resets do not split)."""
    out = []
    cur = []
    first = True
    for i, (k, qs, p) in enumerate(gates):
        if q not in qs:
            continue
        reset = k in {"HMR", "R"} and not stacks[i] and "if" not in p and q in qs
        if reset:
            if cur or (q < 22 and first):
                out.append((0 if (q < 22 and first) else cur[0], i + 1, cur + [i]))
            cur, first = [], False
            continue
        cur.append(i)
    if q < 22 and first:
        out.append((0, len(gates), cur))
    elif cur:
        out.append((cur[0], cur[-1] + 1, cur))
    return out


def live_sets(gates, stacks, wires=range(NQ)):
    """Per op index, the set of wires whose conservative live window covers it."""
    segs = {q: conservative_segments(gates, stacks, q) for q in wires}
    events = collections.defaultdict(list)
    for q, ss in segs.items():
        for a, b, _ in ss:
            events[a].append((q, +1))
            events[b].append((q, -1))
    pts = sorted(events)
    live = set()
    rows = {}
    for i, j in zip(pts, pts[1:]):
        for q, d in events[i]:
            (live.add if d > 0 else live.discard)(q)
        rows[i] = (j, set(live))
    return segs, rows


def main():
    _, ops, gates, stacks = load_ops()
    segs, rows = live_sets(gates, stacks)
    peak = max(len(s) for _, s in rows.values())
    peaks = [(a, b, s) for a, (b, s) in rows.items() if len(s) == peak]
    print("peak", peak, "intervals", len(peaks))
    # wires present in every peak interval
    common = set.intersection(*[s for _, _, s in peaks])
    print("live in ALL peak intervals:", sorted(common))
    per_wire = collections.Counter()
    for _, _, s in peaks:
        for q in s:
            per_wire[q] += 1
    print("wire -> #peak intervals live (of", len(peaks), "):")
    for q in sorted(per_wire, key=lambda z: (-per_wire[z], z)):
        print(f"  q{q}: {per_wire[q]}")
    print("segment count", sum(len(v) for v in segs.values()))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "peak_membership.json").write_text(json.dumps({
        "peak": peak,
        "intervals": [[a, b, sorted(s)] for a, b, s in peaks],
        "counts": {f"q{q}": n for q, n in per_wire.items()},
        "common": sorted(common),
    }, indent=1) + "\n")


if __name__ == "__main__":
    main()
