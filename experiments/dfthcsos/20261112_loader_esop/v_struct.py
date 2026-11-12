"""Follow-ups on basis_rank.py:

  1. Are the 40 interior slices linearly independent (dim V = 40) or dependent (k>=4 LSBs)?
  2. How many random combinations are zero / have rank < 15 (denser sampling)?
  3. What is the k>=4 rank-5 LSB function (bit 0 of each word)?  weight / ANF degree.

Usage: python v_struct.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
W_PATH = ROOT / 'artifacts/20261112_eae_candidate/dfthcsos/submission.npz'
J, BROT, NPTS, NQ, NLOW = 5, 8, 2048, 128, 16


def mobius(x, axis=0):
    x = np.moveaxis(np.array(x, dtype=np.uint8), axis, 0).copy()
    n = x.shape[0]
    bit = 1
    while bit < n:
        idx = np.arange(n)[(np.arange(n) & bit) != 0]
        x[idx] ^= x[idx ^ bit]
        bit <<= 1
    return np.moveaxis(x, 0, axis)


def delta_of(W, k):
    cur = W[:, k * J:(k + 1) * J]
    prev = W[:, (k - 1) * J:k * J] if k else np.zeros_like(cur)
    return (cur ^ prev).astype(np.int64)


def anf_bits(delta):
    n = delta.shape[0]
    bits = np.zeros((NPTS, delta.shape[1] * BROT), np.uint8)
    for j in range(delta.shape[1]):
        for b in range(BROT):
            bits[:n, j * BROT + b] = (delta[:, j] >> b) & 1
    return bits


def anf_tensor(delta):
    A = mobius(anf_bits(delta), axis=0)
    M = np.zeros((A.shape[1], NLOW, NQ), np.uint8)
    for m in range(NPTS):
        M[:, m & 15, m >> 4] = A[m]
    return M


def rank15(rows):
    piv, rk = {}, 0
    for v in rows:
        while v:
            p = v.bit_length() - 1
            if p in piv:
                v ^= piv[p]
            else:
                piv[p] = v
                rk += 1
                break
    return rk


def rk(M):
    return rank15([int(sum(int(M[R, Q]) << (Q - 1) for Q in range(1, NQ))) for R in range(1, NLOW)])


def main():
    W = np.load(W_PATH)['angle_words']
    rng = np.random.default_rng(7)
    for k in (0, 4, 13):
        d = delta_of(W, k)
        M = anf_tensor(d)
        flat = [int(sum(int(M[o, R, Q]) << (R * NQ + Q) for R in range(NLOW) for Q in range(NQ)))
                for o in range(40)]
        # dim of the span of the 40 slices (full 16x128, over 2048 monomials)
        piv, rkdim = {}, 0
        for v in flat:
            while v:
                p = v.bit_length() - 1
                if p in piv:
                    v ^= piv[p]
                else:
                    piv[p] = v
                    rkdim += 1
                    break
        # dependence: which pairs are equal?
        eq = [(a, b) for a in range(40) for b in range(a + 1, 40) if flat[a] == flat[b]]
        # dense sampling: zeros and rank histogram
        from collections import Counter
        h, zeros = Counter(), 0
        for _ in range(20000):
            mask = int(rng.integers(1, 1 << 40))
            acc = np.zeros((NLOW, NQ), np.uint8)
            for o in range(40):
                if mask >> o & 1:
                    acc ^= M[o]
            if not acc.any():
                zeros += 1
            else:
                h[rk(acc)] += 1
        # LSB structure
        bt = anf_bits(d)
        w = [int(bt[:, o].sum()) for o in range(40)]
        deg = []
        for o in range(40):
            A = mobius(bt[:, o])
            supp = np.flatnonzero(A)
            deg.append(int(max((bin(int(m)).count('1') for m in supp), default=0)))
        print(f'k={k}: dim span(40 slices)={rkdim} equal-pairs={eq}')
        print(f'      combo ranks {dict(sorted(h.items()))} zeros {zeros}/20000'
              f'  (nonzero combos must all be 15 for constant rank)')
        print(f'      bit weights {min(w)}..{max(w)}  max ANF degree {sorted(set(deg))}')
        print(f'      weights of bit0-of-word outputs {[w[j * 8] for j in range(5)]}'
              f'  degrees {[deg[j * 8] for j in range(5)]}')


if __name__ == '__main__':
    main()
