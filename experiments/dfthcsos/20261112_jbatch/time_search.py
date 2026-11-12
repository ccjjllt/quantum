"""Time the decomposition search for one circuit at (J, lowbits, sizes, trials)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0, str(ROOT / 'data/competition/verifiers'))
sys.path.insert(0, str(ROOT / 'artifacts/20261112_chem_pipeline/dfthc_refit'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import tensorqrom8 as tq  # noqa: E402
from fourqrom import batch_deltas  # noqa: E402

W = np.load(ROOT / 'artifacts/20261112_eae_candidate/dfthcsos/submission.npz',
            allow_pickle=False)['angle_words']


def main() -> None:
    J = int(sys.argv[1])
    lowbits = int(sys.argv[2])
    trials = int(sys.argv[3])
    ks = [int(x) for x in sys.argv[4].split(',')]
    for sizes in ([6] * (J * 8 // 6) + ([J * 8 % 6] if J * 8 % 6 else []),
                  [4] * (J * 8 // 4),
                  [8] * (J * 8 // 8)):
        for k in ks:
            d = list(batch_deltas(W, J))[k]
            t0 = time.time()
            C = tq.anf_tensor(d, 8, lowbits, full=True)
            terms = tq.shared(C, list(sizes), trials=trials, seed=k)
            ok = np.array_equal(tq.mixed_of(terms, C.shape[0] - 1, C.shape[1] - 1, C.shape[2]), C[1:, 1:])
            print(f'J{J} l{lowbits} sizes{sizes} k{k} trials{trials} nterms{len(terms)} '
                  f'cover{ok} {time.time() - t0:.1f}s', flush=True)


if __name__ == '__main__':
    main()
