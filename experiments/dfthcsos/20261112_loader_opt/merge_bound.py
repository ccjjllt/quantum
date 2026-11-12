"""Upper bound on 'merge two product CCX into one' for the Maoxin loader.

A merge (P1, P2) -> P1+P2 is legal only if
  (i) every word bit receives both or neither  (identical usage set), and
  (ii) P1+P2 = A*B with both forms carrying <= 2 r-side monomials.

(i) is guaranteed when no word-bit tap happens between the two CCX (the accumulator
prefix is then copied as a whole afterwards).  (ii) is guaranteed when they share a
control form exactly.  We report both counts, plus the weaker necessary condition
|low-columns(P1+P2)| <= 9 (3x3 union grid) as an optimistic bound.
"""
from __future__ import annotations

import functools
import re
import sys
from collections import Counter
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
    prods = []
    pending = None   # last product still mergeable (no word tap since)
    pairs_sched = 0
    pairs_form = 0
    pairs_cols = 0
    for i, ln in enumerate(lines):
        parts = ln.split()
        if not parts or parts[0] in ('APPEND_TO_REGISTER', 'REGISTER'):
            continue
        g = parts[0]
        qs = [int(p[1:]) for p in parts[1:] if p.startswith('q')]
        if g == 'CX':
            a, b = qs
            if qname.get(a, '').startswith('w') and qname.get(b, '').startswith('w'):
                pending = None
            f[b] ^= f[a]
        elif g == 'CCX':
            a, b, t = qs
            tt = f[a] & f[b]
            if qname.get(t, '').startswith('w'):
                p = dict(f1=f[a], f2=f[b], tt=tt, i=i)
                if pending is not None:
                    pairs_sched += 1
                    if (p['f1'] == pending['f1'] or p['f1'] == pending['f2']
                            or p['f2'] == pending['f1'] or p['f2'] == pending['f2']):
                        pairs_form += 1
                    cols = {m & 15 for m in anf(p['tt'] ^ pending['tt'])}
                    if len(cols) <= 9:
                        pairs_cols += 1
                pending = p
            f[t] ^= tt
        elif g == 'X':
            for q in qs:
                f[q] = ~f[q] & ALL
        elif g in ('R', 'HMR'):
            for q in qs:
                f[q] = 0
                pending = None
    return dict(path=Path(path).name,
                pairs_sched=pairs_sched, pairs_form=pairs_form, pairs_cols=pairs_cols)


def main():
    d = Path(sys.argv[1])
    tot = Counter()
    for p in sorted(d.glob('angle_k_*.kmx'), key=lambda p: int(p.stem.split('_')[-1])):
        r = analyze(p)
        for k in ('pairs_sched', 'pairs_form', 'pairs_cols'):
            tot[k] += r[k]
        print(f'{r["path"]:>12} consecutive-no-tap pairs={r["pairs_sched"]:>3} '
              f'shared-form={r["pairs_form"]:>3} <=9cols={r["pairs_cols"]:>3}')
    print('TOTAL', dict(tot))


if __name__ == '__main__':
    main()
