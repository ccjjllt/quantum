"""Def-use liveness of the 44Q invsqrt circuit (static; no simulation).

A qubit write ('def') is: X, CX target, CCX target, SWAP (both), NEG, HMR (destroys +
resets).  A read ('use') is: CX control, CCX controls, CZ/CCZ operands, SWAP, HMR operand,
Z_POW? no (Z_POW is a phase on a basis state; it does not consume the value for later
computation, so it neither defines nor kills).

Reports, per scratch line, the merged live intervals and then the pairs of lines whose
interval sets are disjoint (candidates for a free qubit merge).
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from parse_kmx import parse  # noqa: E402

KMX = pathlib.Path('artifacts/20261117_deep_invsqrt/invsqrt_0af21cb8.kmx')


def defs_uses(op):
    n = op.name
    q = op.qubits
    if n == 'X':
        return (q[0],), ()
    if n in ('CX',):
        return (q[1],), (q[0],)
    if n in ('CZ',):
        return (), q
    if n in ('CCX',):
        return (q[2],), (q[0], q[1])
    if n in ('CCZ',):
        return (), q
    if n == 'SWAP':
        return q, q
    if n == 'HMR':
        return (q[0],), (q[0],)
    if n in ('Z', 'Z_POW'):
        return (), ()
    if n == 'NEG':
        return (), ()
    return (), ()


def main() -> None:
    ops, meta = parse(KMX)
    nq = max(max(o.qubits) for o in ops if o.qubits) + 1
    x_reg = meta['registers']['r0']
    scratch = [q for q in range(nq) if q not in x_reg]

    # collect per-qubit event list: (index, 'def'|'use')
    events: dict[int, list[tuple[int, str]]] = {q: [] for q in range(nq)}
    for op in ops:
        d, u = defs_uses(op)
        for q in d:
            events[q].append((op.index, 'def'))
        for q in u:
            if q in d and op.name != 'SWAP':
                continue  # HMR: def+use at same index, count as def only
            events[q].append((op.index, 'use'))

    intervals: dict[int, list[tuple[int, int]]] = {}
    for q in range(nq):
        iv: list[tuple[int, int]] = []
        cur_def = 0  # qubits start at |0>; first def is not needed to "start" liveness
        pending: int | None = 0
        last_use: int | None = None
        for index, kind in events[q]:
            if kind == 'def':
                if last_use is not None:
                    iv.append((pending, last_use))
                pending = index
                last_use = None
            else:
                last_use = index
        if last_use is not None:
            iv.append((pending, last_use))
        # merge overlapping / adjacent
        merged: list[list[int]] = []
        for a, b in iv:
            if merged and a <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], b)
            else:
                merged.append([a, b])
        intervals[q] = [(a, b) for a, b in merged]

    print('## merged live intervals per scratch line')
    for q in scratch:
        total = sum(b - a for a, b in intervals[q])
        print(f'q{q}: n={len(intervals[q]):3d} live_ops={total:6d} hull='
              f'[{min(a for a,_ in intervals[q])},{max(b for _,b in intervals[q])}]')
        print(f'     {intervals[q]}')

    # peak concurrency
    pts: list[tuple[int, int]] = []
    for q in range(nq):
        for a, b in intervals[q]:
            pts.append((a, 1))
            pts.append((b + 1, -1))
    pts.sort()
    peak, cur = 0, 0
    for _, d in pts:
        cur += d
        peak = max(peak, cur)
    print(f'\npeak simultaneous live qubits (all 44 wires): {peak}')

    # disjoint pairs among scratch
    print('\n## scratch pairs with disjoint live intervals (free merge candidates)')
    found = 0
    for i, a in enumerate(scratch):
        for b in scratch[i + 1:]:
            ok = True
            for (a1, a2) in intervals[a]:
                for (b1, b2) in intervals[b]:
                    if not (a2 < b1 or b2 < a1):
                        ok = False
                        break
                if not ok:
                    break
            if ok:
                found += 1
                print(f'  q{a} <-> q{b} disjoint')
    print(f'disjoint scratch pairs: {found}')

    # also check x-vs-scratch disjointness (scratch could hide in a dead x window?)
    print('\n## scratch lines fully inside one x-line live gap (x recycled as scratch)')
    n_found = 0
    for q in scratch:
        for a in x_reg:
            ok = all(any(e < s or e > t for s, t in intervals[a]) for e, _ in [(p, 0) for p, _ in intervals[q]] for _ in [0])
            # simpler: check every scratch interval avoids all x intervals
            ok = True
            for (s, t) in intervals[q]:
                for (xs, xt) in intervals[a]:
                    if not (t < xs or xt < s):
                        ok = False
                        break
                if not ok:
                    break
            if ok:
                n_found += 1
                print(f'  q{q} disjoint from x line q{a}')
    print(f'x/scratch disjoint: {n_found}')


if __name__ == '__main__':
    main()
