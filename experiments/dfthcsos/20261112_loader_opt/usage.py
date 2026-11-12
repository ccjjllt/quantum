"""Exact per-qubit usage / redundancy accounting for a Maoxin .kmx loader.

No structural guessing: replay the circuit and, for every CCX/CX, record the *function*
(2048-bit truth table over the 11 selection bits) of the source at that moment.

Outputs:
  * cache ANDs that are never read afterwards (dead T)
  * wide ancilla CCXs that are never read (dead T)
  * per word bit: the multiset of functions XORed into it, duplicates (cancel), and the
    GF(2) rank of that multiset vs its size (rank < size => a subset is removable)
  * global rank of the product-function pool vs pool size
  * number of distinct functions that a product gate must synthesise (= lower bound on
    product gates for *this* pool)
"""
from __future__ import annotations

import functools
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

N = 2048
ALL = (1 << N) - 1


def var_tt(i):
    period = 1 << i
    block = ((1 << period) - 1) << period
    out = 0
    for s in range(0, N, 2 * period):
        out |= block << s
    return out


VAR = [var_tt(i) for i in range(11)]


@functools.lru_cache(maxsize=None)
def anf(tt):
    x = [(tt >> i) & 1 for i in range(N)]
    bit = 1
    while bit < N:
        for base in range(0, N, bit << 1):
            for j in range(base + bit, base + 2 * bit):
                x[j] ^= x[j - bit]
        bit <<= 1
    return tuple(i for i, v in enumerate(x) if v)


def rank(vecs):
    basis = {}
    for v in vecs:
        x = v
        while x:
            p = x.bit_length() - 1
            if p in basis:
                x ^= basis[p]
            else:
                basis[p] = x
                break
    return len(basis)


def parse(path):
    lines = path.read_text().splitlines()
    names, regs = {}, {}
    for ln in lines:
        m = re.fullmatch(r'APPEND_TO_REGISTER q(\d+) r(\d+)', ln)
        if m:
            regs.setdefault(int(m.group(2)), []).append(int(m.group(1)))
        m = re.fullmatch(r'REGISTER r(\d+) "(\w+)"', ln)
        if m:
            names[int(m.group(1))] = m.group(2)
    qname = {}
    for rid, qs in regs.items():
        nm = names[rid]
        for i, q in enumerate(qs):
            qname[q] = f'sel{i}' if nm == 'selection' else f'w{nm[5:]}.{i}'
    nq = 0
    for ln in lines:
        for p in ln.split():
            if p.startswith('q'):
                nq = max(nq, int(p[1:]) + 1)
    return lines, qname, nq


def analyze(path):
    lines, qname, nq = parse(path)
    f = [0] * nq
    for q, nm in qname.items():
        if nm.startswith('sel'):
            f[q] = VAR[int(nm[3:])]
    reads = Counter()          # qubit -> # times used as control/source
    cache = []                 # (qubit, mask, reads_at_reset)
    wide = []                  # (qubit, anf sizes, reads_at_reset)
    incoming = defaultdict(list)   # word bit -> [(kind, source, function)]
    created = {}
    cache_live = {}
    wide_live = {}
    hist = Counter()
    for i, ln in enumerate(lines):
        parts = ln.split()
        if not parts or parts[0] in ('APPEND_TO_REGISTER', 'REGISTER'):
            continue
        g = parts[0]
        qs = [int(p[1:]) for p in parts[1:] if p.startswith('q')]
        hist[g] += 1
        if g == 'CX':
            a, b = qs
            reads[a] += 1
            incoming[b].append(('cx', a, f[a]))
            f[b] ^= f[a]
            if b in cache_live:
                cache.append((b, cache_live.pop(b), reads[b], i))
            if b in wide_live:
                wide.append((b, wide_live.pop(b), reads[b], i))
        elif g == 'CCX':
            a, b, t = qs
            reads[a] += 1
            reads[b] += 1
            tt = f[a] & f[b]
            A, B = anf(f[a]), anf(f[b])
            if qname.get(t, '').startswith('w'):
                incoming[qname[t]].append(('ccx', (a, b), tt))
            else:
                if len(A) == 1 and len(B) == 1:
                    cache_live[t] = A[0] ^ B[0]
                    created[t] = i
                    cache.append((t, A[0] ^ B[0], 0, i, 'created'))
                else:
                    wide_live[t] = (len(A), len(B))
                    created[t] = i
                    wide.append((t, (len(A), len(B)), 0, i, 'created'))
            f[t] ^= tt
        elif g == 'X':
            for q in qs:
                f[q] = ~f[q] & ALL
        elif g in ('R', 'HMR'):
            for q in qs:
                reads[q] += 0
                f[q] = 0
                cache_live.pop(q, None)
                wide_live.pop(q, None)
        elif g in ('CZ', 'Z', 'CCZ', 'NEG'):
            pass
        else:
            raise SystemExit(f'unknown gate {g}')
    # close out cache qubits never read after creation
    dead_cache = [c for c in cache if c[2] == 0]
    # per-bit redundancy
    per = {}
    prod_pool = []
    for b, evs in incoming.items():
        tt = 0
        for _, _, v in evs:
            tt ^= v
        funcs = [v for _, _, v in evs]
        c = Counter(funcs)
        cancelling = sum(v - v % 2 for v in c.values() if v > 1)
        per[b] = dict(events=len(evs), ccx=sum(1 for k, _, _ in evs if k == 'ccx'),
                      cx=sum(1 for k, _, _ in evs if k == 'cx'),
                      rank=rank(funcs), cancelling=cancelling,
                      distinct=len(c), anf=len(anf(tt)))
        prod_pool += [v for k, _, v in evs if k == 'ccx']
    return dict(path=Path(path).name, nq=nq, hist=dict(hist),
                cache_created=len([c for c in cache]),
                dead_cache=len(dead_cache),
                dead_cache_detail=[(q, bin(m).count('1')) for q, m, *_ in dead_cache],
                wide_created=len(wide), wide=wide,
                per=per, per_tot=dict(
                    events=sum(v['events'] for v in per.values()),
                    ccx=sum(v['ccx'] for v in per.values()),
                    cx=sum(v['cx'] for v in per.values()),
                    cancelling=sum(v['cancelling'] for v in per.values()),
                    rank_lb=sum(v['rank'] for v in per.values())),
                pool=len(prod_pool), pool_rank=rank(prod_pool),
                pool_distinct=len(set(prod_pool)))


def main():
    d = Path(sys.argv[1])
    rows = []
    for p in sorted(d.glob('angle_k_*.kmx'), key=lambda p: int(p.stem.split('_')[-1])):
        r = analyze(p)
        rows.append(r)
        print(f'{r["path"]:>12} Q={r["nq"]:>3} cache={r["cache_created"]:>3} '
              f'dead_cache={r["dead_cache"]:>2} wide={r["wide_created"]:>2} '
              f'prod={r["pool"]:>4} poolrank={r["pool_rank"]:>4} distinct={r["pool_distinct"]:>4} '
              f'perbit_ccx={r["per_tot"]["ccx"]:>4} perbit_cx={r["per_tot"]["cx"]:>4} '
              f'cancel={r["per_tot"]["cancelling"]:>3} ranklb={r["per_tot"]["rank_lb"]:>4}')
        if r['dead_cache']:
            print('   dead cache:', r['dead_cache_detail'])
        if r['wide']:
            print('   wide ancilla:', [(q, s) for q, s, *_ in r['wide']])
    print('TOTAL cache', sum(r['cache_created'] for r in rows),
          'dead', sum(r['dead_cache'] for r in rows),
          'wide', sum(r['wide_created'] for r in rows),
          'prod', sum(r['pool'] for r in rows),
          'poolrank', sum(r['pool_rank'] for r in rows),
          'cancelling', sum(r['per_tot']['cancelling'] for r in rows),
          'ranklb', sum(r['per_tot']['rank_lb'] for r in rows))


if __name__ == '__main__':
    main()
