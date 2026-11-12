"""Rank profile of the 40 output functions under basis change.

Fixes the first pass: the interior 15x127 block is ranked as 15 rows of 127 bits, not one
1905-bit row.

Questions:
  1. which outputs are the low-rank ones (zero-padding artifact)?
  2. is rank constant on the 40-dim space V\\{0}?  (if yes, no invertible output basis B can
     change ANY per-output rank, so sum_o ceil(rank_o/2) is basis-invariant)
  3. does a random B change the profile?

Usage: python basis_rank.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
W_PATH = ROOT / 'artifacts/20261112_eae_candidate/dfthcsos/submission.npz'
J, BROT, NPTS, NQ, NLOW = 5, 8, 2048, 128, 16


def mobius(x: np.ndarray, axis: int = 0) -> np.ndarray:
    x = np.moveaxis(np.array(x, dtype=np.uint8), axis, 0).copy()
    n = x.shape[0]
    bit = 1
    while bit < n:
        idx = np.arange(n)[(np.arange(n) & bit) != 0]
        x[idx] ^= x[idx ^ bit]
        bit <<= 1
    return np.moveaxis(x, 0, axis)


def delta_of(W, k: int) -> np.ndarray:
    cur = W[:, k * J:(k + 1) * J]
    prev = W[:, (k - 1) * J:k * J] if k else np.zeros_like(cur)
    return (cur ^ prev).astype(np.int64)


def anf_tensor(delta: np.ndarray) -> np.ndarray:
    n = delta.shape[0]
    bits = np.zeros((NPTS, delta.shape[1] * BROT), np.uint8)
    for j in range(delta.shape[1]):
        for b in range(BROT):
            bits[:n, j * BROT + b] = (delta[:, j] >> b) & 1
    A = mobius(bits, axis=0)
    M = np.zeros((A.shape[1], NLOW, NQ), np.uint8)
    for m in range(NPTS):
        M[:, m & 15, m >> 4] = A[m]
    return M


def rank_slice(Mo: np.ndarray) -> int:
    """GF(2) rank of the interior 15x127 block of one output."""
    piv: dict[int, int] = {}
    rk = 0
    for R in range(1, NLOW):
        v = 0
        for Q in range(1, NQ):
            if Mo[R, Q]:
                v |= 1 << (Q - 1)
        while v:
            p = v.bit_length() - 1
            if p in piv:
                v ^= piv[p]
            else:
                piv[p] = v
                rk += 1
                break
    return rk


def rank_matrix(M: np.ndarray) -> int:
    """GF(2) rank of the interior block of a (16,128) tensor slice."""
    return rank_slice(M)


def main() -> None:
    W = np.load(W_PATH)['angle_words']
    rng = np.random.default_rng(1)
    print('k : rank histogram over the 40 slices | indices of rank<15 | random-B histogram'
          ' | rank hist over 2000 combos of V')
    for k in range(15):
        M = anf_tensor(delta_of(W, k))
        ri = [rank_matrix(M[o]) for o in range(40)]
        low = [o for o in range(40) if ri[o] < 15]
        # random basis: B invertible over GF(2)
        while True:
            B = rng.integers(0, 2, (40, 40)).astype(np.uint8)
            # rank of B
            piv = {}
            ok = True
            rows = []
            for o in range(40):
                v = int(sum(int(B[o, c]) << c for c in range(40)))
                rows.append(v)
            r = 0
            piv = {}
            for v in rows:
                while v:
                    p = v.bit_length() - 1
                    if p in piv:
                        v ^= piv[p]
                    else:
                        piv[p] = v
                        r += 1
                        break
            if r == 40:
                break
        # g_o = XOR of f_c over B[o,c]=1 ; do it on the ANF tensor
        G = np.zeros_like(M)
        for o in range(40):
            for c in range(40):
                if B[o, c]:
                    G[o] ^= M[c]
        rg = [rank_matrix(G[o]) for o in range(40)]
        # random combos of V (as matrices)
        rnd = []
        for _ in range(2000):
            mask = int(rng.integers(1, 1 << 40))
            acc = np.zeros((NLOW, NQ), np.uint8)
            for o in range(40):
                if mask >> o & 1:
                    acc ^= M[o]
            if acc.any():
                rnd.append(rank_matrix(acc))
        from collections import Counter
        h = Counter(ri)
        hg = Counter(rg)
        hr = Counter(rnd)
        print(f'k={k:2d}: id {dict(sorted(h.items()))} low{low}'
              f' | B {dict(sorted(hg.items()))}'
              f' | combos {dict(sorted(hr.items()))}'
              f' | sum ceil/2 id {sum((r + 1) // 2 for r in ri)} B {sum((r + 1) // 2 for r in rg)}')
    print()
    print('If "combos" contains only 15 (and 16 is impossible on a 15x127 block), then rank is')
    print('constant on V\\{0} and every invertible B has the identical rank profile.')


if __name__ == '__main__':
    main()
