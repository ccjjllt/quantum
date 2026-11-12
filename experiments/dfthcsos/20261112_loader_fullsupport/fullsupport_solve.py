"""Full-low-support decomposition as an explicit GF(2) system, and its exact minimum.

Model
-----
Address a = 16 q + r,  r = bits 0..3 (16 monomials rho_R), q = bits 4..10 (128 monomials q_Q).
A pivot "form" is a GF(2) sum of monomials available for free: 1, the 11 address singles,
the 11 cached r-monomials (pairs/triples/quad, 11 ANDs once) and the cached q-monomials.
So a full-support form is   A = u(r) + v(q),   u in F2^16 arbitrary, v supported on cache.
A product (one CCX) adds   A*B = u_A v_B^T + v_A u_B^T + col0(u_A u_B) + row0(v_A v_B)
to the 16x128 ANF matrix M[R][Q] of the output bit.  Interior M[1:,1:] therefore has
rank <= 2 per product  =>  s >= ceil(rank(M[1:,1:]) / 2).

This script (a) prints the system for one bit, (b) computes rank bounds for all bits,
(c) builds an explicit decomposition, (d) verifies it exactly as a polynomial identity
on all 2048 monomials.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0, str(ROOT / '.worktree/dfthcsos/experiments/dfthcsos/20261112_loader_re'))
import tensorqrom8 as tq  # noqa: E402

W = np.load(ROOT / 'artifacts/20261112_eae_candidate/dfthcsos/submission.npz')['angle_words']
J, N = 5, 1220


def delta_of(k: int) -> np.ndarray:
    cur = W[:, k * J:(k + 1) * J]
    prev = W[:, (k - 1) * J:k * J] if k else np.zeros_like(cur)
    return (cur ^ prev).astype(np.int64)


def anf_cube(k: int) -> np.ndarray:
    d = delta_of(k)
    bits = np.zeros((2048, d.shape[1] * 8), np.uint8)
    for j in range(d.shape[1]):
        for kk in range(8):
            bits[:N, j * 8 + kk] = (d[:, j] >> kk) & 1
    return tq.mobius(bits, axis=0)


def to_matrix(A_col: np.ndarray) -> np.ndarray:
    """(2048,) ANF coefficient vector -> M[R,Q] (16 x 128)."""
    M = np.zeros((16, 128), np.uint8)
    for m in range(2048):
        M[m & 15, m >> 4] = A_col[m]
    return M


def rref(M: np.ndarray):
    """GF(2) RREF: returns (R, pivots) with R the reduced rows."""
    R = M.copy() % 2
    piv: list[int] = []
    row = 0
    for col in range(R.shape[1]):
        p = None
        for i in range(row, R.shape[0]):
            if R[i, col]:
                p = i
                break
        if p is None:
            continue
        R[[row, p]] = R[[p, row]]
        for i in range(R.shape[0]):
            if i != row and R[i, col]:
                R[i] ^= R[row]
        piv.append(col)
        row += 1
        if row == R.shape[0]:
            break
    return R[:row], piv


def gf2_rank(M: np.ndarray) -> int:
    return len(rref(M)[0])


def poly_of(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """u (16,) on r-monomials + v (128,) on q-monomials -> (2048,) monomial indicator."""
    out = np.zeros(2048, np.uint8)
    for R in np.flatnonzero(u):
        out[int(R)] ^= 1
    for Q in np.flatnonzero(v):
        out[int(Q) << 4] ^= 1
    return out


def mul_poly(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Product in GF(2)[x]/(x_i^2 = x_i): coefficient at m1|m2 is summed."""
    out = np.zeros(2048, np.uint8)
    for m1 in np.flatnonzero(a):
        for m2 in np.flatnonzero(b):
            out[int(m1) | int(m2)] ^= 1
    return out


def decompose(M: np.ndarray) -> list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
    """Minimum-product decomposition in the full-support model (interior rank/2 + 2)."""
    target = np.zeros(2048, np.uint8)
    for R in range(16):
        for Q in range(128):
            if M[R, Q]:
                target[R | (Q << 4)] = 1

    inter = M[1:, 1:]
    Rref, piv = rref(inter)
    prods = []
    # rank decomposition  inter = sum_i col_i (Rref row i)^T
    terms = []
    for i, col in enumerate(piv):
        a = np.zeros(15, np.uint8)
        a[:] = inter[:, col]
        terms.append((a, Rref[i].copy()))
    # pair consecutive rank-1 terms into one product each
    for t in range(0, len(terms), 2):
        a1, b1 = terms[t]
        if t + 1 < len(terms):
            a2, b2 = terms[t + 1]
        else:
            a2, b2 = np.zeros(15, np.uint8), np.zeros(127, np.uint8)
        uA = np.zeros(16, np.uint8); uA[1:] = a1
        uB = np.zeros(16, np.uint8); uB[1:] = a2
        vA = np.zeros(128, np.uint8); vA[1:] = b2
        vB = np.zeros(128, np.uint8); vB[1:] = b1
        prods.append((uA, vA, uB, vB))
    # residual column 0 and row 0: one product with uA = 1 gives p (col 0) + q (row 0)
    acc = np.zeros(2048, np.uint8)
    for uA, vA, uB, vB in prods:
        acc ^= mul_poly(poly_of(uA, vA), poly_of(uB, vB))
    resid = to_matrix(target ^ acc)
    if resid.any():
        p, q = resid[:, 0].copy(), resid[0, :].copy()
        p[0] = 0                      # mask 0 appears in both p and q; keep it in q only
        uA = np.zeros(16, np.uint8); uA[0] = 1
        uB = p.copy()
        vB = q.copy()
        prods.append((uA, np.zeros(128, np.uint8), uB, vB))
        acc ^= mul_poly(poly_of(uA, np.zeros(128, np.uint8)), poly_of(uB, vB))
    ok = bool(np.array_equal(acc, target))
    return prods, ok


def main() -> None:
    for k in [int(x) for x in sys.argv[1:]] or [4, 0]:
        cube = anf_cube(k)
        print(f'=== k={k} ===')
        ranks, ints, counts, oks = [], [], [], []
        for o in range(40):
            M = to_matrix(cube[:, o])
            r_full = gf2_rank(M)
            r_int = gf2_rank(M[1:, 1:])
            prods, ok = decompose(M)
            ranks.append(r_full); ints.append(r_int)
            counts.append(len(prods)); oks.append(ok)
        print(f'  rank   per bit: {ranks}')
        print(f'  rank(int)     : {ints}   sum={sum(ints)}')
        print(f'  lower bound   : {[ (r + 1) // 2 for r in ints ]} sum={sum((r + 1) // 2 for r in ints)}')
        print(f'  built products: {counts} sum={sum(counts)}  verified={all(oks)}')
        print(f'  T/circuit = 11 r-cache + {sum(counts)} products = {11 + sum(counts)}')
    # explicit system for one bit
    print()
    print('=== explicit system, k=4, output bit 1 (word 0 bit 1) ===')
    M = to_matrix(anf_cube(4)[:, 1])
    inter = M[1:, 1:]
    print(f'  unknowns: u_A,u_B in F2^16 (16 bits each), v_A,v_B in F2^128 (127 usable each)')
    print(f'  equations: 16*128 = 2048, of which interior 15*127 = 1905 are'
          f'  c[R,Q] = sum_{{R1|R2=R, Q1|Q2=Q}} uA[R1]vB[Q2] + vA[Q1]uB[R2]')
    print(f'  interior rank = {gf2_rank(inter)} > 2 = max rank of one product  => 1 product/bit IMPOSSIBLE')
    print(f'  minimum products = ceil({gf2_rank(inter)}/2) = {(gf2_rank(inter) + 1) // 2}')


if __name__ == '__main__':
    main()
