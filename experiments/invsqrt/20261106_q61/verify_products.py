"""Verify the k=1 product rebuilds on several HMR branches, full legal domain.

For each (op, wire) with a single-product cover found on the all-zero branch, re-solve the
cover on random branches and check whether the SAME affine factors still multiply to the
wire value.  A relation that survives every branch is structural (the circuit really
computes w as that product); one that does not is branch-specific and unusable.
"""
from __future__ import annotations

import json
import sys

import common
import nonlinear_rebuild as nr

CASES = [(16750, [20, 25, 26, 27]), (16887, [25, 27])]


def coeff_of(masks, w, L, n=62):
    """Recover the wire-index set whose XOR equals mask L (exact, via the wire masks)."""
    import functools
    basis = {}
    for v in range(n):
        if v == w:
            continue
        x, c = masks[v], 1 << v
        while x:
            p = x.bit_length() - 1
            if p in basis:
                bv, bc = basis[p]
                x ^= bv
                c ^= bc
            else:
                basis[p] = (x, c)
                break
    x, c = L, 0
    while x:
        p = x.bit_length() - 1
        if p not in basis:
            return None
        bv, bc = basis[p]
        x ^= bv
        c ^= bc
    return c


def main():
    _, ops, gates, stacks = common.load_ops()
    full = (1 << nr.MAXX) - 1
    rows = []
    for op, wires in CASES:
        ref = nr.simulate(gates, op, None)
        for w in wires:
            covers, info = nr.affine_covers(ref, w, full)
            pair = None
            for i in range(len(covers)):
                for j in range(i, len(covers)):
                    if covers[i] & covers[j] == ref[w]:
                        pair = (info["coeffs"][i], info["coeffs"][j],
                                info["consts"][i], info["consts"][j])
                        break
                if pair:
                    break
            if not pair:
                continue
            c1, c2, k1c, k2c = pair
            entry = {"op": op, "wire": w,
                     "factors": [[v for v in range(62) if (c1 >> v) & 1],
                                 [v for v in range(62) if (c2 >> v) & 1]],
                     "complemented": [k1c, k2c],
                     "branches": {}}
            for br in (None, 1, 2):
                m = nr.simulate(gates, op, br)
                L1 = full if k1c else 0
                for v in range(62):
                    if (c1 >> v) & 1:
                        L1 ^= m[v]
                L2 = full if k2c else 0
                for v in range(62):
                    if (c2 >> v) & 1:
                        L2 ^= m[v]
                entry["branches"][str(br)] = bool(L1 & L2 == m[w])
            rows.append(entry)
            print(f"op {op} q{w}: factors of size {bin(c1).count('1')},{bin(c2).count('1')} "
                  f"holds on branches {entry['branches']}")
    (common.OUT / "verify_products.json").write_text(json.dumps(rows, indent=1) + "\n")


if __name__ == "__main__":
    main()
