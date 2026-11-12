"""Rows-scaling proxy: build the local tensorqrom8 loader on row-truncated versions of the current
1220x75 table (rows >= N are dropped, not replaced by a real R=5/R=6 table).

This is a proxy for how this constructor's cost scales with the number of addresses: it keeps the
same 75 word columns, so lambda_eff/heuristic costs do not apply -- only T/pass and Q are reported.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
WT = ROOT / '.worktree/dfthcsos'
HERE = WT / 'experiments/dfthcsos/20261112_loader_re'
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'artifacts/20261112_chem_pipeline/dfthc_refit'))

import tensorqrom8 as tq  # noqa: E402

OUT = WT / 'artifacts/20261112_loader_re/rows'
SUB = ROOT / 'artifacts/20261112_eae_candidate/dfthcsos/submission.npz'


def main() -> None:
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 791
    lowbits = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    trials = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    words = np.load(SUB)['angle_words'][:N]
    t0 = time.time()
    fam = tq.build_family(words, brot=8, j=5, lowbits=lowbits, trials=trials, jobs=10, full=True)
    T = sum(int(c.operation_statistics().num_toffoli_like) for c in fam)
    per = [int(c.operation_statistics().num_toffoli_like) for c in fam]
    qmax = max(int(c.num_qubits) for c in fam)
    d = OUT / f'N{N}_l{lowbits}_t{trials}'
    d.mkdir(parents=True, exist_ok=True)
    for k, c in enumerate(fam):
        c.to_file(str(d / f'angle_k_{k}.kmb'), format='kmb')
    np.savez(d / 'submission.npz', angle_words=words)
    print(json.dumps({'N': N, 'lowbits': lowbits, 'trials': trials, 'T_pass': T, 'per': per,
                      'qmax': qmax, 'sec': round(time.time() - t0, 1)}))


if __name__ == '__main__':
    main()
