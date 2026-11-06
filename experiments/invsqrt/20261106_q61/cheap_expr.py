"""Search for a cheap exact expression of one wire's value in terms of other wires.

At a given operation index, test over the full legal domain whether wire w equals
  V, ~V, V&V', ~V&V', V&~V', ~V&~V', V^V', ~(V^V')
for other wires V,V'.  "~" is bitwise complement inside the legal-x mask.

One fixed all-zero HMR branch; a hit here is an exact identity on that branch (and, when
the relation is structural, on every branch -- checked separately).
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
    for k, qs, p in gates[:checkpoint]:
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


def find(q, w, mask):
    v = q[w]
    nv = v ^ mask
    hits = []
    for a in range(62):
        if a == w:
            continue
        va = q[a]
        if va == v:
            hits.append(("eq", a))
        if (va ^ mask) == v:
            hits.append(("not", a))
        for b in range(a + 1, 62):
            if b == w:
                continue
            vb = q[b]
            if (va & vb) == v:
                hits.append(("and", a, b))
            if (va & (vb ^ mask)) == v:
                hits.append(("and_not", a, b))
            if ((va ^ mask) & vb) == v:
                hits.append(("not_and", a, b))
            if (va ^ vb) == v:
                hits.append(("xor", a, b))
            if ((va ^ vb) ^ mask) == v:
                hits.append(("xnor", a, b))
    return hits


def main():
    pairs = []
    for arg in sys.argv[1:]:
        op, w = arg.split(":")
        pairs.append((int(op), int(w.lstrip("q"))))
    _, ops, gates, stacks = common.load_ops()
    mask = (1 << MAXX) - 1
    out = {}
    for op, w in pairs:
        q = state_at(gates, op)
        hits = find(q, w, mask)
        out[f"op{op}_q{w}"] = hits
        print(f"op {op} q{w} ({ops[op] if op < len(ops) else 'END'}): {len(hits)} cheap expressions -> {hits[:12]}")
    common.OUT.mkdir(parents=True, exist_ok=True)
    (common.OUT / "cheap_expressions.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
