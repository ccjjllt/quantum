"""Gap + concurrency profile of the eae ancilla bank.

1. Per qubit: max gap (in op lines) between consecutive uses, and use count.
   A "parked cache" word would show a multi-million-line gap.
2. Sliding window (W consecutive ops): max number of distinct bank qubits
   touched. This is a lower bound on how many bank wires must coexist
   (each op touches <=3 qubits, so a window of W ops can cover at most 3W).
3. Also records the top windows (line no + qubit set).
"""
from __future__ import annotations

import re
import sys
from collections import Counter, deque
from pathlib import Path

SKIP = ("APPEND", "REGISTER", "INFO_TAG", "SEMANTIC", "ANNOTATION", "PUSH", "POP")
QRE = re.compile(r"q(\d+)")


def main(path: Path, lo: int, hi: int, W: int) -> None:
    last: dict[int, int] = {}
    maxgap: dict[int, int] = {}
    uses: Counter = Counter()
    win: deque = deque()
    win_count: Counter = Counter()
    best = (0, 0, ())
    n = 0
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            n += 1
            if not line or line.startswith(SKIP):
                continue
            aq = [int(m.group(1)) for m in QRE.finditer(line)]
            aq = [q for q in aq if lo <= q < hi]
            if not aq:
                continue
            for q in aq:
                if q in last:
                    g = n - last[q]
                    if g > maxgap.get(q, 0):
                        maxgap[q] = g
                last[q] = n
                uses[q] += 1
                win.append((n, q))
            while win and n - win[0][0] > W:
                win_count[win.popleft()[1]] -= 1
            for q in aq:
                if win_count[q] == 0:
                    pass
            # count distinct in window
            for q in aq:
                win_count[q] += 1
            distinct = sum(1 for q, c in win_count.items() if c)
            if distinct > best[0]:
                best = (distinct, n, tuple(sorted(q for q, c in win_count.items() if c)))
    print(f"window W={W} ops; max distinct bank qubits in window = {best[0]} at line {best[1]}")
    print("qubits:", best[2])
    print(f"\nper-qubit uses and max gap (op lines) / total lines = {n}")
    for q in sorted(uses):
        print(f"q{q}: uses={uses[q]:7d} max_gap={maxgap.get(q,0):9d}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else 200)
