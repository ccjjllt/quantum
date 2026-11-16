# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Rank-74 block search (our own): find 3-dim dual subspaces L of the low space such that some
nonzero combination a of the 75 determined high slices has L in the left kernel of
M_a = sum_h a_h T_h (15 x 35). Such a block has local target rank <= 74.

Kernel attack: fix two nonlinear dual vectors x, y; A = {a : x.M_a = y.M_a = 0} (dimension
about 17-18, thanks to the output relations); scan third vectors z for a dependency of the
columns z.M_{a_i} over a basis a_i of A.
"""
import random
from parity_recover import NOUT

M35 = (1 << NOUT) - 1
LIN = [0, 1, 3, 7]
NL = [m for m in range(15) if m not in LIN]
CUB = [6, 10, 12, 13, 14]
QUAD = [m for m in NL if m not in CUB]


def slices(target, hmax=76):
    """T[h][m] 35-bit ints for h = 1..hmax-1."""
    return [[(x >> (NOUT * m)) & M35 for m in range(15)] for x in target[1:hmax]]


def rslice(T, r):
    out = []
    for th in T:
        v = 0; x = r
        while x:
            b = x & -x; x ^= b
            v ^= th[b.bit_length() - 1]
        out.append(v)
    return out


def dependencies(vecs):
    """basis of {a : XOR_{h in a} vecs[h] = 0} as masks over the index."""
    d = {}; out = []
    for i, x in enumerate(vecs):
        co = 1 << i
        while x:
            p = x.bit_length() - 1
            if p in d:
                x ^= d[p][0]; co ^= d[p][1]
            else:
                d[p] = (x, co); break
        if not x:
            out.append(co)
    return out


def combine(T, a):
    """M_a as 15 ints."""
    M = [0] * 15
    h = 0
    while a:
        if a & 1:
            th = T[h]
            for m in range(15):
                M[m] ^= th[m]
        a >>= 1; h += 1
    return M


def find_third(T, x, y, zs, rng=None):
    """zs: iterable of candidate third dual vectors. Returns list of (z, a)."""
    vx = rslice(T, x); vy = rslice(T, y)
    A = dependencies([a | (b << NOUT) for a, b in zip(vx, vy)])
    if not A:
        return [], 0
    P = [combine(T, a) for a in A]                 # P[i][m]
    cols_m = [[P[i][m] for i in range(len(A))] for m in range(15)]
    found = []
    for z in zs:
        cols = [0] * len(A)
        t = z
        while t:
            b = t & -t; t ^= b
            cm = cols_m[b.bit_length() - 1]
            cols = [c ^ v for c, v in zip(cols, cm)]
        dep = dependencies(cols)
        for dd in dep:
            a = 0
            for i in range(len(A)):
                if (dd >> i) & 1:
                    a ^= A[i]
            if a:
                found.append((z, a))
        if found:
            break
    return found, len(A)


def rand_vec(rng, coords):
    v = 0
    while not v:
        for m in coords:
            if rng.getrandbits(1):
                v |= 1 << m
    return v


def left_kernel(M):
    """dual vectors r (15-bit) with r.M = 0."""
    return dependencies(M)


def _rank(vs):
    b = {}
    for x in vs:
        while x:
            p = x.bit_length() - 1
            if p in b:
                x ^= b[p]
            else:
                b[p] = x; break
    return len(b)


def find_basis(T, rng, zsamples=400, max_xy=40000, verbose=False):
    """Five rank-74 blocks in direct sum. Returns (dual_rows[15], info) or None.
    Block b = [z_b (address-bit class), y_b, x_b]; block 4 = three nonlinear vectors."""
    while True:
        lams = [rng.randrange(1, 16) for _ in range(4)]
        if _rank(lams) == 4:
            break
    rows = []; nlv = []; cubv = []
    for b in range(4):
        zlin = sum(1 << LIN[i] for i in range(4) if (lams[b] >> i) & 1)
        ok = False
        for _ in range(max_xy):
            x = rand_vec(rng, CUB)
            if _rank(cubv + [x]) <= len(cubv):
                continue
            y = rand_vec(rng, NL)
            if _rank(cubv + [x, y]) > len(cubv) + 1:
                pass
            if _rank(nlv + [x, y]) < len(nlv) + 2:
                continue
            zs = [zlin | sum(1 << NL[i] for i in range(11) if (nu >> i) & 1) for nu in rng.sample(range(2048), zsamples)]
            res, dimA = find_third(T, x, y, zs)
            if res:
                z, a = res[0]
                rows += [z, y, x]; nlv += [x, y]; cubv += [x]
                ok = True
                break
        if not ok:
            if verbose:
                print('   mixed block', b, 'not found', flush=True)
            return None
    # last block: three nonlinear vectors completing the nonlinear dual space
    for _ in range(max_xy):
        x = rand_vec(rng, CUB); y = rand_vec(rng, NL)
        if _rank(cubv + [x]) <= len(cubv) or _rank(nlv + [x, y]) < len(nlv) + 2:
            continue
        # third vector: anything completing the nonlinear space; scan the coset
        comp = next((1 << m for m in NL if _rank(nlv + [x, y, 1 << m]) == len(nlv) + 3), None)
        if comp is None:
            continue
        span_basis = nlv + [x, y]
        zs = []
        for s in rng.sample(range(1 << len(span_basis)), min(1 << len(span_basis), 1024)):
            v = comp
            for i, u in enumerate(span_basis):
                if (s >> i) & 1:
                    v ^= u
            zs.append(v)
        res, dimA = find_third(T, x, y, zs)
        if res:
            z, a = res[0]
            rows += [z, y, x]
            assert _rank(rows) == 15
            return rows
    return None


def find_basis_generic(T, rng, zsamples=400, max_xy=60000, verbose=False, time_limit=400):
    """Five rank-74 blocks in direct sum without assuming cubic relations (for five-relation words)."""
    import time as _t
    t0 = _t.time()
    while True:
        lams = [rng.randrange(1, 16) for _ in range(4)]
        if _rank(lams) == 4:
            break
    rows = []; nlv = []
    for b in range(4):
        zlin = sum(1 << LIN[i] for i in range(4) if (lams[b] >> i) & 1)
        ok = False
        for _ in range(max_xy):
            if _t.time() - t0 > time_limit:
                return None
            x = rand_vec(rng, NL); y = rand_vec(rng, NL)
            if _rank(nlv + [x, y]) < len(nlv) + 2:
                continue
            zs = [zlin | sum(1 << NL[i] for i in range(11) if (nu >> i) & 1) for nu in rng.sample(range(2048), zsamples)]
            res, dimA = find_third(T, x, y, zs)
            if res:
                rows += [res[0][0], y, x]; nlv += [x, y]; ok = True
                if verbose:
                    print(f'   block {b} found ({_t.time()-t0:.0f}s)', flush=True)
                break
        if not ok:
            return None
    for _ in range(max_xy):
        if _t.time() - t0 > time_limit:
            return None
        x = rand_vec(rng, NL); y = rand_vec(rng, NL)
        if _rank(nlv + [x, y]) < len(nlv) + 2:
            continue
        comp = next((1 << m for m in NL if _rank(nlv + [x, y, 1 << m]) == len(nlv) + 3), None)
        if comp is None:
            continue
        sb = nlv + [x, y]
        zs = []
        for s in rng.sample(range(1 << len(sb)), min(1 << len(sb), 1024)):
            v = comp
            for i, u in enumerate(sb):
                if (s >> i) & 1:
                    v ^= u
            zs.append(v)
        res, dimA = find_third(T, x, y, zs)
        if res:
            rows += [res[0][0], y, x]
            assert _rank(rows) == 15
            return rows
    return None
