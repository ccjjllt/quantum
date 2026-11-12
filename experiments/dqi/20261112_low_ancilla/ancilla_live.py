"""Ancilla live intervals and peak simultaneity from a .kmx stream. Read-only."""
from __future__ import annotations
import re
import sys
from pathlib import Path

Q = re.compile(r"\bq(\d+)\b")
SKIP = ("APPEND", "REGISTER", "INFO_TAG", "SEMANTIC", "ANNOTATION")


def main(path: Path, base: int) -> None:
    first: dict[int, int] = {}
    last: dict[int, int] = {}
    uses: dict[int, int] = {}
    n = 0
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            n += 1
            if line.startswith(SKIP):
                continue
            for q in Q.findall(line):
                i = int(q)
                if i < base:
                    continue
                if i not in first:
                    first[i] = n
                last[i] = n
                uses[i] = uses.get(i, 0) + 1
    print(f"lines={n} ancilla_used={len(first)}")
    items = sorted(first)
    print("index first last uses")
    for i in items:
        print(i, first[i], last[i], uses[i])
    # peak overlap
    ev = []
    for i in items:
        ev.append((first[i], 1))
        ev.append((last[i] + 1, -1))
    ev.sort()
    cur = peak = 0
    peak_at = None
    for pos, d in ev:
        cur += d
        if cur > peak:
            peak, peak_at = cur, pos
    print(f"peak_live={peak} at line {peak_at}")
    # live at key stage boundaries is printed as-is; total distinct ancilla above
    print(f"distinct_ancilla={len(items)} peak={peak} slack={len(items) - peak}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 840)
