"""Cheap proxy: does the (free) row permutation change the structural cost of the
ANGLE tables?  Counts internal nodes of the break-early segment tree that the
official reference QROM (angle_k_reference_circuit.py) walks -- each internal
node is one CCX; the leaf `load`s are free CX.

No simulation: pure numpy on the submitted word table.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

SUB = Path(
    "/Users/zhaohuaxiang/ccjjllt/quantum/artifacts/20261118_inv_sweep/ds/"
    "junmiaotiao_qcc-frontier-20261117r/dfthcsos/submission.npz"
)


def deltas(words: np.ndarray, J: int) -> np.ndarray:
    A, n = words.shape
    K = max(1, math.ceil(n / J))
    pad = np.zeros((A, K * J), dtype=np.int64)
    pad[:, :n] = words
    b = pad.reshape(A, K, J).transpose(1, 0, 2)
    d = b.copy()
    d[1:] ^= b[:-1]
    return d


def tree_cost(delta: np.ndarray) -> tuple[int, int]:
    """(#internal nodes, #leaves) of the break-early binary segment tree."""
    A, J = delta.shape
    nb = (A - 1).bit_length()
    internal = 0
    leaves = 0

    def node(lo: int, hi: int) -> None:
        nonlocal internal, leaves
        if lo >= A:
            return
        if hi <= A and (hi - lo == 1 or np.all(delta[lo:hi] == delta[lo])):
            leaves += 1
            return
        mid = (lo + hi) // 2
        if A <= mid:
            node(lo, mid)
            return
        internal += 1
        node(lo, mid)
        node(mid, hi)

    half = 1 << (nb - 1)
    node(0, half)
    node(half, 2 * half)
    return internal, leaves


def main() -> None:
    d = np.load(SUB, allow_pickle=False)
    words = d["angle_words"]
    A, n = words.shape
    print(f"table {words.shape}, brot=8, oracle rows A={A}")
    for J in (5, 8, 15):
        ds = deltas(words, J)
        base = sum(tree_cost(x)[0] for x in ds)

        # Permutation 1: sort the two-body rows (blocks of 143) and the 76
        # one-body rows by their word vector.  Metrics are invariant.
        perm = np.arange(A)
        one = np.lexsort(words[:76].T[::-1])
        perm[:76] = one
        for r in range(8):
            s = 76 + r * 143
            blk = np.arange(s, s + 143)
            perm[s:s + 143] = blk[np.lexsort(words[blk].T[::-1])]
        ds2 = deltas(words[perm], J)
        srt = sum(tree_cost(x)[0] for x in ds2)

        # Permutation 2: reverse the two-body blocks only (a sanity check that
        # the proxy is order-sensitive at all).
        perm2 = np.arange(A)
        for r in range(8):
            s = 76 + r * 143
            perm2[s:s + 143] = perm2[s:s + 143][::-1]
        ds3 = deltas(words[perm2], J)
        rev = sum(tree_cost(x)[0] for x in ds3)

        print(f"  J={J:>2}: K={len(ds):>2} internal nodes  natural={base:>6}  "
              f"value-sorted={srt:>6} ({srt / base - 1:+.1%})  block-reversed={rev:>6} "
              f"({rev / base - 1:+.1%})")


if __name__ == "__main__":
    main()
