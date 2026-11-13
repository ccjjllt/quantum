"""Validate qsim's full-circuit phase against the official full-domain tabulation.

The circuit is v-independent by construction (each HMR kickback is exactly
cancelled by its corrections), so the tracked phase must be the same for every
branch.  Repeating the run with four outcome conventions therefore double-checks
the model: all four must equal km.Simulator's tabulated error.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import qsim  # noqa: E402
from qsim import Sim, op_table, run  # noqa: E402

MAX_X = 3 * (2**10 - 2) ** 2
MASK64 = (1 << 64) - 1
WIDTH = 22


def main() -> None:
    circ = Path(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
    dense_max = int(sys.argv[3]) if len(sys.argv) > 3 else 6000
    table, nq = op_table(circ)
    ref = np.load(Path(__file__).resolve().parents[4] / "artifacts/20261112_newfamily_census/base_full.npz")
    rng = np.random.default_rng(7)
    xs = np.unique(np.concatenate([np.arange(1, dense_max + 1, dtype=np.uint64),
                                   rng.integers(dense_max + 1, MAX_X, size=n, dtype=np.uint64)]))
    target = np.array([((math.isqrt((1 << 130) // int(x)) + 1) >> 1) & MASK64 for x in xs], dtype=np.uint64)
    refe = ref["err"][xs.astype(np.int64) - 1]

    results = {}
    for mode in ("value", "zero", "hash"):
        qsim.HMR_MODE = mode
        sim = Sim(len(xs), n_qubits=nq)
        sim.v = xs.copy()
        run(sim, table)
        err = (sim.phase - target).view(np.int64)
        bad = int(np.count_nonzero(err != refe))
        results[mode] = (err.copy(), bad)
        print(f"mode={mode:>5}: phase mismatches vs km tabulation {bad}/{len(xs)}")

    a = results["value"][0]
    b = results["zero"][0]
    c = results["hash"][0]
    print(f"branch-independence: value vs zero {int(np.count_nonzero(a != b))}, "
          f"value vs hash {int(np.count_nonzero(a != c))}")
    lib = results["value"][0]
    if results["value"][1]:
        i = int(np.argmax(lib != refe))
        print("first mismatch x:", int(xs[i]), "mine", int(lib[i]), "ref", int(refe[i]))


if __name__ == "__main__":
    main()
