"""Nonlinear rebuild search at full-rank 62-peak operations.

For a target op and a wire w, ask whether w's value is a cheap function of the other 61
current wire values:

  1. one product of two affine forms          w = L1 & L2            (1 CCX + free CX/X)
  3. one cubic monomial                       w = L1 & L2 & L3       (2 CCX)
  2. a sum of k products                      w = XOR_j (Lj1 & Lj2)  (k CCX)

Affine forms are XOR subsets of the other 61 wires (optionally complemented), built by CX/X.

Reduction used for (1) and (3): if w is the AND of affine forms, each factor equals 1 on
supp(w), so each factor lies in the *cover set*
        A(w) = { L affine in the other 61 wires : supp(V_w) subset of supp(L) } \\ {identically 1, 0}.
A(w) is computed exactly over the full legal domain by one GF(2) elimination on 3.1M-bit
vectors.  |A(w)| is 2^(#free) where #free is the null-space dimension.
"""
from __future__ import annotations

import collections
import json
import sys

import numpy as np

import common

MAXX = 3133452


def simulate(gates, stop, branch_seed=None):
    """Basis-state masks for all 62 wires at op `stop` on one HMR branch."""
    n = MAXX
    q = [0] * 62
    for j in range(22):
        a = np.arange(1, n + 1, dtype=np.uint64)
        b = ((a >> np.uint64(j)) & np.uint64(1)).astype(np.uint8)
        q[j] = int.from_bytes(np.packbits(b, bitorder="little").tobytes(), "little")
    full = (1 << n) - 1
    rng = np.random.default_rng(branch_seed) if branch_seed is not None else None
    for i, (k, qs, p) in enumerate(gates[:stop]):
        if k == "X":
            q[qs[0]] ^= full
        elif k == "R":
            q[qs[0]] = 0
        elif k == "HMR":
            if rng is None:
                q[qs[0]] = 0
            else:
                bits = rng.integers(0, 2, n, dtype=np.uint8)
                q[qs[0]] = int.from_bytes(np.packbits(bits, bitorder="little").tobytes(), "little")
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


def affine_covers(masks, w, full, cap=4096):
    """Affine forms L (subset XOR of the other 61 wires) with supp(V_w) subset of supp(L)."""
    target = masks[w]
    n = len(masks)
    vecs = [(v, masks[v] & target) for v in range(n) if v != w]
    basis = {}
    null = []
    for v, vec in vecs:
        x, c = vec, 1 << v
        while x:
            pbit = x.bit_length() - 1
            if pbit in basis:
                bv, bc = basis[pbit]
                x ^= bv
                c ^= bc
            else:
                basis[pbit] = (x, c)
                break
        else:
            if c:
                null.append(c)
    x, c = target, 0
    while x:
        pbit = x.bit_length() - 1
        if pbit in basis:
            bv, bc = basis[pbit]
            x ^= bv
            c ^= bc
        else:
            return [], {"consistent": False, "rank": len(basis), "null_dim": len(null),
                "enumerated": 0, "covers": 0}

    def expand(cm):
        out = 0
        while cm:
            v = (cm & -cm).bit_length() - 1
            out ^= masks[v]
            cm &= cm - 1
        return out

    sols = [c]
    if len(null) <= 12:
        for bits in range(1, 1 << len(null)):
            cm = c
            for j, nv in enumerate(null):
                if (bits >> j) & 1:
                    cm ^= nv
            sols.append(cm)
            if len(sols) >= cap:
                break
    # L(x)=1 on supp(w) splits into two families:
    #   c=0: XOR a_v V_v = 1   (the particular solution plus null space)
    #   c=1: XOR a_v V_v = 0   (the null space alone), then L = that XOR 1
    covers = {}
    for cm in sols:
        L = expand(cm)
        if L == full or L == 0:
            continue
        covers[L] = (cm, 0)
    for nv in null:
        L = expand(nv) ^ full
        if L == full or L == 0:
            continue
        covers.setdefault(L, (nv, 1))
    ordered = sorted(covers, key=lambda z: z.bit_count())
    return ordered, {"coeffs": [covers[L][0] for L in ordered],
                     "consts": [covers[L][1] for L in ordered],
        "consistent": True, "rank": len(basis), "null_dim": len(null),
        "enumerated": len(sols), "covers": len(covers)}


def analyse(masks, full, cap=4096):
    out = []
    for w in range(len(masks)):
        covers, info = affine_covers(masks, w, full, cap)
        prod = []
        for i in range(len(covers)):
            for j in range(i, len(covers)):
                if covers[i] & covers[j] == masks[w]:
                    prod.append((i, j, i == j))
        cub = []
        if not prod:
            for i in range(len(covers)):
                ai = covers[i]
                for j in range(i, len(covers)):
                    aij = ai & covers[j]
                    if aij & ~masks[w]:
                        continue
                    for k in range(j, len(covers)):
                        if aij & covers[k] == masks[w]:
                            cub.append((i, j, k))
        out.append({"wire": w, "popcount": masks[w].bit_count(), **info,
                    "product": prod[:6], "cubic": cub[:6]})
    return out


def simulate_snapshots(gates, stops, branch_seed=None):
    """One pass through the circuit, snapshotting all 62 masks at each op in `stops`."""
    import numpy as _np
    n = MAXX
    q = [0] * 62
    for j in range(22):
        a = _np.arange(1, n + 1, dtype=_np.uint64)
        b = ((a >> _np.uint64(j)) & _np.uint64(1)).astype(_np.uint8)
        q[j] = int.from_bytes(_np.packbits(b, bitorder="little").tobytes(), "little")
    full = (1 << n) - 1
    rng = _np.random.default_rng(branch_seed) if branch_seed is not None else None
    want = set(stops)
    snaps = {}
    for i, (k, qs, p) in enumerate(gates):
        if i in want:
            snaps[i] = list(q)
        if k == "X":
            q[qs[0]] ^= full
        elif k == "R":
            q[qs[0]] = 0
        elif k == "HMR":
            if rng is None:
                q[qs[0]] = 0
            else:
                bits = rng.integers(0, 2, n, dtype=_np.uint8)
                q[qs[0]] = int.from_bytes(_np.packbits(bits, bitorder="little").tobytes(), "little")
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
    return snaps


def main():
    _, ops, gates, stacks = common.load_ops()
    spec = sys.argv[1:] or ["16750:zero", "16887:zero", "18483:zero"]
    full = (1 << MAXX) - 1
    for item in spec:
        op_s, br_s = item.split(":")
        op = int(op_s)
        seed = None if br_s == "zero" else int(br_s)
        masks = simulate(gates, op, seed)
        rows = analyse(masks, full)
        n_cov = sum(1 for r in rows if r["covers"] > 0)
        n_prod = sum(1 for r in rows if r["product"])
        n_cub = sum(1 for r in rows if r["cubic"])
        big = [(r["wire"], r["covers"], r["null_dim"]) for r in rows if r["null_dim"] > 12]
        print(f"op {op} ({ops[op]}) branch={br_s}: affine-cover wires {n_cov}/62, "
              f"single-product {n_prod}, cubic {n_cub}, null_dim>12 {big[:4]}")
        if n_prod or n_cub:
            for r in rows:
                if r["product"] or r["cubic"]:
                    print(f"   q{r['wire']}: covers={r['covers']} product={r['product']} "
                          f"cubic={r['cubic']}")
        (common.OUT / f"nonlinear_op{op}_b{br_s}.json").write_text(json.dumps(
            {"op": op, "instr": ops[op], "branch": br_s, "rows": rows}, indent=1) + "\n")


if __name__ == "__main__":
    main()
