"""Task3: 62->61Q min-cut.

(a) Verify [2006:14215] composition (pure unconditional X/CX/CCX?) + forward exact
    nonzero (= live, no kills in segment) trace.
(b) Per-wire touch counts + recompute-cone CCX sizes in segment; cheapest candidate
    vs 25 CCX (~1550 pts) budget; gap coverage of in-segment 62-peak points.
(c) Global conservative backward liveness recount (233 intervals / 18650 ops check);
    single-wire spill feasibility: wire untouched on [firstP,lastP]? multi-cluster
    lower bound. Budget: width benefit 95430.78/62 = 1539.2 pts = 25.2 CCX @61Q.
"""
import io
import json
from pathlib import Path

import kickmix as km
import numpy as np

KMB = Path("artifacts/20261108_public_frontier/release/invsqrt.kmb")
SLO, SHI = 2006, 14215
N_INPUTS = 3133452
N_WORDS = (N_INPUTS + 63) // 64
REPORTED_SCORE = 95430.78


def parse_ops():
    c = km.Circuit.from_file(str(KMB))
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    return [l for l in buf.getvalue().splitlines()
            if l and not l.startswith(("APPEND", "REGISTER"))]


def qubits_of(operand_tokens):
    return [int(t[1:]) for t in operand_tokens
            if t.startswith("q") and t[1:].isdigit()]


def main():
    ops = parse_ops()
    n = len(ops)
    seg = ops[SLO:SHI]
    from collections import Counter
    print("segment len:", len(seg))
    print("segment composition:", dict(Counter(l.split()[0] for l in seg)))
    print("has PUSH/POP:", any(l.startswith(("PUSH", "POP")) for l in seg))
    print("has inline if:", any(" if " in l for l in seg))

    # ---- backward conservative liveness (full circuit) ----
    live = set()
    live_after = [0] * n  # count after op i
    live_mask = [0] * n
    depth = 0
    for idx in range(n - 1, -1, -1):
        l = ops[idx]
        if l.startswith("PUSH_CONDITION"):
            depth -= 1
            live_after[idx] = len(live)
            m = 0
            for w in live:
                m |= (1 << w)
            live_mask[idx] = m
            continue
        if l.startswith("POP_CONDITION"):
            depth += 1
            live_after[idx] = len(live)
            m = 0
            for w in live:
                m |= (1 << w)
            live_mask[idx] = m
            continue
        p = l.split()
        op = p[0]
        cond = (depth > 0) or (" if " in l)
        qs = qubits_of([t for t in p[1:] if not t.startswith("b")])
        if cond:
            for w in qs:
                live.add(w)
        elif op in ("HMR", "R"):
            # measurement reads the value (classical output) but frees the qubit
            live.discard(qs[0])
        elif op == "X":
            pass  # reversible single-wire: membership unchanged
        elif op == "CX":
            c, t = qs[0], qs[1]
            if t in live:
                live.add(c)
        elif op == "CCX":
            a, b, t = qs[0], qs[1], qs[2]
            if t in live:
                live.add(a)
                live.add(b)
        elif op == "CSWAP":
            cc, a, b = qs[0], qs[1], qs[2]
            if a in live or b in live:
                live.add(cc)
                live.add(a)
                live.add(b)
        elif op == "SWAP":
            a, b = qs[0], qs[1]
            if a in live or b in live:
                live.add(a)
                live.add(b)
        else:
            # CZ/Z/Z_POW/NEG/phase/classical: conservative use of qubit operands
            for w in qs:
                live.add(w)
        live_after[idx] = len(live)
        m = 0
        for w in live:
            m |= (1 << w)
        live_mask[idx] = m

    peak_idx = [i for i in range(n) if live_after[i] == 62]
    print("global max live:", max(live_after))
    intervals = []
    if peak_idx:
        s = p0 = peak_idx[0]
        for i in peak_idx[1:]:
            if i == p0 + 1:
                p0 = i
            else:
                intervals.append((s, p0))
                s = p0 = i
        intervals.append((s, p0))
    total = sum(e - s + 1 for s, e in intervals)
    print(f"62-peak intervals: {len(intervals)}, total ops: {total}")
    print("first/last peak:", intervals[0] if intervals else None,
          intervals[-1] if intervals else None)
    in_seg = [(s, e) for s, e in intervals if not (e < SLO or s >= SHI)]
    print(f"peak intervals overlapping [{SLO}:{SHI}]: {len(in_seg)}, "
          f"ops: {sum(e - s + 1 for s, e in in_seg)}")

    # ---- forward exact nonzero (full circuit, unconditional only) ----
    xs = np.arange(1, N_INPUTS + 1, dtype=np.uint64)
    pad = N_WORDS * 64 - N_INPUTS
    xs_pad = np.concatenate([xs, np.ones(pad, dtype=np.uint64)]) if pad else xs
    shifts = np.arange(64, dtype=np.uint64)
    q = [np.zeros(N_WORDS, dtype=np.uint64) for _ in range(62)]
    for bit in range(22):
        bval = ((xs_pad >> bit) & 1).astype(np.uint64)
        q[bit] = np.bitwise_or.reduce(bval.reshape(-1, 64) << shifts, axis=1)
    last_mask = (np.uint64(1) << np.uint64(N_INPUTS % 64)) - np.uint64(1)
    ones = np.full(N_WORDS, np.uint64(0xFFFFFFFFFFFFFFFF))
    ones[-1] = last_mask
    fwd_live = [0] * n
    depth = 0
    for idx, l in enumerate(ops):
        if l.startswith("PUSH_CONDITION"):
            depth += 1
            continue
        if l.startswith("POP_CONDITION"):
            depth -= 1
            continue
        if depth > 0 or (" if " in l):
            continue
        p = l.split()
        op = p[0]
        if op in ("HMR", "R"):
            q[int(p[1][1:])].fill(0)
        elif op == "X":
            q[int(p[1][1:])] ^= ones
        elif op == "CX":
            a, b = int(p[1][1:]), int(p[2][1:])
            q[b] ^= q[a]
        elif op == "SWAP":
            a, b = int(p[1][1:]), int(p[2][1:])
            q[a], q[b] = q[b].copy(), q[a].copy()
        elif op == "CCX":
            a, b, t = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            q[t] ^= (q[a] & q[b])
        elif op == "CSWAP":
            cc, a, b = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            d = q[a] ^ q[b]
            pr = q[cc] & d
            q[a] ^= pr
            q[b] ^= pr
        if SLO <= idx < SHI and idx % 500 == 0:
            cnt = 0
            for w in range(62):
                a = q[w].copy()
                a[-1] &= last_mask
                if np.any(a):
                    cnt += 1
            fwd_live[idx] = cnt
    nz_seg = [(i, c) for i, c in enumerate(fwd_live) if c]
    print("fwd nonzero samples in segment:",
          [(i, c) for i, c in nz_seg[:8]], "...",
          [(i, c) for i, c in nz_seg[-4:]])
    print("fwd nonzero min/max in segment:",
          min(c for _, c in nz_seg), max(c for _, c in nz_seg))

    # ---- per-wire touches + cone in segment ----
    touches = {w: [] for w in range(62)}
    for i, l in enumerate(seg, start=SLO):
        for w in qubits_of(l.split()[1:]):
            touches[w].append(i)
    cone = [set() for _ in range(62)]
    for i, l in enumerate(seg, start=SLO):
        p = l.split()
        op = p[0]
        if op == "X":
            pass
        elif op == "CX":
            c, t = int(p[1][1:]), int(p[2][1:])
            cone[t] |= cone[c]
        elif op == "CCX":
            a, b, t = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            cone[t] = cone[t] | cone[a] | cone[b] | {i}
        elif op == "SWAP":
            a, b = int(p[1][1:]), int(p[2][1:])
            cone[a], cone[b] = cone[b], cone[a]
    rows = sorted(((w, len(touches[w]), len(cone[w])) for w in range(62)),
                  key=lambda r: (r[2], r[1]))
    print("wire,count,cone_ccx (10 cheapest):")
    for r in rows[:10]:
        print("  ", r)
    print("wire,count,cone_ccx (5 priciest):")
    for r in rows[-5:]:
        print("  ", r)

    # in-segment 62-peak points from backward pass
    pseg = [i for i in peak_idx if SLO <= i < SHI]
    print(f"in-segment 62-peak points: {len(pseg)}",
          (min(pseg), max(pseg)) if pseg else None)
    pall = set(peak_idx)
    feas = []
    for w in range(62):
        hit = [t for t in touches[w] if t in pall and SLO <= t < SHI]
        feas.append({"w": w, "touches": len(touches[w]),
                     "cone_ccx": len(cone[w]),
                     "touches_on_seg_peak_points": len(hit)})
    feas_sorted = sorted(feas, key=lambda d: (d["cone_ccx"], d["touches"]))
    print("cheapest 5 (seg cone, touches, hits-on-peak):")
    for d in feas_sorted[:5]:
        print("  ", d)

    # global single-spill feasibility
    firstP = intervals[0][0]
    lastP = intervals[-1][1]
    gtouches = {w: [] for w in range(62)}
    for i, l in enumerate(ops):
        if l.startswith(("PUSH", "POP")):
            continue
        for w in qubits_of(l.split()[1:]):
            gtouches[w].append(i)
    blocking = {}
    for w in range(62):
        tl = gtouches[w]
        import bisect
        lo = bisect.bisect_left(tl, firstP)
        hi = bisect.bisect_right(tl, lastP)
        blocking[w] = hi - lo
    free_wires = [w for w in range(62) if blocking[w] == 0]
    print(f"global peak range [{firstP},{lastP}]; "
          f"wires untouched across it: {free_wires}")
    print("5 least-touched-in-peak-range:",
          sorted(blocking.items(), key=lambda kv: kv[1])[:5])

    benefit = REPORTED_SCORE / 62
    print(f"width benefit 62->61Q: {benefit:.1f} pts = {benefit / 61:.2f} CCX @61Q")
    out = {
        "segment": [SLO, SHI],
        "segment_composition": dict(Counter(l.split()[0] for l in seg)),
        "backward_max_live": max(live_after),
        "n_peak_intervals": len(intervals),
        "peak_ops_total": total,
        "peak_first_last": [intervals[0], intervals[-1]] if intervals else None,
        "peak_overlapping_segment": {"n": len(in_seg),
                                     "ops": sum(e - s + 1 for s, e in in_seg)},
        "fwd_nonzero_seg_minmax": [min(c for _, c in nz_seg),
                                   max(c for _, c in nz_seg)],
        "in_segment_peak_points": len(pseg),
        "cheapest_cone_rows": [list(r) for r in rows[:12]],
        "global_peak_range": [firstP, lastP] if intervals else None,
        "wires_untouched_across_peak_range": free_wires,
        "least_touched_in_peak_range": sorted(blocking.items(),
                                              key=lambda kv: kv[1])[:8],
        "width_benefit_pts": benefit,
        "width_budget_ccx_at_61q": benefit / 61,
    }
    Path("experiments/invsqrt/20261109_cache_borrow_mincut/task3_mincut.json").write_text(
        json.dumps(out, indent=2) + "\n")
    print("wrote task3_mincut.json")


if __name__ == "__main__":
    main()
