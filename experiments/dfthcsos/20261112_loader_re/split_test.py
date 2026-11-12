"""Test the hypothesis that Maoxin's tensor split is ``low = address bits 4..10, high = bits 0..3``
(the transpose of tensorqrom8's convention: the cached monomials live on the *slow* bits).

For each circuit: full 2048-point ANF of the 40 delta bits, reshaped as C[low_mono(128), high_mono(16),
output(40)]; report the used monomial supports, per-output rank and the paired product count, and the
cache cost of the needed monomials. Compare with the .kmx counts (cache 70-80, products 190-212).
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0, str(ROOT / 'artifacts/20261112_chem_pipeline/dfthc_refit'))
sys.path.insert(0, str(ROOT / '.worktree/dfthcsos/experiments/dfthcsos/20261112_loader_re'))

import tensorqrom8 as tq  # noqa: E402

W = np.load(ROOT / 'artifacts/20261112_eae_candidate/dfthcsos/submission.npz')['angle_words']
J = 5


def delta_of(k):
    cur = W[:, k * J:(k + 1) * J]
    prev = W[:, (k - 1) * J:k * J] if k else np.zeros_like(cur)
    return (cur ^ prev).astype(np.int64)


def tensor(delta, split):
    """C[low_mono, high_mono, out]; split = the first low bit (low bits are `split`..10)."""
    N, Jw = delta.shape
    bits = np.zeros((2048, Jw * 8), np.uint8)
    for j in range(Jw):
        for kk in range(8):
            bits[:N, j * 8 + kk] = (delta[:, j] >> kk) & 1
    A = tq.mobius(bits, axis=0)                # (2048, J*8) ANF over 11 bits
    L = 1 << (11 - split)
    H = 1 << split
    # monomial m < 2048 splits as m = hi * H + lo with hi < L covering bits split..10
    C = np.zeros((L, H, Jw * 8), np.uint8)
    for m in range(2048):
        C[m >> split, m & (H - 1)] = A[m]
    return C


def report(C, tag):
    L, H, O = C.shape
    low_used = C[1:, :, :].any(axis=(1, 2))
    n_low = int(low_used.sum())
    singles = int(sum(1 for m in np.flatnonzero(low_used) + 1 if m & (m - 1) == 0))
    hi_used = C[:, 1:, :].any(axis=(0, 2))
    n_hi = int(hi_used.sum())
    hi_singles = int(sum(1 for m in np.flatnonzero(hi_used) + 1 if m & (m - 1) == 0))
    hi_nonconst = int(hi_used.sum())
    ranks = []
    for o in range(O):
        X = C[1:, 1:, o]
        r, _ = tq.rank_factor([int(sum(int(v) << i for i, v in enumerate(X[m]))) for m in range(L - 1)])
        ranks.append(len(r))
    pairs = sum((r + 1) // 2 for r in ranks)
    print(f'{tag}: L={L} H={H} O={O} | low mono used {n_low} (ANDs {n_low - singles})'
          f' | high mono used {n_hi} (ANDs {max(0, n_hi - hi_singles)})'
          f' | ranks {sorted(ranks, reverse=True)[:5]}.. total {sum(ranks)} -> paired {pairs}'
          f' | T = {n_low - singles + max(0, n_hi - hi_singles) + pairs}')


def main() -> None:
    print('=== Maoxin split: low = bits 4..10 (slow), high = bits 0..3 (fast) ===')
    tot = 0
    for k in range(15):
        C = tensor(delta_of(k), split=4)
        print(f'k={k:2d}', end=' ')
        report(C, '')
        tot += _t(C)
    print('TOTAL', tot, '(Maoxin 4089)')
    print()
    print('=== tensorqrom8 split: low = bits 0..3 (fast), high = bits 4..10 ===')
    for k in (0, 4, 14):
        C = tensor(delta_of(k), split=7)
        report(C, f'k={k}')


def _t(C):
    L, H, O = C.shape
    low_used = C[1:, :, :].any(axis=(1, 2))
    singles = int(sum(1 for m in np.flatnonzero(low_used) + 1 if m & (m - 1) == 0))
    hi_used = C[:, 1:, :].any(axis=(0, 2))
    hi_singles = int(sum(1 for m in np.flatnonzero(hi_used) + 1 if m & (m - 1) == 0))
    ranks = []
    for o in range(O):
        X = C[1:, 1:, o]
        r, _ = tq.rank_factor([int(sum(int(v) << i for i, v in enumerate(X[m]))) for m in range(L - 1)])
        ranks.append(len(r))
    return (int(low_used.sum()) - singles + max(0, int(hi_used.sum()) - hi_singles)
            + sum((r + 1) // 2 for r in ranks))


if __name__ == '__main__':
    main()
