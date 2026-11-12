"""Per-qubit paid-gate census for the eae bank q840..q891 (control vs target).

One pass over the .kmx. Prints, per qubit, the paid gates it takes part in,
split by stage, so the 4 flags can be priced separately from the two 24-bit
accumulator words.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

PAID = ("CCX", "CCZ", "CSWAP", "CCX_CARRY")
SKIP = ("APPEND", "REGISTER", "INFO_TAG", "SEMANTIC", "ANNOTATION", "PUSH", "POP")
QRE = re.compile(r"q(\d+)")
STAGES = ["extract", "synthesis", "convert", "scan", "unconvert", "unsynthesis", "unextract"]


def main(path: Path, lo: int, hi: int) -> None:
    stack: list[str] = []
    stage = None
    ctl: Counter = Counter()
    tgt: Counter = Counter()
    ops: Counter = Counter()
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
            qs = [int(m.group(1)) for m in QRE.finditer(line)]
            aq = [q for q in qs if lo <= q < hi]
            if not aq:
                continue
            for q in aq:
                ops[(stage, q)] += 1
            if op in PAID:
                t = qs[-1]
                for q in aq:
                    (tgt if q == t else ctl)[(stage, q)] += 1

    print("q      word   tot_paid  " + "  ".join(f"{s[:9]:>9s}" for s in STAGES))
    grand = 0
    groups = Counter()
    for q in range(lo, hi):
        word = "A" if q < 864 else ("B" if q < 888 else "flag")
        row = [ctl[(s, q)] + tgt[(s, q)] for s in STAGES]
        tot = sum(row)
        grand += tot
        groups[word] += tot
        print(f"q{q:<5d} {word:6s} {tot:8d}  " + "  ".join(f"{v:9d}" for v in row))
    print(f"\ngrand paid touching bank = {grand}")
    for g, v in groups.items():
        print(f"  group {g}: {v} ({v / grand * 100:.1f}%)")
    print("\nper stage totals (paid, bank-touching):")
    for s in STAGES:
        a = sum(ctl[(s, q)] + tgt[(s, q)] for q in range(lo, hi))
        b = sum(ctl[(s, q)] + tgt[(s, q)] for q in range(888, hi))
        print(f"  {s:14s} {a:7d}   flags-only {b:6d}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]))
