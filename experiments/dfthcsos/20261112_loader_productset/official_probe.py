"""Instrument the official verifier: patch `_check_state` to report the phase flag, then run
`evaluate_circuits(..., shots_per_address=1)` so we see exactly which circuit/address fails.

Usage: python official_probe.py <circuit_dir> [kmax]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
VER = ROOT / 'data/competition/verifiers'
sys.path.insert(0, str(VER))
sys.path.insert(0, str(VER / 'dfthcsos'))


def main() -> None:
    d = Path(sys.argv[1])
    import dfthcsos.scoreinfra.circuits as C
    from dfthcsos.verify import evaluate_circuits, load_inputs, load_tree_edges

    orig = C._check_state
    state = {'cur': None}

    def patched(sim, circuit, layout, address_bits, label):
        ph = np.asarray(sim.read_phase_flipped_across_shots())
        n = int(np.count_nonzero(ph))
        first = np.flatnonzero(ph)[:8].tolist()
        print(f'  {label:18s} phase_flipped={n:5d} first={first}')
        return orig(sim, circuit, layout, address_bits, label)

    C._check_state = patched
    inputs = load_inputs(ROOT / 'artifacts/20261113_chem_slim/submission.npz')
    edges = load_tree_edges(None, d)
    family = C.load_circuits(d, format='kmx')
    print(f'{len(family)} circuits; layout.words = {[str(w) for w in C.register_layout(family).words]}')
    try:
        r = evaluate_circuits(inputs, family, edges, shots_per_address=1)
        print(f'PASS  score={r["score"]:.2f}  toffoli={r["resources"]["toffoli"]}')
    except Exception as exc:
        print(f'REJECTED: {type(exc).__name__}: {exc}')


if __name__ == '__main__':
    main()
