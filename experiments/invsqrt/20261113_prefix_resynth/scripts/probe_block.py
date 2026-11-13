"""Probe block B (op 650..7031) as a 62-bit permutation: affine? multiplier? etc.

Read-only structural probe.  Runs arbitrary basis inputs through the block,
which is legal because those ops are pure classical permutation gates.
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
    table, nq = op_table(path)
    rng = np.random.default_rng(3)

    # affine test
    f0 = apply_block(table, nq, lo, hi, np.array([0], dtype=np.uint64))[0]
    e = np.array([np.uint64(1) << np.uint64(i) for i in range(62)], dtype=np.uint64)
    fe = apply_block(table, nq, lo, hi, e)
    basis = fe ^ f0
    rand = rng.integers(0, 2**62, size=200, dtype=np.uint64)
    fr = apply_block(table, nq, lo, hi, rand)
    cols = np.zeros((62, 200), dtype=np.uint64)
    for i in range(62):
        bit = ((rand >> np.uint64(i)) & np.uint64(1)).astype(bool)
        cols[i] = np.where(bit, basis[i], np.uint64(0))
    pred = f0 ^ np.bitwise_xor.reduce(cols, axis=0)
    print(f"block [{lo}:{hi}) affine? mismatches {int(np.count_nonzero(pred != fr))}/200")

    # how many output bits depend on input bit i (affine part)
    print("affine column weights (input bit -> popcount of f(e_i)^f(0)):",
          [bin(int(x)).count("1") for x in basis])


if __name__ == "__main__":
    main()
