"""Build the Q43 candidate: retire q25 (exact atom substitution), relabel, rebuild.

Every read of q25 is rewritten to read the wire that currently holds q25's single atom
(exact GF(2) identity, no sampling).  q25's one accumulator write is deleted, its one
HMR is replaced by "copy the atom onto the dead wire q43 and measure that".  Then every
wire index > 25 is shifted down by one, so num_qubits becomes 43 while the x register
stays q0..q21.

Writes cand_q25.kmb + cand_q25_subs.json (op index -> replacement text, pre-relabel).
"""

from __future__ import annotations

import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from parse_kmx import parse  # noqa: E402

KMX = pathlib.Path('artifacts/20261117_deep_invsqrt/invsqrt_0af21cb8.kmx')
OUT = pathlib.Path('experiments/frontier/20261117_deep/invsqrt')
CONST = -1
RETIRE = 25
COPY_WIRE = 43          # dead since op 19144


def main() -> None:
    ops, meta = parse(KMX)
    nq = 44
    support: list[frozenset[int]] = [frozenset() for _ in range(nq)]
    holder: dict[int, set[int]] = collections.defaultdict(set)
    next_atom = 0
    depth = 0
    rewrite: dict[int, str] = {}
    drop: set[int] = set()

    def set_support(q: int, s: frozenset[int]) -> None:
        for a in support[q]:
            holder[a].discard(q)
        support[q] = s
        for a in s:
            holder[a].add(q)

    def pick(q: int) -> int:
        s = support[q]
        assert len(s) == 1, (q, sorted(s))
        a = next(iter(s))
        if a == CONST:
            return CONST
        return min(holder[a] - {q})

    for op in ops:
        n = op.name
        if n == 'PUSH_CONDITION':
            depth += 1
            continue
        if n == 'POP_CONDITION':
            depth -= 1
            continue
        q = list(op.qubits)
        if n in ('Z', 'Z_POW'):
            if q[0] == RETIRE:
                h = pick(RETIRE)
                rewrite[op.index] = f'{n} q{h}' if h != CONST else f'{n} q0  # CONST1 (unexpected)'
            continue
        if n in ('CZ', 'CCZ'):
            if RETIRE in q:
                h = pick(RETIRE)
                qq = [h if w == RETIRE else w for w in q]
                rewrite[op.index] = n + ' ' + ' '.join(f'q{w}' for w in qq)
            continue
        if n == 'NEG' or n.startswith('BIT_'):
            continue
        if n == 'X':
            w = q[0]
            assert w != RETIRE
            if depth:
                next_atom += 1
                set_support(w, support[w] ^ frozenset({next_atom}))
            else:
                set_support(w, support[w] ^ frozenset({CONST}))
            continue
        if n == 'HMR':
            w = q[0]
            if w == RETIRE:
                h = pick(RETIRE)
                assert h != CONST and h < 22, h
                rewrite[op.index] = f'CX q{h} q{COPY_WIRE}\nHMR q{COPY_WIRE} b{op.bits[0]}'
                set_support(COPY_WIRE, frozenset())
            else:
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
                h = pick(RETIRE)
                rewrite[op.index] = f'CX q{h} q{b}' if h != CONST else f'X q{b}'
            if b == RETIRE:
                drop.add(op.index)
            if depth:
                next_atom += 1
                set_support(b, support[b] ^ frozenset({next_atom}))
            else:
                set_support(b, support[b] ^ support[a])
            continue
        if n == 'CCX':
            a, b, t = q
            if a == RETIRE or b == RETIRE:
                h = pick(RETIRE)
                aa, bb = (h if a == RETIRE else a), (h if b == RETIRE else b)
                rewrite[op.index] = f'CCX q{aa} q{bb} q{t}' if h != CONST else f'CX q{bb} q{t}'
            if t == RETIRE:
                drop.add(op.index)
            next_atom += 1
            set_support(t, support[t] ^ frozenset({next_atom}))
            continue

    # sanity: after the rewrite no op may mention q25
    for i, text in rewrite.items():
        assert 'q25' not in text, (i, text)
    for i in drop:
        assert 'q25' in ops[i].raw
    leftovers = [op.raw for op in ops if 'q25' in op.raw and op.index not in rewrite and op.index not in drop]
    print('leftover q25 mentions:', leftovers)
    assert not leftovers

    def shift_line(line: str) -> str:
        out = []
        for tok in line.split():
            if tok[0] == 'q' and tok[1:].isdigit() and int(tok[1:]) > RETIRE:
                out.append(f'q{int(tok[1:]) - 1}')
            else:
                out.append(tok)
        return ' '.join(out)

    def shift(text: str) -> str:
        return '\n'.join(shift_line(l) for l in text.splitlines())

    header = [l for op in ops[:0] for l in []]  # placeholder
    header = []
    for line in KMX.read_text().splitlines():
        s = line.strip()
        if s.startswith('APPEND_TO_REGISTER') or s.startswith('REGISTER'):
            header.append(line)
    body = []
    for op in ops:
        if op.index in drop:
            continue
        text = rewrite.get(op.index, op.raw)
        body.append(text)
    new_text = '\n'.join(header + [shift(l) for l in body]) + '\n'
    p = OUT / 'cand_q25.kmx'
    p.write_text(new_text)

    import kickmix
    c = kickmix.Circuit(new_text)
    # x register must stay q0..q21
    print('registers:', {k: len(v) for k, v in c.register_data.items()})
    print(f'candidate: {c.num_qubits}Q ops={len(c)} stats={dict(c.operation_statistics())}')
    kmb = OUT / 'cand_q25.kmb'
    with kmb.open('wb') as f:
        c.to_file(f, format='kmb')
    import hashlib
    print('sha256', hashlib.sha256(kmb.read_bytes()).hexdigest())
    (OUT / 'cand_q25_subs.json').write_text(json.dumps(
        {'rewrite': {str(k): v for k, v in sorted(rewrite.items())},
         'drop': sorted(drop), 'copy_wire': COPY_WIRE, 'retire': RETIRE}, indent=0))
    print('rewrites', len(rewrite), 'drops', len(drop))


if __name__ == '__main__':
    main()
