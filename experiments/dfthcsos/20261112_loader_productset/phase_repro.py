"""Reproduce the official ANGLE_k phase check *including the preloaded word register*.

The verifier runs circuit 0 with z=0, reads batch 0, then re-initialises the simulator and
writes batch 0 into the word registers before running circuit 1 (and so on).  A loader is a
XOR oracle |a>|z> -> |a>|z+delta[a]>, so z is an arbitrary input: any rewrite that is only
valid at z=0 breaks here.  This script replicates that sequence with kickmix and reports the
phase flag, so we can bisect substitutions.

Usage: python phase_repro.py <circuit_dir> [kmax]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import kickmix as km

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0, str(Path(__file__).parent))
from phase_bisect import N, SEL, WORD, WS, official_seed, simulate  # noqa: E402

SUB = ROOT / 'artifacts/20261113_chem_slim/submission.npz'


def run_family(d: Path, seed: int, kmax: int = 14):
    """Exact copy of recover_words_from_circuits' forward pass for k = 0..kmax."""
    from dfthcsos.scoreinfra.circuits import register_layout
    fam = [km.Circuit.from_file(d / f'angle_k_{k}.kmx', format='kmx')
           for k in range(kmax + 1)]
    layout = register_layout(fam)
    sim = km.Simulator(batch_size=N, debug_print=False, seed=seed, counting_operations=True)
    sim.use_same_registers_as(fam[0])
    addr = np.arange(N, dtype=np.int64)
    addrbits = ((addr[None, :] >> np.arange(11)[:, None]) & 1).astype(bool)
    sim.write_across_shots(km.array(SEL), addrbits)
    batches = []
    rows = []
    for k, c in enumerate(fam):
        sim.do(c)
        ph = sim.read_phase_flipped_across_shots().copy()
        sel_ok = np.array_equal(sim.read_across_shots(km.array(SEL)), addrbits)
        ws = sim.read_across_shots(km.array(WS))
        w = sim.read_across_shots(km.array(WORD)).copy()
        rows.append(dict(k=k, phase=int(np.count_nonzero(ph)), sel_ok=bool(sel_ok),
                         ws=int(np.count_nonzero(ws)),
                         toffoli=int(c.operation_statistics().num_toffoli_like)))
        batches.append(w)
        sim.clear_for_shot()
        sim.write_across_shots(km.array(SEL), addrbits)
        for j in range(5):
            bits = ((w[j * 8:(j + 1) * 8].T >> np.arange(8)[None, :]) & 1).astype(bool)
            sim.write_across_shots(km.array(WORD[j * 8:(j + 1) * 8]), bits.T)
    return rows


if __name__ == '__main__':
    d = Path(sys.argv[1])
    kmax = int(sys.argv[2]) if len(sys.argv) > 2 else 14
    seed = official_seed(d, SUB)
    print(f'{d.name}: official seed {seed}')
    rows = run_family(d, seed, kmax)
    for r in rows:
        flag = 'PHASE' if r['phase'] else 'ok'
        print(f'  k={r["k"]:2d} T={r["toffoli"]:4d} phase_flipped={r["phase"]:5d}'
              f' sel_ok={r["sel_ok"]} workspace_nonzero={r["ws"]}  {flag}')
