"""Cubic / rank-2 check for the blocked rebuild points.

For a (op, wire) pair: list the affine cover set A(w) on the all-zero branch, then test
    w = L1 & L2                 (1 CCX)
    w = L1 & L2 & L3            (2 CCX, cubic monomial)
    w = (L1 & L2) ^ (L3 & L4)   (2 CCX, rank-2 quadratic)
and report the smallest form found and the cover-set size.
"""
from __future__ import annotations

import json
import sys

import common
import nonlinear_rebuild as nr

CASES = [(24922, 23), (16877, 42), (16886, 61), (17921, 40), (16222, 43),
         (15796, 23), (15925, 27), (16093, 23), (15306, 57), (18483, 52)]


def main():
    _, ops, gates, stacks = common.load_ops()
    full = (1 << nr.MAXX) - 1
    out = []
    for op, w in CASES:
        masks = nr.simulate(gates, op, None)
        covers, info = nr.affine_covers(masks, w, full)
        W = masks[w]
        k1 = k3 = k2 = None
        for i in range(len(covers)):
            for j in range(i, len(covers)):
                if covers[i] & covers[j] == W:
                    k1 = (i, j)
        if k1 is None:
            for i in range(len(covers)):
                cij = covers[i]
                for j in range(i, len(covers)):
                    cij2 = cij & covers[j]
                    if cij2 & ~W:
                        continue
                    for k in range(j, len(covers)):
                        if cij2 & covers[k] == W:
                            k3 = (i, j, k)
                            break
                    if k3:
                        break
                if k3:
                    break
        prods = {}
        for i in range(len(covers)):
            for j in range(i, len(covers)):
                prods[covers[i] & covers[j]] = (i, j)
        for p, ij in prods.items():
            if (W ^ p) in prods:
                k2 = (ij, prods[W ^ p])
                break
        out.append({"op": op, "wire": w, "instr": ops[op], "covers": len(covers),
                    "null_dim": info.get("null_dim"), "k1": bool(k1), "k2": bool(k2),
                    "k3": bool(k3)})
        print(f"op {op} q{w} ({ops[op]}): covers={len(covers)} null_dim={info.get('null_dim')} "
              f"1CCX={bool(k1)} 2CCX_cubic={bool(k3)} 2CCX_rank2={bool(k2)}")
    (common.OUT / "cubic_check.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
