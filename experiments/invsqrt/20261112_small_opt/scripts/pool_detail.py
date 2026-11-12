"""Detail dump for the 'move behind a flag' pool of an invsqrt kmx.

Reuses the census model (HMR outcomes = iid fair coins, x-independent) and, for
each unconditional CCX/CSWAP whose target's later uses are all conditional,
prints the gate, its target, and every later use with its condition bits and
trigger probability.  Read-only.
"""

import bisect
import collections
import sys

import numpy as np

TOF = {"CCX", "CCZ", "CSWAP"}
path = sys.argv[1]
N = int(sys.argv[2]) if len(sys.argv) > 2 else 200000

ops = []
for line in open(path):
    p = line.split()
    if not p or p[0] in ("APPEND_TO_REGISTER", "REGISTER"):
        continue
    ops.append(p)
n = len(ops)

rng = np.random.default_rng(7)
bits, stack = {}, []
condP = np.ones(n)
condbits = [()] * n


def bv(c):
    return bits.get(c, np.zeros(N, bool))


for i, p in enumerate(ops):
    op = p[0]
    if op == "HMR":
        bits[p[2]] = rng.random(N) < 0.5
    elif op == "BIT_STORE0":
        bits[p[1]] = (np.zeros(N, bool) if len(p) == 2
                      else bits.get(p[1], np.zeros(N, bool)) & ~bv(p[3]))
    elif op == "BIT_STORE1":
        bits[p[1]] = (np.ones(N, bool) if len(p) == 2
                      else bits.get(p[1], np.zeros(N, bool)) | bv(p[3]))
    elif op == "BIT_INVERT":
        bits[p[1]] = (~bits.get(p[1], np.zeros(N, bool)) if len(p) == 2
                      else bits.get(p[1], np.zeros(N, bool)) ^ bv(p[3]))
    elif op == "PUSH_CONDITION":
        stack.append(p[2])
    elif op == "POP_CONDITION":
        stack.pop()
    cb = list(dict.fromkeys(stack))
    if len(p) >= 2 and p[-2] == "if" and p[-1] not in cb:
        cb.append(p[-1])
    condbits[i] = tuple(cb)
    if cb:
        v = np.ones(N, bool)
        for c in cb:
            v = v & bv(c)
        condP[i] = v.mean()

WRITE_ARG = {"X": (0,), "CX": (1,), "CCX": (2,), "SWAP": (0, 1), "CSWAP": (2,), "HMR": (0,)}
events = collections.defaultdict(list)
for i, p in enumerate(ops):
    op = p[0]
    if op in ("PUSH_CONDITION", "POP_CONDITION", "BIT_STORE0", "BIT_STORE1", "BIT_INVERT"):
        continue
    qa = [a for a in p[1:] if a.startswith("q")]
    over = {qa[k] for k in WRITE_ARG[op] if k < len(qa)} if op in ("X", "HMR") else set()
    for q in qa:
        events[q].append((i, "over" if q in over else "use"))
for q in events:
    events[q].sort()


def target(p):
    if p[0] in ("CCX", "CSWAP"):
        return p[3]
    if p[0] == "CX":
        return p[2]
    return None


pool = []
for i, p in enumerate(ops):
    if p[0] not in TOF or condbits[i]:
        continue
    t = target(p)
    if t is None:
        continue
    ev = events[t]
    j = bisect.bisect_left(ev, (i, "")) + 1
    while j < len(ev) and ev[j][0] == i:
        j += 1
    uses = []
    while j < len(ev):
        ii, kind = ev[j]
        if kind == "use":
            uses.append(ii)
            j += 1
        else:
            break
    if uses and max(condP[u] for u in uses) <= 0.55:
        pool.append((i, p, t, uses))

print(f"pool size {len(pool)}")
for i, p, t, uses in pool:
    print(f"\nop {i}: {' '.join(p)}   target={t}")
    for u in uses:
        print(f"   use op {u}: {' '.join(ops[u])}")
        print(f"      condbits={condbits[u]} P={condP[u]:.4f}")
    # also report the previous op writing/using target for context
