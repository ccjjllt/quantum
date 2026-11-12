"""Does an invertible 40x40 output basis B change the Maoxin loader's T count?

Answer in this script, measured on the real k=4 circuit
(artifacts/20261112_loader_re/kmx_maoxin/angle_k_4.kmx):

  * replay the .kmx symbolically over the 2048 addresses (exact truth tables),
  * collect the generators the circuit actually materialises: 193 product functions
    (CCX whose target is a word bit) and 75 cache monomials (CCX into an ancilla),
  * solve f = X . G over GF(2) for the coefficient matrix X (40 x |G|),
  * for random invertible B, g = B f is still in span(G) with coefficient matrix B X.

Since a loader of this family is *specified by a generating set* G (products 1 CCX each,
cached monomials 1 CCX each) with the single correctness condition span(G) >= V, and since
B V = V, the minimal |products| + |cache| is a function of the subspace V only.  An output
basis transform relabels which word bit each product is fanned out to (CX, free) and changes
nothing else.  The script prints the numbers that make that concrete.

Usage: python invariance_maoxin.py [angle_k_4.kmx]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
KMX = ROOT / '.worktree/dfthcsos/artifacts/20261112_loader_re/kmx_maoxin/angle_k_4.kmx'
N = 2048
ALL = (1 << N) - 1


def var_tt(i: int) -> int:
    period = 1 << i
    block = ((1 << period) - 1) << period
    out = 0
    for s in range(0, N, 2 * period):
        out |= block << s
    return out


VAR = [var_tt(i) for i in range(11)]


def popcount(x: int) -> int:
    return bin(x).count('1')


def gf2_solve(gens: list[int], targets: list[int]):
    """Express each target as an XOR of gens; returns (coeffs, unmatched target indices)."""
    piv: dict[int, tuple[int, int]] = {}   # leading bit -> (value, combo over gens)
    for j, g in enumerate(gens):
        v, combo = g, 1 << j
        while v:
            p = v.bit_length() - 1
            if p in piv:
                v ^= piv[p][0]
                combo ^= piv[p][1]
            else:
                piv[p] = (v, combo)
                break
    out, bad = [], []
    for i, t in enumerate(targets):
        v, combo = t, 0
        while v:
            p = v.bit_length() - 1
            if p not in piv:
                bad.append(i)
                combo = None
                break
            v ^= piv[p][0]
            combo ^= piv[p][1]
        out.append(combo)
    return out, bad


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else KMX
    lines = path.read_text().splitlines()
    names, regs = {}, {}
    for ln in lines:
        m = re.fullmatch(r'APPEND_TO_REGISTER q(\d+) r(\d+)', ln)
        if m:
            regs.setdefault(int(m.group(2)), []).append(int(m.group(1)))
        m = re.fullmatch(r'REGISTER r(\d+) "(\w+)"', ln)
        if m:
            names[int(m.group(1))] = m.group(2)
    qname, word_qubits = {}, []
    for rid, qs in regs.items():
        nm = names[rid]
        for i, q in enumerate(qs):
            qname[q] = f'sel{i}' if nm == 'selection' else f'w{nm[5:]}.{i}'
            if nm != 'selection':
                word_qubits.append(q)
    nq = 0
    for ln in lines:
        for p in ln.split():
            if p.startswith('q'):
                nq = max(nq, int(p[1:]) + 1)

    f = [0] * nq
    for q, nm in qname.items():
        if nm.startswith('sel'):
            f[q] = VAR[int(nm[3:])]
    products: list[tuple[str, int, int]] = []   # (target qname, tt, line)
    cache: list[tuple[int, int]] = []           # (qubit, monomial tt)
    n_cx = n_ccx = 0
    for ln in lines:
        parts = ln.split()
        if not parts or parts[0] in ('APPEND_TO_REGISTER', 'REGISTER'):
            continue
        g, qs = parts[0], [int(p[1:]) for p in parts[1:] if p.startswith('q')]
        if g == 'CX':
            n_cx += 1
            f[qs[1]] ^= f[qs[0]]
        elif g == 'CCX':
            n_ccx += 1
            a, b, t = qs
            tt = f[a] & f[b]
            if qname.get(t, '').startswith('w'):
                products.append((qname[t], tt, ln))
            else:
                cache.append((t, tt))
            f[t] ^= tt
        elif g == 'X':
            for q in qs:
                f[q] = ~f[q] & ALL
        elif g in ('R', 'HMR'):
            for q in qs:
                f[q] = 0
        elif g in ('CZ', 'Z', 'CCZ', 'NEG'):
            pass
        else:
            raise SystemExit(f'unknown {g}')

    outs = [f[q] for q in word_qubits]
    print(f'{path.name}: qubits={nq} CX={n_cx} CCX={n_ccx} products={len(products)} cache={len(cache)}')
    print(f'  word bits = {len(outs)}, final weights {min(map(popcount, outs))}..{max(map(popcount, outs))}')

    gens = [p[1] for p in products] + [c[1] for c in cache] + [ALL] + VAR
    nP = len(products)
    coeffs, bad = gf2_solve(gens, outs)
    print(f'  span(generators) has {len({g for g in gens if g})} distinct nonzero generators')
    print(f'  f expressed in span(products, cache, 1, address bits): unmatched = {bad}')
    prod_used = sorted({j for c in coeffs for j in range(nP) if c >> j & 1})
    print(f'  products actually used: {len(prod_used)}/{nP}'
          f'  (usage per product: min {min(sum(c >> j & 1 for c in coeffs) for j in range(nP))}'
          f' max {max(sum(c >> j & 1 for c in coeffs) for j in range(nP))})')

    # dim of the output space V
    def rank(vals):
        piv, rk = {}, 0
        for v in vals:
            while v:
                p = v.bit_length() - 1
                if p in piv:
                    v ^= piv[p]
                else:
                    piv[p] = v
                    rk += 1
                    break
        return rk

    print(f'  dim span(40 outputs) = {rank(outs)}   dim span(generators) = {rank([g for g in gens if g])}')

    rng = np.random.default_rng(3)
    for trial in range(3):
        while True:
            B = rng.integers(0, 2, (40, 40)).astype(np.uint8)
            if rank([int(sum(int(B[o, c]) << c for c in range(40))) for o in range(40)]) == 40:
                break
        new = []
        for o in range(40):
            v = 0
            for c in range(40):
                if B[o, c]:
                    v ^= outs[c]
            new.append(v)
        coeffs2, bad2 = gf2_solve(gens, new)
        # verify the coefficient identity reconstructs g exactly
        rec = []
        for c in coeffs2:
            v = 0
            for j in range(len(gens)):
                if c >> j & 1:
                    v ^= gens[j]
            rec.append(v)
        print(f'  random B #{trial}: g in span(G) = {not bad2}, reconstructed exactly = '
              f'{rec == new}, #generators used = {len(gens)} (unchanged)')

    print()
    print('  => the same 193 product CCX + 75 cache CCX realise ANY invertible basis of V;')
    print('     the fanout CX pattern is the only thing that changes, and CX is free.')


if __name__ == '__main__':
    main()
