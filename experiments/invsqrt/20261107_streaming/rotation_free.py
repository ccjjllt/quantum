"""Rotation machinery extent + rotation-free liveness floor (q61 model).

Part 1: for every rotation gadget we find the HMR measurement bit it uses and the
last op that mentions that bit.  The union of [gadget start, last mention] is the
"rotation machinery" (loading gates, Z_POW, HMR, and all post-correction Z/CZ).

Part 2: we delete that machinery from the gate list and recompute the q61
value-liveness peak.  Deleting is *more* optimistic than any reschedule: a value
that no rotation reads can only become shorter.  If the peak stays 62 the peak is
not caused by the rotations at all, and no interleaving can reach 61.

Read-only; baseline untouched.
"""
from __future__ import annotations

import collections
import json

import common


def liveness(gates):
    """Exact copy of the q61 value-liveness model.

    Returns (peak, peak_op, per_wire merged intervals, reads per interval).
    """
    NQ = common.NQ
    open_start = [None] * NQ
    last_read = [None] * NQ
    reads = [[] for _ in range(NQ)]
    intervals = [[] for _ in range(NQ)]
    for i, (k, qs, p) in enumerate(gates):
        if k in {"X", "R", "HMR"}:
            t = qs[0]
            if open_start[t] is not None:
                intervals[t].append((open_start[t], last_read[t], reads[t]))
                open_start[t] = None
                reads[t] = []
            continue
        if k in {"CX", "CCX", "SWAP", "CSWAP", "Z", "CZ", "CCZ", "NEG", "Z_POW"}:
            for w in qs:
                if open_start[w] is None:
                    open_start[w] = i
                if last_read[w] is None or last_read[w] < i:
                    last_read[w] = i
                reads[w].append(i)
            continue
        if k in {"BIT_STORE0", "BIT_STORE1", "BIT_INVERT",
                 "PUSH_CONDITION", "POP_CONDITION"}:
            continue
        raise ValueError((i, k, p))
    for w in range(NQ):
        if open_start[w] is not None:
            intervals[w].append((open_start[w], last_read[w], reads[w]))

    merged = {}
    for w in range(NQ):
        ms = []
        for a, b, _ in sorted(intervals[w]):
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
    return peak, at, merged, intervals


def main() -> None:
    ops, gates = common.load_ops()
    masks, rops, rwires, angles = common.load_masks_full()

    # last op mentioning each classical bit
    last_mention = {}
    for i, (k, qs, p) in enumerate(gates):
        for tok in p:
            if tok.startswith("b") and tok[1:].isdigit():
                last_mention[int(tok[1:])] = i

    # rotation gadget ranges: from the previous period-2 gate on the ancilla
    # (the HMR that clears it) up to the last mention of its measurement bit
    ranges = []
    for i, rop in enumerate(rops):
        anc = rwires[i]
        prev_hmr = None
        for j in range(rop - 1, -1, -1):
            k, qs, p = gates[j]
            if k == "HMR" and qs == [anc]:
                prev_hmr = j
                break
        assert prev_hmr is not None
        # the measurement bit of this rotation is the HMR right after Z_POW
        k, qs, p = gates[rop + 1]
        assert k == "HMR" and qs == [anc], (i, gates[rop + 1])
        bit = int(p[2][1:])
        end = last_mention[bit]
        ranges.append({"rot": i, "z_pow": rop, "ancilla": anc,
                       "gadget_start": prev_hmr + 1, "bit": bit,
                       "last_mention": end})
        print(f"rot{i:2d} ancilla q{anc:2d} Z_POW {rop} bit b{bit} "
              f"gadget {prev_hmr + 1}..{rop} corrections end {end}")

    # union of machinery ranges (merge overlapping)
    spans = sorted((r["gadget_start"], r["last_mention"]) for r in ranges)
    merged_spans = []
    for a, b in spans:
        if merged_spans and a <= merged_spans[-1][1] + 1:
            merged_spans[-1][1] = max(merged_spans[-1][1], b)
        else:
            merged_spans.append([a, b])
    print("\nmerged rotation-machinery spans:", merged_spans,
          "total ops", sum(b - a + 1 for a, b in merged_spans))

    peak, at, merged, intervals = liveness(gates)
    print(f"\nbaseline q61 value-liveness peak {peak} at op {at}")

    drop = set()
    for a, b in merged_spans:
        drop.update(range(a, b + 1))
    kept_idx = [i for i in range(len(gates)) if i not in drop]
    kept = [gates[i] for i in kept_idx]
    peak2, at2, merged2, _ = liveness(kept)
    orig_at2 = kept_idx[at2] if at2 < len(kept_idx) else None
    print(f"rotation-free (machinery deleted) peak {peak2} at original op {orig_at2}")

    # where do the remaining peaks sit?
    events = collections.Counter()
    for w, ms in merged2.items():
        for a, b in ms:
            events[a] += 1
            events[b + 1] -= 1
    live = 0
    hot = []
    for i in sorted(events)[:-1]:
        live += events[i]
        if live >= peak2:
            hot.append(i)
    hot_orig = [kept_idx[h] for h in hot]
    print(f"ops at the rotation-free peak: {len(hot_orig)}  first 12: {hot_orig[:12]}")
    print("wires live at the first hotspot:",
          sorted(w for w, ms in merged2.items()
                 if any(a <= hot[0] <= b for a, b in ms)))
    print("baseline live count at those original ops not measured here")

    common.OUT.mkdir(parents=True, exist_ok=True)
    (common.OUT / "rotation_free.json").write_text(json.dumps({
        "scope": "q61 value-liveness model, all-zero branch, structural only",
        "baseline_peak": peak, "baseline_peak_op": at,
        "rotation_free_peak": peak2, "rotation_free_peak_op": orig_at2,
        "peak_ops_after_deletion": len(hot),
        "peak_ops_after_deletion_orig": hot_orig,
        "machinery_spans": merged_spans,
        "machinery_ops": len(drop),
        "ranges": ranges,
    }, indent=1) + "\n")


if __name__ == "__main__":
    main()
