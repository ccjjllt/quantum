"""Decompose each Maoxin circuit into (product gates, prefix-tap fanout) and check for
linear-algebraic redundancy.

Model discovered in the .kmx: within a fanout group one word qubit `acc` accumulates
products; before each CCX the current prefix is CX-copied to other word bits, so a
target bit's function is the XOR of the prefixes it taps, i.e. the XOR of a union of
product intervals.

Reports per circuit: accumulator(s), taps per bit, dead products (never tapped and not
an accumulator), global rank of product functions vs count, and per-bit independence.
"""
from __future__ import annotations

import functools
import pickle
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


def gf2_rank(vecs):
    """rank of a list of ints as GF(2) vectors (integers = bit vectors)."""
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
    # ---- pass 1: replay, record product CCXs and word-word CX taps in order
    ops = []   # (idx, kind, payload)
    word_ccx = []
    word_cx = []
    cache_ands = []
    for i, ln in enumerate(lines):
        parts = ln.split()
        if not parts or parts[0] in ('APPEND_TO_REGISTER', 'REGISTER'):
            continue
        g = parts[0]
        qs = [int(p[1:]) for p in parts[1:] if p.startswith('q')]
        if g == 'CX':
            a, b = qs
            if qname.get(a, '').startswith('w') and qname.get(b, '').startswith('w'):
                word_cx.append((i, a, b, f[a]))
            f[b] ^= f[a]
        elif g == 'CCX':
            a, b, t = qs
            tt = f[a] & f[b]
            if qname.get(t, '').startswith('w'):
                word_ccx.append((i, a, b, t, tt))
            else:
                A, B = anf(f[a]), anf(f[b])
                if len(A) == 1 and len(B) == 1:
                    cache_ands.append((t, A[0] ^ B[0]))
            f[t] ^= tt
        elif g == 'X':
            for q in qs:
                f[q] = ~f[q] & ALL
        elif g in ('R', 'HMR'):
            for q in qs:
                f[q] = 0
    # ---- pass 2: prefix-tap decomposition
    # accumulator = word target of the majority of CCX; taps are word->word CX
    accs = Counter(t for _, _, _, t, _ in word_ccx)
    acc = accs.most_common(1)[0][0]
    # walk operations in order, tracking prefix index per accumulator
    per_acc = defaultdict(list)   # acc -> list of product tt
    prefix = defaultdict(int)     # acc -> running XOR
    taps = defaultdict(list)      # (acc, target) -> list of prefix values tapped
    order = []
    ev = []
    for i, a, b, t, tt in word_ccx:
        ev.append((i, 'ccx', (t, tt)))
    for i, a, b, fa in word_cx:
        ev.append((i, 'cx', (a, b, fa)))
    ev.sort()
    for i, kind, payload in ev:
        if kind == 'ccx':
            t, tt = payload
            per_acc[t].append(tt)
            prefix[t] ^= tt
            order.append(('p', t))
        else:
            a, b, fa = payload
            taps[(a, b)].append(prefix[a])
    # net contribution per word bit
    contrib = defaultdict(int)
    for (a, b), vals in taps.items():
        v = 0
        for x in vals:
            v ^= x
        contrib[b] ^= v
    for a, ps in per_acc.items():
        contrib[a] ^= prefix[a]
    final = {qname[q]: f[q] for q in range(nq) if f[q]}
    # compare
    mismatch = 0
    for nm, tt in final.items():
        if nm.startswith('w'):
            if contrib[nm] != tt:
                mismatch += 1
    # ---- redundancy numbers
    all_prod = [tt for ps in per_acc.values() for tt in ps]
    rank = gf2_rank(all_prod)
    # a bit's own product set (products whose interval ends up in it): use taps on prefix
    # Dead: product j of acc is used only if some tap happens between product j-1 and j
    # (i.e. the prefix containing it is tapped) or the acc itself is a word bit.
    dead = []
    for a, ps in per_acc.items():
        # recompute per product: was prefix after product j ever tapped (for a tag != a) ?
        # easier: replay again with an explicit tag
        pass
    # replay per product with tags
    tag = {}   # (acc) -> list of product ids
    accprod = defaultdict(list)
    used = set()
    # rebuild timeline
    timeline = sorted([(i, 'ccx', (t, tt)) for i, a, b, t, tt in word_ccx] +
                      [(i, 'cx', (a, b, f)) for i, a, b, f in word_cx])
    live = defaultdict(list)   # acc -> product ids contributing to current prefix
    for i, kind, payload in timeline:
        if kind == 'ccx':
            t, tt = payload
            accprod[t].append(tt)
            live[t].append(len(accprod[t]) - 1)
        else:
            a, b, fa = payload
            if b != a:
                for pid in live[a]:
                    used.add((a, pid))
    for a, ps in accprod.items():
        if qname.get(a, '').startswith('w'):
            # the accumulator itself is a word bit: all its products count
            for pid in range(len(ps)):
                used.add((a, pid))
    dead = [(a, pid) for a, ps in accprod.items() for pid in range(len(ps))
            if (a, pid) not in used]
    return dict(path=str(path), nq=nq, accs=dict(accs), acc=acc,
                products=len(all_prod), rank=rank,
                word_cx=len(word_cx), cache=len(cache_ands),
                mismatch=mismatch, dead=len(dead),
                taps_per_bit=dict(Counter(b for (_, b) in taps)),
                distinct_tap_targets=len({b for (_, b) in taps}),
                # per-bit product counts
                per_bit=dict(Counter()),
                )


def main():
    d = Path(sys.argv[1])
    rows = []
    for p in sorted(d.glob('angle_k_*.kmx'), key=lambda p: int(p.stem.split('_')[-1])):
        r = analyze(p)
        rows.append(r)
        print(f'{p.stem:>12} Q={r["nq"]:>3} prod={r["products"]:>4} rank={r["rank"]:>4} '
              f'acc={r["acc"]} accs={r["accs"]} dead={r["dead"]} mismatch={r["mismatch"]} '
              f'wordCX={r["word_cx"]} taps_targets={r["distinct_tap_targets"]}')
    print('TOTAL prod', sum(r['products'] for r in rows), 'cache', sum(r['cache'] for r in rows),
          'dead', sum(r['dead'] for r in rows))


if __name__ == '__main__':
    main()
