"""Concurrency profile + peak-window inventory for 0af21cb8 (static)."""

from __future__ import annotations

import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from parse_kmx import parse  # noqa: E402
from liveness import defs_uses  # noqa: E402

KMX = pathlib.Path('artifacts/20261117_deep_invsqrt/invsqrt_0af21cb8.kmx')


def compute_intervals(ops, nq):
    events: dict[int, list[tuple[int, str]]] = {q: [] for q in range(nq)}
    for op in ops:
        d, u = defs_uses(op)
        for q in d:
            events[q].append((op.index, 'def'))
        for q in u:
            if q in d and op.name != 'SWAP':
                continue
            events[q].append((op.index, 'use'))
    intervals: dict[int, list[tuple[int, int, str]]] = {}
    for q in range(nq):
        iv: list[tuple[int, int, str]] = []
        pending = 0
        defop = 'init'
        last_use = None
        for index, kind in events[q]:
            if kind == 'def':
                if last_use is not None:
                    iv.append((pending, last_use, defop))
                pending = index
                last_use = None
                defop = ops[index].name
            else:
                last_use = index
        if last_use is not None:
            iv.append((pending, last_use, defop))
        merged: list[list] = []
        for a, b, k in iv:
            if merged and a <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], b)
            else:
                merged.append([a, b, k])
        intervals[q] = [(a, b, k) for a, b, k in merged]
    return intervals


def main() -> None:
    ops, meta = parse(KMX)
    nq = max(max(o.qubits) for o in ops if o.qubits) + 1
    intervals = compute_intervals(ops, nq)
    n = len(ops)

    delta = [0] * (n + 2)
    for q, ivs in intervals.items():
        for a, b, _ in ivs:
            delta[a] += 1
            delta[b + 1] -= 1
    conc = [0] * n
    cur = 0
    for i in range(n):
        cur += delta[i]
        conc[i] = cur
    peak = max(conc)
    print(f'peak concurrency = {peak}')
    hist = collections.Counter(conc)
    for k in sorted(hist, reverse=True):
        print(f'  concurrency {k}: {hist[k]} op positions')

    # peak windows
    wins = []
    i = 0
    while i < n:
        if conc[i] == peak:
            j = i
            while j + 1 < n and conc[j + 1] == peak:
                j += 1
            wins.append((i, j))
            i = j + 1
        else:
            i += 1
    print(f'peak windows ({peak}): {len(wins)}')
    for a, b in wins:
        live = [q for q in range(nq) if any(s <= a <= t for s, t, _ in intervals[q])]
        print(f'  [{a},{b}] len={b-a+1} live={live}')
        for q in live:
            iv = [x for x in intervals[q] if x[0] <= a <= x[1]][0]
            print(f'      q{q}: interval {iv}')
    print('\nfirst 40 ops around each peak window:')
    for a, b in wins[:6]:
        print(f'--- window [{a},{b}]')
        for op in ops[max(0, a - 4):min(n, b + 5)]:
            print(f'   {op.index:6d} {op.raw}')


if __name__ == '__main__':
    main()
