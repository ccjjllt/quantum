"""Bilinear rank of GF(2^m) multiplication over GF(2), m = 2, 3 — exhaustive.

rank(T) = minimum k such that T = sum_{t<=k} u_t (x) v_t (x) w_t.  Flattened: the k
rank-1 matrices u_t v_t^T must span a space containing every output matrix
M_k[i][j] = coeff of basis vector k in y^i * y^j.  Over GF(2) a 3x3 matrix is a
9-bit vector, there are only (2^m-1)^2 rank-1 matrices, so C(49,5) is decidable.
Pure integer arithmetic; no circuit is read or simulated.
"""
import itertools

import numpy as np


def mult_tensor(m, poly):
    """poly: reduction coefficients, y^m = sum_{i} poly[i] y^i (bit i of poly)."""
    # powers: vec[e] = basis vector of y^e mod poly, as m-bit int
    vec = [1 << i for i in range(m)]
    p = 0
    for i in range(m):
        if poly >> i & 1:
            p |= 1 << i
    for e in range(m, 2 * m - 1):
        # y^e = y * y^(e-1)
        prev = vec[e - 1]
        hi = prev >> (m - 1) & 1
        nxt = ((prev << 1) & ((1 << m) - 1))
        if hi:
            nxt ^= p
        vec.append(nxt)
    M = np.zeros((m, m, m), dtype=np.uint8)   # M[k][i][j]
    for i in range(m):
        for j in range(m):
            v = vec[i + j]
            for k in range(m):
                M[k, i, j] = (v >> k) & 1
    return M, vec


def gf2_rank(rows):
    rows = [r for r in rows if r]
    rank = 0
    for col in range(len(bin(max(rows, default=0))) - 2):
        piv = None
        for r in rows[rank:]:
            if r >> col & 1:
                piv = r
                break
        if piv is None:
            continue
        rows = [r for r in rows if r is not piv]
        rows.insert(rank, piv)
        rows = [r ^ piv if (r >> col & 1 and r is not piv) else r for r in rows]
        rank += 1
    return rank


def span_dim(mats):
    return gf2_rank(list(mats))


def search(m, k_max, poly):
    M, vec = mult_tensor(m, poly)
    S = [int(sum(int(M[k, i, j]) << (i * m + j) for i in range(m) for j in range(m))) for k in range(m)]
    dS = span_dim(S)
    r1 = []
    for u in range(1, 1 << m):
        for v in range(1, 1 << m):
            r1.append(int(sum(((u >> i & 1) & (v >> j & 1)) << (i * m + j) for i in range(m) for j in range(m))))
    print(f"m={m} poly={bin(poly)}  dim S = {dS}, {len(r1)} rank-1 matrices")
    best = None
    for k in range(dS, k_max + 1):
        sol = find_cover(r1, S, k)
        print(f"  k={k}: {'SOLUTION' if sol else 'none'}")
        if sol:
            best = (k, sol)
            break
    return M, best


def find_cover(r1, S, k, limit=1):
    """Find k rank-1 matrices whose span contains S. Exhaustive DFS with pruning."""
    n = len(r1)
    sols = []

    def rec(start, chosen, span):
        if len(sols) >= limit:
            return True
        if len(span) >= 0 and span_dim(span + S) - span_dim(span) > k - len(chosen):
            return
        if len(chosen) == k:
            if span_dim(span) and span_dim([*span, *S]) == span_dim(span):
                sols.append(list(chosen))
                return True
            return
        for t in range(start, n):
            if rec(t + 1, chosen + [t], span + [r1[t]]):
                return True
        return False

    rec(0, [], [])
    return sols[0] if sols else None


for m, poly in ((2, 0b111), (2, 0b011), (3, 0b1011), (3, 0b1101)):
    M, best = search(m, 6 if m == 3 else 3, poly)
    if best:
        k, sol = best
        print(f"   -> rank {k} for m={m} poly {bin(poly)}")
