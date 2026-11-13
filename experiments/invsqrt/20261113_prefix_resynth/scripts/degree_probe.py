"""Test the algebraic degree of block B (op 650..7031) over GF(2).

A degree-d function has vanishing (d+1)-th derivatives.  A multiplier (or any
bilinear form) has degree 2; 2nd derivatives are then constant in the base
point.  This distinguishes "arithmetic block" from "linear routing".
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
    rng = np.random.default_rng(5)
    nb = 12

    def bit(i):
        return np.uint64(1) << np.uint64(i)

    for (ui, vi) in ((14, 15), (14, 23), (0, 14), (24, 25)):
        u, v = bit(ui), bit(vi)
        base = rng.integers(0, 2**62, size=nb, dtype=np.uint64)
        base = base & np.uint64(((1 << 62) - 1) ^ int(u | v))
        states = np.concatenate([base, base ^ u, base ^ v, base ^ u ^ v])
        out = apply_block(table, nq, lo, hi, states)
        d2 = out[:nb] ^ out[nb:2 * nb] ^ out[2 * nb:3 * nb] ^ out[3 * nb:]
        print(f"2nd derivative along ({ui},{vi}): distinct values = {len(set(d2.tolist()))}, "
              f"popcounts {sorted({bin(int(x)).count('1') for x in d2})}")

    # degree-3 test: third difference along three directions
    for (ui, vi, wi) in ((14, 15, 16), (14, 0, 1), (24, 25, 26)):
        u, v, w = bit(ui), bit(vi), bit(wi)
        base = rng.integers(0, 2**62, size=nb, dtype=np.uint64) & np.uint64(((1 << 62) - 1) ^ int(u | v | w))
        states = []
        for m in range(8):
            s = base.copy()
            if m & 1:
                s = s ^ u
            if m & 2:
                s = s ^ v
            if m & 4:
                s = s ^ w
            states.append(s)
        out = apply_block(table, nq, lo, hi, np.concatenate(states))
        d3 = out[:nb].copy()
        for k in range(1, 8):
            d3 = d3 ^ out[k * nb:(k + 1) * nb]
        print(f"3rd derivative along ({ui},{vi},{wi}): distinct = {len(set(d3.tolist()))}, "
              f"max popcount {max(bin(int(x)).count('1') for x in d3)}")


if __name__ == "__main__":
    main()
