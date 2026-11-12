"""Fix-up accounting: per-qubit AND lifetime read counts + zero-effect gates.

For every AND (cache or wide) record how many times the qubit is read as a control or
CX source between creation and its next reset.  Also list every CX/CCX whose XOR
operand is identically 0 (a gate that does nothing) with its line number.
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
    reads = Counter()
    live = {}           # qubit -> dict(kind, mask, created_line, reads_at_creation)
    ands = []           # finished AND records
    zero_gates = []
    zero_prod = 0
    for i, ln in enumerate(lines):
        parts = ln.split()
        if not parts or parts[0] in ('APPEND_TO_REGISTER', 'REGISTER'):
            continue
        g = parts[0]
        qs = [int(p[1:]) for p in parts[1:] if p.startswith('q')]
        if g == 'CX':
            a, b = qs
            if f[a] == 0:
                zero_gates.append((i + 1, 'CX', a, b))
            reads[a] += 1
            f[b] ^= f[a]
            if b in live:
                live[b]['reads'] = reads[b]
                ands.append(live.pop(b))
        elif g == 'CCX':
            a, b, t = qs
            tt = f[a] & f[b]
            if tt == 0:
                zero_gates.append((i + 1, 'CCX', a, b, t, qname.get(t, f'q{t}')))
            reads[a] += 1
            reads[b] += 1
            A, B = anf(f[a]), anf(f[b])
            if not qname.get(t, '').startswith('w'):
                kind = 'cache' if (len(A) == 1 and len(B) == 1) else 'wide'
                live[t] = dict(kind=kind, mask=(A[0] ^ B[0] if kind == 'cache' else None),
                               line=i + 1, created=i + 1, reads=0,
                               deg=(len(A), len(B)))
            f[t] ^= tt
        elif g == 'X':
            for q in qs:
                f[q] = ~f[q] & ALL
        elif g in ('R', 'HMR'):
            for q in qs:
                f[q] = 0
                if q in live:
                    live[q]['reads'] = reads[q]
                    ands.append(live.pop(q))
        elif g in ('CZ', 'Z', 'CCZ', 'NEG'):
            pass
        else:
            raise SystemExit(f'unknown gate {g}')
    for q, rec in live.items():
        rec['reads'] = reads[q]
        ands.append(rec)
    cache = [a for a in ands if a['kind'] == 'cache']
    wide = [a for a in ands if a['kind'] == 'wide']
    return dict(path=Path(path).name, nq=nq,
                cache=len(cache), cache_unread=sum(1 for a in cache if a['reads'] == 0),
                wide=len(wide), wide_unread=sum(1 for a in wide if a['reads'] == 0),
                wide_degs=dict(Counter(a['deg'] for a in wide)),
                zero=len(zero_gates), zero_detail=zero_gates,
                cache_reads=dict(Counter(a['reads'] for a in cache)),
                wide_reads=dict(Counter(a['reads'] for a in wide)))


def main():
    d = Path(sys.argv[1])
    T = Counter()
    for p in sorted(d.glob('angle_k_*.kmx'), key=lambda p: int(p.stem.split('_')[-1])):
        r = analyze(p)
        for k in ('cache', 'cache_unread', 'wide', 'wide_unread', 'zero'):
            T[k] += r[k]
        print(f'{r["path"]:>12} cache={r["cache"]:>3} unread={r["cache_unread"]:>2} '
              f'wide={r["wide"]:>2} wunread={r["wide_unread"]:>2} zeroGates={r["zero"]:>2} '
              f'cache_reads={r["cache_reads"]} wide_degs={r["wide_degs"]}')
        for z in r['zero_detail']:
            print('    zero:', z)
    print('TOTAL', dict(T))


if __name__ == '__main__':
    main()
