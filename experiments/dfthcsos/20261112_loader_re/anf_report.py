"""ANF structure of the real 1220x75 table, per 5-word circuit.

Questions answered:
  * union of ANF monomials (over the 11 address bits) of the 40 delta bit functions -> how many
    monomials of degree >= 2 must a cache hold?
  * for lowbits=7: per-output mixed-matrix ranks -> ``per_output`` pairing cost
  * the 35-output variant (bit 7 replaced by d7 ^ d6, the top-bit trick)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0, str(ROOT / 'artifacts/20261112_chem_pipeline/dfthc_refit'))
HERE = ROOT / '.worktree/dfthcsos/experiments/dfthcsos/20261112_loader_re'
sys.path.insert(0, str(HERE))

import tensorqrom8 as tq  # noqa: E402

W = np.load(ROOT / 'artifacts/20261112_eae_candidate/dfthcsos/submission.npz')['angle_words']
J, BROT, N = 5, 8, 1220


def delta_of(k: int) -> np.ndarray:
    cur = W[:, k * J:(k + 1) * J]
    prev = W[:, (k - 1) * J:k * J] if k else np.zeros_like(cur)
    return (cur ^ prev).astype(np.int64)


def trick(delta: np.ndarray) -> np.ndarray:
    """7 output bits per word: bits 0..5 as-is, bit 6 := d7 ^ d6."""
    out = delta.copy()
    for j in range(out.shape[1]):
        out[:, j] = (out[:, j] & 0x7F) | ((((delta[:, j] >> 7) ^ (delta[:, j] >> 6)) & 1) << 6)
        out[:, j] &= 0x7F
    return out


def bits_of(delta: np.ndarray, nb: int) -> np.ndarray:
    """(N, J*nb) truth table bits, output o = j*nb + k = bit k of word j."""
    out = np.zeros((N, delta.shape[1] * nb), np.uint8)
    for j in range(delta.shape[1]):
        for k in range(nb):
            out[:, j * nb + k] = (delta[:, j] >> k) & 1
    return out


def anf_support(delta: np.ndarray, nb: int) -> dict:
    b = bits_of(delta, nb)
    pad = np.zeros((2048 - N, b.shape[1]), np.uint8)
    A = tq.mobius(np.vstack([b, pad]), axis=0)   # (2048, J*nb) ANF coefficients
    support = A.any(axis=1)
    deg = {int(m): bin(m).count('1') for m in np.flatnonzero(support)}
    from collections import Counter
    return {'n_mono': int(support.sum()), 'by_degree': dict(sorted(Counter(deg.values()).items())),
            'n_nonconst': int(support[1:].sum())}


def report(delta, brot, lowbits, tag):
    C = tq.anf_tensor(delta, brot, lowbits, full=True)
    L, H, O = C.shape
    used = C[1:, :, :].any(axis=(1, 2))
    low_used = int(used.sum())
    singles = int(sum(1 for m in np.flatnonzero(used) + 1 if m & (m - 1) == 0))
    high_used = int(C[:, 1:, :].any(axis=(0, 2)).sum())
    high_singles = int(sum(1 for m in range(1, H) if m & (m - 1) == 0))
    ranks = []
    for o in range(O):
        X = C[1:, 1:, o]
        r, _ = tq.rank_factor([int(sum(int(v) << i for i, v in enumerate(X[m]))) for m in range(L - 1)])
        ranks.append(len(r))
    pairs = sum((r + 1) // 2 for r in ranks)
    cache = (low_used - singles) + (high_used - high_singles)
    print(f'  {tag} lowbits={lowbits}: low mono {low_used} (ANDs {low_used - singles})'
          f' high mono {high_used} (ANDs {high_used - high_singles})'
          f' | ranks sum {sum(ranks)} max {max(ranks)} -> paired products {pairs}'
          f' | T/pass {cache + pairs}')


def main() -> None:
    for k in (0, 4, 14):
        d = delta_of(k)
        print(f'--- k={k} ---')
        print('  ANF 40-bit:', anf_support(d, 8))
        print('  ANF 35-bit trick:', anf_support(trick(d), 7))
        report(d, 8, 7, 'full40')
        report(trick(d), 7, 7, 'trick35')
    for lo in (6, 7):
        tot = 0
        print(f'--- all 15 circuits, trick35, lowbits={lo} ---')
        for k in range(15):
            d = trick(delta_of(k))
            C = tq.anf_tensor(d, 7, lo, full=True)
            L, H, O = C.shape
            used = C[1:, :, :].any(axis=(1, 2))
            singles = int(sum(1 for m in np.flatnonzero(used) + 1 if m & (m - 1) == 0))
            high_used = int(C[:, 1:, :].any(axis=(0, 2)).sum())
            hs = int(sum(1 for m in range(1, H) if m & (m - 1) == 0))
            ranks = []
            for o in range(O):
                X = C[1:, 1:, o]
                r, _ = tq.rank_factor([int(sum(int(v) << i for i, v in enumerate(X[m]))) for m in range(L - 1)])
                ranks.append(len(r))
            pairs = sum((r + 1) // 2 for r in ranks)
            cache = (int(used.sum()) - singles) + (high_used - hs)
            tot += cache + pairs
            print(f'  k={k:2d}: cache {cache} + products {pairs} = {cache + pairs}')
        print(f'  TOTAL {tot}  (Maoxin 4089)')


if __name__ == '__main__':
    main()
