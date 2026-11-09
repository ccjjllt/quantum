"""Task3e: true-constant (dep=empty) wires + per-peak-interval coverage.

dep[w] = set of primary sources (input idx 0..21) w's value depends on.
Init: dep[w]={w} for w<22 (input bits), {} for ancilla (start |0>).
X: unchanged. CX c->t: dep[t]|=dep[c]. CCX: dep[t]|=dep[a]|dep[b].
HMR/R uncond: dep[w]={} (reset to |0>). Conditional write: taint (dep=None).
SWAP: swap deps.

A wire is HMR-spillable across a gap only if dep=={} on the gap (constant =>
unentangled => measurement disturbs nothing) AND untouched on the gap.
Check: (1) segment-untouched wires' dep@2006; (2) for each global 62-peak
interval (sound backward set, 372), list wires with dep=={} & untouched there.
"""
import io
import json
from pathlib import Path

import kickmix as km

KMB = Path("artifacts/20261108_public_frontier/release/invsqrt.kmb")
SLO, SHI = 2006, 14215


def parse_ops():
    c = km.Circuit.from_file(str(KMB))
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    return [l for l in buf.getvalue().splitlines()
            if l and not l.startswith(("APPEND", "REGISTER"))]


def main():
    ops = parse_ops()
    n = len(ops)

    # ---- forward dep DP + snapshots at segment start ----
    dep = [({w} if w < 22 else set()) for w in range(62)]
    tainted = [False] * 62
    depth = 0
    for idx, l in enumerate(ops):
        if idx == SLO:
            dep_at_start = [None if tainted[w] else set(dep[w])
                            for w in range(62)]
            break
        if l.startswith("PUSH_CONDITION"):
            depth += 1
            continue
        if l.startswith("POP_CONDITION"):
            depth -= 1
            continue
        p = l.split()
        op = p[0]
        cond = (depth > 0) or (" if " in l)
        if op in ("HMR", "R"):
            w = int(p[1][1:])
            if cond:
                tainted[w] = True
            else:
                dep[w] = set()
        elif op == "X":
            w = int(p[1][1:])
            if cond:
                tainted[w] = True
        elif op == "CX":
            a, b = int(p[1][1:]), int(p[2][1:])
            if cond:
                tainted[b] = True
            else:
                dep[b] = dep[b] | dep[a]
        elif op == "CCX":
            a, b, t = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            if cond:
                tainted[t] = True
            else:
                dep[t] = dep[t] | dep[a] | dep[b]
        elif op in ("CSWAP", "SWAP"):
            if op == "CSWAP":
                cc, a, b = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
                if cond:
                    tainted[a] = tainted[b] = True
                else:
                    dep[a], dep[b] = dep[b], dep[a]
            else:
                a, b = int(p[1][1:]), int(p[2][1:])
                if not cond:
                    dep[a], dep[b] = dep[b], dep[a]

    touch = {w: [] for w in range(62)}
    for i, l in enumerate(ops):
        if l.startswith(("PUSH", "POP")):
            continue
        for t in l.split()[1:]:
            if t.startswith("q") and t[1:].isdigit():
                touch[int(t[1:])].append(i)
    import bisect
    seg_untouched = [w for w in range(62)
                     if not any(SLO <= t < SHI for t in touch[w])]
    print(f"segment-untouched wires ({len(seg_untouched)}): {seg_untouched}")
    print("their dep@2006 ({} = TRUE CONSTANT, HMR-spillable):")
    const_seg = []
    for w in seg_untouched:
        d = dep_at_start[w]
        tag = "CONST" if d == set() else ("TAINTED" if d is None else f"dep={sorted(d)}")
        print(f"  q{w}: {tag}")
        if d == set():
            const_seg.append(w)
    print(f"true-constant segment-untouched: {const_seg}")

    # ---- global 62-peak intervals (sound backward liveness) ----
    live = set()
    live_after = [0] * n
    depth = 0
    for idx in range(n - 1, -1, -1):
        l = ops[idx]
        if l.startswith("PUSH_CONDITION"):
            depth -= 1
            live_after[idx] = len(live)
            continue
        if l.startswith("POP_CONDITION"):
            depth += 1
            live_after[idx] = len(live)
            continue
        p = l.split()
        op = p[0]
        cond = (depth > 0) or (" if " in l)
        qs = [int(t[1:]) for t in p[1:]
              if t.startswith("q") and t[1:].isdigit()]
        if cond:
            for w in qs:
                live.add(w)
        elif op in ("HMR", "R"):
            live.discard(qs[0])
        elif op == "X":
            pass
        elif op == "CX":
            c, t = qs[0], qs[1]
            if t in live:
                live.add(c)
        elif op == "CCX":
            a, b, t = qs[0], qs[1], qs[2]
            if t in live:
                live.add(a)
                live.add(b)
        elif op == "CCZ":
            a, b, t = qs[0], qs[1], qs[2]
            if t in live or True:
                live.update([a, b, t])
        elif op == "CSWAP":
            cc, a, b = qs[0], qs[1], qs[2]
            if a in live or b in live:
                live.update([cc, a, b])
        elif op == "SWAP":
            a, b = qs[0], qs[1]
            if a in live or b in live:
                live.update([a, b])
        else:
            for w in qs:
                live.add(w)
        live_after[idx] = len(live)
    peak = [i for i in range(n) if live_after[i] == 62]
    intervals = []
    s = p0 = peak[0]
    for i in peak[1:]:
        if i == p0 + 1:
            p0 = i
        else:
            intervals.append((s, p0))
            s = p0 = i
    intervals.append((s, p0))
    print(f"peak intervals: {len(intervals)}, ops: "
          f"{sum(e - a + 1 for a, e in intervals)}")

    # ---- forward dep DP full circuit, snapshot dep at each interval start ----
    # (cheaper: track dep only; 53k steps)
    dep = [({w} if w < 22 else set()) for w in range(62)]
    tainted = [False] * 62
    starts = sorted({a for a, _ in intervals})
    dep_at = {}
    depth = 0
    si = 0
    for idx, l in enumerate(ops):
        while si < len(starts) and starts[si] == idx:
            dep_at[idx] = [None if tainted[w] else set(dep[w])
                           for w in range(62)]
            si += 1
        if l.startswith("PUSH_CONDITION"):
            depth += 1
            continue
        if l.startswith("POP_CONDITION"):
            depth -= 1
            continue
        p = l.split()
        op = p[0]
        cond = (depth > 0) or (" if " in l)
        if op in ("HMR", "R"):
            w = int(p[1][1:])
            if cond:
                tainted[w] = True
            else:
                dep[w] = set()
        elif op == "X":
            w = int(p[1][1:])
            if cond:
                tainted[w] = True
        elif op == "CX":
            a, b = int(p[1][1:]), int(p[2][1:])
            if cond:
                tainted[b] = True
            else:
                dep[b] = dep[b] | dep[a]
        elif op == "CCX":
            a, b, t = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            if cond:
                tainted[t] = True
            else:
                dep[t] = dep[t] | dep[a] | dep[b]
        elif op == "CSWAP":
            cc, a, b = int(p[1][1:]), int(p[2][1:]), int(p[3][1:])
            if cond:
                tainted[a] = tainted[b] = True
            else:
                dep[a], dep[b] = dep[b], dep[a]
        elif op == "SWAP":
            a, b = int(p[1][1:]), int(p[2][1:])
            if not cond:
                dep[a], dep[b] = dep[b], dep[a]
    cover = []
    for a, e in intervals:
        cands = [w for w in range(62)
                 if dep_at[a][w] == set()
                 and not any(a <= t <= e for t in touch[w])]
        cover.append({"interval": [a, e], "len": e - a + 1,
                      "const_untouched": cands})
    n_covered = sum(1 for c in cover if c["const_untouched"])
    print(f"intervals with >=1 const+untouched wire: {n_covered}/{len(cover)}")
    for c in cover[:15]:
        print(f"  [{c['interval'][0]},{c['interval'][1]}] len={c['len']} "
              f"cover={c['const_untouched'][:8]}")
    uncovered_lens = sorted([c["len"] for c in cover
                             if not c["const_untouched"]])
    print(f"uncovered interval lengths: n={len(uncovered_lens)}, "
          f"min={min(uncovered_lens) if uncovered_lens else None}, "
          f"max={max(uncovered_lens) if uncovered_lens else None}")
    Path("experiments/invsqrt/20261109_cache_borrow_mincut/task3e_cover.json").write_text(
        json.dumps({"n_intervals": len(intervals), "n_covered": n_covered,
                    "const_seg_untouched": const_seg,
                    "cover": cover}, indent=2) + "\n")
    print("wrote task3e_cover.json")


if __name__ == "__main__":
    main()
