"""Per-wire access map for a window, to find retirement candidates.

Usage: python access_map.py <circuit.kmb> <lo> <hi>
"""
import sys
from pathlib import Path

from analyze_live import effect, load_ops

path = Path(sys.argv[1])
lo, hi = int(sys.argv[2]), int(sys.argv[3])
ops = load_ops(path)
n = max(max(o["q"]) for o in ops if o["q"]) + 1
reads = {w: [] for w in range(n)}
writes = {w: [] for w in range(n)}
for o in ops:
    rd, wr = effect(o)
    for w in set(rd):
        reads[w].append(o["i"])
    for w in set(wr):
        writes[w].append(o["i"])

print(f"window [{lo},{hi}]  Q={n}")
for w in range(n):
    r_in = [i for i in reads[w] if lo <= i <= hi]
    w_in = [i for i in writes[w] if lo <= i <= hi]
    r_after = [i for i in reads[w] if i > hi]
    w_before = [i for i in writes[w] if i < lo]
    r_before = [i for i in reads[w] if i < lo]
    print(
        f"w{w:2d} reads_before {len(r_before):5d} writes_before {len(w_before):5d} "
        f"| in-window reads {len(r_in):4d} writes {len(w_in):4d} "
        f"| first read after {r_after[0] if r_after else None} (total after {len(r_after)})"
    )
