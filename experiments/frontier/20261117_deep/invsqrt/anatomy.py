"""Per-wire anatomy + compute/uncompute split for 0af21cb8 (static only)."""

from __future__ import annotations

import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from parse_kmx import Op, parse  # noqa: E402

KMX = pathlib.Path('artifacts/20261117_deep_invsqrt/invsqrt_0af21cb8.kmx')
PHASE = {'Z', 'CZ', 'CCZ', 'Z_POW', 'NEG'}
CLIFF = {'X', 'Z', 'CZ', 'CX', 'SWAP', 'CCZ'}
SELFC = {'X', 'Z', 'CX', 'CZ', 'SWAP', 'CCX', 'CCZ'}


def target_of(op: Op) -> int | None:
    n = op.name
    if n in ('X', 'Z', 'Y', 'H', 'S', 'SDG', 'T', 'TDG', 'NEG', 'HMR', 'Z_POW', 'R'):
        return op.qubits[0] if op.qubits else None
    if n in ('CX', 'CZ', 'SWAP'):
        return op.qubits[1] if len(op.qubits) > 1 else None
    if n in ('CCX', 'CCZ'):
        return op.qubits[2] if len(op.qubits) > 2 else None
    return None


def controls_of(op: Op) -> tuple[int, ...]:
    return op.qubits[:-1]


def windows(indices: list[int], gap: int = 200) -> list[tuple[int, int, int]]:
    out: list[tuple[int, int, int]] = []
    for i in indices:
        if out and i - out[-1][1] <= gap:
            out[-1] = (out[-1][0], i, out[-1][2] + 1)
        else:
            out.append((i, i, 1))
    return out


def main() -> None:
    ops, meta = parse(KMX)
    nq = max(max(o.qubits) for o in ops if o.qubits) + 1
    x_reg = meta['registers']['r0']
    scratch = [q for q in range(nq) if q not in x_reg]

    # ---- per-wire role counts, split by gate name -------------------------
    role = {q: {'target': collections.Counter(), 'control': collections.Counter()}
            for q in range(nq)}
    idx = {q: [] for q in range(nq)}
    for op in ops:
        if not op.qubits:
            continue
        t = target_of(op)
        for q in op.qubits:
            idx[q].append(op.index)
            if q == t and op.name not in ('SWAP',):
                role[q]['target'][op.name] += 1
            elif q != t:
                role[q]['control'][op.name] += 1
            if op.name in ('SWAP',):
                role[q]['control']['SWAP'] += 1

    print('## SCRATCH lines')
    for q in scratch:
        tgt = dict(role[q]['target'])
        ctl = dict(role[q]['control'])
        w = windows(idx[q])
        print(f'q{q}: CCX-writes={sum(1 for o in ops if o.name=="CCX" and o.qubits[2]==q)}'
              f' first={idx[q][0]} last={idx[q][-1]}')
        print(f'    target {tgt}')
        print(f'    control {ctl}')
        print(f'    activity windows (gap>200): {w}')

    # ---- compute vs uncompute -------------------------------------------
    print('\n## CCX fate: mirrored pair vs HMR-uncompute')
    pair_of: dict[int, int] = {}
    used: set[int] = set()
    stack: list[Op] = []
    for op in ops:
        if op.name == 'CCX':
            # look for identical CCX back in the stack (LIFO)
            for j in range(len(stack) - 1, -1, -1):
                if stack[j].name == 'CCX' and stack[j].qubits == op.qubits:
                    pair_of[op.index] = stack[j].index
                    pair_of[stack[j].index] = op.index
                    del stack[j:]
                    break
            else:
                stack.append(op)
        elif op.name in ('HMR', 'X', 'CX', 'Z', 'CZ'):
            continue
    ccx = [o for o in ops if o.name == 'CCX']
    paired = [o for o in ccx if o.index in pair_of]
    print(f'CCX total {len(ccx)}; mirrored-pair CCX {len(paired)} '
          f'({len(paired)//2} pairs); unpaired {len(ccx)-len(paired)}')

    # HMR followed within 30 ops by a conditional clifford block?
    hmr_cond = 0
    for k, op in enumerate(ops):
        if op.name == 'HMR':
            window = ops[k + 1:k + 40]
            if any(w.name == 'PUSH_CONDITION' for w in window):
                hmr_cond += 1
    print(f'HMR total {sum(1 for o in ops if o.name=="HMR")}; with conditional '
          f'correction within 40 ops: {hmr_cond}')

    # ---- op-count split by halves ---------------------------------------
    half = len(ops) // 2
    for name in ('CCX', 'CCZ', 'CX', 'CZ', 'Z', 'X', 'Z_POW', 'HMR'):
        a = sum(1 for o in ops[:half] if o.name == name)
        b = sum(1 for o in ops[half:] if o.name == name)
        print(f'{name:6s} first-half {a:5d} second-half {b:5d}')


if __name__ == '__main__':
    main()
