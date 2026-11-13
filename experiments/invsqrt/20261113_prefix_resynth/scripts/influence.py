"""Influence matrix of a permutation block: which input bit changes which output bit.

Read-only probe.  For each input bit i, flip it on several random bases and mark
every output bit that ever changed.  Reveals operand grouping of an arithmetic
block without knowing its function.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from qsim import Sim, op_table, run  # noqa: E402


def apply_block(table, nq, lo, hi, states):
    sim = Sim(len(states), n_qubits=nq)
    sim.v = states.astype(np.uint64).copy()
    run(sim, table[lo:hi])
    return sim.v


def main() -> None:
    path = Path(sys.argv[1])
    lo = int(sys.argv[2]) if len(sys.argv) > 2 else 650
    hi = int(sys.argv[3]) if len(sys.argv) > 3 else 7031
    nb = int(sys.argv[4]) if len(sys.argv) > 4 else 8
    table, nq = op_table(path)
    rng = np.random.default_rng(9)
    MASK = (1 << 62) - 1

    inf = np.zeros((62, 62), dtype=bool)
    for i in range(62):
        base = rng.integers(0, 2**62, size=nb, dtype=np.uint64) & np.uint64(MASK ^ (1 << i))
        st = np.concatenate([base, base ^ np.uint64(1 << i)])
        out = apply_block(table, nq, lo, hi, st)
        for j in range(62):
            b0 = (out[:nb] >> np.uint64(j)) & np.uint64(1)
            b1 = (out[nb:] >> np.uint64(j)) & np.uint64(1)
            if np.any(b0 != b1):
                inf[i, j] = True

    print("     output bits 61..0")
    for i in range(61, -1, -1):
        row = "".join("#" if inf[i, j] else "." for j in range(61, -1, -1))
        print(f"in{i:>3} {row}  ({int(inf[i].sum())})")


if __name__ == "__main__":
    main()
