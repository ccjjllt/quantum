"""Rigour check for the exhaustively proven small-tensor ranks.

`solve()`/`search_general()` accept a mask multiset when the linear system has a
solution whose output vectors are all nonzero.  If the solution space is affine
of positive dimension, the particular solution returned by back-substitution
could in principle have a zero coordinate while another solution has none, which
would make the "no decomposition" counts unsound.

This script re-runs the decisive cases and, whenever the system is feasible,
enumerates the whole affine solution space and reports whether some point has all
outputs nonzero.  It also reports how many multisets were feasible at all.
"""
import sys
import time
from itertools import combinations_with_replacement, product
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mulmath as mm


def reduce_system(rows, r):
    """rows: list of (mask_int_over_r_bits, value). Returns (piv dict, order)."""
    piv = {}
    for m, val in rows:
        while m:
            p = (m & -m).bit_length() - 1
            if p in piv:
                m ^= piv[p][0]
                val ^= piv[p][1]
            else:
                piv[p] = (m, val)
                break
        if m == 0 and val:
            return None
    return piv


def all_solutions(piv, r):
    """Enumerate the affine solution space of the reduced system."""
    used = set(piv)
    free = [j for j in range(r) if j not in used]
    out = []
    for bits in product((0, 1), repeat=len(free)):
        x = [0] * r
        for j, b in zip(free, bits):
            x[j] = b
        for p, (m, val) in sorted(piv.items(), reverse=True):
            v = val
            for j in mm.bits(m ^ (1 << p)):
                v ^= x[j]
            x[p] = v
        out.append(tuple(x))
    return out


def scan(variants, r, rhs_fn, label):
    """variants yields lists of r items; build rows per variant and decide."""
    feasible = good = 0
    t0 = time.time()
    for cols in variants:
        rows = []
        for key, val in rhs_fn(cols):
            rows.append((key, val))
        piv = reduce_system(rows, r)
        if piv is None:
            continue
        feasible += 1
        sols = all_solutions(piv, r)
        if any(all(w) for w in sols):
            good += 1
            print(f'  !! {label}: genuine {r}-term decomposition found: {cols}')
    print(f'{label} r={r}: feasible_systems={feasible}  with_all_nonzero_outputs={good}'
          f'  ({time.time()-t0:.0f}s)', flush=True)
    return feasible, good


def main():
    print('== rigour check: full affine solution space, no zero outputs allowed ==')
    for n, r in ((2, 2), (3, 3), (3, 4), (4, 7)):
        fld = mm.F(n).f
        feasible = good = 0
        t0 = time.time()
        for cols in combinations_with_replacement(range(1, 1 << n), r):
            rows = []
            for i in range(n):
                for j in range(i, n):
                    m = 0
                    for t, u in enumerate(cols):
                        if (u >> i & 1) and (u >> j & 1):
                            m |= 1 << t
                    rows.append((m, fld.mul(1 << i, 1 << j)))
            piv = reduce_system(rows, r)
            if piv is None:
                continue
            feasible += 1
            if any(all(w) for w in all_solutions(piv, r)):
                good += 1
        print(f'symmetric GF(2^{n}) r={r}: feasible={feasible} all_nonzero={good}'
              f'  ({time.time()-t0:.1f}s)', flush=True)

    # GF(2^3) general r=5: the decisive case
    fld = mm.F(3).f
    pairs = [(a, b) for a in range(1, 8) for b in range(1, 8)]
    feasible = good = 0
    t0 = time.time()
    for cols in combinations_with_replacement(pairs, 5):
        rows = []
        for i in range(3):
            for j in range(3):
                m = 0
                for t, (a, b) in enumerate(cols):
                    if (a >> i & 1) and (b >> j & 1):
                        m |= 1 << t
                rows.append((m, fld.mul(1 << i, 1 << j)))
        piv = reduce_system(rows, 5)
        if piv is None:
            continue
        feasible += 1
        if any(all(w) for w in all_solutions(piv, 5)):
            good += 1
    print(f'general GF(2^3) r=5: feasible={feasible} all_nonzero={good}  ({time.time()-t0:.0f}s)')


if __name__ == '__main__':
    main()
