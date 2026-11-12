"""Decomposition-only probe: product count of ``shared`` for candidate output groupings on one
circuit (no circuit build, no verification). Tests whether wider output groups (more fanout/sharing)
approach Maoxin's 4.8 products per output at lowbits=4.

Local reference: sizes (7,6,6,6,5,5) -> 263 products for k=4 (measured from the built family).
Maoxin k=4: 193 products, 70 cache ANDs.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
HERE = ROOT / '.worktree/dfthcsos/experiments/dfthcsos/20261112_loader_re'
sys.path.insert(0, str(ROOT / 'artifacts/20261112_chem_pipeline/dfthc_refit'))
sys.path.insert(0, str(HERE))

import tensorqrom8 as tq  # noqa: E402

W = np.load(ROOT / 'artifacts/20261112_eae_candidate/dfthcsos/submission.npz')['angle_words']
J = 5


def delta_of(k):
    cur = W[:, k * J:(k + 1) * J]
    prev = W[:, (k - 1) * J:k * J] if k else np.zeros_like(cur)
    return (cur ^ prev).astype(np.int64)


def main() -> None:
    k = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    trials = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    C = tq.anf_tensor(delta_of(k), 8, 4, full=True)
    print(f'k={k}: C shape {C.shape}', flush=True)
    plans = [[40], [20, 20], [14, 13, 13], [10, 10, 10, 10], [8, 8, 8, 8, 8],
             [7, 6, 6, 6, 5, 5], [6] * 6 + [4]]
    for sizes in plans:
        t0 = time.time()
        terms = tq.shared(C, list(sizes), trials=trials, seed=0)
        print(f'  sizes {sizes}: products {len(terms)}  ({time.time() - t0:.1f}s)', flush=True)


if __name__ == '__main__':
    main()
