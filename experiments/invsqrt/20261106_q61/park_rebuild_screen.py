"""Cheap-rebuild screen for every parking option that touches the uncovered peak ops.

Uses a 512-x sample state (2 HMR branches) and tests, at each gap's right end, whether the
wire's value is a constant, another wire, or a 2-input AND/XOR/OR of two wires.
"""
from __future__ import annotations

import collections
import json
import random

import common

N = 512
MAXX = 3133452


def states_at(gates, checkpoints):
    rng = random.Random(5)
    xs = [rng.randint(1, MAXX) for _ in range(N)]
    n = N
    q = [sum(((x >> j) & 1) << i for i, x in enumerate(xs)) for j in range(22)] + [0] * 40
    mask = (1 << n) - 1
    cps = set(checkpoints)
    out = {}
    for i, (k, qs, p) in enumerate(gates):
        if i in cps:
            out[i] = list(q)
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
    return out, mask


def cheap(st, w, mask):
    """Return the cheapest expression class found for st[w] in terms of other wires."""
    v = st[w]
    if v == 0:
        return 0, "const0"
    if v == mask:
        return 0, "const1"
    for a in range(62):
        if a == w:
            continue
        if st[a] == v or (st[a] ^ mask) == v:
            return 0, "copy"
        for b in range(a + 1, 62):
            if b == w:
                continue
            va, vb = st[a], st[b]
            if (va & vb) == v or (va ^ vb) == v:
                return 1, "and/xor"
    return 9, "unknown"


def main():
    d = json.loads((common.OUT / "park_missing.json").read_text())
    options = d["candidates"]
    _, ops, gates, stacks = common.load_ops()
    rights = sorted({o["gap"][1] for o in options})
    st, mask = states_at(gates, rights)
    out = []
    for o in options:
        c, why = cheap(st[o["gap"][1]], o["wire"], mask)
        out.append({**o, "screen_cost": c, "screen_why": why})
    # show the best options for the missing ops
    best = sorted(out, key=lambda o: (o["screen_cost"], -o["gain"]))
    print(f"options touching missing ops: {len(out)}")
    for c in (0, 1):
        sel = [o for o in best if o["screen_cost"] == c]
        print(f"screen cost {c}: {len(sel)} options")
        for o in sel[:12]:
            print(f"   q{o['wire']} gap {o['gap']} gain {o['gain']} {o['screen_why']} "
                  f"at {o['gap'][1]}: {o['next_instr']}")
    (common.OUT / "park_rebuild_screen.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
