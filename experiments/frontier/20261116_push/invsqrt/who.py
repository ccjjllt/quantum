"""Print the occupied (dirty|live) wire set at chosen op indices.

Usage: python who.py <circuit.kmb> <op> [<op> ...]
"""
import sys
from pathlib import Path

from analyze_live import effect, load_ops

path = Path(sys.argv[1])
cuts = [int(a) for a in sys.argv[2:]]
ops = load_ops(path)
n = max(max(o["q"]) for o in ops if o["q"]) + 1
XW = 22

live_mask = [0] * len(ops)
live = set()
for o in reversed(ops):
    rd, wr = effect(o)
    live = (live - set(wr)) | set(rd)
    live_mask[o["i"]] = sum(1 << w for w in live)

clean = [w >= XW for w in range(n)]
dirty = [set() for _ in ops]
cur = set()
for o in ops:
    i = o["i"]
    for w in o["q"]:
        if clean[w]:
            clean[w] = False
            cur.add(w)
    if o["op"] == "HMR":
        cur.discard(o["q"][0])
        clean[o["q"][0]] = True
    dirty[i] = set(cur)

for c in cuts:
    lv = {w for w in range(n) if live_mask[c] >> w & 1}
    occ = lv | dirty[c]
    print(f"op {c}: live {len(lv)} dirty {len(dirty[c])} occupied {len(occ)}")
    print("   occupied:", sorted(occ))
    print("   dirty-only:", sorted(dirty[c] - lv))
