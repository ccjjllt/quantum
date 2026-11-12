"""Exact usage set of every product gate, and merge opportunities.

Model: each word-bit function is a GF(2) sum of product functions P_j (CCX into a word
qubit) and tap copies (CX word->word, which copy the *running* sum of the source).
So every word bit ends up as the XOR of a well-defined subset of products.  That subset
is the product's *usage set* (a 40-bit mask over word bits).

Two products with the same usage set are always applied together, so if they share one
control form A, then  A*B1 + A*B2 = A*(B1+B2)  is a single product with the same usage
set: one CCX can replace two.  Report all such pairs (and a greedy matching).
"""
from __future__ import annotations

import functools
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
    bits = sorted({nm for nm in qname.values() if nm.startswith('w')})
    bidx = {b: i for i, b in enumerate(bits)}
    # replay, tracking for every qubit a *set of product ids* alongside the truth table
    pid = {}       # qubit -> frozenset of product ids currently in its function
    acc = []       # product records: dict(tt, f1, f2, target, usage=set())
    word_sets = defaultdict(set)   # bit name -> symmetric difference of product sets
    cache_ands = 0
    for i, ln in enumerate(lines):
        parts = ln.split()
        if not parts or parts[0] in ('APPEND_TO_REGISTER', 'REGISTER'):
            continue
        g = parts[0]
        qs = [int(p[1:]) for p in parts[1:] if p.startswith('q')]
        if g == 'CX':
            a, b = qs
            # track sets on word bits only (pivots get whatever, unused downstream)
            if qname.get(a, '').startswith('w') or a in pid:
                pid[b] = pid.get(b, frozenset()) ^ pid.get(a, frozenset())
            f[b] ^= f[a]
        elif g == 'CCX':
            a, b, t = qs
            tt = f[a] & f[b]
            A, B = anf(f[a]), anf(f[b])
            if qname.get(t, '').startswith('w'):
                acc.append(dict(tt=tt, f1=f[a], f2=f[b], t=qname[t], i=i))
                pid[t] = pid.get(t, frozenset()) ^ frozenset([len(acc) - 1])
            else:
                if len(A) == 1 and len(B) == 1:
                    cache_ands += 1
                f[t] ^= tt
                pid[t] = frozenset()
        elif g == 'X':
            for q in qs:
                f[q] = ~f[q] & ALL
                # X changes a function by a constant; products unaffected
        elif g in ('R', 'HMR'):
            for q in qs:
                f[q] = 0
                pid.pop(q, None)
    # final sets per word bit
    for b in bits:
        word_sets[b] = set(pid.get(qname and next(q for q, nm in qname.items() if nm == b), None)
                           or set()) if False else set()
    # rebuild: pid at end for qubits still alive
    for q, nm in qname.items():
        if nm.startswith('w'):
            word_sets[nm] = set(pid.get(q, frozenset()))
    # sanity: XOR of used products must reproduce the bit function
    bad = []
    for b in bits:
        v = 0
        for j in word_sets[b]:
            v ^= acc[j]['tt']
        if v != f[qname_inv(qname, b)]:
            bad.append(b)
    usage = Counter()
    for b in bits:
        for j in word_sets[b]:
            usage[j] += 1
    empty = [j for j in range(len(acc)) if usage[j] == 0]
    # group products by usage set
    groups = defaultdict(list)
    for b in bits:
        pass
    byset = defaultdict(list)
    for j in range(len(acc)):
        key = frozenset(b for b in bits if j in word_sets[b])
        byset[key].append(j)
    # merge candidates: same usage set, share one control form
    cand = []
    for key, js in byset.items():
        for x in range(len(js)):
            for y in range(x + 1, len(js)):
                p, q = acc[js[x]], acc[js[y]]
                if p['f1'] == q['f1'] or p['f1'] == q['f2'] or p['f2'] == q['f1'] or p['f2'] == q['f2']:
                    cand.append((js[x], js[y]))
    # greedy matching over candidates
    used = set()
    match = []
    for p, q in cand:
        if p in used or q in used:
            continue
        used.add(p)
        used.add(q)
        match.append((p, q))
    return dict(path=Path(path).name, nq=nq, products=len(acc), cache=cache_ands,
                empty_products=len(empty), bad_bits=bad,
                usage_hist=dict(Counter(usage[j] for j in range(len(acc)))),
                groups=dict(Counter(len(v) for v in byset.values())),
                cand_pairs=len(cand), merges=len(match),
                bits=len(bits))


def qname_inv(qname, b):
    for q, nm in qname.items():
        if nm == b:
            return q
    return None


def main():
    d = Path(sys.argv[1])
    tot = Counter()
    for p in sorted(d.glob('angle_k_*.kmx'), key=lambda p: int(p.stem.split('_')[-1])):
        r = analyze(p)
        for k in ('products', 'cache', 'empty_products', 'cand_pairs', 'merges'):
            tot[k] += r[k]
        print(f'{r["path"]:>12} prod={r["products"]:>4} cache={r["cache"]:>4} '
              f'empty={r["empty_products"]:>2} cand={r["cand_pairs"]:>3} merges={r["merges"]:>3} '
              f'bad={len(r["bad_bits"])} usage_hist={r["usage_hist"]} groups={r["groups"]}')
    print('TOTAL', dict(tot))


if __name__ == '__main__':
    main()
