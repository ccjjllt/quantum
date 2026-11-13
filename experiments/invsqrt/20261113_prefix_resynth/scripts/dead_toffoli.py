"""Domain-exact dead-Toffoli test for the prefix.

For every Toffoli-class op in [0:CUT), delete it and compare the *full state at
the cut* (62 qubit values, every classical bit, and the tracked phase) against
the baseline, over the reachable domain.  Everything after CUT is untouched, so
a deletion whose cut state is unchanged for all x and all HMR branches is an
exactly sound edit -- and the mean Toffoli count drops by that gate.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import qsim  # noqa: E402
from qsim import Sim, op_table, run  # noqa: E402

MAX_X = 3 * (2**10 - 2) ** 2
TOFF = {"CCX", "CCZ", "CSWAP"}


def state_at(table, nq, cut, xs, skip=None):
    sim = Sim(len(xs), n_qubits=nq)
    sim.v = xs.copy()
    if skip is None:
        run(sim, table, limit=cut)
    else:
        run(sim, table[:skip])
        run(sim, table[skip + 1:cut])
    return sim.v.copy(), sim.b.copy(), sim.phase.copy()


def main() -> None:
    path = Path(sys.argv[1])
    cut = int(sys.argv[2]) if len(sys.argv) > 2 else 8546
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 1200
    table, nq = op_table(path)
    rng = np.random.default_rng(31)
    xs = np.unique(np.concatenate([np.arange(1, 801, dtype=np.uint64),
                                   rng.integers(801, MAX_X, size=n, dtype=np.uint64)]))
    gates = [i for i in range(cut) if table[i][0] in TOFF]
    print(f"prefix Toffoli-class ops below {cut}: {len(gates)} "
          f"(CCX {sum(1 for i in gates if table[i][0] == 'CCX')}, "
          f"CSWAP {sum(1 for i in gates if table[i][0] == 'CSWAP')})")

    for mode in ("value", "zero"):
        qsim.HMR_MODE = mode
        v0, b0, p0 = state_at(table, nq, cut, xs)
        same = []
        for g in gates:
            v, b, p = state_at(table, nq, cut, xs, skip=g)
            if np.array_equal(v, v0) and np.array_equal(b, b0) and np.array_equal(p, p0):
                same.append((g, table[g]))
        print(f"mode={mode}: deletions that leave the cut state identical: {len(same)}")
        for s in same[:20]:
            print("   ", s)


if __name__ == "__main__":
    main()
