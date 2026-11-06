"""Random-branch product rank for the three big blocks.

Complements block_rank.py: the all-zero branch can have accidental dependencies;
this script samples a random measurement branch and recomputes the rank of the
actual CCX products on 20,000 random legal x.
"""
from __future__ import annotations

import io
import json
import random
from pathlib import Path

import numpy as np
import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "artifacts/20261106_syed_v9/invsqrt/syed_v9_nofallback.kmb"
OUT = ROOT / "artifacts/20261106_structural_negatives"
BLOCKS = [(21434, 23311, "block1"), (33980, 36370, "block2"), (3429, 14081, "block3")]
N = 20000


def rank(rows):
    basis = []
    for v in rows:
        x = v
        for b, piv in basis:
            if (x >> piv) & 1:
                x ^= b
        if x:
            piv = x.bit_length() - 1
            basis.append((x, piv))
            basis.sort(key=lambda t: -t[1])
    return len(basis)


def run(ops, lo, hi, seed):
    rng = random.Random(seed)
    mask = (1 << N) - 1
    xs = np.array([rng.randint(1, 3133452) for _ in range(N)], dtype=np.uint64)
    q = [int.from_bytes(np.packbits(((xs >> j) & 1).astype(np.uint8), bitorder="little").tobytes(), "little") for j in range(22)] + [0] * 40
    bits = {}
    stack = []
    prods = []
    for i, line in enumerate(ops):
        if i >= hi:
            break
        p = line.split()
        k = p[0]
        qs = [int(t[1:]) for t in p[1:] if t.startswith("q")]
        active = mask
        for s in stack:
            active &= s
        if "if" in p:
            active &= bits.get(int(p[-1][1:]), 0)
        if k == "CCX":
            v = q[qs[0]] & q[qs[1]] & active
            if i >= lo:
                prods.append(v)
            q[qs[2]] ^= v
        elif k == "X":
            q[qs[0]] ^= active
        elif k == "CX":
            q[qs[1]] ^= q[qs[0]] & active
        elif k in {"SWAP", "CSWAP"}:
            a, b = qs[-2:]
            d = (q[a] ^ q[b]) & active
            if k == "CSWAP":
                d &= q[qs[0]]
            q[a] ^= d
            q[b] ^= d
        elif k == "HMR":
            bits[int(p[2][1:])] = rng.getrandbits(N) & mask
            q[qs[0]] &= ~active
        elif k == "R":
            q[qs[0]] &= ~active
        elif k == "PUSH_CONDITION":
            stack.append(bits.get(int(p[-1][1:]), 0))
        elif k == "POP_CONDITION":
            stack.pop()
        elif k in {"BIT_STORE0", "BIT_STORE1", "BIT_INVERT"}:
            bid = int(p[1][1:])
            old = bits.get(bid, 0)
            bits[bid] = old & ~active if k == "BIT_STORE0" else old | active if k == "BIT_STORE1" else old ^ active
        elif k in {"Z", "CZ", "CCZ", "NEG", "Z_POW"}:
            pass
        else:
            raise ValueError(line)
    return len(prods), rank(prods)


def main():
    c = km.Circuit.from_file(BASE)
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    ops = [l for l in buf.getvalue().splitlines() if not l.startswith(("APPEND", "REGISTER"))]
    result = {"baseline": str(BASE.relative_to(ROOT)), "N": N, "branches": [1, 2], "blocks": []}
    for lo, hi, name in BLOCKS:
        rows = [run(ops, lo, hi, seed) for seed in (1, 2)]
        result["blocks"].append({"name": name, "window": [lo, hi],
                                 "ccx": rows[0][0], "ranks": [r[1] for r in rows]})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "random_rank.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
