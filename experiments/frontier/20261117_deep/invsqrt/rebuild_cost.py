"""Q43 rebuild economics: per-scratch-line lifetime count x rebuild cost, vs the 158 T budget.

Retiring line q means its value has to be *materialised on a borrowed wire* at each of
its lifetimes.  Rebuild cost is followed along the definition chain, and every input that
is already held by another live wire is free (this is the optimistic lower bound, so any
line that still exceeds the budget is closed for good).

  lifetime        a write whose pre-value is |0> (HMR / X reset / first use)
  rebuild cost R  Toffoli needed to recompute the line's value from live lines:
                    CX / X writes        -> 0 Toffoli (Clifford)
                    CCX a b              -> 1 + (cost of a if not live) + (cost of b if not live)
                  where "live" means: every atom of that wire's value is also held by some
                  other wire at that op (exact GF(2) atom support, see atoms.py)
  net             lifetimes x R, in T units = 4 x Toffoli
"""

from __future__ import annotations

import collections
import functools
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from parse_kmx import parse  # noqa: E402

KMX = pathlib.Path('artifacts/20261117_deep_invsqrt/invsqrt_0af21cb8.kmx')
CONST = -1
BUDGET_T = 158.2          # 39.54 C units


def main() -> None:
    ops, meta = parse(KMX)
    nq = 22 + 22
    support: list[frozenset[int]] = [frozenset() for _ in range(nq)]
    holder: dict[int, set[int]] = collections.defaultdict(set)
    next_atom = 0
    depth = 0

    def set_support(q: int, s: frozenset[int]) -> None:
        for a in support[q]:
            holder[a].discard(q)
        support[q] = s
        for a in s:
            holder[a].add(q)

    # per wire: last definition = (index, op name, controls)
    last_def: dict[int, tuple[int, str, tuple[int, ...]]] = {}
    fresh_defs: dict[int, list[int]] = collections.defaultdict(list)
    snap_support: dict[int, frozenset[int]] = {}
    snap_avail: dict[int, bool] = {}

    def avail(s: frozenset[int], exclude: int) -> bool:
        return all(a == CONST or (holder[a] - {exclude}) for a in s)

    for op in ops:
        n = op.name
        if n == 'PUSH_CONDITION':
            depth += 1
            continue
        if n == 'POP_CONDITION':
            depth -= 1
            continue
        q = op.qubits
        if n in ('Z', 'Z_POW', 'CZ', 'CCZ', 'NEG') or n.startswith('BIT_'):
            continue
        if n == 'X':
            w = q[0]
            if not support[w]:
                fresh_defs[w].append(op.index)
            last_def[w] = (op.index, 'X', ())
            set_support(w, frozenset({CONST}) if not depth else frozenset({next_atom}))
            if depth:
                next_atom += 1
            continue
        if n == 'HMR':
            w = q[0]
            set_support(w, frozenset() if not depth else frozenset({next_atom + 1}))
            if depth:
                next_atom += 1
            continue
        if n == 'SWAP':
            a, b = q
            sa, sb = support[a], support[b]
            set_support(a, sb)
            set_support(b, sa)
            last_def[a] = (op.index, 'SWAP', (b,))
            last_def[b] = (op.index, 'SWAP', (a,))
            continue
        if n == 'CX':
            a, b = q
            if not support[b]:
                fresh_defs[b].append(op.index)
            last_def[b] = (op.index, 'CX', (a,))
            if depth:
                next_atom += 1
                set_support(b, support[b] ^ frozenset({next_atom}))
            else:
                set_support(b, support[b] ^ support[a])
            continue
        if n == 'CCX':
            a, b, t = q
            if not support[t]:
                fresh_defs[t].append(op.index)
            last_def[t] = (op.index, 'CCX', (a, b))
            snap_support[op.index] = support[a]
            snap_support[op.index * 1000 + 1] = support[b]
            next_atom += 1
            set_support(t, support[t] ^ frozenset({next_atom}))
            continue

    # exact availability snapshots: recompute by replaying (cheap second pass)
    avail_at: dict[tuple[int, int], bool] = {}
    sup_at: dict[tuple[int, int], frozenset[int]] = {}
    support = [frozenset() for _ in range(nq)]
    holder = collections.defaultdict(set)
    next_atom = 0
    depth = 0
    hist: dict[int, list[tuple[int, str, tuple[int, ...]]]] = collections.defaultdict(list)
    for op in ops:
        n = op.name
        if n == 'PUSH_CONDITION':
            depth += 1
            continue
        if n == 'POP_CONDITION':
            depth -= 1
            continue
        q = op.qubits
        if n in ('Z', 'Z_POW', 'CZ', 'CCZ', 'NEG') or n.startswith('BIT_'):
            continue
        if n == 'X':
            w = q[0]
            sup_at[(w, op.index)] = support[w]
            avail_at[(w, op.index)] = avail(support[w], w)
            hist[w].append((op.index, 'X', ()))
            set_support(w, frozenset({CONST}) if not depth else frozenset({next_atom}))
            if depth:
                next_atom += 1
            continue
        if n == 'HMR':
            w = q[0]
            set_support(w, frozenset() if not depth else frozenset({next_atom + 1}))
            if depth:
                next_atom += 1
            continue
        if n == 'SWAP':
            a, b = q
            sa, sb = support[a], support[b]
            set_support(a, sb)
            set_support(b, sa)
            hist[a].append((op.index, 'SWAP', (b,)))
            hist[b].append((op.index, 'SWAP', (a,)))
            continue
        if n == 'CX':
            a, b = q
            sup_at[(a, op.index)] = support[a]
            avail_at[(a, op.index)] = avail(support[a], a)
            hist[b].append((op.index, 'CX', (a,)))
            if depth:
                next_atom += 1
                set_support(b, support[b] ^ frozenset({next_atom}))
            else:
                set_support(b, support[b] ^ support[a])
            continue
        if n == 'CCX':
            a, b, t = q
            for w in (a, b):
                sup_at[(w, op.index)] = support[w]
                avail_at[(w, op.index)] = avail(support[w], w)
            hist[t].append((op.index, 'CCX', (a, b)))
            next_atom += 1
            set_support(t, support[t] ^ frozenset({next_atom}))
            continue

    def cost(wire: int, at: int, retired: int, seen: frozenset = frozenset()) -> int:
        """Optimistic Toffoli cost to materialise `wire`'s value at op `at`."""
        if wire >= 22:                       # scratch input must be rebuilt
            if avail_at.get((wire, at), False) and wire != retired:
                return 0
        else:
            return 0                         # x bits are always available
        if wire == retired:
            pass
        cand = [t for t in hist.get(wire, []) if t[0] < at]
        if not cand or wire in seen:
            return 0
        idx, name, ctrl = cand[-1]
        if name in ('CX', 'X', 'SWAP'):
            return 0
        base = 1 if name == 'CCX' else 0
        return base + sum(cost(c, idx, retired, seen | {wire}) for c in ctrl)

    rows = []
    for q in range(22, 44):
        L = len(fresh_defs[q])
        per = [cost(q, i, q) for i in sorted(fresh_defs[q])]
        R = max(per) if per else 0
        net = sum(per)
        rows.append((q, L, R, net, net * 4))
        print(f'q{q:2d}  lifetimes={L:4d}  rebuild R={R:5d} Toffoli  '
              f'net={net:6d} Toffoli = {net*4:7.1f} T   {"OK < budget" if net*4 < BUDGET_T else ""}')
    print(f'\nbudget: {BUDGET_T:.1f} T (= +39.54 C).  '
          f'lines under budget: {[r[0] for r in rows if r[4] < BUDGET_T]}')
    rows.sort(key=lambda r: r[4])
    print('cheapest five:', [(f'q{r[0]}', r[1], r[2], round(r[4], 1)) for r in rows[:5]])


if __name__ == '__main__':
    main()
