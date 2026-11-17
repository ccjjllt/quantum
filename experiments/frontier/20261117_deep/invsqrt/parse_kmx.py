"""Static parse of a kickmix .kmx text circuit (no simulation, no kickmix import).

Reads the .kmx produced by `kickmix.Circuit.to_file(format='kmx')`, returns a flat
operation list with integer qubit / bit operands.
"""

from __future__ import annotations

import collections
import dataclasses
import re
import pathlib

QRE = re.compile(r'^q(\d+)$')
BRE = re.compile(r'^b(\d+)$')


@dataclasses.dataclass(frozen=True)
class Op:
    index: int          # position among operations (0-based)
    name: str           # 'CCX', 'CX', 'HMR', 'PUSH_CONDITION', ...
    qubits: tuple[int, ...]
    bits: tuple[int, ...]
    raw: str
    cond: int | None    # bit index for PUSH_CONDITION

    @property
    def arity(self) -> int:
        return len(self.qubits)


def parse(path: pathlib.Path | str) -> tuple[list[Op], dict]:
    ops: list[Op] = []
    regs: dict[str, list[int]] = {}
    reg_order: list[str] = []
    for line in pathlib.Path(path).read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        name = parts[0]
        if name == 'APPEND_TO_REGISTER':
            regs.setdefault(parts[2], []).append(int(parts[1][1:]))
            reg_order.append(parts[2])
            continue
        if name == 'REGISTER':
            continue
        qubits: list[int] = []
        bits: list[int] = []
        cond = None
        for tok in parts[1:]:
            m = QRE.match(tok)
            if m:
                qubits.append(int(m.group(1)))
                continue
            m = BRE.match(tok)
            if m:
                bits.append(int(m.group(1)))
                continue
            if tok == 'if':
                continue
            if BRE.match(tok) is None and tok.startswith('b'):
                bits.append(int(tok[1:]))
                continue
            # numeric literal (angle, etc.) -> ignore for now but keep raw
        if name == 'PUSH_CONDITION' and bits:
            cond = bits[0]
        ops.append(Op(len(ops), name, tuple(qubits), tuple(bits), line, cond))
    meta = {'registers': regs, 'register_order': reg_order}
    return ops, meta


def histogram(ops: list[Op]) -> collections.Counter:
    return collections.Counter(o.name for o in ops)


if __name__ == '__main__':
    import sys
    ops, meta = parse(sys.argv[1])
    print('ops', len(ops), 'registers', {k: len(v) for k, v in meta['registers'].items()})
    for name, n in histogram(ops).most_common():
        print(f'{name:20s} {n:6d}')
