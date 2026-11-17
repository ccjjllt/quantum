"""Exact GF(2) atom-support analysis: what does it cost to retire a scratch line?

Every wire value is decomposed exactly into a symmetric difference of *atoms*:

  CONST          the constant 1
  P@i            the product a&b created by the CCX at op i
  M@i            the measurement bit produced by the HMR at op i
  V@i            any other value created at op i (conditional writes, HMR reset, ...)

so `support[w]` is a set of atoms and the wire value is their XOR.  A read of a wire
whose support is {A1..Ak} can be rewritten on the fly as long as each atom is still
held by some live wire (or is CONST):  CX/CZ reads cost nothing, a CCX/CCZ control
costs k-1 extra Toffoli because (a1^..^ak)&y = sum ai&y.

This is exact (no sampling, no simulation) and gives the retirement price in Toffoli.
"""

from __future__ import annotations

import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from parse_kmx import parse  # noqa: E402

KMX = pathlib.Path('artifacts/20261117_deep_invsqrt/invsqrt_0af21cb8.kmx')
CONST = -1


def main() -> None:
    ops, meta = parse(KMX)
    nq = 44
    support: list[frozenset[int]] = [frozenset({-(i + 2)}) for i in range(22)]
    support += [frozenset() for _ in range(nq - 22)]   # x wires start at their INPUT bit  # start |0> = XOR of nothing
    holder: dict[int, set[int]] = collections.defaultdict(set)        # atom -> wires
    next_atom = 0
    depth = 0
    reads: list[tuple[int, int, str]] = []      # index, wire, role
    write_ops: list[tuple[int, int, str]] = []
    support_at: dict[int, frozenset[int]] = {}  # index -> support of the read wire
    atom_avail: dict[int, bool] = {}

    def new_atom() -> int:
        nonlocal next_atom
        next_atom += 1
        return next_atom

    def set_support(q: int, s: frozenset[int]) -> None:
        for a in support[q]:
            holder[a].discard(q)
        support[q] = s
        for a in s:
            holder[a].add(q)

    for op in ops:
        n = op.name
        if n == 'PUSH_CONDITION':
            depth += 1
            if op.bits:
                set_support  # noqa: B018  (bits live in classical space; tracked separately)
            continue
        if n == 'POP_CONDITION':
            depth -= 1
            continue
        q = op.qubits
        if n in ('Z', 'Z_POW', 'CZ', 'CCZ'):
            for w in q:
                reads.append((op.index, w, n))
                support_at[(op.index, w)] = support[w]
            continue
        if n == 'NEG' or n.startswith('BIT_'):
            continue
        if n == 'X':
            w = q[0]
            write_ops.append((op.index, w, 'X'))
            if depth:
                set_support(w, support[w] ^ frozenset({new_atom()}))
            else:
                set_support(w, support[w] ^ frozenset({CONST}))
            continue
        if n == 'HMR':
            w = q[0]
            write_ops.append((op.index, w, 'HMR'))
            set_support(w, frozenset() if not depth else frozenset({new_atom()}))
            continue
        if n == 'SWAP':
            a, b = q
            sa, sb = support[a], support[b]
            set_support(a, sb)
            set_support(b, sa)
            continue
        if n == 'CX':
            a, b = q
            reads.append((op.index, a, 'CX-ctrl'))
            support_at[(op.index, a)] = support[a]
            write_ops.append((op.index, b, 'CX'))
            if depth:
                set_support(b, support[b] ^ frozenset({new_atom()}))
            else:
                set_support(b, support[b] ^ support[a])
            continue
        if n == 'CCX':
            a, b, t = q
            reads.append((op.index, a, 'CCX-ctrl'))
            reads.append((op.index, b, 'CCX-ctrl'))
            support_at[(op.index, a)] = support[a]
            support_at[(op.index, b)] = support[b]
            write_ops.append((op.index, t, 'CCX'))
            atom = new_atom()
            set_support(t, support[t] ^ frozenset({atom}))

    print(f'atoms created: {next_atom}')
    for q in (22, 23, 24, 25):
        print(f'\n===== q{q}: support evolution')
        hist = collections.Counter()
        for (i, w, role) in reads:
            if w != q:
                continue
            s = support_at[(i, w)]
            hist[len(s)] += 1
        print(f'  support sizes over {sum(hist.values())} reads: {dict(sorted(hist.items()))}')

    # For each candidate line: per-read price, assuming atoms are available.
    print('\n## retirement price (extra Toffoli) for the affine lines')
    for q in (22, 23, 24, 25):
        by_role = collections.Counter()
        price = 0
        worst = 0
        for (i, w, role) in reads:
            if w != q:
                continue
            k = len(support_at[(i, w)])
            by_role[role] += 1
            if role in ('CCX-ctrl',):
                price += max(0, k - 1)
                worst = max(worst, k)
        print(f'  q{q}: reads {dict(by_role)}  price >= {price}  max support {worst}')

    # availability: at each read is every atom in the support held by another live wire?
    print('\n## atom availability at the reads of q22..q25 '
          '(an atom is unavailable if no other wire holds it)')
    # rebuild with per-read availability requires replaying; do a second pass
    support = [frozenset() for _ in range(nq)]
    holder = collections.defaultdict(set)
    next_atom = 0
    depth = 0
    miss = collections.Counter()
    for op in ops:
        n = op.name
        if n == 'PUSH_CONDITION':
            depth += 1
            continue
        if n == 'POP_CONDITION':
            depth -= 1
            continue
        q = op.qubits
        if n in ('Z', 'Z_POW', 'CZ', 'CCZ'):
            for w in q:
                if w in (22, 23, 24, 25):
                    s = support[w]
                    ok = all(a == CONST or (holder[a] - {w}) for a in s)
                    if not ok:
                        miss[w] += 1
            continue
        if n in ('NEG',) or n.startswith('BIT_'):
            continue
        if n == 'X':
            w = q[0]
            if depth:
                next_atom += 1
                set_support(w, support[w] ^ frozenset({next_atom}))
            else:
                set_support(w, support[w] ^ frozenset({CONST}))
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
            if a in (22, 23, 24, 25):
                s = support[a]
                if not all(x == CONST or (holder[x] - {a}) for x in s):
                    miss[a] += 1
            if depth:
                next_atom += 1
                set_support(b, support[b] ^ frozenset({next_atom}))
            else:
                set_support(b, support[b] ^ support[a])
            continue
        if n == 'CCX':
            a, b, t = q
            for w in (a, b):
                if w in (22, 23, 24, 25):
                    s = support[w]
                    if not all(x == CONST or (holder[x] - {w}) for x in s):
                        miss[w] += 1
            next_atom += 1
            set_support(t, support[t] ^ frozenset({next_atom}))
    print(f'  reads whose atoms are NOT fully held elsewhere: {dict(miss)}')


if __name__ == '__main__':
    main()
