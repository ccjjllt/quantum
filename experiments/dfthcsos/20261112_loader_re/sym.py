"""Symbolically replay a .kmx ANGLE circuit over the 11 selection bits (truth tables, 2048 points).

Each qubit's function of the address is a 2048-bit truth table. CX/CCX/X are exact; R and HMR reset
the target to |0> (measurement-based uncompute of an AND). The word registers start at |0> (the
verifier's first pass), so a word bit's final function is the delta the circuit applies.

Prints the op histogram, the distribution of CCX control degrees, and the monomial cache contents.
"""
from __future__ import annotations

import functools
import re
import sys
from collections import Counter
from pathlib import Path

N = 2048


def var_tt(i: int) -> int:
    period = 1 << i
    block = ((1 << period) - 1) << period
    out = 0
    for start in range(0, N, 2 * period):
        out |= block << start
    return out


VAR = [var_tt(i) for i in range(11)]


@functools.lru_cache(maxsize=None)
def anf(tt: int) -> tuple[int, ...]:
    x = [(tt >> i) & 1 for i in range(N)]
    bit = 1
    while bit < N:
        for base in range(0, N, bit << 1):
            for j in range(base + bit, base + 2 * bit):
                x[j] ^= x[j - bit]
        bit <<= 1
    return tuple(i for i, v in enumerate(x) if v)


def name(m: int) -> str:
    return '1' if m == 0 else ''.join(f'q{i}' if m >> i & 1 else '' for i in range(11))


def poly_name(tt: int) -> str:
    return ' + '.join(name(m) for m in anf(tt))


def main() -> None:
    path = Path(sys.argv[1])
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
            qname[q] = (f'sel{i}' if nm == 'selection' else f'w{nm[5:]}.{i}')
    qmax = max(max(qs) for qs in regs.values())
    nq = qmax + 1
    # account for allocated ancillas beyond the named registers
    for ln in lines:
        for p in ln.split():
            if p.startswith('q'):
                nq = max(nq, int(p[1:]) + 1)
    f = [0] * nq
    for q, nm in qname.items():
        if nm.startswith('sel'):
            f[q] = VAR[int(nm[3:])]
    hist = Counter()
    ccx_deg = Counter()
    cache_seen: dict[int, int] = {}   # qubit -> degree when first assigned a monomial-like function
    word_products = []
    for ln in lines:
        parts = ln.split()
        if not parts or parts[0] in ('APPEND_TO_REGISTER', 'REGISTER'):
            continue
        g, qs = parts[0], [int(p[1:]) for p in parts[1:] if p.startswith('q')]
        hist[g] += 1
        if g == 'CX':
            f[qs[1]] ^= f[qs[0]]
        elif g == 'CCX':
            a, b, t = qs
            da, db = len(anf(f[a])), len(anf(f[b]))
            ccx_deg[(da, db, 'word' if qname.get(t, '').startswith('w') else 'anc')] += 1
            if qname.get(t, '').startswith('w'):
                word_products.append((da, db, qname[t], f[a], f[b]))
            f[t] ^= f[a] & f[b]
        elif g == 'X':
            for q in qs:
                f[q] = ~f[q] & (1 << N) - 1
        elif g in ('R', 'HMR'):
            for q in qs:
                f[q] = 0
        elif g in ('CZ', 'Z', 'CCZ', 'NEG'):
            pass
        else:
            raise SystemExit(f'unknown gate {g}: {ln}')
    print(f'== {path.name}: qubits={nq}')
    print('gates:', dict(hist))
    print('CCX (deg c1, deg c2, target):')
    for k in sorted(ccx_deg):
        print('   ', k, ccx_deg[k])
    live = [(q, anf(f[q])) for q in range(nq) if f[q]]
    print('final nonconstant qubits:', len(live), 'by degree:', dict(Counter(len(a) for _, a in live)))
    print('final monomials on qubits:')
    for q, a in live:
        if len(a) == 1:
            print(f'    q{q} = {name(a[0])}')
    print('word-bit product CCXs:', len(word_products))
    print('  degree pairs:', dict(Counter((a, b) for a, b, *_ in word_products)))
    for a, b, t, fa, fb in word_products:
        print(f'    {t} ^= ({poly_name(fa)}) & ({poly_name(fb)})')


if __name__ == '__main__':
    main()
