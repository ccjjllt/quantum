"""Audit the claimed invsqrt prefix resynthesis target.

The previous report treated ops 0..8545 as one 193-CCX normaliser and proposed
193 -> ~110 CCX (-83 C).  This script splits the segment by op range and tests
whether the 167-CCX block at 650..7030 is affine/quadratic (i.e. replaceable by
CX gates) or genuinely nonlinear arithmetic.
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'experiments/invsqrt/20261112_newfamily_census/scripts'))
from kmx_parse import load_ops  # noqa: E402

import kickmix as km  # noqa: E402

BASE = ROOT / 'artifacts/20261112_newfamily_census/invsqrt.kmb'
ops, nq, regs = load_ops(BASE)

ranges = [(0, 650), (650, 7031), (7031, 8546)]
counts = {}
for a, b in ranges:
    sub = [o for o in ops if a <= o.index < b]
    counts[f'{a}:{b}'] = {
        'CCX': sum(o.kind == 'CCX' for o in sub),
        'CSWAP': sum(o.kind == 'CSWAP' for o in sub),
        'HMR': sum(o.kind == 'HMR' for o in sub),
    }
print('range counts', json.dumps(counts, indent=2))

# Extract the 650..7030 block as a standalone classical circuit.
c = km.Circuit.from_file(str(BASE), format='auto')
buf = io.StringIO(); c.to_file(buf, format='kmx'); lines = buf.getvalue().splitlines()
flat = []
for i, line in enumerate(lines):
    h = line.split()[0] if line else ''
    if h in ('APPEND_TO_REGISTER', 'REGISTER'):
        continue
    flat.append(i)
block = km.Circuit.from_file(
    io.StringIO('\n'.join(lines[flat[650]:flat[7030] + 1]) + '\n'), format='kmx')
regs_all = km.array([km.q(i) for i in range(62)])

def run(states: np.ndarray) -> np.ndarray:
    bits = ((states[None, :] >> np.arange(62, dtype=np.uint64)[:, None]) & 1) == 1
    sim = km.Simulator(batch_size=len(states), debug_print=False,
                       counting_operations=True, seed=1)
    sim.clear_for_shot(); sim.write_across_shots(regs_all, bits); sim.do(block)
    out = sim.read_across_shots(regs_all)
    vals = np.zeros(len(states), dtype=np.uint64)
    for i in range(62):
        vals |= out[i].astype(np.uint64) << np.uint64(i)
    return vals

rng = np.random.default_rng(2)
deriv = {}
for deg in (2, 3, 4, 5, 6):
    n = 16
    xs = [rng.integers(0, 1 << 62, size=n, dtype=np.uint64) for _ in range(deg)]
    acc = np.zeros(n, dtype=np.uint64)
    for mask in range(1 << deg):
        v = np.zeros(n, dtype=np.uint64)
        for j in range(deg):
            if (mask >> j) & 1:
                v ^= xs[j]
        val = run(v)
        if bin(mask).count('1') % 2 == 0:
            acc ^= val
    deriv[deg] = {'nonzero': int(np.count_nonzero(acc)), 'samples': n}
    print('degree', deg, deriv[deg])

(HERE / 'audit.json').write_text(json.dumps({'ranges': counts, 'derivatives': deriv}, indent=2))
print('DONE')
