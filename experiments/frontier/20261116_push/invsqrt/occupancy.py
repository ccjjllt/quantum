"""Occupancy analysis: how many wires hold a non-|0> value (or are touched) at once.

A wire is *clean* (|0>) at time t if it was reset by the last HMR and has not been
written since.  Two logical wires can share a physical wire only if their
occupied intervals are disjoint.  Peak occupancy is therefore a lower bound on Q
for any pure re-labelling of the same op sequence.

Usage: python occupancy.py <circuit.kmb|.kmx> [--window 100]
"""
import sys
from pathlib import Path

from analyze_live import load_ops


def main() -> None:
    path = Path(sys.argv[1])
    window = 200
    if "--window" in sys.argv:
        window = int(sys.argv[sys.argv.index("--window") + 1])
    ops = load_ops(path)
    n = max(max(o["q"]) for o in ops if o["q"]) + 1
    x_width = 22  # register x

    clean = [w >= x_width for w in range(n)]  # scratch starts at |0>
    events = [[] for _ in range(len(ops) + 1)]
    touched_any = []
    for o in ops:
        i = o["i"]
        q = list(o["q"])
        if not q:
            continue
        for w in q:
            if clean[w]:
                # becomes occupied now; it will be released at the next HMR
                events[i].append((w, +1))
                clean[w] = False
        if o["op"] == "HMR":
            w = q[0]
            # reset happens at the end of this op
            events[i + 1].append((w, -1))
            clean[w] = True
        touched_any.append(i)
    # sweep
    occ = 0
    prof = [0] * len(ops)
    for i in range(len(ops)):
        for (w, d) in events[i]:
            occ += d
        prof[i] = occ
    peak = max(prof)
    print(f"ops {len(ops)}  peak occupancy {peak}")
    # windows
    print("window maxima (start,end,max,mean):")
    rows = []
    for s in range(0, len(prof), window):
        seg = prof[s:s + window]
        rows.append((s, s + len(seg) - 1, max(seg), round(sum(seg) / len(seg), 1)))
    for r in rows:
        if r[2] >= peak - 4:
            print(" ", r)
    # contiguous runs at peak
    runs, start = [], None
    for i, c in enumerate(prof):
        if c == peak and start is None:
            start = i
        elif c != peak and start is not None:
            runs.append((start, i - 1))
            start = None
    if start is not None:
        runs.append((start, len(prof) - 1))
    print("runs at peak:", len(runs), "longest", max((b - a + 1) for a, b in runs))
    print("top runs:", sorted(((b - a + 1, a, b) for a, b in runs), reverse=True)[:10])


if __name__ == "__main__":
    main()
