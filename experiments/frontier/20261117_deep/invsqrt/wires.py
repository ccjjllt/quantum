"""Wire-level static anatomy of the 0af21cb8 44Q invsqrt circuit.

Pure static analysis of the parsed .kmx; no simulation.
"""

from __future__ import annotations

import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from parse_kmx import Op, parse  # noqa: E402

KMX = pathlib.Path('artifacts/20261117_deep_invsqrt/invsqrt_0af21cb8.kmx')

TARGET1 = {'X', 'Z', 'Y', 'H', 'S', 'SDG', 'T', 'TDG', 'NEG', 'HMR', 'Z_POW', 'R', 'BIT_INVERT',
           'BIT_STORE0', 'BIT_STORE1'}


def role_of(op: Op, qubit: int) -> str:
    """Return the role this qubit plays in `op`, or ''."""
    if qubit not in op.qubits:
        return 'target' if qubit in op.bits else ''  # classical bit read/write
    pos = op.qubits.index(qubit)
    n = op.name
    if n in ('X', 'Z', 'Y', 'H', 'S', 'SDG', 'T', 'TDG', 'NEG', 'HMR', 'Z_POW', 'R'):
        return 'target'
    if n in ('CX', 'CZ'):
        return 'ctrl' if pos == 0 else 'target'
    if n in ('CCX', 'CCZ'):
        return 'ctrl' if pos < 2 else 'target'
    if n == 'SWAP':
        return 'swap'
    return f'{n}?{pos}'


def main() -> None:
    ops, meta = parse(KMX)
    x_reg = meta['registers']['r0']
    nq = max(max(o.qubits) for o in ops if o.qubits) + 1
    print(f'num_qubits={nq}  x register ({len(x_reg)}): {x_reg}')
    print(f'scratch: {[q for q in range(nq) if q not in x_reg]}')
    scratch = [q for q in range(nq) if q not in x_reg]

    roles: dict[int, collections.Counter] = {q: collections.Counter() for q in range(nq)}
    first: dict[int, int] = {}
    last: dict[int, int] = {}
    for op in ops:
        for q in op.qubits:
            roles[q][role_of(op, q)] += 1
            first.setdefault(q, op.index)
            last[q] = op.index

    names = ['ctrl', 'target', 'swap']
    print('\n## per-wire role table (all ops)')
    hdr = f'{"q":>3s} {"kind":>7s} {"first":>6s} {"last":>6s} ' + ' '.join(f'{n:>8s}' for n in names) + f' {"ops":>6s}'
    print(hdr)
    for q in range(nq):
        kind = 'x' if q in x_reg else 'scratch'
        counts = [roles[q][n] for n in names]
        print(f'{q:3d} {kind:>7s} {first[q]:6d} {last[q]:6d} ' + ' '.join(f'{c:8d}' for c in counts)
              + f' {sum(roles[q].values()):6d}')

    print('\n## scratch detail (all role keys)')
    for q in scratch:
        print(f'q{q}: {dict(roles[q])} first={first[q]} last={last[q]}')

    print('\n## x detail')
    for q in x_reg:
        print(f'q{q}: {dict(roles[q])} first={first[q]} last={last[q]}')

    # discard / write-only detection
    print('\n## write-only candidates (target>0, never read as ctrl or earlier target)')
    for q in range(nq):
        if roles[q]['ctrl'] == 0 and roles[q]['swap'] == 0:
            print(f'  q{q} ({("x" if q in x_reg else "scratch")}) targets={roles[q]["target"]}')

    # multi-writer detection: count distinct CCX/CX that write each scratch line
    print('\n## writers per scratch line')
    for q in scratch:
        ccx = sum(1 for o in ops if o.name in ('CCX',) and o.qubits and o.qubits[-1] == q)
        cx = sum(1 for o in ops if o.name == 'CX' and o.qubits[1] == q)
        one = sum(1 for o in ops if o.name in TARGET1 and q in o.qubits)
        print(f'  q{q}: CCX-target {ccx:4d}  CX-target {cx:4d}  1q {one:4d}')


if __name__ == '__main__':
    main()
