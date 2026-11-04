"""Route B survey: HMR sites with preceding uncompute-like ladders (read-only)."""
import io
from collections import Counter
from pathlib import Path
import kickmix as km

P = Path("artifacts/20261104_public62_optimization/invsqrt/public62_nofallback.kmb")
c = km.Circuit.from_file(P)
buf = io.StringIO(); c.to_file(buf, format="kmx")
ops = [l for l in buf.getvalue().splitlines() if not l.startswith(("APPEND", "REGISTER"))]
BAR = ("HMR", "R", "Z_POW", "BIT_STORE0", "BIT_STORE1", "BIT_INVERT",
       "PUSH_CONDITION", "POP_CONDITION", "CCX", "CCZ", "CSWAP", "SWAP")


def qset(l):
    p = l.split()
    return {int(t[1:]) for t in p[1:] if t.startswith('q')}


hmrs = [(i, ops[i].split()) for i in range(len(ops)) if ops[i].split()[0] == "HMR"]
print("HMR total:", len(hmrs))
# stack depth at each HMR
st = []
depth = []
for l in ops:
    p = l.split()
    depth.append(len(st))
    if p[0] == "PUSH_CONDITION": st.append(p[-1])
    elif p[0] == "POP_CONDITION": st.pop()
print("HMR depth histogram:", Counter(depth[i] for i, _ in hmrs))
# for each HMR, look back <=64 ops: gates touching measured wire, barrier-free?
cand = []
for i, p in hmrs:
    q = int(p[1][1:])
    lo = max(0, i - 64)
    window = ops[lo:i]
    if any(w.split()[0] in ("HMR", "R", "Z_POW", "BIT_STORE0", "BIT_STORE1", "BIT_INVERT",
                            "PUSH_CONDITION", "POP_CONDITION") for w in window):
        continue
    if any(d != depth[i] for d in depth[lo:i]):
        continue
    touch = [w for w in window if q in qset(w)]
    kinds = Counter(w.split()[0] for w in touch)
    # uncompute-like: >=3 gates touching q, mostly CX, no CCX on q
    if len(touch) >= 3 and kinds.get("CX", 0) >= 2:
        wires = {w for g in window for w in qset(g)}
        cand.append((i, q, p[2], len(touch), dict(kinds), len(wires), depth[i]))
print("UNCOMPUTE-LIKE HMR SITES:", len(cand))
for row in cand[:40]:
    print(row)
