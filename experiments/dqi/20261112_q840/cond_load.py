"""Do the eae ancilla qubits get (re)loaded from classical bits, or only from quantum gates?

Streams .kmx tracking PUSH_CONDITION/POP_CONDITION depth. For ops touching the
ancilla bank it records whether the op is classically conditioned and whether the
ancilla qubit is a destination (target) or a source (control).

Also records, per stage boundary (top-level @enter/@exit line), how many ancilla
are "written" (destination) in each stage -- a quantum stage that ends with the
bank holding classical data can reload it; one that ends holding a quantum state
cannot.
"""
from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

SKIP = ("APPEND", "REGISTER", "INFO_TAG", "SEMANTIC", "ANNOTATION")
QRE = re.compile(r"q(\d+)")
PAID = ("CCX", "CCZ", "CSWAP", "CCX_CARRY")


def main(path: Path, lo: int, hi: int) -> None:
    stack: list[str] = []
    stage = None
    depth = 0
    cond = Counter()      # (stage, op, role) -> n    with classical condition
    uncond = Counter()    # same, unconditioned
    writes = Counter()    # (stage, q) -> destination count
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("INFO_TAG "):
                try:
                    tag = line.strip().split('"', 2)[1]
                except IndexError:
                    continue
                if tag.startswith("@enter:"):
                    if stage is None:
                        stage = tag[7:]
                    stack.append(tag[7:])
                elif tag.startswith("@exit:") and stack:
                    stack.pop()
                    if not stack:
                        stage = None
                continue
            if not line or line.startswith(SKIP):
                continue
            parts = line.split()
            op = parts[0]
            if op == "PUSH_CONDITION":
                depth += 1
                continue
            if op == "POP_CONDITION":
                depth -= 1
                continue
            qs = [int(m.group(1)) for m in QRE.finditer(line)]
            aq = [q for q in qs if lo <= q < hi]
            if not aq:
                continue
            dst = qs[-1] if qs else -1
            role = "dst" if (lo <= dst < hi) else "src"
            (cond if depth else uncond)[(stage, op, role)] += 1
            if lo <= dst < hi:
                writes[(stage, dst)] += 1

    print(f"### classically-conditioned ops touching ancilla (depth>0)")
    for (st, op, role), c in sorted(cond.items(), key=lambda kv: -kv[1]):
        print(f"{str(st):16s} {op:10s} {role:4s} {c}")
    print(f"\n### unconditioned ops touching ancilla (depth==0)")
    for (st, op, role), c in sorted(uncond.items(), key=lambda kv: -kv[1]):
        print(f"{str(st):16s} {op:10s} {role:4s} {c}")
    print("\n### destination writes per (stage,q), nonzero only")
    for st in ["extract", "synthesis", "convert", "scan", "unconvert", "unsynthesis", "unextract"]:
        row = [(q, writes[(st, q)]) for q in range(lo, hi) if writes[(st, q)]]
        print(f"{st:12s} n_q={len(row):3d} total={sum(c for _, c in row):7d} " +
              " ".join(f"q{q}:{c}" for q, c in row[:14]) + (" ..." if len(row) > 14 else ""))


if __name__ == "__main__":
    main(Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]))
