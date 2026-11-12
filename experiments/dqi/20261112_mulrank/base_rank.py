"""General (non-symmetric) rank of the small base tensors used by the Chudnovsky tower.

The DQI tensors are compositions:  GF(2^12) = 7 points x tensor(3),  GF(2^24) = 11 x tensor(4),
GF(2^6) = 5 x tensor(2).  So a base tensor of rank r_k turns into
    7*r3 terms for n=12,  11*r4 for n=24,  3*r6 for the k=6 route.
The parent question is therefore: does GF(2^3) have rank 5 (lower bound 2n-1=5),
GF(2^4) rank 8 (lower bound 7), GF(2^6) rank 14 (lower bound 11)?

Here a decomposition is the *general* one: z = sum_t u_t(x) v_t(y) w_t with u_t != v_t allowed
(implementable in the circuit with two pivots and zero scratch), so this is stronger than the
symmetric census in calibrate.py.
"""
import sys
import time
from itertools import combinations_with_replacement
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mulmath as mm


def solve_general(cols, f, n):
    """cols: list of (a,b) masks in GF(2)^n. Feasible?  W(a_i . b_j) = e_i*e_j for all i,j."""
    piv = {}
    bad = 0
    for i in range(n):
        for j in range(n):
            m = 0
            for t, (a, b) in enumerate(cols):
                if (a >> i & 1) and (b >> j & 1):
                    m |= 1 << t
            val = f.mul(1 << i, 1 << j)
            while m:
                p = (m & -m).bit_length() - 1
                if p in piv:
                    m ^= piv[p][0]
                    val ^= piv[p][1]
                else:
                    piv[p] = (m, val)
                    break
            if m == 0 and val:
                bad += 1
    if bad:
        return False, bad
    out = [0] * len(cols)
    for p, (m, val) in sorted(piv.items(), reverse=True):
        for j in mm.bits(m ^ (1 << p)):
            val ^= out[j]
        out[p] = val
    return True, out


def search_general(n, r, limit=5, verbose=True):
    """Exhaustive over multisets of r nonzero (a,b) column pairs, deduped by signature."""
    f = mm.F(n)
    fld = f.f
    # signature: for each (i,j) pair (n*n of them) one bit -> integer
    sig = {}
    for a in range(1, 1 << n):
        for b in range(1, 1 << n):
            s = 0
            for i in range(n):
                for j in range(n):
                    if (a >> i & 1) and (b >> j & 1):
                        s |= 1 << (i * n + j)
            sig.setdefault(s, (a, b))
    keys = sorted(sig)
    if verbose:
        print(f'  GF(2^{n}) r={r}: {len(keys)} distinct signatures of {((1<<n)-1)**2} nonzero pairs',
              flush=True)
    rhs = [fld.mul(1 << i, 1 << j) for i in range(n) for j in range(n)]
    sols = []
    tested = 0
    t0 = time.time()
    for combo in combinations_with_replacement(keys, r):
        tested += 1
        # build the n*n row patterns of r bits
        piv = {}
        bad = False
        for p in range(n * n):
            m = 0
            for t, s in enumerate(combo):
                if (s >> p) & 1:
                    m |= 1 << t
            val = rhs[p]
            while m:
                q = (m & -m).bit_length() - 1
                if q in piv:
                    m ^= piv[q][0]
                    val ^= piv[q][1]
                else:
                    piv[q] = (m, val)
                    break
            if m == 0 and val:
                bad = True
                break
        if bad:
            continue
        out = [0] * r
        ok = True
        for p, (m, val) in sorted(piv.items(), reverse=True):
            for j in mm.bits(m ^ (1 << p)):
                val ^= out[j]
            out[p] = val
        if not all(out):
            continue
        cols = [sig[s] for s in combo]
        sols.append((cols, tuple(out)))
        if len(sols) >= limit:
            break
    return tested, sols, time.time() - t0


if __name__ == '__main__':
    print('== general (non-symmetric) rank of the base tensors ==')
    for n, rmax in ((2, 3), (3, 5)):
        for r in range(1, rmax + 1):
            tested, sols, dt = search_general(n, r)
            print(f'GF(2^{n}) r={r}: {tested} signature multisets, {len(sols)} solutions ({dt:.1f}s)'
                  + (f'\n    example: {sols[0]}' if sols else ''), flush=True)
