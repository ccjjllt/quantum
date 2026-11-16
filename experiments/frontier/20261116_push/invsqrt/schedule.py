"""Occupancy profile including the input register, plus the Q implied by a pure re-labelling.

occupied(w, t) = (w holds a non-|0> value at t) OR (w is live at t)
Q_min = max_t |occupied(., t)|

Also supports forcing a set of wires clean on an op window (retire & rebuild recipe),
and reports the greedy interval-colouring count for a concrete physical assignment.

Usage: python schedule.py <circuit.kmb> [--retire q22:7350:20510 ...] [--windows 200]
"""
import sys
from pathlib import Path

from analyze_live import effect, load_ops

path = Path(sys.argv[1])
retire = []
for a in sys.argv[2:]:
    if a.startswith("q") and a.count(":") == 2:
        w, lo, hi = a.split(":")
        retire.append((int(w[1:]), int(lo), int(hi)))
windows = 200
if "--windows" in sys.argv:
    windows = int(sys.argv[sys.argv.index("--windows") + 1])
retire = [r for r in retire if isinstance(r, tuple)]

ops = load_ops(path)
n = max(max(o["q"]) for o in ops if o["q"]) + 1
XW = 22

# liveness (backward)
live_mask = [0] * len(ops)
live = set()
for o in reversed(ops):
    rd, wr = effect(o)
    live = (live - set(wr)) | set(rd)
    live_mask[o["i"]] = sum(1 << w for w in live)

# dirty intervals (forward)
clean = [w >= XW for w in range(n)]
dirty_start = [None] * n
intervals = [[] for _ in range(n)]
forced = {w: (lo, hi) for (w, lo, hi) in retire}
for o in ops:
    i = o["i"]
    for w in o["q"]:
        if clean[w]:
            clean[w] = False
            dirty_start[w] = i
    if o["op"] == "HMR":
        w = o["q"][0]
        if dirty_start[w] is not None:
            intervals[w].append((dirty_start[w], i))
            dirty_start[w] = None
        clean[w] = True
for w in range(n):
    if dirty_start[w] is not None:
        intervals[w].append((dirty_start[w], len(ops) - 1))

# apply forced-clean windows: truncate dirty intervals inside the window,
# and start a new interval right after the window if the wire is written there.
if retire:
    for w, lo, hi in retire:
        new = []
        for (a, b) in intervals[w]:
            if b < lo or a > hi:
                new.append((a, b))
                continue
            if a < lo:
                new.append((a, lo - 1))
            if b > hi:
                new.append((hi + 1, b))
        intervals[w] = new

prof = [0] * len(ops)
for w in range(n):
    for (a, b) in intervals[w]:
        for i in range(max(0, a), min(len(ops), b + 1)):
            prof[i] += 1
if retire:
    for w, lo, hi in retire:
        for i in range(max(0, lo), min(len(ops), hi + 1)):
            live_mask[i] &= ~(1 << w)
live_prof = [bin(live_mask[i]).count("1") for i in range(len(ops))]
occ = [max(prof[i], live_prof[i]) for i in range(len(ops))]
peak = max(occ)
print(f"Q={n} ops={len(ops)}")
print(f"peak dirty {max(prof)}  peak live {max(live_prof)}  peak occupied {peak}")
runs, start = [], None
for i, c in enumerate(occ):
    if c == peak and start is None:
        start = i
    elif c != peak and start is not None:
        runs.append((start, i - 1))
        start = None
if start is not None:
    runs.append((start, len(occ) - 1))
print(f"runs at peak: {len(runs)}  longest {max((b-a+1) for a,b in runs)}")
print("top runs:", sorted(((b - a + 1, a, b) for a, b in runs), reverse=True)[:10])
rows = []
for s in range(0, len(occ), windows):
    seg = occ[s:s + windows]
    rows.append((s, s + len(seg) - 1, max(seg), round(sum(seg) / len(seg), 1)))
print("window maxima:")
for r in rows:
    print("  ", r)
