"""Rank search for the symmetric multiplication tensor of GF(2^n).

Term model (what the DQI circuit implements, 1 CCX each):
    z ^= parity(mask,x) * parity(mask,y) * out
i.e. T[i][j] = sum_t u_t[i] u_t[j] w_t  must equal  e_i * e_j  (field product).

Two tools:
  solve(masks)      exact feasibility of the output vectors for a fixed mask set
  sa(...)           simulated annealing on (masks, outputs) with Hamming objective
  exhaustive(n,r)   all multisets of r nonzero masks (small n only) -> exact answer
"""
import sys
import time
from itertools import combinations_with_replacement
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mulmath as mm


def rhs_table(f, n):
    return {(i, j): f.mul(1 << i, 1 << j) for i in range(n) for j in range(i, n)}


def solve(masks, f, n, rhs=None):
    """Return (ok, outs) for z^=sum_t u_t(x)u_t(y)w_t == xy, fixed mask list."""
    rhs = rhs or rhs_table(f, n)
    piv = {}
    bad = 0
    for (i, j), val in rhs.items():
        m = 0
        for t, u in enumerate(masks):
            if (u >> i & 1) and (u >> j & 1):
                m |= 1 << t
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
    out = [0] * len(masks)
    for p, (m, val) in sorted(piv.items(), reverse=True):
        for j in mm.bits(m ^ (1 << p)):
            val ^= out[j]
        out[p] = val
    return True, out


def exhaustive(n, r, f=None, limit=None):
    """Enumerate every multiset of r nonzero masks. Returns (n_solutions, examples)."""
    f = f or mm.F(n)
    fld = f.f
    rhs = rhs_table(fld, n)
    vectors = list(range(1, 1 << n))
    sols = []
    tested = 0
    for masks in combinations_with_replacement(vectors, r):
        tested += 1
        ok, out = solve(list(masks), fld, n, rhs)
        if ok and all(out):
            sols.append((masks, tuple(out)))
            if limit and len(sols) >= limit:
                break
    return tested, sols


def sa(n, r, iters, seed=0, temp0=4.0, temp1=0.05, init=None, report_every=0, time_budget=None):
    """Cleaner re-implementation: SA with copy-on-write revert."""
    import random
    rng = random.Random(seed)
    f = mm.F(n)
    rhs = rhs_table(f.f, n)
    pairs = list(rhs)
    U = [rng.randrange(1, 1 << n) for _ in range(r)]
    W = [rng.randrange(1, 1 << n) for _ in range(r)]
    if init:
        U, W = list(init[0]), list(init[1])

    def evaluate(U, W):
        cur = {p: 0 for p in pairs}
        for t in range(r):
            u, w = U[t], W[t]
            for (i, j) in pairs:
                if (u >> i & 1) and (u >> j & 1):
                    cur[(i, j)] ^= w
        return cur

    cur = evaluate(U, W)
    score = sum(bin(v ^ rhs[p]).count('1') for p, v in cur.items())
    best = score
    t0 = time.time()
    for it in range(iters):
        if time_budget and it % 4096 == 0 and time.time() - t0 > time_budget:
            break
        temp = temp0 * (temp1 / temp0) ** (it / max(iters - 1, 1))
        t = rng.randrange(r)
        if rng.random() < 0.5:
            i = rng.randrange(n)
            new = U[t] ^ (1 << i)
            if new == 0:
                continue
            delta = {}
            for j in range(n):
                p = (i, j) if i <= j else (j, i)
                was = (U[t] >> i & 1) and (U[t] >> j & 1)
                now = (new >> i & 1) and (new >> j & 1)
                if was != now:
                    delta[p] = W[t]
            old = sum(bin(cur[p] ^ rhs[p]).count('1') for p in delta)
            nv = {p: cur[p] ^ delta[p] for p in delta}
            new_s = sum(bin(nv[p] ^ rhs[p]).count('1') for p in delta)
            d = new_s - old
            if d <= 0 or rng.random() < pow(2.718281828, -d / max(temp, 1e-9)):
                for p in delta:
                    cur[p] = nv[p]
                U[t] = new
                score += d
        else:
            i = rng.randrange(n)
            w = W[t] ^ (1 << i)
            if w == 0:
                continue
            aff = [p for p in pairs if (U[t] >> p[0] & 1) and (U[t] >> p[1] & 1)]
            old = sum(bin(cur[p] ^ rhs[p]).count('1') for p in aff)
            bit = 1 << i
            new_s = sum(bin((cur[p] ^ bit) ^ rhs[p]).count('1') for p in aff)
            d = new_s - old
            if d <= 0 or rng.random() < pow(2.718281828, -d / max(temp, 1e-9)):
                for p in aff:
                    cur[p] ^= bit
                W[t] = w
                score += d
        if score < best:
            best = score
            bestUW = (list(U), list(W))
            if best == 0:
                return 0, bestUW, it + 1, time.time() - t0
        if report_every and it % report_every == 0:
            print(f'    it={it} score={score} best={best} T={temp:.3f} ({time.time()-t0:.0f}s)', flush=True)
    return best, (list(U), list(W)), it + 1, time.time() - t0
