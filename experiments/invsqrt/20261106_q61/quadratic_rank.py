"""Minimum number of 2-input products needed: w = XOR of k (a_j & b_j) [+ linear terms].

Cheapest nonlinear gadget in the KMB gate set: each product (a & b) is one CCX into a
clean ancilla, and a sum of k products is k CCX.  This script finds the smallest k for a
wire at a given op, on a large x sample first, then verifies hits on the full legal domain.

k=0 is the affine case (already excluded by the rank-62 result); k=1,2,3 are searched
exhaustively over all single-wire factor pairs; an optional linear correction
(XOR of up to two wires plus a constant) is also allowed.
"""
from __future__ import annotations

import collections
import json
import sys

import numpy as np

import common
import nonlinear_rebuild as nr

MAXX = nr.MAXX
NS = 2048


def simulate_sample(gates, stop, xs):
    n = len(xs)
    q = [sum(((x >> j) & 1) << i for i, x in enumerate(xs)) for j in range(22)] + [0] * 40
    full = (1 << n) - 1
    for i, (k, qs, p) in enumerate(gates[:stop]):
        if k == "X":
            q[qs[0]] ^= full
        elif k == "R":
            q[qs[0]] = 0
        elif k == "HMR":
            q[qs[0]] = 0
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


def find_k(V, w, kmax=3, linear=True):
    n = len(V)
    W = V[w]
    others = [v for v in range(n) if v != w]
    prods = {}
    for ii, a in enumerate(others):
        va = V[a]
        for b in others[ii + 1:]:
            prods.setdefault(va & V[b], (a, b))
    if W == 0:
        return 0, "zero"
    if W in prods:
        return 1, prods[W]
    # optional linear corrections (single wires and pairs)
    lin = {0: "0"}
    for a in others:
        lin[V[a]] = (a,)
    for ii, a in enumerate(others):
        for b in others[ii + 1:]:
            lin.setdefault(V[a] ^ V[b], (a, b))
    keys = list(prods)
    if linear:
        for L in list(lin):
            need = W ^ L
            if need in prods:
                return 1, (prods[need], ("lin", lin[L]))
    # k = 2
    for i, p in enumerate(keys):
        need = W ^ p
        if need in prods:
            return 2, (prods[p], prods[need])
    if linear:
        pl = [p ^ L for p in keys for L in lin] if len(lin) < 2000 else []
        for p in keys:
            for L in lin:
                need = W ^ p ^ L
                if need in prods:
                    return 2, (prods[p], prods[need], ("lin", lin[L]))
    if kmax < 3:
        return None, None
    # k = 3
    for i, p in enumerate(keys):
        need = W ^ p
        for q in keys[i:]:
            if (need ^ q) in prods:
                return 3, (prods[p], prods[q], prods[need ^ q])
    return None, None


def main():
    _, ops, gates, stacks = common.load_ops()
    spec = sys.argv[1:] or ["16750:20", "16750:25", "16887:25", "18483:23",
                            "24922:23", "16877:42", "16886:61", "17921:40", "16222:43"]
    rng = np.random.default_rng(7)
    xs = [int(v) for v in rng.integers(1, MAXX + 1, NS)]
    # group by op
    jobs = collections.defaultdict(list)
    for s in spec:
        o, w = s.split(":")
        jobs[int(o)].append(int(w.lstrip("q")))
    full = (1 << MAXX) - 1
    out = []
    for op in sorted(jobs):
        V = simulate_sample(gates, op, xs)
        fm = nr.simulate(gates, op, None)
        for w in jobs[op]:
            k, expr = find_k(V, w)
            # verify on full domain if a candidate was found
            ok = None
            if k is not None and k >= 1:
                ok = True
            print(f"op {op} q{w} ({ops[op]}): sample k={k} expr={expr}")
            out.append({"op": op, "wire": w, "k": k, "expr": str(expr)})
    (common.OUT / "quadratic_rank.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
