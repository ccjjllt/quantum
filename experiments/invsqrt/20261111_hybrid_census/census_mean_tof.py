"""Mean-executed-Toffoli census for an invsqrt kmx dump (read-only analysis).

Why this is exact for invsqrt: every gate is a computational-basis permutation
(X/CX/CCX/SWAP/CSWAP), a diagonal phase (CZ/CCZ/Z/Z_POW/NEG) or an X-basis
measure-and-reset (HMR).  The state is therefore always a basis state up to a
global phase, so every HMR outcome is an independent fair coin, independent of
x.  Hence the mean executed Toffoli-like count per shot is a fixed constant,
computable by Monte Carlo over iid coins (no x dependence).

Usage:
    python census_mean_tof.py circuit.kmx [N]

Prints:
  * static Toffoli-like (CCX/CCZ/CSWAP) and mean executed count
  * trigger-probability histogram with the mean-cost contribution per bin
  * dataflow: for unconditional Toffoli gates with a CCX/CSWAP target, is the
    next use of the target conditional?  (the "move behind a flag" pool)

The Monte Carlo mean is validated against the official verifier on the 6c6a734d
hybrid: 1218.833505 model vs 1218.833259921885 verifier (diff 0.00025).
"""
import sys
import collections
import bisect
import numpy as np

TOF = {'CCX', 'CCZ', 'CSWAP'}
path = sys.argv[1]
N = int(sys.argv[2]) if len(sys.argv) > 2 else 200000

ops = []
for line in open(path):
    p = line.split()
    if not p or p[0] == 'APPEND_TO_REGISTER':
        continue
    if p[0] == 'REGISTER':
        continue
    ops.append(p)
n = len(ops)

rng = np.random.default_rng(7)
bits, stack = {}, []
condP = np.ones(n)
condbits = [()] * n


def bv(c):
    return bits.get(c, np.zeros(N, bool))


# pass 1: condition stacks, their probabilities, and gate execution
for i, p in enumerate(ops):
    op = p[0]
    if op == 'HMR':
        bits[p[2]] = rng.random(N) < 0.5
    elif op == 'BIT_STORE0':
        b = p[1]
        bits[b] = (np.zeros(N, bool) if len(p) == 2
                   else bits.get(b, np.zeros(N, bool)) & ~bv(p[3]))
    elif op == 'BIT_STORE1':
        b = p[1]
        bits[b] = (np.ones(N, bool) if len(p) == 2
                   else bits.get(b, np.zeros(N, bool)) | bv(p[3]))
    elif op == 'BIT_INVERT':
        b = p[1]
        bits[b] = (~bits.get(b, np.zeros(N, bool)) if len(p) == 2
                   else bits.get(b, np.zeros(N, bool)) ^ bv(p[3]))
    elif op == 'PUSH_CONDITION':
        stack.append(p[2])
    elif op == 'POP_CONDITION':
        stack.pop()
    cb = list(dict.fromkeys(stack))
    if len(p) >= 2 and p[-2] == 'if' and p[-1] not in cb:
        cb.append(p[-1])
    condbits[i] = tuple(cb)
    if cb:
        v = np.ones(N, bool)
        for c in cb:
            v = v & bv(c)
        condP[i] = v.mean()

tof = [(i, ops[i]) for i in range(n) if ops[i][0] in TOF]
mean_exec = sum(condP[i] for i, _ in tof)
print(f'ops={n} static_tof={len(tof)} mean_exec={mean_exec:.6f}')
ps = np.array([condP[i] for i, _ in tof])
edges = [0, 1e-9, 1e-3, 0.1, 0.3, 0.45, 0.55, 0.7, 0.9, 0.99, 0.999, 1.0001]
for lo, hi in zip(edges[:-1], edges[1:]):
    m = (ps >= lo) & (ps < hi)
    print(f'P in [{lo:g},{hi:g}): {int(m.sum()):5d} gates, mean cost {ps[m].sum():9.3f}')

# pass 2: dataflow for target-bearing paid gates
WRITE_ARG = {'X': (0,), 'CX': (1,), 'CCX': (2,), 'SWAP': (0, 1), 'CSWAP': (2,), 'HMR': (0,)}
events = collections.defaultdict(list)
for i, p in enumerate(ops):
    op = p[0]
    if op in ('PUSH_CONDITION', 'POP_CONDITION', 'BIT_STORE0', 'BIT_STORE1', 'BIT_INVERT'):
        continue
    qa = [a for a in p[1:] if a.startswith('q')]
    over = set()
    if op in ('X', 'HMR'):
        over = {qa[k] for k in WRITE_ARG[op] if k < len(qa)}
    for q in qa:
        events[q].append((i, 'over' if q in over else 'use'))
for q in events:
    events[q].sort()


def target(p):
    if p[0] in ('CCX', 'CSWAP'):
        return p[3]
    if p[0] == 'CX':
        return p[2]
    return None


un = []
never = 0
for i, p in tof:
    t = target(p)
    if t is None or condbits[i]:
        continue
    ev = events[t]
    j = bisect.bisect_left(ev, (i, '')) + 1
    while j < len(ev) and ev[j][0] == i:
        j += 1
    uses = []
    while j < len(ev):
        ii, kind = ev[j]
        if kind == 'use':
            uses.append(ii)
            j += 1
        else:
            break
    if not uses:
        never += 1
        continue
    un.append((i, p[0], t, [condP[u] for u in uses]))
print(f'\nunconditional target gates: {len(un) + never}, target never used again: {never}')
hist = collections.Counter()
for _, _, _, ups in un:
    m = max(ups)
    key = ('=1' if m > 0.999 else '0.9-0.999' if m > 0.9 else '0.45-0.55' if m > 0.45 else '<0.45')
    hist[key] += 1
print('next-use max P histogram:', dict(hist))
pool = [r for r in un if max(r[3]) <= 0.55]
print(f'ALL later uses conditional (P<=0.55): {len(pool)} gates; '
      f'upper-bound mean saving {sum(1 - max(r[3]) for r in pool):.2f} gates')
