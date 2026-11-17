"""Gate hygiene + Z_POW accounting + CCX uncompute partner accounting (static)."""

from __future__ import annotations

import collections
import pathlib
import sys
from fractions import Fraction

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from parse_kmx import parse  # noqa: E402


def main() -> None:
    ops, meta = parse('artifacts/20261117_deep_invsqrt/invsqrt_0af21cb8.kmx')

    # --- duplicated operands ------------------------------------------------
    dup = collections.Counter()
    examples = []
    for op in ops:
        if len(set(op.qubits)) != len(op.qubits):
            dup[op.name] += 1
            if len(examples) < 10:
                examples.append(op.raw)
    print('gates with duplicated qubit operands:', dict(dup), examples)

    # --- Z_POW accounting --------------------------------------------------
    zp = [op for op in ops if op.name == 'Z_POW']
    print(f'\nZ_POW count: {len(zp)}')
    cls = collections.Counter()
    totT = Fraction(0)
    for op in zp:
        ang = Fraction(op.raw.split()[-1])
        half = 2 * ang
        if half % Fraction(1, 2) == 0:
            cls['clifford'] += 1
        elif half % Fraction(1, 4) == 0:
            cls['t'] += 1
            totT += Fraction(1)
        else:
            cls['rotation'] += 1
    print('  classification:', dict(cls))
    cond = sum(1 for op in zp if op.cond is not None or ' if ' in op.raw)
    print(f'  Z_POW with "if" in raw: {cond}')

    # --- CCX uncompute partner --------------------------------------------
    # For each CCX at index i targeting t: classify as
    #   'mirror'  : an identical CCX appears later before any other write to t
    #   'hmr'     : an HMR on t appears before any other write to t
    #   'other'   : something else
    kind = collections.Counter()
    detail = []
    by_index = {op.index: op for op in ops}
    for op in ops:
        if op.name != 'CCX':
            continue
        t = op.qubits[2]
        res = 'none'
        for nxt in ops[op.index + 1:]:
            if nxt.name == 'HMR' and nxt.qubits[0] == t:
                res = 'hmr'
                break
            if nxt.name == 'CCX' and nxt.qubits == op.qubits:
                res = 'mirror'
                break
            d = []
            if nxt.name in ('X', 'CX', 'CCX', 'SWAP', 'HMR'):
                # does it write t?
                if nxt.name == 'X' and nxt.qubits[0] == t:
                    d.append(1)
                if nxt.name == 'CX' and nxt.qubits[1] == t:
                    d.append(1)
                if nxt.name == 'CCX' and nxt.qubits[2] == t:
                    d.append(1)
                if nxt.name == 'SWAP' and t in nxt.qubits:
                    d.append(1)
                if nxt.name == 'HMR' and nxt.qubits[0] == t:
                    d.append(1)
            if d:
                res = 'overwritten'
                break
        kind[res] += 1
        detail.append((op.index, t, res))
    print('\nCCX uncompute partner class:', dict(kind))
    print('  (mirror = same CCX later; hmr = measurement-based uncompute)')
    hmr_share = kind['hmr'] / max(1, sum(kind.values()))
    print(f'  HMR-uncomputed share of CCX: {hmr_share:.4%}')

    # --- CCZ inventory -----------------------------------------------------
    ccz = [op for op in ops if op.name == 'CCZ']
    print(f'\nCCZ count {len(ccz)}; conditional {sum(1 for o in ccz if " if " in o.raw)}')
    ccz_q = collections.Counter()
    for o in ccz:
        ccz_q[o.qubits] += 1
    for q, n in ccz_q.most_common(10):
        print('   ', q, n)

    # --- CZ / Z inventory --------------------------------------------------
    print(f'\nCZ {sum(1 for o in ops if o.name=="CZ")}, '
          f'Z {sum(1 for o in ops if o.name=="Z")}, '
          f'conditional CZ {sum(1 for o in ops if o.name=="CZ" and " if " in o.raw)}, '
          f'conditional Z {sum(1 for o in ops if o.name=="Z" and " if " in o.raw)}')


if __name__ == '__main__':
    main()
