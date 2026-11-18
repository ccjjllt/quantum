"""Row-sparsity probe: for a v-basis V of GF(2)^35, measure
   K(V) = sum_i dim( row_i(S) )   where row_i(S) = image of S under the i-th dual of V.

Construction: for each i, choose a basis {r_1..r_k} of row_i(S) (15-bit coord vectors)
and emit columns V_i (x) r_j.  Those columns span a superset of S, so
   products = sum_i ceil(k_i / 2),   k_i = dim row_i(S).
Lower bound products >= ceil(dim S / 2) = 38.

Pure GF(2) arithmetic.
"""
import json, random, sys
import numpy as np
from common import load_words, gf2_rank, gf2_basis, NOUT, M35

from planner import complete_words, cross_tensor


def S_basis(target, lo=1, hi=76):
    return [int(x) for x in target[lo:hi]]


def rows_of(S, V):
    """V: list of 35 masks (basis of the 35-bit space).  Returns list of 15-bit spans."""
    out = []
    for phi in V:
        im = []
        for x in S:
            v = 0
            y = x
            while y:
                b = y & -y
                y ^= b
                m = b.bit_length() - 1
                w = (x >> (NOUT * m)) & M35
                if bin(phi & w).count('1') & 1:
                    v |= 1 << m
            im.append(v)
        out.append(gf2_rank(im))
    return out


def rand_invertible(rng):
    while True:
        rows = [rng.getrandbits(NOUT) for _ in range(NOUT)]
        d = {}
        for x in rows:
            while x:
                p = x.bit_length() - 1
                if p in d:
                    x ^= d[p]
                else:
                    d[p] = x
                    break
        if len(d) == NOUT:
            return rows


def objective(S, V):
    r = rows_of(S, V)
    return sum((x + 1) // 2 for x in r), sum(r), r


def main():
    W = load_words()
    Wc = complete_words(W)
    k = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    trials = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    S = S_basis(cross_tensor(Wc, k))
    print('dim S (rank of 75 slices):', gf2_rank(S), flush=True)
    rng = random.Random(12345)
    idV = [1 << i for i in range(NOUT)]
    p, K, r = objective(S, idV)
    print(f'identity V : K={K} p={p}', flush=True)
    best = None
    for t in range(trials):
        V = rand_invertible(rng)
        p, K, r = objective(S, V)
        print(f'random {t}   : K={K} p={p}', flush=True)
        if best is None or p < best[0]:
            best = (p, K, r, V)
    print('best random', best[0], best[1], best[2], flush=True)


if __name__ == '__main__':
    main()
