"""Identify the Horner coefficient register by matching wire values to ideal phase bits.

Read-only diagnostic.  At a set of checkpoint ops we compare the 62 wire values
(bit-parallel over all legal x, all-zero HMR branch) against:
  * each bit of N = floor(T_half * 2^35) (the ideal fine-phase fixed point),
  * each of the 41 fine-rotation masks.
Prints an exact-match table (equality on every legal x).
"""
from __future__ import annotations

import json

import numpy as np

import common

CHECKS = [14000, 14200, 14400, 14600, 14800, 14900, 15000, 15100,
          15200, 15246, 15247, 15280, 15282, 15286, 25392, 25400]


def main() -> None:
    ops, gates = common.load_ops()
    n = common.MAXX
    masks0, rops0, rwires0, _ = common.load_masks_full()
    checkpoints = sorted(set(CHECKS) | set(rops0))
    state, touched = common.trace_checkpoints(gates, set(checkpoints))

    N = np.load(common.ROT33 / "N.npy")          # int64, len n, index x-1
    nbits = 34
    nbitmask = []
    for b in range(nbits):
        arr = ((N >> b) & 1).astype(np.uint8)
        nbitmask.append(int.from_bytes(np.packbits(arr, bitorder="little").tobytes(),
                                       "little"))
    masks, rops, rwires, angles = common.load_masks_full()

    print("== wire value == bit_b(N) (all 3,133,452 legal x) ==")
    hits = 0
    for op in CHECKS:
        q = state[op]
        for w in range(common.NQ):
            for b in range(nbits):
                if q[w] == nbitmask[b]:
                    print(f"  op {op:5d} q{w:2d} == N bit {b:2d}")
                    hits += 1
    print("total exact matches:", hits)

    print("\n== rotation mask == some wire value at the same op ==")
    single = 0
    for i, (op, w) in enumerate(zip(rops, rwires)):
        q = state[op]
        eq = [ww for ww in range(common.NQ) if ww != w and q[ww] == masks[i]]
        if eq:
            single += 1
        print(f"  rot{i:2d} op{op} target q{w}: equals wires {eq}")
    print(f"masks equal to another single wire value at their own Z_POW: {single}/41")

    common.OUT.mkdir(parents=True, exist_ok=True)
    (common.OUT / "checkpoint_ops.json").write_text(json.dumps(CHECKS) + "\n")


if __name__ == "__main__":
    main()
