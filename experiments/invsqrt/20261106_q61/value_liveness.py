"""Full-domain (all 3,133,452 legal x) basis-state simulation on one fixed HMR branch.

Read-only analysis of the baseline KMB.  Produces:
  * for every CCX/CSWAP/CCZ the target value before the gate (is it always |0>?)
  * value-liveness intervals per wire (write -> last read before next write)
  * per-op wire values are not stored; only summaries.

HMR outcomes are fixed to 0, which is one reachable branch; the phase is irrelevant to
basis-state values.  This is a basis-state/structural check, NOT official validation.
"""
from __future__ import annotations

import collections
import json
import sys

import numpy as np

import common

MAXX = 3133452


def main():
    _, ops, gates, stacks = common.load_ops()
    n = MAXX
    # column bit j of the mask = wire value for x = j+1
    q = [0] * 62
    for j in range(22):
        a = np.arange(1, n + 1, dtype=np.uint64)
        bits = ((a >> np.uint64(j)) & np.uint64(1)).astype(np.uint8)
        q[j] = int.from_bytes(np.packbits(bits, bitorder="little").tobytes(), "little")
    bits = {}
    stackv = []
    mask = (1 << n) - 1
    all_on = mask

    target_zero = {}          # paid op -> dict(always_zero=bool, live_fraction=float)
    ccx_zero_violations = []
    # value liveness: for each wire a list of (start, end) intervals
    open_start = [None] * 62
    intervals = [[] for _ in range(62)]
    last_read = [None] * 62
    nonzero_at_peak = []

    reads = collections.Counter()
    for i, (k, qs, p) in enumerate(gates):
        if k in {"CCX", "CSWAP"}:
            tgt = common.written(k, qs)
            vals = [q[t] for t in tgt]
            z = all(v == 0 for v in vals)
            target_zero[i] = {"instr": ops[i], "always_zero": z,
                              "live_bits": [int(v.bit_count()) for v in vals]}
            if not z:
                ccx_zero_violations.append({"op": i, "instr": ops[i],
                                            "live_bits": [int(v.bit_count()) for v in vals]})
        if k in {"X", "R", "HMR"}:
            t = qs[0]
            # pure write: close old interval
            if open_start[t] is not None:
                intervals[t].append((open_start[t], last_read[t]))
                open_start[t] = None
            q[t] = 0 if k in {"R", "HMR"} else q[t] ^ mask
            continue
        if k == "CX":
            c, t = qs
            if open_start[c] is None:
                open_start[c] = i
            if last_read[c] is None or last_read[c] < i:
                last_read[c] = i
            if open_start[t] is None:
                open_start[t] = i
            if last_read[t] is None or last_read[t] < i:
                last_read[t] = i
            q[t] ^= q[c]
            continue
        if k == "SWAP":
            a, b = qs
            for w in (a, b):
                if open_start[w] is None:
                    open_start[w] = i
                if last_read[w] is None or last_read[w] < i:
                    last_read[w] = i
            q[a], q[b] = q[b], q[a]
            continue
        if k == "CSWAP":
            c, a, b = qs
            for w in (c, a, b):
                if open_start[w] is None:
                    open_start[w] = i
                if last_read[w] is None or last_read[w] < i:
                    last_read[w] = i
            d = (q[a] ^ q[b]) & q[c]
            q[a] ^= d
            q[b] ^= d
            continue
        if k == "CCX":
            a, b, t = qs
            for w in (a, b):
                if open_start[w] is None:
                    open_start[w] = i
                if last_read[w] is None or last_read[w] < i:
                    last_read[w] = i
            if open_start[t] is None:
                open_start[t] = i
            if last_read[t] is None or last_read[t] < i:
                last_read[t] = i
            q[t] ^= q[a] & q[b]
            continue
        if k in {"Z", "CZ", "CCZ", "NEG"}:
            for w in qs:
                if open_start[w] is None:
                    open_start[w] = i
                if last_read[w] is None or last_read[w] < i:
                    last_read[w] = i
            continue
        if k in {"BIT_STORE0", "BIT_STORE1", "BIT_INVERT", "PUSH_CONDITION", "POP_CONDITION"}:
            continue
        if k == "Z_POW":
            w = qs[0]
            if open_start[w] is None:
                open_start[w] = i
            if last_read[w] is None or last_read[w] < i:
                last_read[w] = i
            continue
        raise ValueError((i, k))
    for w in range(62):
        if open_start[w] is not None:
            intervals[w].append((open_start[w], last_read[w]))

    merged = {}
    for w in range(62):
        ms = []
        for a, b in sorted(intervals[w]):
            if ms and a <= ms[-1][1]:
                ms[-1][1] = max(ms[-1][1], b)
            else:
                ms.append([a, b])
        merged[w] = ms
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

    print("value-liveness peak (write->last read before next write):", peak, "at op", at)
    print("wires live at that op:", sorted(w for w, ms in merged.items() if any(a <= at <= b for a, b in ms)))
    print("worst CCX/CSWAP/CCZ target-value popcounts (top 5):")
    worst = sorted(target_zero.items(), key=lambda kv: -max(kv[1]["live_bits"]))[:5]
    for i, r in worst:
        print(" ", i, r)
    print(f"paid ops with always-zero target: {sum(r['always_zero'] for r in target_zero.values())}/{len(target_zero)}")
    out = {
        "scope": "full legal domain, single fixed all-zero HMR branch, basis states only; not official validation",
        "max_x": MAXX,
        "value_liveness_peak": peak, "peak_op": at,
        "value_liveness": {f"q{w}": ms for w, ms in merged.items()},
        "paid_target_not_always_zero": ccx_zero_violations,
        "paid_ops": {str(i): r for i, r in target_zero.items()},
    }
    common.OUT.mkdir(parents=True, exist_ok=True)
    (common.OUT / "value_liveness.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
