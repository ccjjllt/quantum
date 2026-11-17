"""Emit the q25-retirement rewrite (Q44 -> Q43) from the exact atom-support analysis.

q25's value is a single atom at all 80 of its reads, and that atom is held by another
live wire at every read (see atoms.py).  So every read of q25 can be rewritten to read
the holder wire instead, at zero extra Toffoli:

    CX  q25 x   ->  CX  h x        (Clifford, free)
    CZ  q25 r   ->  CZ  h r        (Clifford, free)
    CCZ q25 a b ->  CCZ h a b      (same Toffoli count; support size 1)
    Z   q25     ->  Z   h          (Clifford, free)
    CX  a   q25 ->  (delete: the accumulator write)
    HMR q25 b   ->  HMR h b        (only if h is dead afterwards)

then relabel every wire > 25 down by one so num_qubits drops to 43.

This script prints the substitution table as JSON (op index -> replacement gate text) and
checks the HMR holder's liveness.
"""

from __future__ import annotations

import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from parse_kmx import parse  # noqa: E402

KMX = pathlib.Path('artifacts/20261117_deep_invsqrt/invsqrt_0af21cb8.kmx')
CONST = -1
RETIRE = 25


def main() -> None:
    ops, meta = parse(KMX)
    nq = 44
    support: list[frozenset[int]] = [frozenset() for _ in range(nq)]
    holder: dict[int, set[int]] = collections.defaultdict(set)
    next_atom = 0
    depth = 0
    subs: list[tuple[int, str, int]] = []   # (op index, original gate, holder)
    # pre-compute liveness (last event per wire) for the HMR decision
    last_event = {}
    for op in ops:
        for q in op.qubits:
            last_event[q] = op.index

    def set_support(q: int, s: frozenset[int]) -> None:
        for a in support[q]:
            holder[a].discard(q)
        support[q] = s
        for a in s:
            holder[a].add(q)

    def pick(q: int) -> int:
        s = support[q]
        assert len(s) == 1, (q, s)
        a = next(iter(s))
        if a == CONST:
            return CONST
        cands = sorted(holder[a] - {q})
        assert cands, (q, a)
        return cands[0]

    def pick_dead(q: int, at: int) -> int | None:
        s = support[q]
        a = next(iter(s))
        cands = sorted(holder[a] - {q})
        dead = [w for w in cands if last_event[w] <= at]
        return dead[0] if dead else None

    hmr_info = None
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
            w = q[0]
            if w == RETIRE:
                h = pick(w)
                subs.append((op.index, op.raw, h))
            continue
        if n in ('CZ', 'CCZ'):
            if RETIRE in q:
                h = pick(RETIRE)
                subs.append((op.index, op.raw, h))
            continue
        if n in ('NEG',) or n.startswith('BIT_'):
            continue
        if n == 'X':
            w = q[0]
            if w == RETIRE:
                raise SystemExit('q25 has an X write')
            set_support(w, support[w] ^ frozenset({CONST}) if not depth
                        else support[w] ^ frozenset({next_atom}))
            if depth:
                next_atom += 1
            continue
        if n == 'HMR':
            w = q[0]
            if w == RETIRE:
                hmr_info = (op.index, op.raw, sorted(holder[next(iter(support[w]))] - {w}),
                            last_event)
                h = pick_dead(w, op.index)
                assert h is not None, ('no dead holder for HMR', hmr_info[:3])
                subs.append((op.index, op.raw, h))
                set_support(h, frozenset())
            set_support(w, frozenset() if not depth else frozenset({next_atom + 1}))
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
            if a == RETIRE:
                h = pick(a)
                subs.append((op.index, op.raw, h))
            if b == RETIRE:
                subs.append((op.index, op.raw, -2))       # delete the accumulator write
            if depth:
                next_atom += 1
                set_support(b, support[b] ^ frozenset({next_atom}))
            else:
                set_support(b, support[b] ^ support[a])
            continue
        if n == 'CCX':
            a, b, t = q
            for w in (a, b):
                if w == RETIRE:
                    h = pick(w)
                    subs.append((op.index, op.raw, h))
            if t == RETIRE:
                subs.append((op.index, op.raw, -2))
            next_atom += 1
            set_support(t, support[t] ^ frozenset({next_atom}))
            continue

    print(f'substitutions: {len(subs)}')
    print('HMR:', hmr_info[0], hmr_info[1], 'holders:', hmr_info[2])
    print(json.dumps([[i, raw, h] for i, raw, h in subs], indent=0))
    # sanity: q25 must not appear in any kept op afterwards
    print('\nholder distribution:', collections.Counter(h for _, _, h in subs))


if __name__ == '__main__':
    main()
