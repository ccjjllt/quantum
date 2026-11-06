"""Rotation-free liveness floor under the q61 value-liveness model.

The naive "delete the rotation ops" test is not monotone: HMR gates are pure
writes in the q61 model, so deleting them merges adjacent intervals of the same
wire and can *increase* liveness.  This script instead keeps every write in place
and only removes the *reads* that belong to the rotation machinery (loading
gates, Z_POW, HMR ancilla reads, post-correction Z/CZ).  Intervals can then only
shorten or disappear, so the resulting peak is a true lower bound for any
implementation of the 41 rotations that does not read more than the baseline.

If that floor is still 62, no interleaving/rescheduling of the rotations can
reach 61 under the q61 model; the peak is set by the arithmetic that is not
rotation related.
"""
from __future__ import annotations

import collections
import json

import common


def collect(gates):
    """Per wire: write ops (X/R/HMR) and read ops (all other multi-qubit gates)."""
    NQ = common.NQ
    writes = [[] for _ in range(NQ)]
    reads = [[] for _ in range(NQ)]
    for i, (k, qs, p) in enumerate(gates):
        if k in {"X", "R", "HMR"}:
            writes[qs[0]].append(i)
        elif k in {"CX", "CCX", "SWAP", "CSWAP", "Z", "CZ", "CCZ", "NEG", "Z_POW"}:
            for w in qs:
                reads[w].append(i)
    return writes, reads


def intervals_from(writes, reads):
    """q61 model: interval = [first read after a write, last read before next write]."""
    NQ = common.NQ
    out = [[] for _ in range(NQ)]
    for w in range(NQ):
        ws = writes[w]
        rs = reads[w]
        bounds = [-1] + ws + [10 ** 9]
        for a, b in zip(bounds, bounds[1:]):
            seg = [r for r in rs if a < r < b]
            if seg:
                out[w].append([seg[0], seg[-1]])
    merged = {}
    for w in range(NQ):
        ms = []
        for a, b in sorted(out[w]):
            if ms and a <= ms[-1][1]:
                ms[-1][1] = max(ms[-1][1], b)
            else:
                ms.append([a, b])
        merged[w] = ms
    return merged


def peak_of(merged):
    events = collections.Counter()
    for w, ms in merged.items():
        for a, b in ms:
            events[a] += 1
            events[b + 1] -= 1
    live = peak = 0
    at = 0
    pts = sorted(events)
    for i in pts[:-1]:
        live += events[i]
        if live > peak:
            peak, at = live, i
    return peak, at


def main() -> None:
    ops, gates = common.load_ops()
    masks, rops, rwires, angles = common.load_masks_full()
    # reuse the machinery spans computed by rotation_free.py
    prev = json.loads((common.OUT / "rotation_free.json").read_text())
    spans = prev["machinery_spans"]
    drop = set()
    for a, b in spans:
        drop.update(range(a, b + 1))
    print("machinery spans", spans, "ops", len(drop))

    writes, reads = collect(gates)
    base = intervals_from(writes, reads)
    p0, a0 = peak_of(base)
    print(f"baseline q61 peak {p0} at op {a0}")
    assert p0 == 62

    reads2 = [[r for r in reads[w] if r not in drop] for w in range(common.NQ)]
    reduced = intervals_from(writes, reads2)
    p1, a1 = peak_of(reduced)
    print(f"rotation-read-free peak {p1} at op {a1}")

    events = collections.Counter()
    for w, ms in reduced.items():
        for a, b in ms:
            events[a] += 1
            events[b + 1] -= 1
    live = 0
    hot = []
    for i in sorted(events)[:-1]:
        live += events[i]
        if live >= p1:
            hot.append(i)
    print(f"peak ops: {len(hot)} first 15 {hot[:15]}")
    for op in hot[:3]:
        L = sorted(w for w, ms in reduced.items()
                   if any(a <= op <= b for a, b in ms))
        print(f" at op {op}: {len(L)} live {L}")

    # A second, even more optimistic variant: also drop the ancillas' own
    # transient intervals by removing every read that is inside the Z_POW..HMR
    # window (that is already covered by the machinery spans).
    common.OUT.mkdir(parents=True, exist_ok=True)
    (common.OUT / "rotation_read_free.json").write_text(json.dumps({
        "scope": "q61 value-liveness model; writes kept, rotation-machinery reads removed",
        "baseline_peak": p0, "baseline_peak_op": a0,
        "rotation_read_free_peak": p1, "rotation_read_free_peak_op": a1,
        "peak_ops": len(hot), "peak_ops_list": hot,
        "machinery_spans": spans,
    }, indent=1) + "\n")


if __name__ == "__main__":
    main()
