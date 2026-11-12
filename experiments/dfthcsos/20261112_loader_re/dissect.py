"""Structural dissection of a Maoxin .kmx loader: cache monomials, pivot linear forms, product fanout."""
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
    for s in range(0, N, 2 * period):
        out |= block << s
    return out


VAR = [var_tt(i) for i in range(11)]
ALL = (1 << N) - 1


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


def nm(m: int) -> str:
    return '1' if m == 0 else ''.join(str(i) for i in range(11) if m >> i & 1)


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
        name = names[rid]
        for i, q in enumerate(qs):
            qname[q] = f'sel{i}' if name == 'selection' else f'w{name[5:]}.{i}'
    nq = 128
    f = [0] * nq
    for q, name in qname.items():
        if name.startswith('sel'):
            f[q] = VAR[int(name[3:])]
    cache = {}          # qubit -> monomial mask, while it holds one
    cached_masks = []   # (qubit, mask) in creation order
    products = []       # (p1func, p2func, targets)
    cur_p1 = cur_p2 = None
    role = Counter()
    for ln in lines:
        p = ln.split()
        if not p or p[0] in ('APPEND_TO_REGISTER', 'REGISTER'):
            continue
        g = p[0]
        qs = [int(x[1:]) for x in p[1:] if x.startswith('q')]
        if g == 'CX':
            a, b = qs
            f[b] ^= f[a]
            if b in cache and f[b] != VAR_MINUS(f[b]) and True:
                cache.pop(b, None)
        elif g == 'CCX':
            a, b, t = qs
            A, B = anf(f[a]), anf(f[b])
            if qname.get(t, '').startswith('w'):
                products.append((A, B, qname[t], f[a], f[b]))
                role['word_ccx'] += 1
            else:
                role['anc_ccx'] += 1
                if len(A) == 1 and len(B) == 1:
                    cache[t] = A[0] ^ B[0]
                    cached_masks.append((t, A[0] ^ B[0]))
                else:
                    role[f'anc_ccx_deg{len(A)},{len(B)}'] += 1
            f[t] ^= f[a] & f[b]
        elif g == 'X':
            for q in qs:
                f[q] = ~f[q] & ALL
        elif g in ('R', 'HMR'):
            for q in qs:
                f[q] = 0
                cache.pop(q, None)
        elif g in ('CZ', 'Z', 'CCZ', 'NEG'):
            pass
        else:
            raise SystemExit(f'unknown gate {g}')
    cm = sorted(set(m for _, m in cached_masks))
    print(f'{path.name}: cache ANDs={len(cached_masks)} distinct monomials={len(cm)} '
          f'products={len(products)} ({role})')
    bits = sorted({i for m in cm for i in range(11) if m >> i & 1})
    print('  cached monomials live on address bits', bits, ' degrees:', dict(Counter(bin(m).count("1") for m in cm)))
    cset = set(cm)
    # product control supports: are they linear combos of cached monomials (plus maybe address bits)?
    bad = 0
    deg = Counter()
    tgt = Counter()
    for A, B, name, fa, fb in products:
        for a in (A, B):
            if not set(a) <= cset:
                bad += 1
                break
        deg[(len(A), len(B))] += 1
        tgt[name] += 1
    print('  products whose control support leaves the cache basis:', bad)
    print('  product control term counts:', dict(Counter(sorted(deg)[0:5])), 'range',
          min(min(a, b) for a, b in deg), max(max(a, b) for a, b in deg))
    print('  distinct targets:', len(tgt), 'targets per product:',
          dict(Counter(tgt.values())))
    print('  cached monomial list (mask: bits):')
    print('   ', ' '.join(nm(m) for m in cm))


def VAR_MINUS(x):
    return x


if __name__ == '__main__':
    main()
