"""Parse a .kmb circuit through its kmx text form into flat instructions.

Read-only helper shared by the 20261112 census scripts.  No kickmix simulation.
"""

from __future__ import annotations

import dataclasses
import io
from pathlib import Path


@dataclasses.dataclass(frozen=True)
class Op:
    index: int          # flat op index (0-based, APPEND/REGISTER excluded)
    kind: str           # e.g. CCX, CX, HMR, PUSH_CONDITION, ...
    args: tuple[str, ...]  # bare tokens after the kind
    cond: tuple[str, ...]   # active classical conditions at this op (outermost first)
    raw: str

    @property
    def qubits(self) -> tuple[int, ...]:
        return tuple(int(a[1:]) for a in self.args if a.startswith("q"))

    @property
    def bits(self) -> tuple[int, ...]:
        return tuple(int(a[1:]) for a in self.args if a.startswith("b"))


def load_ops(path: Path) -> tuple[list[Op], int, dict[str, list[int]]]:
    import kickmix as km

    circuit = km.Circuit.from_file(str(path), format="auto")
    buf = io.StringIO()
    circuit.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    registers: dict[str, list[int]] = {}
    ops: list[Op] = []
    cond: list[str] = []
    for line in lines:
        if not line:
            continue
        parts = line.split()
        head = parts[0]
        if head == "APPEND_TO_REGISTER":
            registers.setdefault(parts[2], []).append(int(parts[1][1:]))
            continue
        if head == "REGISTER":
            continue
        if head == "PUSH_CONDITION":
            # "PUSH_CONDITION if b45"
            cond.append(parts[2])
            ops.append(Op(len(ops), head, tuple(parts[1:]), tuple(cond[:-1]), line))
            continue
        if head == "POP_CONDITION":
            ops.append(Op(len(ops), head, (), tuple(cond), line))
            cond.pop()
            continue
        ops.append(Op(len(ops), head, tuple(parts[1:]), tuple(cond), line))
    return ops, circuit.num_qubits, registers


def summarize(ops: list[Op]) -> dict[str, int]:
    out: dict[str, int] = {}
    for op in ops:
        out[op.kind] = out.get(op.kind, 0) + 1
    return out


if __name__ == "__main__":
    import sys

    ops, nq, regs = load_ops(Path(sys.argv[1]))
    print(nq, regs, summarize(ops))
