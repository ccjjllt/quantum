"""Minimum number of product functions needed to span V, given the cache.

Reduction used everywhere below
-------------------------------
Let G0 = span(cache monomials, 1, 11 address bits)  (dim 82 for k=4).
Correctness of a Maoxin-family loader is exactly  V subseteq G0 + span(P).
Quotient by G0: need  pi(V) subseteq span(pi(P)).  pi(V) has dim 35, the 193 product
images have rank 163 (30 products already lie in G0, hence are replaceable by free CX).

So the problem is:
    min |J|  s.t.  A subseteq span{r_j : j in J},  A = pi(V) (35-dim), r_j = pi(p_j).

Coordinate trick: put a basis of span(A cup r) = 198 dims, A first, so A = {x : bits 35..197 = 0}.
Then  dim(S cap A) = dim(S) - dim(proj_{35..197}(S)), evaluated on 198-bit ints.

Outputs: greedy, greedy + drop pass, randomized restarts, and the CCX/T projection.

Usage: python select.py [angle_k_4.kmx]
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from loaderlib import KMXDIR, REAL, Basis, g0_basis, replay  # noqa: E402


class Coords:
    """Coordinate system: 198-bit ints, A = span of the low `da` bits."""

    def __init__(self, A: list[int], r: list[int]):
        b = Basis(A)                     # A first
        self.A = A
        self.da = len(b)
        basis_vecs = b.values()          # these must be e_0..e_{da-1}
        for v in r:
            b.add(v)                     # extend
        self.dim = len(b)
        # build coordinates: map each basis vector of `b` to a unit vector.
        # `b.values()` is a row-echelon basis; assign e_k in that order.
        vals = b.values()
        self.map_basis = Basis()
        self.unit: dict[int, int] = {}
        # We need an invertible map.  Build it by elimination on the vals themselves:
        # coordinate of v = the coefficient vector.  Track combos.
        piv: dict[int, tuple[int, int]] = {}
        for k, v in enumerate(vals):
            w, combo = v, 1 << k
            while w:
                p = w.bit_length() - 1
                if p in piv:
                    w ^= piv[p][0]
                    combo ^= piv[p][1]
                else:
                    piv[p] = (w, combo)
                    break
        self.piv = piv
        self.zero = 0  # unused

    def coord(self, v: int) -> int:
        w, combo = v, 0
        while w:
            p = w.bit_length() - 1
            if p not in self.piv:
                raise ValueError('vector outside the coordinate space')
            w ^= self.piv[p][0]
            combo ^= self.piv[p][1]
        return combo

    def dim_cap_A(self, vecs: list[int]) -> int:
        """dim(span(vecs) cap A) where A = vectors whose bits >= da are zero."""
        hi = ((1 << (self.dim - self.da)) - 1) << self.da
        S = Basis(vecs)
        proj = Basis([v & hi for v in S.values() if v & hi])
        return len(S) - len(proj)


def greedy(A, r, rng=None, ordered=False) -> list[int]:
    CAND = list(range(len(r)))
    S: list[int] = []
    chosen: list[int] = []
    target = 35
    cur = 0
    pool = list(CAND)
    while cur < target:
        best, bg, bv = None, cur, None
        order = list(pool)
        if rng is not None and not ordered:
            rng.shuffle(order)
        for j in order:
            gain = None
            trial = S + [r[j]]
            g = dim_capA(trial)
            if g > bg:
                best, bg, bv = j, g, trial
                if g == target:
                    break
            _ = gain
        if best is None:
            break
        chosen.append(best)
        S = bv
        pool.remove(best)
        cur = bg
    return chosen


DIMS: tuple[int, int] = (0, 0)


def dim_capA(vecs: list[int]) -> int:
    da, dim = DIMS
    hi = ((1 << (dim - da)) - 1) << da
    S = Basis(vecs)
    proj = Basis([v & hi for v in S.values() if v & hi])
    return len(S) - len(proj)


def main() -> None:
    global DIMS
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else KMXDIR / 'angle_k_4.kmx'
    d = replay(path)
    mask = REAL
    G0 = g0_basis(d['cache'], mask)
    bV = Basis([o & mask for o in d['outs']])
    A = [a for a in (G0.reduce(v) for v in bV.values()) if a]
    bA = Basis(A)
    A = bA.values()
    r_all = [G0.reduce(tt & mask) for (_, tt, _) in d['prods']]
    r_idx = [j for j, v in enumerate(r_all) if v]
    r = [r_all[j] for j in r_idx]
    print(f'{path.name}: dim G0={len(G0)}  dim V={len(bV)}  dim pi(V)={len(bA)}'
          f'  products={len(r_all)}  nonzero images={len(r)}  (in G0: {len(r_all) - len(r)})')

    C = Coords(A, r)
    DIMS = (C.da, C.dim)
    print(f'coordinate space dim={C.dim}  A-dim={C.da}')
    coords = [C.coord(v) for v in r]
    Ac = [C.coord(v) for v in A]
    DIMS = (C.da, C.dim)
    base = dim_capA([C.coord(v) for v in A])
    print(f'sanity: dim(span(A) cap A) = {base} (should be {C.da})')

    # A = vectors with bits >= da zero -> in coordinates, A = span(e_0..e_{da-1})
    S0 = Basis(Ac)
    print(f'dim of coordinate A-span = {len(S0)}')

    rng = random.Random(0)
    best = None
    for trial in range(60):
        if trial == 0:
            ch = greedy(Ac, coords, None, ordered=True)
        else:
            ch = greedy(Ac, coords, rng)
        if not ch:
            continue
        if dim_capA([coords[j] for j in ch]) < C.da:
            continue
        # drop pass
        cur = list(ch)
        improved = True
        while improved:
            improved = False
            for j in list(cur):
                t = [x for x in cur if x != j]
                if dim_capA([coords[x] for x in t]) == C.da:
                    cur = t
                    improved = True
        if best is None or len(cur) < len(best):
            best = cur
            print(f'  trial {trial:2d}: |J| = {len(cur)}')
    if best is None:
        print('no cover found')
        return
    J = sorted(r_idx[j] for j in best)
    print(f'\nBEST cover: |J| = {len(J)} products  (of {len(r_all)}; '
          f'{len(r_all) - len(r)} were already in G0)')
    print(f'  => {len(d["cache"])} cache + {len(J)} products = {len(d["cache"]) + len(J)} CCX '
          f'(was {d["n_ccx"]})')

    # verify directly on truth tables
    check = Basis([r_all[j] for j in J] + [v for v in G0.values()])
    bad = [i for i, v in enumerate(bV.values()) if not check.contains(v)]
    print(f'  direct truth-table check: V basis vectors outside span(G0 + J) = {bad}')
    Path('/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dfthcsos/artifacts/20261112_loader_productset/'
         'k4_selected.json').write_text(
        __import__('json').dumps({'kmx': path.name, 'n_cache': len(d['cache']),
                                  'n_products_total': len(r_all),
                                  'selected': J, 'selected_sorted': sorted(J)}, indent=1))
    print('  wrote artifacts/20261112_loader_productset/k4_selected.json')


if __name__ == '__main__':
    main()
