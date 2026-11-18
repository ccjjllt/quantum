"""Tape surgery on a .kmb: replace an instruction range with a supplied instruction list.

The .kmb is a struct-of-arrays file (see vqcc_ir.py). An instruction range [a, b) maps to a
contiguous range in every operand array, so a replacement is a numpy concatenation per packet,
never a per-instruction decode of the 57M-instruction tape.

    c = ir.Circuit.read(src)
    new = ir.Circuit.from_ops([...], registers=[])      # the replacement, in tape order
    out = splice(c, a, b, new)
    out.write(dst)

Checks performed (all cheap, all before writing):
  * the replacement's condition-stack depth at its end equals the tape's depth at `a`
    (the stack is simulator state; a replacement must not leak or consume a condition);
  * the replacement never pops below depth 0;
  * qubit / bit ids stay inside the tape's width;
  * the spliced circuit re-validates through Circuit._check() and re-reads.

A null splice (new = c.slice(a, b)) must reproduce the source byte for byte; that is the
round-trip test that proves the toolchain before any semantic change is attempted.
"""
from __future__ import annotations

import sys

import numpy as np

import vqcc_ir as ir

PACKETS = ("qqq0", "qqq1", "qqq2", "qq0", "qq1", "q0", "b0", "bc", "angles")


def splice(c: ir.Circuit, a: int, b: int, new: ir.Circuit) -> ir.Circuit:
    if not (0 <= a <= b <= c.num_ops):
        raise ValueError(f"bad range [{a}, {b}) of {c.num_ops}")
    t_new = new.types
    d_new = np.cumsum(ir.LPUSH[t_new].astype(np.int64) - ir.LPOP[t_new].astype(np.int64))
    if len(d_new) and d_new.min() < 0:
        raise ValueError("replacement pops an empty condition stack")
    depth_new = int(d_new[-1]) if len(d_new) else 0
    if c.depth(a) + depth_new != c.depth(b):
        raise ValueError(
            f"condition depth {c.depth(a)} + {depth_new} != tape depth at b ({c.depth(b)})")
    if new._max_id(True) >= c.num_qubits or new._max_id(False) >= c.num_bits:
        raise ValueError("replacement touches qubits/bits outside the tape's width")

    parts = []
    if a:
        parts.append(c.slice(0, a, allow_open=True))
    parts.append(new)
    if b < c.num_ops:
        parts.append(c.slice(b, c.num_ops, allow_open=True))
    out = ir.Circuit.concat(parts)
    out.registers = c.registers
    out._check()
    return out


def splice_ops(c: ir.Circuit, a: int, b: int, ops) -> tuple[ir.Circuit, int, int]:
    """Convenience: replacement given as ir.from_ops() instructions. Returns (circuit, n_old, n_new)."""
    new = ir.Circuit.from_ops(ops, registers=[])
    return splice(c, a, b, new), b - a, new.num_ops


def main(argv: list[str]) -> int:
    """CLI: splice.py SRC DST A B [--null]  (null = round-trip test, writes the identical tape)."""
    src, dst, a, b = argv[0], argv[1], int(argv[2]), int(argv[3])
    c = ir.Circuit.read(src)
    sha_src = c.sha256()
    if "--null" in argv:
        new = c.slice(a, b, allow_open=True)
    else:
        raise SystemExit("only --null is implemented here; build replacements in a kernel")
    out = splice(c, a, b, new)
    sha_out = out.write(dst)
    print(f"src {srclen(c)} ops {c.num_ops} sha {sha_src}")
    print(f"dst ops {out.num_ops} sha {sha_out} identical={sha_out == sha_src}")
    return 0 if sha_out == sha_src else 1


def srclen(c: ir.Circuit) -> str:
    return f"{c.num_qubits}q/{c.num_bits}b"


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
