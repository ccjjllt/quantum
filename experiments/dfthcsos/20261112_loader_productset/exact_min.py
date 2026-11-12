"""EXACT minimum number of products for every one of the 15 Maoxin loaders.

Theory
------
Correctness of a Maoxin-family loader is  V subseteq G0 + span(P)  with
G0 = span(cache monomials, 1, 11 address bits).  Quotient by G0 and let
    A = pi(V)                      (35-dim for k=4..14, 40-dim for k=0..3)
    r_j = pi(p_j)                  (m nonzero ones; the rest are already in G0)
    r_j = (u_j, v_j)               u in F2^dim A, v in the complement (dim D - dim A)

A set J works iff for every x in A there is c in F2^J with  sum c_j u_j = x
and sum c_j v_j = 0.  Let phi: F2^m -> F2^D', c |-> sum c_j v_j and K = ker phi.
Because span(r) supseteq A, phi restricted to K maps ONTO A isomorphically, so for
each x there is a UNIQUE c(x) in K.  Hence J works  iff  J supseteq supp(K) :=
{j : exists c in K, c_j = 1}.  Therefore

    min |J| = |supp(K)| = m - #{j : e_j in colspan(M)},   M = matrix of v_j rows.

i.e. the minimum is exactly the number of products whose image is *used* by some
element of A; every other product is dead weight and every used one is mandatory.
This is an exact answer, not a heuristic.

Usage: python exact_min.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from loaderlib import KMXDIR, REAL, Basis, g0_basis, replay  # noqa: E402

OUT = Path('/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dfthcsos/artifacts/20261112_loader_productset')


def exact_min(A: list[int], R: list[int]):
    """A: basis of pi(V).  R: nonzero product images.  Returns (min|J|, used_mask)."""
    bA = Basis(A)
    da = len(bA)
    Avals = bA.values()
    bb = Basis(A)
    for v in R:
        bb.add(v)
    dim = len(bb)
    vals = bb.values()
    # coordinates: vals[k] -> e_k
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

    def coord(v):
        w, combo = v, 0
        while w:
            p = w.bit_length() - 1
            w ^= piv[p][0]
            combo ^= piv[p][1]
        return combo

    coords = [coord(v) for v in R]
    m = len(coords)
    hi = ((1 << (dim - da)) - 1) << da
    M_rows = [c & hi for c in coords]           # m rows, each dim-da bits
    # columns of M restricted to the nonzero part: column i is the m-bit vector of bit i
    cols = []
    for i in range(da, dim):
        col = 0
        bit = 1 << i
        for j, row in enumerate(M_rows):
            if row & bit:
                col |= 1 << j
        if col:
            cols.append(col)
    colspan = Basis(cols)
    drop = 0
    for j in range(m):
        if colspan.contains(1 << j):
            drop |= 1 << j        # e_j in colspan -> coordinate j is dead
    n_min = m - bin(drop).count('1')
    return n_min, drop, da, dim


def main() -> None:
    rows = []
    tot_ccx = 0
    tot_cache = 0
    tot_prod = 0
    tot_min = 0
    tot_zero_cache = 0
    tot_dup_cache = 0
    tot_zero_prod = 0
    tot_unused_cache = 0
    for k in range(15):
        path = KMXDIR / f'angle_k_{k}.kmx'
        d = replay(path)
        mask = REAL
        ctt = [tt & mask for _, tt in d['cache']]
        pt = [tt & mask for _, tt, _ in d['prods']]
        G0 = g0_basis(d['cache'], mask)
        bV = Basis([o & mask for o in d['outs']])
        A = [a for a in (G0.reduce(v) for v in bV.values()) if a]
        A = Basis(A).values()
        r_all = [G0.reduce(v) for v in pt]
        R_idx = [j for j, v in enumerate(r_all) if v]
        R = [r_all[j] for j in R_idx]
        nmin, drop, da, dim = exact_min(A, R)
        J = [R_idx[j] for j in range(len(R)) if not (drop >> j) & 1]
        # verify by direct truth-table span
        chk = Basis([r_all[j] for j in J] + G0.values())
        ok = all(chk.contains(v) for v in bV.values())
        # and prove minimality empirically: drop any single one -> should fail
        dropfail = 0
        for j in J[:min(len(J), 12)]:
            t = Basis([r_all[i] for i in J if i != j] + G0.values())
            if not all(t.contains(v) for v in bV.values()):
                dropfail += 1
        zero_c = sum(1 for v in ctt if v == 0)
        dup_c = len(ctt) - len(set(ctt))
        zero_p = sum(1 for v in pt if v == 0)
        ccx_new = len(ctt) - zero_c - dup_c + nmin
        rows.append(dict(k=k, ccx=d['n_ccx'], cache=len(ctt), prod=len(pt),
                         zero_cache=zero_c, dup_cache=dup_c, zero_prod=zero_p,
                         nonzero_images=len(R), min_products=nmin, ccx_new=ccx_new,
                         dimA=da, dim_span=dim, ok=bool(ok),
                         drop_tests=min(len(J), 12), drop_fail=dropfail,
                         selected=J))
        tot_ccx += d['n_ccx']
        tot_cache += len(ctt)
        tot_prod += len(pt)
        tot_min += nmin
        tot_zero_cache += zero_c
        tot_dup_cache += dup_c
        tot_zero_prod += zero_p
        print(f'k={k:2d} T={d["n_ccx"]:4d} cache={len(ctt):3d} prod={len(pt):4d} | '
              f'zeroC={zero_c} dupC={dup_c} zeroP={zero_p} | images={len(R):3d} '
              f'dimA={da} span={dim} | MIN products={nmin:3d} -> CCX {ccx_new:4d} | '
              f'cover {"OK" if ok else "FAIL"} '
              f'drop-fails {dropfail}/{min(len(J), 12)}')
    print(f'\nTOTAL CCX {tot_ccx}  cache {tot_cache}  products {tot_prod}  min products {tot_min}')
    t_new = tot_min + tot_cache - tot_zero_cache - tot_dup_cache
    print(f'  cache after removing zero/duplicate: {tot_cache - tot_zero_cache - tot_dup_cache}')
    print(f'  T/pass = {t_new}   (now {tot_ccx}, target 243*15=3645)')
    lam = 46.9074
    for T in (tot_ccx, t_new):
        print(f'  T={T:5d} -> T_total={2 * T + 6662:6d} -> cost={lam * (2 * T + 6662) * 427 / 1e6:.2f}M')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'exact_min.json').write_text(json.dumps(rows, indent=1))
    print(f'wrote {OUT / "exact_min.json"}')


if __name__ == '__main__':
    main()
