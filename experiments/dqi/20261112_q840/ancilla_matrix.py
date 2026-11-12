"""Per-(stage, qubit) op census for the eae ancilla bank q840..q891.

Prints a matrix: rows = stage, cols = qubit, value = CCX count (and total ops).
Also prints, per stage, the exact subset of ancilla touched, plus a
per-qubit "target-only vs control-only" split, to separate working data
(transformed in place) from storage (read-only in the middle stages).
"""
from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

PAID = ("CCX", "CCZ", "CSWAP", "CCX_CARRY")
SKIP = ("APPEND", "REGISTER", "INFO_TAG", "SEMANTIC", "ANNOTATION", "PUSH", "POP")
QRE = re.compile(r"q(\d+)")
STAGES = ["mask_projection", "initial", "extract", "synthesis", "convert", "scan",
          "unconvert", "unsynthesis", "unextract", "uninitial", "restore_masks"]


def main(path: Path, lo: int, hi: int) -> None:
    stack: list[str] = []
    stage = None
    tot: Counter = Counter()          # (stage, q) -> ops
    tgt: Counter = Counter()          # (stage, q) -> times q is the target of a paid gate
    ctl: Counter = Counter()          # (stage, q) -> times q is a control of a paid gate
    cx_out: Counter = Counter()       # (stage, q) as CX control  (fan-out = read)
    cx_in: Counter = Counter()        # (stage, q) as CX target   (write)
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("INFO_TAG "):
                try:
                    tag = line.strip().split('"', 2)[1]
                except IndexError:
                    continue
                if tag.startswith("@enter:"):
                    name = tag[7:]
                    if stage is None:
                        stage = name
                    stack.append(name)
                elif tag.startswith("@exit:") and stack:
                    stack.pop()
                    if not stack:
                        stage = None
                continue
            if not line or line.startswith(SKIP):
                continue
            parts = line.split()
            op = parts[0]
            qs = [int(m.group(1)) for m in QRE.finditer(line)]
            aq = [q for q in qs if lo <= q < hi]
            if not aq:
                continue
            for q in aq:
                tot[(stage, q)] += 1
            if op in PAID:
                t = qs[-1]
                for q in aq:
                    if q == t:
                        tgt[(stage, q)] += 1
                    else:
                        ctl[(stage, q)] += 1
            elif op == "CX" and len(qs) == 2:
                a, b = qs
                if lo <= a < hi:
                    cx_out[(stage, a)] += 1
                if lo <= b < hi:
                    cx_in[(stage, b)] += 1

    qs_all = list(range(lo, hi))
    print("### touched-ancilla subset per stage + paid totals")
    for st in STAGES:
        used = [q for q in qs_all if tot[(st, q)]]
        p = sum(tgt[(st, q)] + ctl[(st, q)] for q in qs_all)
        if not used:
            print(f"{st:16s} none")
            continue
        rng = f"q{min(used)}..q{max(used)}" if used == qs_all else ",".join(f"q{q}" for q in used)
        print(f"{st:16s} paid_touching={p:7d} n_q={len(used):3d} set={rng if len(used)<=8 else (rng if used==qs_all else f'{len(used)} qubits, not the full bank')}")
    print("\n### matrix: paid-control / paid-target / CX-out / CX-in / total  per (stage,q)")
    hdr = "stage".ljust(16) + "".join(f"q{q:<8d}" for q in qs_all)
    print(hdr)
    for st in STAGES:
        row = st.ljust(16)
        for q in qs_all:
            t_ = tot[(st, q)]
            row += f"{ctl[(st,q)]:5d}/{tgt[(st,q)]:<3d}" if t_ else "    .    "
        print(row)
    print("\n### CX fan-out (read) / fan-in (write) per (stage,q)   fmt out/in")
    print(hdr)
    for st in STAGES:
        row = st.ljust(16)
        for q in qs_all:
            if tot[(st, q)]:
                row += f"{cx_out[(st,q)]:5d}/{cx_in[(st,q)]:<3d}"
            else:
                row += "    .    "
        print(row)


if __name__ == "__main__":
    main(Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]))
