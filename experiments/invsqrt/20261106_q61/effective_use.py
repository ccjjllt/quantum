"""Effective-use census: at each use of a scratch wire, is the wire identically 0 / 1?

An identically-0 control makes the gate a no-op; an identically-1 control is a plain gate.
Full legal domain, one fixed all-zero HMR branch (branch-dependence is discussed in the
notes; a constant on one branch is not a proof for other branches).
"""
from __future__ import annotations

import collections
import json

import numpy as np

import common

MAXX = 3133452


def main():
    _, ops, gates, stacks = common.load_ops()
    n = MAXX
    q = [0] * 62
    for j in range(22):
        a = np.arange(1, n + 1, dtype=np.uint64)
        bits = ((a >> np.uint64(j)) & np.uint64(1)).astype(np.uint8)
        q[j] = int.from_bytes(np.packbits(bits, bitorder="little").tobytes(), "little")
    mask = (1 << n) - 1
    rows = collections.defaultdict(lambda: collections.Counter())
    details = collections.defaultdict(list)
    for i, (k, qs, p) in enumerate(gates):
        for w in qs:
            if w < 22:
                continue
            v = q[w]
            if v == 0:
                rows[w]["const0"] += 1
                details[w].append([i, "0", ops[i]])
            elif v == mask:
                rows[w]["const1"] += 1
            else:
                rows[w]["varying"] += 1
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
    print(f"{'q':>3} {'const0':>7} {'const1':>7} {'varying':>8} {'total':>6}")
    out = {}
    for w in range(22, 62):
        c = rows[w]
        tot = c["const0"] + c["const1"] + c["varying"]
        print(f"{w:>3} {c['const0']:>7} {c['const1']:>7} {c['varying']:>8} {tot:>6}")
        out[f"q{w}"] = {"const0": c["const0"], "const1": c["const1"],
                        "varying": c["varying"], "total": tot,
                        "const0_ops": details[w]}
    (common.OUT / "effective_use.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
