"""Quadratic-form fitting over wire values (GF(2)), with product rank.

For a target wire w at an operation, fit

    w_value(x) = c  XOR  XOR_i a_i v_i(x)  XOR  XOR_{i<j} b_ij v_i(x) v_j(x)

where v_i are the other 61 wire values at that op.

The fit is done on a sample of x (default 4096) by Gaussian elimination over the feature
vectors (each feature is a bit vector over the sample).  The returned coefficient set is
then checked on the full legal domain / other branches by the caller.

The quadratic part has an alternating polar matrix B.  Its GF(2) rank is even, 2r, and
the form can be written as a sum of r products of affine forms plus an affine form.
`rank_products` returns r.
"""
from __future__ import annotations

import numpy as np

FEATURE_CONST = 0
FEATURE_LINEAR = 1
FEATURE_QUAD = 2


def build_features(V, w, ns):
    """Feature list and bit-vector list for target wire w."""
    others = [v for v in range(len(V)) if v != w]
    feats = [(FEATURE_CONST,)]
    vecs = [(1 << ns) - 1]
    for a in others:
        feats.append((FEATURE_LINEAR, a))
        vecs.append(V[a])
    for ii, a in enumerate(others):
        va = V[a]
        for b in others[ii + 1:]:
            feats.append((FEATURE_QUAD, a, b))
            vecs.append(va & V[b])
    return feats, vecs


def solve_features(vecs, target, ns):
    """Return coefficient int c with XOR_{c_i=1} vecs[i] == target, or None."""
    basis = {}
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
    y = target
    c = 0
    while y:
        p = y.bit_length() - 1
        if p in basis:
            bv, bc = basis[p]
            y ^= bv
            c ^= bc
        else:
            return None
    return c


def rank_products(coef, feats, w, nq=62):
    """Rank r of the quadratic part's polar form divided by 2 (number of products)."""
    others = [v for v in range(nq) if v != w]
    idx = {v: i for i, v in enumerate(others)}
    n = len(others)
    rows = [0] * n
    for i, f in enumerate(feats):
        if (coef >> i) & 1 and f[0] == FEATURE_QUAD:
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
    assert rank % 2 == 0, rank
    return rank // 2


def eval_poly(coef, feats, V, ns):
    """Evaluate the fitted polynomial on the bit-vector values V."""
    out = 0
    for i, f in enumerate(feats):
        if (coef >> i) & 1:
            if f[0] == FEATURE_CONST:
                out ^= (1 << ns) - 1
            elif f[0] == FEATURE_LINEAR:
                out ^= V[f[1]]
            else:
                out ^= V[f[1]] & V[f[2]]
    return out


def fit_snapshot(V, w, ns):
    feats, vecs = build_features(V, w, ns)
    coef = solve_features(vecs, V[w], ns)
    if coef is None:
        return None
    return {"coef": coef, "feats": feats, "rank": rank_products(coef, feats, w),
            "monomials": coef.bit_count()}


def sample_xs(ns=4096, seed=12345, maxx=3133452):
    rng = np.random.default_rng(seed)
    return rng.integers(1, maxx + 1, ns, dtype=np.int64)
