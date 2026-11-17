"""Strict occupancy model: when can a wire actually be released?

A target of any write gate is XOR-accumulated into the wire's old value, so the old
value is consumed (and its function leaks into the new one).  A wire can only be
handed to a *different* logical value for free when the write's pre-value is a known
constant 0/1 (then the write is an assignment up to a free X), or when the value is
dead and we clear it with the (free) HMR + conditional X sequence and the next write
is a fresh assignment.

This script reports the strict occupancy peak (lower bound on Q) and the release
points found by a {0,1,top} constant propagation on the ORIGINAL wire assignment.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from parse_kmx import parse  # noqa: E402


def main() -> None:
    ops, meta = parse('artifacts/20261117_deep_invsqrt/invsqrt_0af21cb8.kmx')
    nq = max(max(o.qubits) for o in ops if o.qubits) + 1
    n = len(ops)

    # constant propagation (same rules as peephole.const_prop)
    val: list[int | None] = [None] * nq
    pre_known: list[tuple[int, int, int | None]] = []  # (index, qubit, pre-value)
    depth = 0
    writes = ('X', 'CX', 'CCX', 'SWAP', 'HMR')
    for op in ops:
        if op.name == 'PUSH_CONDITION':
            depth += 1
            continue
        if op.name == 'POP_CONDITION':
            depth -= 1
            continue
        if depth > 0 and op.name in writes:
            for q in op.qubits:
                val[q] = None
            continue
        if op.name == 'X':
            q = op.qubits[0]
            pre_known.append((op.index, q, val[q]))
            val[q] = None if val[q] is None else 1 - val[q]
        elif op.name == 'CX':
            a, b = op.qubits
            pre_known.append((op.index, b, val[b]))
            val[b] = 1 - val[a] if (val[a] is not None and val[b] is not None) else None
        elif op.name == 'CCX':
            a, b, t = op.qubits
            pre_known.append((op.index, t, val[t]))
            val[t] = None
        elif op.name == 'HMR':
            pre_known.append((op.index, op.qubits[0], val[op.qubits[0]]))
            val[op.qubits[0]] = 0
        elif op.name == 'SWAP':
            a, b = op.qubits
            pre_known.append((op.index, a, None))
            pre_known.append((op.index, b, None))
            val[a] = val[b] = None

    # strict occupancy: [first write, last event]
    first: dict[int, int] = {}
    last: dict[int, int] = {}
    for op in ops:
        for q in op.qubits:
            first.setdefault(q, op.index)
            last[q] = op.index
    print('## strict occupancy (first event .. last event)')
    occ = []
    for q in range(nq):
        occ.append((first[q], last[q] + 1, q))
        print(f'  q{q:2d}: [{first[q]:5d}, {last[q]:5d}]  len={last[q]-first[q]+1}')
    delta = [0] * (n + 2)
    for a, b, _ in occ:
        delta[a] += 1
        delta[b] -= 1
    cur = 0
    peak = 0
    peak_at = -1
    for i in range(n):
        cur += delta[i]
        if cur > peak:
            peak, peak_at = cur, i
    print(f'\nstrict occupancy peak = {peak} at op {peak_at}')
    print('  (this is a lower bound on num_qubits for this gate sequence)')

    # release points: writes whose pre-value is a known constant
    known = [(i, q, v) for (i, q, v) in pre_known if v is not None]
    print(f'\nwrites with known constant pre-value (free relocation points): {len(known)}')
    per_q = {}
    for i, q, v in known:
        per_q.setdefault(q, []).append(i)
    for q in sorted(per_q):
        print(f'  q{q:2d}: {len(per_q[q]):4d} points, first {per_q[q][0]}, last {per_q[q][-1]}')
    print(f'\nlines with NO known-pre-value write anywhere: '
          f'{[q for q in range(nq) if q not in per_q]}')


if __name__ == '__main__':
    main()
