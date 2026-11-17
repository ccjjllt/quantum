"""Per-scratch-line retirement price, exact, all 22 lines.

Two complementary lower bounds, both exact (no sampling):

  substitution price  sum over CCX/CCZ control reads of (k-1), where k is the size of the
                      exact GF(2) atom support of the line's value at that read
                      (CX/CZ/Z reads are free: CX(a1^..^ak, t) = prod CX(ai,t),
                       CZ(a1^..^ak, r) = prod CZ(ai,r))
  rebuild price       sum over reads of the Toffoli depth of the line's definition chain
                      evaluated at that read, with every input that is still held by
                      another live wire counted as free (optimistic), plus the same again
                      for the Bennett uncompute

A retirement must pay at least min(substitution, rebuild) per read, so a line whose
*cheapest* per-read scheme already blows the +39.54 C (= 158.2 T = 39.5 Toffoli) budget is
closed regardless of any smarter rewriting.
"""

from __future__ import annotations

import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from parse_kmx import parse  # noqa: E402

KMX = pathlib.Path('artifacts/20261117_deep_invsqrt/invsqrt_0af21cb8.kmx')
CONST = -1
BUDGET_TOFFOLI = 39.5


def main() -> None:
    ops, meta = parse(KMX)
    nq = 44
    support: list[frozenset[int]] = [frozenset() for _ in range(nq)]
    holder: dict[int, set[int]] = collections.defaultdict(set)
    next_atom = 0
    depth = 0

    def set_support(q, s):
        for a in support[q]:
            holder[a].discard(q)
        support[q] = s
        for a in s:
            holder[a].add(q)

    read_support: dict[tuple[int, int], frozenset[int]] = {}
    read_role: dict[tuple[int, int], str] = {}
    hist: dict[int, list] = collections.defaultdict(list)
    lifetimes = collections.Counter()
    ops_reads: list[tuple[int, int, str]] = []

    for op in ops:
        n = op.name
        if n == 'PUSH_CONDITION':
            depth += 1
            continue
        if n == 'POP_CONDITION':
            depth -= 1
            continue
        q = op.qubits
        if n in ('Z', 'Z_POW'):
            read_support[(op.index, q[0])] = support[q[0]]
            read_role[(op.index, q[0])] = n
            ops_reads.append((op.index, q[0], n))
            continue
        if n in ('CZ', 'CCZ'):
            for w in q:
                read_support[(op.index, w)] = support[w]
                read_role[(op.index, w)] = n
                ops_reads.append((op.index, w, n))
            continue
        if n == 'NEG' or n.startswith('BIT_'):
            continue
        if n == 'X':
            w = q[0]
            if not support[w]:
                lifetimes[w] += 1
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
            read_support[(op.index, a)] = support[a]
            read_role[(op.index, a)] = 'CX'
            ops_reads.append((op.index, a, 'CX'))
            if not support[b]:
                lifetimes[b] += 1
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
                read_support[(op.index, w)] = support[w]
                read_role[(op.index, w)] = 'CCX'
                ops_reads.append((op.index, w, 'CCX'))
            if not support[t]:
                lifetimes[t] += 1
            hist[t].append((op.index, 'CCX', (a, b)))
            next_atom += 1
            set_support(t, support[t] ^ frozenset({next_atom}))
            continue

    # availability snapshot at every read (need "held by another wire at that op")
    avail: dict[tuple[int, int], bool] = {}
    # replay with holder sets captured per read is expensive to store; recompute per line
    def cost_of(wire: int, at: int, retired: int, seen: frozenset = frozenset()) -> int:
        cand = [t for t in hist.get(wire, []) if t[0] < at]
        if not cand or wire in seen:
            return 0
        idx, name, ctrl = cand[-1]
        if name in ('CX', 'X', 'SWAP'):
            base = 0
        else:
            base = 1
        total = base
        for c in ctrl:
            if c < 22:
                continue
            s = read_support.get((idx, c))
            if s is not None and all(a == CONST or (a in avail_holder[a] and
                                                    (avail_holder[a] - {c})) for a in s):
                continue
            total += cost_of(c, idx, retired, seen | {wire})
        return total

    # rebuild the holder map step by step to evaluate availability exactly at read points
    avail_holder: dict[int, set[int]] = collections.defaultdict(set)
    support = [frozenset() for _ in range(nq)]
    holder = collections.defaultdict(set)
    next_atom = 0
    depth = 0
    rebuild_per_read: dict[tuple[int, int], int] = {}
    for op in ops:
        n = op.name
        if n == 'PUSH_CONDITION':
            depth += 1
            continue
        if n == 'POP_CONDITION':
            depth -= 1
            continue
        q = op.qubits

        def held_elsewhere(w):
            s = support[w]
            return all(a == CONST or (holder[a] - {w}) for a in s)

        if n in ('Z', 'Z_POW'):
            w = q[0]
            if w >= 22:
                rebuild_per_read[(op.index, w)] = 0 if held_elsewhere(w) else \
                    cost_of(w, op.index, w)
            continue
        if n in ('CZ', 'CCZ'):
            for w in q:
                if w >= 22:
                    rebuild_per_read[(op.index, w)] = 0 if held_elsewhere(w) else \
                        cost_of(w, op.index, w)
            continue
        if n == 'NEG' or n.startswith('BIT_'):
            continue
        if n == 'X':
            set_support(q[0], frozenset({CONST}) if not depth else frozenset({next_atom}))
            if depth:
                next_atom += 1
            continue
        if n == 'HMR':
            set_support(q[0], frozenset() if not depth else frozenset({next_atom + 1}))
            if depth:
                next_atom += 1
            continue
        if n == 'SWAP':
            a, b = q
            sa, sb = support[a], support[b]
            set_support(a, sb)
            set_support(b, sa)
            continue
        if n == 'CX':
            a, b = q
            if a >= 22:
                rebuild_per_read[(op.index, a)] = 0 if held_elsewhere(a) else \
                    cost_of(a, op.index, a)
            if depth:
                next_atom += 1
                set_support(b, support[b] ^ frozenset({next_atom}))
            else:
                set_support(b, support[b] ^ support[a])
            continue
        if n == 'CCX':
            a, b, t = q
            for w in (a, b):
                if w >= 22:
                    rebuild_per_read[(op.index, w)] = 0 if held_elsewhere(w) else \
                        cost_of(w, op.index, w)
            next_atom += 1
            set_support(t, support[t] ^ frozenset({next_atom}))
            continue

    print(f'{"line":>5s} {"life":>5s} {"reads":>6s} {"k=1":>5s} {"k>=2":>5s} '
          f'{"subst":>7s} {"rebuild":>8s} {"best":>6s}  verdict')
    rows = []
    for q in range(22, 44):
        rs = [(i, w, r) for (i, w, r) in ops_reads if w == q]
        k1 = sum(1 for (i, w, r) in rs if len(read_support[(i, w)]) == 1)
        sub = sum(max(0, len(read_support[(i, w)]) - 1) for (i, w, r) in rs
                  if r in ('CCX', 'CCZ'))
        reb = sum(rebuild_per_read.get((i, w), 0) for (i, w, r) in rs)
        best = min(sub, reb)
        rows.append((q, lifetimes[q], len(rs), k1, len(rs) - k1, sub, reb, best))
        verdict = 'GO' if best <= BUDGET_TOFFOLI else 'closed'
        print(f'q{q:2d}  {lifetimes[q]:5d} {len(rs):6d} {k1:5d} {len(rs)-k1:5d} '
              f'{sub:7d} {reb:8d} {best:6d}  {verdict}')
    print(f'\nbudget {BUDGET_TOFFOLI} Toffoli (= +39.54 C = 158.2 T)')
    print('GO lines:', [r[0] for r in rows if r[7] <= BUDGET_TOFFOLI])


if __name__ == '__main__':
    main()
