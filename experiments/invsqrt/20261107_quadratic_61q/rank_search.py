"""Try to lower the product rank of a fitted quadratic form using kernel elements.

On a finite sample the monomial features are linearly dependent: c and c^k represent the
same function whenever the feature XOR of k is zero.  The echelon solution is one
representative; a different representative can have a smaller quadratic rank.  We collect
a basis of the kernel and run a greedy / randomized descent on the rank.
"""
from __future__ import annotations

import json
import random
import sys

import branchsim
import common
import quadfit

OUT = common.ROOT / "artifacts/20261107_quadratic_61q"
NS = 4096


def solve_with_kernel(vecs, target, ns):
    basis = {}
    kernel = []
    for j, vec in enumerate(vecs):
        x = vec
        c = 1 << j
        while x:
            p = x.bit_length() - 1
            if p in basis:
                bv, bc = basis[p]
                x ^= bv
                c ^= bc
            else:
                basis[p] = (x, c)
                break
        else:
            kernel.append(c)
    y = target
    c = 0
    while y:
        p = y.bit_length() - 1
        if p in basis:
            bv, bc = basis[p]
            y ^= bv
            c ^= bc
        else:
            return None, kernel
    return c, kernel


def rank_of_coef(coef, feats, w, nq=62):
    others = [v for v in range(nq) if v != w]
    idx = {v: i for i, v in enumerate(others)}
    n = len(others)
    rows = [0] * n
    for i, f in enumerate(feats):
        if (coef >> i) & 1 and f[0] == quadfit.FEATURE_QUAD:
            a, b = idx[f[1]], idx[f[2]]
            rows[a] |= 1 << b
            rows[b] |= 1 << a
    rank = 0
    for col in range(n):
        piv = None
        for r in range(rank, n):
            if (rows[r] >> col) & 1:
                piv = r
                break
        if piv is None:
            continue
        rows[rank], rows[piv] = rows[piv], rows[rank]
        pr = rows[rank]
        for r in range(n):
            if r != rank and ((rows[r] >> col) & 1):
                rows[r] ^= pr
        rank += 1
    return rank // 2


def search(op, w, gates, stacks, seed=0, iters=20000):
    xs = quadfit.sample_xs(NS)
    snaps = branchsim.snapshot(gates, stacks, [op], xs, branch="zero")
    V = snaps[op]
    feats, vecs = quadfit.build_features(V, w, NS)
    coef, kernel = solve_with_kernel(vecs, V[w], NS)
    assert coef is not None
    cur = rank_of_coef(coef, feats, w)
    best = (cur, coef)
    rng = random.Random(seed)
    # greedy single-vector pass, repeated
    improved = True
    while improved:
        improved = False
        order = list(range(len(kernel)))
        rng.shuffle(order)
        for j in order:
            r2 = rank_of_coef(coef ^ kernel[j], feats, w)
            if r2 < cur:
                coef ^= kernel[j]
                cur = r2
                best = (cur, coef)
                improved = True
    # random multi-vector perturbations
    for it in range(iters):
        c2 = coef
        for _ in range(rng.randint(2, 6)):
            c2 ^= kernel[rng.randrange(len(kernel))]
        r2 = rank_of_coef(c2, feats, w)
        if r2 < cur:
            coef = c2
            cur = r2
            best = (cur, coef)
            print(f"  op {op} q{w} iter {it}: rank -> {cur}", flush=True)
    return {"op": op, "wire": w, "rank": best[0], "start_rank": rank_of_coef(
        solve_with_kernel(vecs, V[w], NS)[0], feats, w), "kernel_dim": len(kernel),
        "coef": best[1], "feats": feats, "ns": NS}


def main():
    _, ops, gates, stacks = common.load_ops()
    specs = [(17078, 59), (16903, 22), (17413, 37), (17613, 46),
             (18001, 50), (18301, 28), (18542, 53), (16877, 42)]
    if len(sys.argv) > 1:
        specs = [(int(a.split(":")[0]), int(a.split(":")[1])) for a in sys.argv[1:]]
    out = []
    for op, w in specs:
        print(f"op {op} q{w}", flush=True)
        r = search(op, w, gates, stacks)
        print(f"  start {r['start_rank']} -> best {r['rank']} (kernel {r['kernel_dim']})",
              flush=True)
        out.append({k: v for k, v in r.items() if k not in ("feats",)})
    (OUT / "rank_search.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
