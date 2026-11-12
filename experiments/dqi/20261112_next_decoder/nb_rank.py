"""Normal-basis multiplication rank search for GF(2^n) in the DQI rank-1-term model.

Model (verified against `playbook/kit/decoder/exp/arithmetic/field.py::mul_xor0`):
one term = (u . x)(v . y) -> z ^= w, costing exactly **1 CCX** with zero
workspace.  `mul_xor0` currently uses symmetric terms (u == v), but a
non-symmetric term costs the same one CCX (two pivot bits instead of one
shared pivot), so the relevant quantity is the *general* bilinear rank.

This script enumerates every normal basis (beta -> {beta^{2^i}}) of GF(2^n),
computes the number of distinct rank-1 terms needed, and reports the minimum.
A normal basis multiplier needs  n * |S_0|  terms where S_0 is the support of
one row of the multiplication table, because the table is invariant under the
diagonal Frobenius shift.

Usage:
    python nb_rank.py 4 6 12            # exhaustive over beta != 0
    python nb_rank.py 24 --samples 20000
"""
from __future__ import annotations

import argparse
import json
import random
import sys

import kickmix as km


def mat_inv_rows(rows: list[int], n: int) -> list[int] | None:
    """Inverse of the GF(2) matrix given by `rows` (row i = bits 0..n-1)."""
    a = [rows[i] | (1 << (n + i)) for i in range(n)]
    for j in range(n):
        p = -1
        for i in range(j, n):
            if (a[i] >> j) & 1:
                p = i
                break
        if p < 0:
            return None
        a[j], a[p] = a[p], a[j]
        for i in range(n):
            if i != j and ((a[i] >> j) & 1):
                a[i] ^= a[j]
    return [(a[i] >> n) & ((1 << n) - 1) for i in range(n)]


def cols_to_rows(cols: list[int], n: int) -> list[int]:
    rows = [0] * n
    for i, c in enumerate(cols):
        for k in range(n):
            if (c >> k) & 1:
                rows[k] |= 1 << i
    return rows


def coords_fn(inv_rows: list[int]):
    def coords(v: int) -> int:
        out = 0
        k = 0
        while v:
            if v & 1:
                out ^= inv_rows[k]
            v >>= 1
            k += 1
        return out
    return coords


def normal_basis_terms(f: km.GF2Field, n: int, beta: int):
    """Return (n_terms, terms) with terms = [(umask, vmask, outmask)] in standard
    (polynomial) basis, or None if {beta^{2^i}} is not a basis."""
    cols = [beta]
    for _ in range(n - 1):
        cols.append(f.square(cols[-1]))
    # Gauss-Jordan on [A|I] returns the ROWS of A^{-1}.  We need L[k] = column k of
    # M^{-1} (so that coords(v) = XOR of L[k] over set bits k of v), and
    # (M^{-1})^T = (M^T)^{-1}, whose row k is column k of M^{-1}.  The rows of M^T
    # are just the basis elements c_i themselves.
    inv_rows = mat_inv_rows(cols, n)
    if inv_rows is None:
        return None
    coords = coords_fn(inv_rows)
    # a_i(x) = bit i of coords(x); build its mask over the standard-basis bits of x.
    imgs = [coords(1 << k) for k in range(n)]
    lin = [sum(1 << k for k in range(n) if (imgs[k] >> i) & 1) for i in range(n)]
    # x = sum_i a_i c_i with a = C^{-1} x, so the linear form for coordinate i is
    # row i of C^{-1} (a mask over the standard-basis bits of x).  The output
    # vector is a coordinate vector, mapped back to the standard basis by C.
    terms = []
    nz = 0
    for i in range(n):
        for j in range(n):
            lam = coords(f.mul(cols[i], cols[j]))
            if lam:
                outmask = 0
                k = 0
                while lam:
                    if lam & 1:
                        outmask ^= cols[k]
                    lam >>= 1
                    k += 1
                terms.append((lin[i], lin[j], outmask))
                nz += 1
    return nz, terms


def verify(f: km.GF2Field, n: int, terms, samples: int = 2000) -> bool:
    rng = random.Random(12345)
    lim = 1 << n
    pairs = [(x, y) for x in range(n) for y in range(n)]
    pairs = [(1 << x, 1 << y) for x, y in pairs]
    for _ in range(samples):
        pairs.append((rng.randrange(lim), rng.randrange(lim)))
    pairs += [(0, 0), (0, 1), (1, 0)]
    for x, y in pairs:
        z = 0
        for umask, vmask, outmask in terms:
            if (bin(umask & x).count('1') & 1) and (bin(vmask & y).count('1') & 1):
                z ^= outmask
        if z != f.mul(x, y):
            return False
    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('ns', nargs='+', type=int)
    ap.add_argument('--samples', type=int, default=0, help='random beta sample count (0 = exhaustive)')
    ap.add_argument('--out', default=None)
    args = ap.parse_args()

    result = {}
    for n in args.ns:
        f = km.GF2Field(n)
        total = (1 << n) - 1
        betas = list(range(1, total + 1))
        if args.samples and total > args.samples:
            rng = random.Random(7)
            betas = rng.sample(betas, args.samples)
            betas += [2 ** i for i in range(n)]  # powers of x etc.
        best = None
        nb_count = 0
        hist = {}
        for beta in betas:
            r = normal_basis_terms(f, n, beta)
            if r is None:
                continue
            nb_count += 1
            cnt, terms = r
            hist[cnt] = hist.get(cnt, 0) + 1
            if best is None or cnt < best[0]:
                best = (cnt, beta, terms)
        if best is None:
            result[str(n)] = {'normal_bases': 0}
            print(f'GF(2^{n}): no normal basis found in sample', flush=True)
            continue
        cnt, beta, terms = best
        ok = verify(f, n, terms, samples=300 if n >= 12 else 5000)
        result[str(n)] = {
            'n': n,
            'normal_bases_tested': nb_count,
            'betas_tested': len(betas),
            'best_rank': cnt,
            'best_beta': beta,
            'verified': ok,
            'term_count_histogram': {str(k): v for k, v in sorted(hist.items())[:12]},
            'terms': [list(map(int, t)) for t in terms],
        }
        print(f'GF(2^{n}): normal_bases={nb_count} best_rank={cnt} beta={beta} verify={ok} '
              f'hist={dict(sorted(hist.items())[:8])}', flush=True)
    if args.out:
        with open(args.out, 'w') as fh:
            json.dump(result, fh, indent=1)
        print('wrote', args.out)


if __name__ == '__main__':
    main()
