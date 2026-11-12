"""Wrap selected unconditional CCX gates in an existing classical condition.

Reads a .kmb, writes a .kmx with `PUSH_CONDITION if <bit>` / `POP_CONDITION`
around each requested flat op index.  Used to test whether moving a gate behind
the condition of its only (conditional) consumer preserves the phase.

Usage: python wrap_cond.py in.kmb out.kmx OP:BIT [OP:BIT ...]
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import kickmix as km


def main() -> None:
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    edits = {}
    for e in sys.argv[3:]:
        op, bit = e.split(":")
        edits[int(op)] = bit
    c = km.Circuit.from_file(str(src), format="auto")
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    flat = [i for i, l in enumerate(lines)
            if l.split() and l.split()[0] not in ("APPEND_TO_REGISTER", "REGISTER")]
    ins: dict[int, list[str]] = {}
    for op, bit in edits.items():
        li = flat[op]
        ins.setdefault(li, []).extend([f"PUSH_CONDITION if {bit}", None])
    out = []
    for i, l in enumerate(lines):
        if i in ins:
            out.append(ins[i][0])
            out.append(l)
            out.append("POP_CONDITION")
        else:
            out.append(l)
    dst.write_text("\n".join(out) + "\n")
    print(f"wrote {dst} with {len(edits)} wrapped gates: "
          f"{', '.join(f'{k}->{v}' for k, v in edits.items())}")


if __name__ == "__main__":
    main()
