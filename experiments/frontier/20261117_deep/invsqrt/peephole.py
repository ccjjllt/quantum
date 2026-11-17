"""Peephole feasibility checks on 0af21cb8 (static; no simulation).

(1) adjacent self-inverse cancel pairs
(2) constant-propagation over {0,1,top}: dead CCX / CCX->CX downgrade / dead phase controls
(3) dead writes (value never read before the next write)
(4) conditional-block inventory
"""

from __future__ import annotations

import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from parse_kmx import Op, parse  # noqa: E402

KMX = pathlib.Path('artifacts/20261117_deep_invsqrt/invsqrt_0af21cb8.kmx')
SELF_INV = {'X', 'Z', 'CX', 'CZ', 'SWAP', 'CCX', 'CCZ'}


def const_prop(ops: list[Op], nq: int) -> dict:
    val: list[int | None] = [None] * nq  # None = unknown, 0/1 = known
    stats = collections.Counter()
    dead: list[Op] = []
    downgrade: list[tuple[Op, int]] = []
    dead_phase: list[Op] = []
    depth = 0
    for op in ops:
        n = op.name
        if n in ('PUSH_CONDITION',):
            stats['cond_blocks'] += 1
            depth += 1
            continue
        if n == 'POP_CONDITION':
            depth -= 1
            continue
        cond = depth > 0
        if cond and n in ('X', 'CX', 'CCX', 'SWAP', 'HMR'):
            # may or may not execute -> all written qubits become unknown
            for q in op.qubits:
                val[q] = None
            continue
        if n in ('Z', 'CZ', 'CCZ', 'Z_POW', 'NEG'):
            # phase gate: optional; check constant controls
            if n in ('CZ', 'CCZ'):
                ctrls = op.qubits[:-1]
                for c in ctrls:
                    if val[c] == 0:
                        stats[f'dead_phase_ctrl0_{n}'] += 1
                        dead_phase.append(op)
                        break
                    if val[c] == 1:
                        stats[f'phase_ctrl1_{n}'] += 1
            continue
        if n == 'X':
            q = op.qubits[0]
            val[q] = None if val[q] is None else 1 - val[q]
            continue
        if n == 'SWAP':
            a, b = op.qubits
            val[a], val[b] = val[b], val[a]
            continue
        if n == 'HMR':
            val[op.qubits[0]] = 0
            continue
        if n == 'CX':
            a, b = op.qubits
            if val[a] == 0:
                stats['dead_CX'] += 1
                dead.append(op)
            elif val[a] == 1:
                val[b] = None if val[b] is None else 1 - val[b]
            else:
                val[b] = None
            continue
        if n == 'CCX':
            a, b, t = op.qubits
            if val[a] == 0 or val[b] == 0:
                stats['dead_CCX'] += 1
                dead.append(op)
            elif val[a] == 1:
                stats['ccx_to_cx'] += 1
                downgrade.append((op, 0))
                val[t] = None
            elif val[b] == 1:
                stats['ccx_to_cx'] += 1
                downgrade.append((op, 1))
                val[t] = None
            else:
                val[t] = None
            continue
        if n in ('BIT_INVERT', 'BIT_STORE0', 'BIT_STORE1'):
            continue
        stats[f'unhandled_{n}'] += 1
    return {'stats': stats, 'dead': dead, 'downgrade': downgrade, 'dead_phase': dead_phase}


def main() -> None:
    ops, meta = parse(KMX)
    nq = max(max(o.qubits) for o in ops if o.qubits) + 1

    # ---- (1) adjacent cancel pairs (stack peephole) --------------------
    stack: list[Op] = []
    pairs = 0
    for op in ops:
        if op.name in SELF_INV and op.cond is None:
            if stack and stack[-1].name == op.name and stack[-1].qubits == op.qubits:
                stack.pop()
                pairs += 1
            else:
                stack.append(op)
        else:
            stack.clear()
    print(f'(1) adjacent cancel pairs: {pairs}')

    # ---- conditional inventory -----------------------------------------
    blocks: list[list[Op]] = []
    cur: list[Op] | None = None
    for op in ops:
        if op.name == 'PUSH_CONDITION':
            cur = []
            blocks.append(cur)
        elif op.name == 'POP_CONDITION':
            cur = None
        elif cur is not None:
            cur.append(op)
    kinds = collections.Counter()
    for b in blocks:
        ks = tuple(sorted({o.name for o in b}))
        kinds[ks] += 1
    print(f'(4) conditional blocks: {len(blocks)}')
    for ks, n in kinds.most_common():
        print(f'    {n:4d} x {ks}')
    state_changing = [b for b in blocks if any(o.name in ('X', 'CX', 'CCX', 'SWAP', 'HMR') for o in b)]
    print(f'    blocks containing state-changing ops: {len(state_changing)}')
    for b in state_changing[:5]:
        print('      ', [o.raw for o in b][:8])

    # ---- (2)/(3) const propagation -------------------------------------
    res = const_prop(ops, nq)
    print('\n(2) const-prop stats:', dict(res['stats']))
    for op in res['dead'][:20]:
        print('    dead:', op.raw)
    for op, which in res['downgrade'][:20]:
        print('    downgrade:', op.raw, 'ctrl', which)
    for op in res['dead_phase'][:20]:
        print('    dead phase:', op.raw)


if __name__ == '__main__':
    main()
