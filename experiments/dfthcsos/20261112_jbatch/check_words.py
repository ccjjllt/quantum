"""Local structural check: recover the words of a candidate family at 1 shot per address.

Not official verification (that is `scripts/manual_verify.py` with full shot counts); this only
confirms the family loads the intended 1220x75 table and reports its Toffoli count per pass.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0, str(ROOT / 'data/competition/verifiers'))

from dfthcsos.scoreinfra.circuits import load_circuits, recover_words_from_circuits  # noqa: E402

WORDS = ROOT / 'artifacts/20261112_eae_candidate/dfthcsos/submission.npz'


def main() -> None:
    want = np.load(WORDS, allow_pickle=False)['angle_words']
    for d in sys.argv[1:]:
        fam = load_circuits(Path(d))
        got, layout, toff = recover_words_from_circuits(
            fam, num_vectors=1220, num_angles=75, shots_per_address=1, seed=0)
        print(f'{d}: circuits={len(fam)} brot={layout.brot} J={layout.batch_size} '
              f'toffoli_per_pass={toff / 2:g} qmax={max(c.num_qubits for c in fam)} '
              f'words_equal={np.array_equal(got, want)}', flush=True)


if __name__ == '__main__':
    main()
