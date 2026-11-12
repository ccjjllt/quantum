"""Decisive semantics test: is a Maoxin circuit a general XOR oracle |z> -> |z ^ f(a)>, or only
correct when z is the batch it was designed to follow (word bits used as basis functions)?

For a few addresses, simulate circuit k with z = 0, z = batch[k-1], z = batch[k] and z = all-127,
and count differing word bits from batch[k].
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

import kickmix as km

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0, str(ROOT / 'data/competition/verifiers'))
from dfthcsos.scoreinfra.circuits import load_circuits, register_layout  # noqa: E402

WORDS = ROOT / 'artifacts/20261112_eae_candidate/dfthcsos/submission.npz'


def words_after(circ, layout, addrs, z):
    """z: (len(addrs), J) ints. Returns (len(addrs), J) ints read from the word registers."""
    sim = km.Simulator(batch_size=len(addrs), debug_print=False, seed=1, counting_operations=True)
    sim.use_same_registers_as(circ)
    sim.write_across_shots(
        layout.selection,
        np.array([[(a >> i) & 1 for a in addrs] for i in range(len(layout.selection))], bool))
    for j, reg in enumerate(layout.words):
        sim.write_across_shots(
            reg, np.array([[(z[i, j] >> k) & 1 for k in range(layout.brot)] for i in range(len(addrs))], bool).T)
    sim.do(circ)
    out = np.zeros((len(addrs), layout.batch_size), np.int64)
    for j, reg in enumerate(layout.words):
        b = np.array(sim.read_across_shots(reg), bool)
        out[:, j] = (b.T.astype(np.int64) << np.arange(layout.brot)).sum(axis=1)
    return out


def main() -> None:
    fam = load_circuits(ROOT / 'artifacts/20261112_frontier/chem14840')
    layout = register_layout(fam)
    W = np.load(WORDS)['angle_words']
    J = layout.batch_size
    addrs = np.array([0, 1, 5, 16, 127, 128, 1000, 1219])
    for k in range(15):
        circ = fam[k]
        batch = W[:, k * J:(k + 1) * J]
        prev = W[:, (k - 1) * J:k * J] if k else np.zeros_like(batch)
        line = [f'k={k:2d}']
        for label, zrow in (('prev', prev), ('zero', np.zeros_like(batch)),
                            ('self', batch), ('ones', 255 * np.ones_like(batch))):
            got = words_after(circ, layout, addrs, zrow[addrs])
            diff = int((got ^ batch[addrs]).astype(bool).sum())
            line.append(f'{label}={diff:4d}')
        print('  '.join(line), flush=True)


if __name__ == '__main__':
    main()
