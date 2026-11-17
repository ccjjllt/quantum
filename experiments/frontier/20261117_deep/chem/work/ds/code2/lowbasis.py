# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Low-basis changes for the block planner (our own implementation).

A low form is a 15-bit mask over the nonconstant low monomials. With an invertible basis
{b_i} (forms), T = sum_m e_m (x) t_m = sum_i b_i (x) t'_i with t'_i = sum_m Binv[i, m] t_m.
The planner runs on the transformed target with coordinate blocks [[0,1,2],...]; a low form
l' in new coordinates is the physical mask XOR_i l'_i b_i.
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'inputs/chem_goal_v18/deliverables/six_cache_words_combined_v18/compiler'))
from parity_recover import NOUT

M35 = (1 << NOUT) - 1


def inverse15(B):
    """B: list of 15 ints (basis forms as monomial masks). Returns Binv rows: Binv[i] = mask over m."""
    n = 15
    # matrix M[m][i] = bit m of B[i]; solve for inverse over GF(2)
    rows = [[(B[i] >> m) & 1 for i in range(n)] + [1 if j == m else 0 for j in range(n)] for m in range(n)]
    r = 0
    for c in range(n):
        p = next((i for i in range(r, n) if rows[i][c]), None)
        if p is None:
            raise ValueError('basis is singular')
        rows[r], rows[p] = rows[p], rows[r]
        for i in range(n):
            if i != r and rows[i][c]:
                rows[i] = [a ^ b for a, b in zip(rows[i], rows[r])]
        r += 1
    # rows[i][n + m] = Binv[i][m]
    return [sum(rows[i][n + m] << m for m in range(n)) for i in range(n)]


def transform_target(target, B):
    Binv = inverse15(B)
    out = []
    for x in target:
        sl = [(x >> (NOUT * m)) & M35 for m in range(15)]
        y = 0
        for i in range(15):
            v = 0
            for m in range(15):
                if (Binv[i] >> m) & 1:
                    v ^= sl[m]
            y |= v << (NOUT * i)
        out.append(y)
    return out


def to_physical(lp, B):
    l = 0
    for i in range(15):
        if (lp >> i) & 1:
            l ^= B[i]
    return l
