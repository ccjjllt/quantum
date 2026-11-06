"""Exhaustive local collision test at a chosen checkpoint, for several wires.

For each candidate wire w at checkpoint op c: pack the other 61 wires per legal x, sort, and
count adjacent pairs with identical 61-bit states but different w.  Such a pair is a
counterexample to "w is a deterministic function of the other 61 wires" at that point.

One fixed all-zero HMR branch; basis states only.  HMR outcomes are random coins in this
circuit (see notes), so this is a per-branch statement, not a proof for all branches.
"""
from __future__ import annotations

import json
import sys

import numpy as np

import common

MAXX = 3133452


def state_at(gates, checkpoint):
    n = MAXX
    q = [0] * 62
    for j in range(22):
        a = np.arange(1, n + 1, dtype=np.uint64)
        bits = ((a >> np.uint64(j)) & np.uint64(1)).astype(np.uint8)
        q[j] = int.from_bytes(np.packbits(bits, bitorder="little").tobytes(), "little")
    mask = (1 << n) - 1
    for i, (k, qs, p) in enumerate(gates[:checkpoint]):
        if k in {"X", "R", "HMR"}:
            q[qs[0]] = 0 if k in {"R", "HMR"} else q[qs[0]] ^ mask
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
    return q


def unpack(v, n=MAXX):
    return np.unpackbits(
        np.frombuffer(v.to_bytes((n + 7) // 8, "little"), dtype=np.uint8),
        bitorder="little")[:n]


def main():
    checkpoint = int(sys.argv[1]) if len(sys.argv) > 1 else 15283
    wires = [int(a.lstrip("q")) for a in sys.argv[2:]] or [49, 34, 53, 35, 33]
    _, ops, gates, stacks = common.load_ops()
    q = state_at(gates, checkpoint)
    bits = {w: unpack(v).astype(np.uint64) for w, v in enumerate(q)}
    out = {"checkpoint": checkpoint, "max_x": MAXX, "branch": "all HMR outcomes fixed to 0",
           "wires": {}}
    for w in wires:
        states = np.zeros(MAXX, dtype=np.uint64)
        for j in range(62):
            if j != w:
                states |= bits[j] << np.uint64(j)
        order = np.argsort(states, kind="stable")
        s = states[order]
        d = bits[w][order]
        adj = (s[:-1] == s[1:]) & (d[:-1] != d[1:])
        idx = np.flatnonzero(adj)
        examples = []
        for k in idx[:5]:
            a, b = int(order[k]), int(order[k + 1])
            examples.append({"x_a": a + 1, "x_b": b + 1,
                             "w_a": int(d[k]), "w_b": int(d[k + 1]),
                             "other_61_state": int(states[a])})
        out["wires"][f"q{w}"] = {"collision_pairs": int(idx.size), "examples": examples}
        print(f"q{w}: collision pairs = {int(idx.size)}; examples {examples[:2]}")
    common.OUT.mkdir(parents=True, exist_ok=True)
    (common.OUT / f"collision_op{checkpoint}.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
