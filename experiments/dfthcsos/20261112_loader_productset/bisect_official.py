"""Bisect the phase failure through the official `evaluate_circuits` path.

For a chosen k it writes a family where only circuit k is replaced by a variant
(original / drop identically-zero CX only / drop identically-zero CCX only / both),
then runs the official verifier with `shots_per_address=1` and reports the phase flag
per ANGLE_k.

Usage: python bisect_official.py [k]
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import numpy as np

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
VER = ROOT / 'data/competition/verifiers'
sys.path.insert(0, str(VER))
sys.path.insert(0, str(VER / 'dfthcsos'))
sys.path.insert(0, str(Path(__file__).parent))

from loaderlib import KMXDIR  # noqa: E402
from phase_debug import classify  # noqa: E402

ORIG = KMXDIR
SUB = ROOT / 'artifacts/20261113_chem_slim/submission.npz'
TMP = Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/bisect_phases')


def make_dir(tag: str, k: int, variant: str) -> Path:
    d = TMP / tag
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    for j in range(15):
        src = ORIG / f'angle_k_{j}.kmx'
        if j != k:
            (d / src.name).write_text(src.read_text())
            continue
        lines = src.read_text().splitlines()
        header = [ln for ln in lines if ln.startswith(('APPEND_TO_REGISTER', 'REGISTER'))]
        gates = [ln for ln in lines if not ln.startswith(('APPEND_TO_REGISTER', 'REGISTER'))]
        cls = classify(lines)
        out = []
        for (op, zc, zx), ln in zip(cls, gates):
            if variant in ('cx', 'both') and op == 'CX' and zx:
                continue
            if variant in ('ccx', 'both') and op == 'CCX' and zc:
                continue
            out.append(ln)
        (d / src.name).write_text('\n'.join(header + out) + '\n')
    shutil.copy(SUB, d / 'submission.npz')
    return d


def run(d: Path):
    import dfthcsos.scoreinfra.circuits as C
    from dfthcsos.verify import evaluate_circuits, load_inputs, load_tree_edges
    seen = {}

    def patched(sim, circuit, layout, address_bits, label):
        ph = np.asarray(sim.read_phase_flipped_across_shots())
        seen[label] = (int(np.count_nonzero(ph)), np.flatnonzero(ph)[:6].tolist())
        return None      # do not raise: keep going so we see every circuit

    C._check_state = patched
    inputs = load_inputs(SUB)
    edges = load_tree_edges(None, d)
    fam = C.load_circuits(d, format='kmx')
    try:
        evaluate_circuits(inputs, fam, edges, shots_per_address=1)
    except Exception as exc:
        print(f'    (evaluate raised {type(exc).__name__}: {exc})')
    return seen


if __name__ == '__main__':
    k = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    for variant, tag in (('orig', 'orig'), ('cx', f'k{k}_dropZeroCX'),
                         ('ccx', f'k{k}_dropZeroCCX'), ('both', f'k{k}_both')):
        d = make_dir(tag, k, variant)
        seen = run(d)
        # the patched check never raises, so the words also get checked downstream; the
        # interesting number is the phase count for ANGLE_k
        print(f'{variant:5s}: ' + '  '.join(
            f'{lab}:{v[0]}' for lab, v in seen.items() if lab.startswith('ANGLE')))
