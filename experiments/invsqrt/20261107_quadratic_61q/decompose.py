"""Decompose a fitted quadratic form into products of affine forms (GF(2)).

Given q(v) = c + sum a_i v_i + sum_{i<j} b_ij v_i v_j with polar matrix rank 2r,
produce r pairs (L_j, M_j) of nonzero linear forms and an affine correction A such that

    q(v) = A(v) XOR XOR_j L_j(v) M_j(v).

The algorithm is symplectic Gram-Schmidt on the alternating polar matrix.  The basis change
S is tracked in original coordinates; the current polar matrix is recomputed as S^T B S.
"""
from __future__ import annotations

import quadfit


def _bit_indices(x):
    out = []
    while x:
        b = x & -x
        out.append(b.bit_length() - 1)
        x ^= b
    return out


def _form_matrix(R, B0, n):
    """Return M[i][j] = R[i]^T B0 R[j] (R rows are linear forms)."""
    BR = []
    for j in range(n):
        r = 0
        x = R[j]
        while x:
            b = x & -x
            r ^= B0[b.bit_length() - 1]
            x ^= b
        BR.append(r)
    M = [0] * n
    for i in range(n):
        out = 0
        ri = R[i]
        for j in range(n):
            if (ri & BR[j]).bit_count() & 1:
                out |= 1 << j
        M[i] = out
    return M


def _columns(R, n):
    """Column vectors of R: col_j = sum_i R[i][j] e_i."""
    cols = [0] * n
    for i in range(n):
        row = R[i]
        while row:
            b = row & -row
            j = b.bit_length() - 1
            cols[j] |= 1 << i
            row ^= b
    return cols


def symplectic_decompose(coef, feats, w, nq=62):
    others = [v for v in range(nq) if v != w]
    n = len(others)
    pos = {v: i for i, v in enumerate(others)}
    B0 = [0] * n
    lin = 0
    const = 0
    for i, f in enumerate(feats):
        if not ((coef >> i) & 1):
            continue
        if f[0] == quadfit.FEATURE_CONST:
            const ^= 1
        elif f[0] == quadfit.FEATURE_LINEAR:
            lin ^= 1 << pos[f[1]]
        else:
            a, b = pos[f[1]], pos[f[2]]
            B0[a] |= 1 << b
            B0[b] |= 1 << a

    R = [1 << i for i in range(n)]
    B = _form_matrix(R, B0, n)
    active = list(range(n))
    pairs = []
    while True:
        found = None
        for ii in range(len(active)):
            p = active[ii]
            for jj in range(ii + 1, len(active)):
                q = active[jj]
                if (B[p] >> q) & 1:
                    found = (p, q)
                    break
            if found:
                break
        if found is None:
            break
        p, q = found
        for k in active:
            if k in (p, q):
                continue
            alpha = (B[k] >> q) & 1
            beta = (B[p] >> k) & 1
            if alpha:
                R[k] ^= R[p]
            if beta:
                R[k] ^= R[q]
        cols = _columns(R, n)
        pairs.append((cols[p], cols[q]))
        active = [k for k in active if k not in (p, q)]
        B = _form_matrix(R, B0, n)

    # affine correction = q - sum products
    qlin = lin
    qconst = const
    qB = [0] * n
    for i, f in enumerate(feats):
        if (coef >> i) & 1 and f[0] == quadfit.FEATURE_QUAD:
            a, b = pos[f[1]], pos[f[2]]
            qB[a] |= 1 << b
            qB[b] |= 1 << a
    for u, wv in pairs:
        for i in _bit_indices(u):
            for j in _bit_indices(wv):
                if i == j:
                    qlin ^= 1 << i
                else:
                    lo, hi = (i, j) if i < j else (j, i)
                    qB[lo] ^= 1 << hi
                    qB[hi] ^= 1 << lo
    assert all(x == 0 for x in qB), "decomposition left quadratic terms"
    return {
        "products": pairs,
        "affine_linear": qlin,
        "affine_const": qconst,
        "others": others,
    }


def evaluate_ns(dec, V, ns):
    out = 0
    if dec["affine_const"]:
        out ^= (1 << ns) - 1
    for i in _bit_indices(dec["affine_linear"]):
        out ^= V[dec["others"][i]]
    for u, w in dec["products"]:
        a = 0
        for i in _bit_indices(u):
            a ^= V[dec["others"][i]]
        b = 0
        for i in _bit_indices(w):
            b ^= V[dec["others"][i]]
        out ^= a & b
    return out
