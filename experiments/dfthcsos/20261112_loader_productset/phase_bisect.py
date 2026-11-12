"""Bisect the measurement-kickback phase at the *official* simulator seed.

The verifier's seed is `initial_seed(submission_sha256(circuits, ...))`, i.e. it depends on
the circuit files themselves, so a phase defect only shows up for some seeds.  This script
computes the official seed for a circuit directory and then runs the exact `_check_state`
phase test per circuit, so we can bisect which rewrite introduces the nondeterminism.

Usage: python phase_bisect.py <circuit_dir> [k]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import kickmix as km

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
VER = ROOT / 'data/competition/verifiers'
sys.path.insert(0, str(VER))
sys.path.insert(0, str(VER / 'dfthcsos'))
sys.path.insert(0, str(Path(__file__).parent))

from loaderlib import KMXDIR, REAL  # noqa: E402

N = 1220
SEL = [km.q(i) for i in range(11)]
WORD = [km.q(i) for i in range(11, 51)]
WS = [km.q(i) for i in range(51, 128)]


def official_seed(circuit_dir: Path, submission: Path) -> int:
    from dfthcsos.scoreinfra.circuits import (initial_seed, load_circuits,
                                              submission_sha256)
    from dfthcsos.verify import load_inputs, load_tree_edges
    inputs = load_inputs(submission)
    edges = load_tree_edges(None, circuit_dir)
    family = load_circuits(circuit_dir, format='kmx')
    digest = submission_sha256(family, inputs.factorization_file or inputs.params, edges)
    base = initial_seed(digest, '')
    return int.from_bytes(
        np.random.SeedSequence(base, pool_size=8).generate_state(4, dtype=np.uint64),
        'little')


def simulate(circ, seed):
    sim = km.Simulator(batch_size=N, debug_print=False, seed=seed, counting_operations=True)
    sim.use_same_registers_as(circ)
    addr = np.arange(N, dtype=np.int64)
    sim.write_across_shots(km.array(SEL),
                           ((addr[None, :] >> np.arange(11)[:, None]) & 1).astype(bool))
    sim.do(circ)
    return dict(phase=sim.read_phase_flipped_across_shots().copy(),
                word=sim.read_across_shots(km.array(WORD)).copy(),
                ws=sim.read_across_shots(km.array(WS)).copy(),
                toffoli=circ.operation_statistics().num_toffoli_like)


def tmp(lines, tag):
    p = Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T') / f'pb_{tag}.kmx'
    p.write_text('\n'.join(lines) + '\n')
    return str(p)


if __name__ == '__main__':
    d = Path(sys.argv[1])
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    sub = ROOT / 'artifacts/20261113_chem_slim/submission.npz'
    seed = official_seed(d, sub)
    print(f'official sim seed for {d.name} = {seed}')
    c = km.Circuit.from_file(d / f'angle_k_{k}.kmx', format='kmx')
    r = simulate(c, seed)
    bad = np.flatnonzero(r['phase'])
    print(f'k={k}: phase_flipped={len(bad)}/{N}  first={bad[:8].tolist()}')
