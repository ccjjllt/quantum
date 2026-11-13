"""Bisect the first op where qsim and km.Simulator disagree (debug aid)."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from qsim import Sim, op_table, run  # noqa: E402
from debug_qsim import flat_line_index, kmx_lines, km_state  # noqa: E402


def main() -> None:
    path = Path(sys.argv[1])
    lo, hi = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (1, 36389)
    xs = [int(a) for a in sys.argv[4].split(",")] if len(sys.argv) > 4 else [2]
    lines = kmx_lines(path)
    flat = flat_line_index(lines)
    table, nq = op_table(path)

    def mismatch(cut):
        sim = Sim(len(xs), n_qubits=nq)
        sim.v = np.array(xs, dtype=np.uint64)
        run(sim, table, limit=cut)
        mine = np.stack([(sim.v >> np.uint64(q)) & np.uint64(1) for q in range(nq)], axis=0).astype(bool)
        theirs = km_state(lines, flat, cut, xs)
        return not np.array_equal(mine, theirs)

    assert mismatch(hi), "no mismatch at hi"
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if mismatch(mid):
            hi = mid
        else:
            lo = mid
    print(f"first bad op = {hi}: {table[hi - 1]}")
    for k in range(max(0, hi - 4), min(len(table), hi + 2)):
        print(f"  {k}: {table[k]}")


if __name__ == "__main__":
    main()
