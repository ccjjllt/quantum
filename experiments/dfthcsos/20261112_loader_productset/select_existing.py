"""Minimum subset of the 193 k=4 products whose span (together with G0 = cache + 1 + addr bits)
still contains V.

Exact question the loader T count depends on:
    min |J|  s.t.  V subseteq G0 + span{products_j : j in J}.

Reports:
  * dim G0 / V / pi(V), rank of the product images, kernel dim,
  * how many products have a word-bit control (stateful dependency),
  * greedy cover size over the 193,
  * min-weight coset expression per basis vector and the union size (a valid cover),
  * a local-search / drop pass on the union cover.

Usage: python select_existing.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from repro import KMX, REAL, VAR, replay, add_basis, mk_basis, reduce_mod, dim  # noqa: E402


def echelon(vals: list[int]):
    """Full reduced-row-echelon style elimination; returns pivots, combos, kernel basis."""
    piv: dict[int, tuple[int, int]] = {}
    kern: list[int] = []
    for j, v in enumerate(vals):
        w, combo = v, 1 << j
        while w:
            p = w.bit_length() - 1
            if p in piv:
                w ^= piv[p][0]
                combo ^= piv[p][1]
            else:
                piv[p] = (w, combo)
                break
        if not w:
            kern.append(combo)
    return piv, kern


def solve_coset(piv, target: int):
    w, combo = target, 0
    while w:
        p = w.bit_length() - 1
        if p not in piv:
            return None
        w ^= piv[p][0]
        combo ^= piv[p][1]
    return combo


def min_weight_coset(c: int, kern: list[int]) -> int:
    cur = [c]
    for kb in kern:
        cur += [x ^ kb for x in cur]
    return min(cur, key=lambda x: bin(x).count('1'))


def cover_of(piv, Alist, J: list[int]) -> int:
    """dim of span(r_j, j in J) cap pi(V)."""
    if not J:
        return 0
    b = mk_basis([r_global[j] for j in J])
    return dim(b) + len(Alist) - dim(mk_basis(list(b.values()) + Alist))


def main() -> None:
    global r_global
    d = replay(KMX)
    prods, cache, outs = d['products'], d['cache'], d['outs']
    mask = REAL
    G0 = [v & mask for v in [c[1] for c in cache] + [mask] + VAR]
    bG = mk_basis(G0)
    r = [reduce_mod(tt & mask, bG) for (_, tt, _) in prods]
    r_global = r
    V = [v & mask for v in outs]
    bV = mk_basis(V)
    A = [a for a in (reduce_mod(v, bG) for v in bV.values()) if a]
    dA = dim(mk_basis(A))
    print(f'dim G0={dim(bG)}  dim V={dim(bV)}  dim pi(V)={dA}  #products={len(r)}')

    word_ctrl = 0
    for (tgt, tt, ln) in prods:
        qs = [int(p[1:]) for p in ln.split()[1:] if p.startswith('q')]
        if any(d['qname'].get(q, '').startswith('w') for q in qs[:2]):
            word_ctrl += 1
    print(f'products with a word-bit control (stateful dependency): {word_ctrl}/{len(prods)}')
    nz = [j for j in range(len(r)) if r[j]]
    print(f'products with nonzero image mod G0: {len(nz)}/{len(r)}')

    piv, kern = echelon(r)
    nu = len(piv)
    print(f'rank(product images)={nu}  kernel dim={len(kern)}')

    # ---- per-basis-vector sparse coset expression ----
    per, union = [], 0
    for a in A:
        c = solve_coset(piv, a)
        if c is None:
            print('  !! basis vector not in span of products')
            continue
        best = min_weight_coset(c, kern)
        per.append(bin(best).count('1'))
        union |= best
    J = [j for j in range(len(r)) if union >> j & 1]
    print(f'min-weight coset weights per basis vector: {sorted(per)}')
    print(f'  sum={sum(per)}  union cover |J| = {len(J)}   covers all: {cover_of(piv, A, J) == dA}')

    # ---- drop pass: try removing each product and check coverage ----
    cur = list(J)
    improved = True
    while improved:
        improved = False
        for j in list(cur):
            trial = [x for x in cur if x != j]
            if cover_of(piv, A, trial) == dA:
                cur = trial
                improved = True
    print(f'after drop pass: |J| = {len(cur)}')

    # ---- greedy for reference ----
    S, sel, cur_cov = mk_basis([]), [], 0
    rem = list(range(len(r)))
    while cur_cov < dA:
        best, bg, bt = None, cur_cov, None
        for j in rem:
            if not r[j]:
                continue
            t = dict(S)
            add_basis(t, r[j])
            g = dim(t) + dA - dim(mk_basis(list(t.values()) + A))
            if g > bg:
                best, bg, bt = j, g, t
        if best is None:
            break
        sel.append(best)
        rem.remove(best)
        S, cur_cov = bt, bg
    print(f'greedy cover |J| = {len(sel)}  (coverage {cur_cov}/{dA})')

    print(f'\nFLOOR: |J| >= dim V = {dim(bV)}; current 193; target 168.')


if __name__ == '__main__':
    r_global: list[int] = []
    main()
