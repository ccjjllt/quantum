"""Multi-branch simulation: is a wire identically 0 at a checkpoint on *every* HMR branch?

Random HMR outcomes (many branches), full legal domain, basis states only.  A wire that is
0 on every branch at a checkpoint (and untouched across the surrounding stretch) can be
reset for free with no phase effect.
"""
from __future__ import annotations

import json
import random
import sys

import numpy as np

import common

MAXX = 3133452


def run_branch(gates, hmr_bits, checkpoints, wires):
    """hmr_bits[i] is either None (deterministic 0) or a mask of x with outcome 1."""
    n = MAXX
    q = [0] * 62
    for j in range(22):
        a = np.arange(1, n + 1, dtype=np.uint64)
        bits = ((a >> np.uint64(j)) & np.uint64(1)).astype(np.uint8)
        q[j] = int.from_bytes(np.packbits(bits, bitorder="little").tobytes(), "little")
    mask = (1 << n) - 1
    cps = set(checkpoints)
    out = {}
    for i, (k, qs, p) in enumerate(gates):
        if i in cps:
            out[i] = {w: q[w] for w in wires}
        if k in {"X", "R", "HMR"}:
            if k == "R":
                q[qs[0]] = 0
            elif k == "HMR":
                q[qs[0]] = hmr_bits.get(i, 0)
            else:
                q[qs[0]] ^= mask
        elif k == "CX":
            q[qs[1]] ^= q[qs[0]]
        elif k == "SWAP":
            q[qs[0]], q[qs[1]] = q[qs[1]], q[qs[0]]
        elif k == "CSWAP":
            c, a, b = qs
            d = (q[a] ^ q[b]) & q[c]
            q[a] ^= d
            q[b] ^= d
        elif k == "CCX":
            q[qs[2]] ^= q[qs[0]] & q[qs[1]]
    return out


def main():
    spec = [a for a in sys.argv[1:]] or ["28380:q50", "28383:q41", "28415:q23"]
    pairs = [(int(a.split(":")[0]), int(a.split(":")[1].lstrip("q"))) for a in spec]
    _, ops, gates, stacks = common.load_ops()
    cps = [p[0] for p in pairs]
    wires = sorted({p[1] for p in pairs})
    hmr_ops = [i for i, (k, qs, p) in enumerate(gates) if k == "HMR"]
    rng = random.Random(11)
    mask = (1 << MAXX) - 1
    ever_one = {i: {w: False for w in wires} for i in cps}
    ever_zero = {i: {w: True for w in wires} for i in cps}
    snapshots = []
    for b in range(6):
        bits = {}
        for i in hmr_ops:
            if b == 0:
                bits[i] = 0
            else:
                # random outcome per x: build a random mask of density 1/2
                r = np.random.default_rng(1000 + b * 97 + i)
                bits[i] = int.from_bytes(np.packbits(r.integers(0, 2, MAXX, dtype=np.uint8),
                                                     bitorder="little").tobytes(), "little")
        res = run_branch(gates, bits, cps, wires)
        row = {"branch": b}
        for i in cps:
            row[i] = {f"q{w}": int(res[i][w].bit_count()) for w in wires}
            for w in wires:
                if res[i][w] != 0:
                    ever_zero[i][w] = False
        snapshots.append(row)
        print(row, flush=True)
    print("\nidentically zero at checkpoint on every branch:")
    for i in cps:
        for w in wires:
            print(f"  op {i} q{w}: zero_always={ever_zero[i][w]}")


if __name__ == "__main__":
    main()
