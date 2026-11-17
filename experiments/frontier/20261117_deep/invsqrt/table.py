"""Compact per-wire table for the RESULT write-up."""

from __future__ import annotations

import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from parse_kmx import parse  # noqa: E402

ops, meta = parse('artifacts/20261117_deep_invsqrt/invsqrt_0af21cb8.kmx')
nq = 44
x_reg = meta['registers']['r0']

TGT1 = {'X', 'Z', 'NEG', 'HMR', 'Z_POW', 'R'}
rows = []
for q in range(nq):
    t = collections.Counter()
    c = collections.Counter()
    first = last = None
    nops = 0
    for op in ops:
        if q not in op.qubits:
            continue
        nops += 1
        first = op.index if first is None else first
        last = op.index
        n = op.name
        if n in ('CZ', 'CCZ'):
            c[n] += 1
            continue
        if n == 'SWAP':
            t['SWAP'] += 1
            continue
        tgt = (op.qubits[-1] if n in ('CX', 'CCX') else op.qubits[0])
        if q == tgt:
            t[n] += 1
        else:
            c[n] += 1
    rows.append((q, first, last, nops, dict(t), dict(c)))

print('q  kind     first  last  nops  ccxW hmrW  | target ops                       | '
      'control ops')
for q, first, last, nops, t, c in rows:
    kind = 'x' if q in x_reg else 'scratch'
    print(f'{q:2d} {kind:8s} {first:5d} {last:5d} {nops:5d} {t.get("CCX",0):5d} {t.get("HMR",0):4d} | '
          f'{str(t):33s} | {str(c)}')

print()
tot_ccx = sum(1 for o in ops if o.name == 'CCX')
tot_hmr = sum(1 for o in ops if o.name == 'HMR')
print('CCX', tot_ccx, 'CCZ', sum(1 for o in ops if o.name == 'CCZ'),
      'HMR', tot_hmr)
print('scratch CCX-target writes total',
      sum(rows[q][4].get('CCX', 0) for q in range(22, nq)))
print('x-register CCX-target writes total',
      sum(rows[q][4].get('CCX', 0) for q in range(22)))
