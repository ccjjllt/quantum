"""A product-cache ANGLE_k circuit: every monomial of the address bits is cached, no data bank.

Split the address a = 2**k h + l into k low bits and the high bits. Each output bit (word bit
below the signed-gauge top bit) is a GF(2) polynomial in the address bits; with the rows past the
table's end treated as zeros, its algebraic normal form is

    f_o(l, h) = sum_{m, M} C[m, M, o] m(l) M(h)

over low monomials m and high monomials M below the number of high chunks. The circuit caches every
nonconstant monomial of the low bits (2**k - 1 - k ANDs) and of the high bits in qubits, so every
term with m = 0 or M = 0 costs only CNOTs. The mixed tensor C[1:, 1:, :] is covered by Toffolis
whose controls are parities of cached qubits:

    (a1 . m + b2 . M)(a2 . m + b1 . M) = (a1 . m)(b1 . M) + (a2 . m)(b2 . M) + pure low + pure high,

so one Toffoli adds the mixed matrix a1 b1^T + a2 b2^T to every output it is fanned out to, and its
pure parts are folded into the CNOT corrections. The cache is erased by measurement (`del_and`),
without Toffolis, so a circuit costs (low cache) + (high cache) + (products).

This design follows mrmeows' exact lookup emitter ("QCC 15.75 open circuits and sources",
Apache-2.0: cached monomials, paired affine products, measurement erasure); the decomposition and
the code here are our own.
"""
from __future__ import annotations

import numpy as np
import kickmix as km


def _bits(value: int) -> list[int]:
    out, i = [], 0
    while value:
        if value & 1:
            out.append(i)
        value >>= 1
        i += 1
    return out


def mobius(x: np.ndarray, axis: int = 0) -> np.ndarray:
    """The GF(2) Moebius transform along `axis` (size 2**k): truth table <-> ANF coefficients."""
    x = np.moveaxis(np.array(x, dtype=np.uint8), axis, 0).copy()
    n = x.shape[0]
    bit = 1
    while bit < n:
        idx = np.array([i for i in range(n) if i & bit])
        x[idx] ^= x[idx ^ bit]
        bit <<= 1
    return np.moveaxis(x, 0, axis)


def anf_tensor(delta: np.ndarray, brot: int, lowbits: int, full: bool = False) -> np.ndarray:
    """C (2**lowbits, H, O): ANF coefficients over (low monomial, high monomial < H, output bit).

    Output bit o = (brot - 1) j + k is bit k < brot - 1 of word j; in the signed gauge the top bit
    copies bit brot - 2. Rows past the table are zero; H = the number of high chunks, and since
    {0, ..., H-1} is closed under bit subsets the high monomials below H are exact on every row.
    """
    delta = np.asarray(delta, dtype=np.int64)
    count, J = delta.shape
    L = 1 << lowbits
    H = -(-count // L)
    hb = max(1, (H - 1).bit_length())
    nob = brot if full else brot - 1          # outputs per word: all `brot` bits, or the signed gauge's
    bits = np.zeros((L * H, J * nob), np.uint8)
    for j in range(J):
        for k in range(nob):
            bits[:count, j * nob + k] = (delta[:, j] >> k) & 1
    truth = bits.reshape(H, L, -1)
    padded = np.zeros((1 << hb, L, truth.shape[2]), np.uint8)
    padded[:H] = truth
    C = mobius(mobius(padded, 0), 1)[:H]
    return C.transpose(1, 0, 2).copy()


def rank_factor(rows: list[int]) -> tuple[list[int], list[int]]:
    """rows[i] = XOR of basis[k] over the bits k of coeffs[i]; basis = independent rows, in order."""
    piv: dict[int, tuple[int, int]] = {}
    basis, coeffs = [], []
    for r in rows:
        v, combo = r, 0
        while v:
            p = v.bit_length() - 1
            if p in piv:
                v ^= piv[p][0]
                combo ^= piv[p][1]
            else:
                k = len(basis)
                basis.append(r)
                piv[p] = (v, combo ^ (1 << k))
                combo = 1 << k
                break
        coeffs.append(combo)
    return basis, coeffs


def per_output(C: np.ndarray) -> list[tuple[int, int, int, int, int]]:
    """Toffolis (a1, b1, a2, b2, outs): each output's mixed matrix by its own rank factorization, terms paired."""
    Lm, Hm, O = C.shape[0] - 1, C.shape[1] - 1, C.shape[2]
    terms = []
    for o in range(O):
        rows = [int(sum(int(v) << i for i, v in enumerate(C[1 + m, 1:, o]))) for m in range(Lm)]
        basis, coeffs = rank_factor(rows)
        rank1 = [(sum(1 << m for m in range(Lm) if coeffs[m] >> k & 1), basis[k]) for k in range(len(basis))]
        for i in range(0, len(rank1), 2):
            a1, b1 = rank1[i]
            a2, b2 = rank1[i + 1] if i + 1 < len(rank1) else (0, 0)
            terms.append((a1, b1, a2, b2, 1 << o))
    return terms


def mixed_of(terms, Lm: int, Hm: int, O: int) -> np.ndarray:
    """The mixed tensor (Lm, Hm, O) that the Toffolis add up to."""
    vec = lambda v, n: np.array([(v >> i) & 1 for i in range(n)], np.uint8)  # noqa: E731
    out = np.zeros((Lm, Hm, O), np.uint8)
    for a1, b1, a2, b2, s in terms:
        P = (np.outer(vec(a1, Lm), vec(b1, Hm)) ^ np.outer(vec(a2, Lm), vec(b2, Hm)))
        out ^= P[:, :, None] & vec(s, O)[None, None, :]
    return out


def _monomial_values(n_mono: int, n_points: int) -> np.ndarray:
    """(n_points, n_mono - 1): value of nonconstant monomial m (mask m + 1) at point x."""
    x = np.arange(n_points)[:, None]
    m = np.arange(1, n_mono)[None, :]
    return ((x & m) == m).astype(np.uint8)


def build_circuit(delta: np.ndarray, terms, n_sel: int, brot: int, lowbits: int,
                  groups: list[list[int]] | None = None, scratch: bool = False,
                  full: bool = False) -> km.Circuit:
    """The XOR oracle |a>|z> -> |a>|z ^ f(a)> for the (A, J) table `delta`, from a decomposition `terms`.

    With `groups` (the decomposition must have been planned with them, see `shared`), the low
    monomials are cached one group at a time: same Toffolis, at most max(len(g)) low cache qubits.

    `scratch` borrows each word's top bit as a cache qubit (heliosli's idea): in the signed gauge it
    equals the bit below, so one CNOT clears it and one restores it from the new word. That saves J
    qubits but holds only for incoming words in the signed gauge, which is all the official verifier
    feeds an ANGLE circuit (zero, or a batch of the table itself, forward and in reverse); it is not
    a general XOR oracle on arbitrary register contents."""
    delta = np.asarray(delta, dtype=np.int64)
    count, J = delta.shape
    if not full:
        assert not np.any(((delta >> (brot - 1)) ^ (delta >> (brot - 2))) & 1), 'words must be in the signed gauge'
    C = anf_tensor(delta, brot, lowbits, full=full)
    L, H, O = C.shape
    assert np.array_equal(mixed_of(terms, L - 1, H - 1, O), C[1:, 1:]), 'decomposition does not cover the tensor'

    # Pure parts: constant, low-only (row m, column M = 0), high-only (m = 0, M >= 1), plus the
    # products' pure terms (a1 . m)(a2 . m) and (b2 . M)(b1 . M), as ANF corrections per output.
    low = C[:, 0].copy()                      # (L, O), includes the constant at m = 0
    high = C[0].copy()                        # (H, O)
    high[0] = 0
    vl, vh = _monomial_values(L, L), _monomial_values(H, H)
    hb = max(1, (H - 1).bit_length())
    for a1, b1, a2, b2, s in terms:
        outs = np.array(_bits(s))
        if a2:
            pl = mobius((vl @ np.array(_bits_vec(a1, L - 1)) & 1) & (vl @ np.array(_bits_vec(a2, L - 1)) & 1))
            low[:, outs] ^= pl[:, None]
        if b2:
            th = np.zeros(1 << hb, np.uint8)
            th[:H] = (vh @ np.array(_bits_vec(b2, H - 1)) & 1) & (vh @ np.array(_bits_vec(b1, H - 1)) & 1)
            ph = mobius(th)[:H]
            high[:, outs] ^= ph[:, None]
    low[0] ^= high[0]
    high[0] = 0

    b = km.CircuitBuilder()
    sel = b.create_quantum_register(n_sel, 'selection')
    words = [b.create_quantum_register(brot, f'word_{j}') for j in range(J)]
    if full:    # the table is not in the signed gauge: all `brot` bits are real outputs, nothing borrowed
        scratch = False   # a word's top bit is a real output here, it must never be used as cache
        outputs = [[words[j][k]] for j in range(J) for k in range(brot)]
    elif scratch:  # the top bit copies the one below: clear it, borrow it, restore it from the new word at the end
        for w in words:
            b.cx(w[brot - 2], w[brot - 1])
        outputs = [[words[j][k]] for j in range(J) for k in range(brot - 1)]
    else:
        outputs = [[words[j][k]] + ([words[j][brot - 1]] if k == brot - 2 else []) for j in range(J) for k in range(brot - 1)]
    pool = [w[brot - 1] for w in words] if scratch else []
    borrowed: list = []

    def take():
        if pool:
            borrowed.append(pool[-1])
            return pool.pop()
        return b.alloc_qubits(1)[0]

    def give(t) -> None:
        if any(t is q for q in borrowed):
            borrowed[:] = [q for q in borrowed if q is not t]
            pool.append(t)
        else:
            b.free(t)

    def cache(size: int, offset: int, made: list) -> dict:
        q = {}
        for mask in range(1, size):
            top = mask.bit_length() - 1
            if mask == 1 << top:
                q[mask] = sel[offset + top]
            else:
                t = take()
                b.init_and(q[mask ^ (1 << top)], sel[offset + top], t)
                q[mask] = t
                made.append((q[mask ^ (1 << top)], sel[offset + top], t))
        return q

    made: list = []
    Y = cache(H, lowbits, made)
    if groups is None:  # every low monomial cached for the whole circuit
        X = cache(L, 0, made)
        phases = [([], list(terms))]
    else:  # one group of low monomials at a time; the low address bits themselves are always there
        X = {m: sel[m.bit_length() - 1] for m in range(1, L) if m & (m - 1) == 0}
        phases = [(g, []) for g in groups]
        for t in terms:
            phases[_phase(t, groups)][1].append(t)

    def qubit(q: int):  # basis index -> qubit: low monomial q + 1, or high monomial q - L + 2
        return X[q + 1] if q < L - 1 else Y[q - L + 2]

    def targets(s) -> list:
        return [q for o in s for q in outputs[o]]

    def fan_ccx(c1, c2, ts: list) -> None:
        first, rest = ts[0], ts[1:]
        for t in rest:
            b.cx(first, t)
        b.ccx(c1, c2, first)
        for t in reversed(rest):
            b.cx(first, t)

    def product(a1, b1, a2, b2, s) -> None:
        m1, m2 = a1 | (b2 << (L - 1)), a2 | (b1 << (L - 1))
        if not m1 or not m2 or m1 == m2:
            return
        # Materialize m1 on a pivot p1 and m2 on p2 by CNOTs from the other basis qubits, then undo.
        p1 = _bits(m1)[0]
        ops = [(q, p1) for q in _bits(m1) if q != p1]
        if m2 >> p1 & 1:  # in the new basis, p1 holds m1: x_p1 = new_p1 + (m1 without p1)
            m2 ^= m1 ^ (1 << p1)
        p2 = next(q for q in _bits(m2) if q != p1)
        ops += [(q, p2) for q in _bits(m2) if q != p2]
        for src, dst in ops:
            b.cx(qubit(src), qubit(dst))
        fan_ccx(qubit(p1), qubit(p2), targets(_bits(s)))
        for src, dst in reversed(ops):
            b.cx(qubit(src), qubit(dst))

    def low_correction(m: int) -> None:
        ts = targets(np.flatnonzero(low[m]))
        if ts:
            if m == 0:
                b.x(km.array(ts))
            else:
                b.cx(X[m], km.array(ts))

    for group, phase_terms in phases:
        held = []
        for m in group:  # ascending, so a monomial's parent (m without its top bit) comes first
            top = m.bit_length() - 1
            t = take()
            b.init_and(X[m ^ (1 << top)], sel[top], t)
            X[m] = t
            held.append((X[m ^ (1 << top)], sel[top], t, m))
        for t in phase_terms:
            product(*t)
        for m in group:
            low_correction(m)
        for c1, c2, t, m in reversed(held):
            b.del_and(c1, c2, t)
            give(t)
            del X[m]
    for m in range(L):
        if m in X or m == 0:
            low_correction(m)
    for m in range(1, H):
        ts = targets(np.flatnonzero(high[m]))
        if ts:
            b.cx(Y[m], km.array(ts))

    for c1, c2, t in reversed(made):
        b.del_and(c1, c2, t)
        give(t)
    if scratch:
        for w in words:
            b.cx(w[brot - 2], w[brot - 1])
    return b.finish_circuit()


def low_groups(lowbits: int, size: int = 4) -> list[list[int]]:
    """The nonlinear low monomials (bit masks) in groups of at most `size`, each closed under dropping
    the top bit, so every AND's parent is a single address bit or in the same group (k = 4: three
    groups, 11 ANDs in all, at most 4 cached at once). Trees rooted at degree-2 monomials, packed
    first-fit by decreasing size."""
    trees: dict[int, list[int]] = {}
    for m in range(1, 1 << lowbits):
        if m & (m - 1):
            root = m
            while (root ^ (1 << (root.bit_length() - 1))) & ((root ^ (1 << (root.bit_length() - 1))) - 1):
                root ^= 1 << (root.bit_length() - 1)
            trees.setdefault(root, []).append(m)
    groups: list[list[int]] = []
    for tree in sorted(trees.values(), key=len, reverse=True):
        assert len(tree) <= size, f'a tree of {len(tree)} monomials does not fit groups of {size}'
        for g in groups:
            if len(g) + len(tree) <= size:
                g += tree
                break
        else:
            groups.append(list(tree))
    return [sorted(g) for g in groups]


def _phase(term, groups: list[list[int]]) -> int:
    """The first group whose cache (with the low address bits) holds both low forms of a product."""
    a1, _, a2, _, _ = term
    need = {q + 1 for q in _bits(a1 | a2) if (q + 1) & q}
    for i, g in enumerate(groups):
        if need <= set(g):
            return i
    raise AssertionError(f'a product needs low monomials {sorted(need)} from more than one group')


def _bits_vec(v: int, n: int) -> list[int]:
    return [(v >> i) & 1 for i in range(n)]


def cost(terms, L: int, H: int) -> int:
    """Toffolis per circuit pass: the two caches plus one per product."""
    return (L - 1 - (L - 1).bit_length()) + (H - 1 - (H - 1).bit_length()) + len(terms)


def nullspace(rows: list[int], n: int) -> list[int]:
    """A basis of {x in GF(2)^n : parity(x & r) = 0 for every r in rows}."""
    piv: dict[int, int] = {}
    for r in rows:
        v = r
        for p in sorted(piv, reverse=True):
            if v >> p & 1:
                v ^= piv[p]
        if v:
            p = v.bit_length() - 1
            for q in piv:  # keep the echelon form reduced
                if piv[q] >> p & 1:
                    piv[q] ^= v
            piv[p] = v
    out = []
    for f in range(n):
        if f in piv:
            continue
        x = 1 << f
        for p, r in piv.items():
            if r >> f & 1:
                x |= 1 << p
        out.append(x)
    return out


def _reduce(v: int, piv: dict) -> int:
    while v:
        p = v.bit_length() - 1
        if p not in piv:
            return v
        v ^= piv[p]
    return 0


def group_features(rows: list[int], Y: int, m: int, codim: int, rng, restarts: int = 8,
                   allowed: list[int] | None = None) -> list[tuple[int, int, int, int]] | None:
    """Rank-one features (y, s, vector, g) whose span holds every row (a Y x m matrix flattened as bit y m + o).

    The span is the annihilator of `codim` random relations of the rows; features of one output
    direction s are taken in even counts so they pair into Toffolis. With `allowed` (bit masks over
    the Y feature coordinates), a feature's y lies inside one of them, g, and only features of the
    same (s, g) pair. None if the features run out.
    """
    rel = nullspace(rows, Y * m)
    if len(rel) > codim:
        chosen, ind = [], {}
        while len(chosen) < codim:
            v = 0
            for r in rel:
                if rng.random() < 0.5:
                    v ^= r
            red = _reduce(v, ind)
            if red:
                chosen.append(v)
                ind[red.bit_length() - 1] = red
        rel = chosen
    span = Y * m - len(rel)
    flat = lambda y, s: sum(s << (i * m) for i in _bits(y))  # noqa: E731
    choices = {}
    for s in range(1, 1 << m):
        cons = [sum((bin((r >> (i * m)) & s).count('1') & 1) << i for i in range(Y)) for r in rel]
        for g, A in enumerate(allowed or [(1 << Y) - 1]):
            idx = _bits(A)  # solve in the coordinates of A only
            red = [sum(((c >> i) & 1) << j for j, i in enumerate(idx)) for c in cons]
            ys = [sum(((v >> j) & 1) << i for j, i in enumerate(idx)) for v in nullspace(red, len(idx))]
            rng.shuffle(ys)
            choices[(s, g)] = [(y, s, flat(y, s), g) for y in ys]
    best = None
    for _ in range(restarts):
        chosen = _pair_first(choices, span, rng)
        if chosen is not None:
            n = _products(chosen)
            if best is None or n < best[0]:
                best = (n, chosen)
    return None if best is None else best[1]


def _products(feats) -> int:
    count: dict[tuple[int, int], int] = {}
    for f in feats:
        count[f[1], f[3]] = count.get((f[1], f[3]), 0) + 1
    return sum((c + 1) // 2 for c in count.values())


def _pair_first(choices: dict, span: int, rng) -> list | None:
    """A basis of the span from the features, two of one direction at a time while possible."""
    piv: dict[int, int] = {}
    chosen = []

    def novel(feats):
        trial, out = dict(piv), []
        for f in feats:
            red = _reduce(f[2], trial)
            if red:
                trial[red.bit_length() - 1] = red
                out.append(f)
        return out

    def add(fs):
        for f in fs:
            red = _reduce(f[2], piv)
            piv[red.bit_length() - 1] = red
            chosen.append(f)

    dirs = list(choices)
    while len(piv) < span:
        rng.shuffle(dirs)
        paired = False
        for d in dirs:
            if span - len(piv) < 2:
                break
            nv = novel(choices[d])
            if len(nv) >= 2:
                add(nv[:2])
                paired = True
        if paired:
            continue
        for d in dirs:  # no pair left: singles
            nv = novel(choices[d])
            if nv:
                add(nv[:1])
                break
        else:
            return None
    return chosen


def express(rows: list[int], vectors: list[int]) -> list[int]:
    """coeffs[i]: the subset of `vectors` (as bits) XORing to rows[i]; vectors must be independent."""
    tracked: dict[int, tuple[int, int]] = {}
    for j, v in enumerate(vectors):
        c = 1 << j
        while v:
            p = v.bit_length() - 1
            if p not in tracked:
                tracked[p] = (v, c)
                break
            v ^= tracked[p][0]
            c ^= tracked[p][1]
        assert v, 'dependent features'
    out = []
    for r in rows:
        c = 0
        while r:
            p = r.bit_length() - 1
            assert p in tracked, 'row outside the feature span'
            r ^= tracked[p][0]
            c ^= tracked[p][1]
        out.append(c)
    return out


def grouped(C: np.ndarray, m: int, codims=range(17, -1, -1), trials: int = 16, transpose: bool = False,
            seed: int = 0) -> list[tuple[int, int, int, int, int]]:
    """Toffolis from groups of m outputs: per group, features (y, s) spanning the flattened rows.

    Rows are the low monomials and features carry high vectors (transpose: the other way round).
    """
    import random
    rng = random.Random(seed)
    X = C[1:, 1:]
    if transpose:
        X = X.transpose(1, 0, 2)
    nr, Y, O = X.shape
    terms = []
    for g0 in range(0, O, m):
        mm = min(m, O - g0)
        rows = [sum(1 << (y * mm + o) for y in range(Y) for o in range(mm) if X[r, y, g0 + o]) for r in range(nr)]
        best, extra = None, 0
        for cd in codims:  # the highest feasible codimension and two below it
            for _ in range(trials):
                feats = group_features(rows, Y, mm, cd, rng)
                if feats is not None and (best is None or _products(feats) < best[0]):
                    best = (_products(feats), feats)
            if best is not None:
                extra += 1
                if extra == 3:
                    break
        _, feats = best
        coeffs = express(rows, [f[2] for f in feats])
        by_s: dict[int, list[tuple[int, int]]] = {}
        for j, (y, s, _, _) in enumerate(feats):
            r_vec = sum(1 << r for r in range(nr) if coeffs[r] >> j & 1)
            by_s.setdefault(s, []).append((r_vec, y))
        for s, fs in by_s.items():
            for i in range(0, len(fs), 2):
                (r1, y1), (r2, y2) = fs[i], (fs[i + 1] if i + 1 < len(fs) else (0, 0))
                outs = s << g0
                # (row form) x (feature form): rows are low unless transposed
                terms.append((r1, y1, r2, y2, outs) if not transpose else (y1, r1, y2, r2, outs))
    return terms


def _solve(A: np.ndarray, c: np.ndarray) -> np.ndarray | None:
    """A solution x of A x = c over GF(2) (free variables 0), or None."""
    A, c = A.astype(np.uint8).copy(), c.astype(np.uint8).copy()
    n_rows, n = A.shape
    pivots, r = [], 0
    for col in range(n):
        hits = np.flatnonzero(A[r:, col]) + r if r < n_rows else []
        if len(hits) == 0:
            continue
        p = hits[0]
        A[[r, p]], c[[r, p]] = A[[p, r]], c[[p, r]]
        others = np.flatnonzero(A[:, col])
        others = others[others != r]
        A[others] ^= A[r]
        c[others] ^= c[r]
        pivots.append(col)
        r += 1
        if r == n_rows:
            break
    if np.any(c[r:]):
        return None
    x = np.zeros(n, np.uint8)
    for i, col in enumerate(pivots):
        x[col] = c[i]
    return x


def shared(C: np.ndarray, sizes: list[int], transpose: bool = True, trials: int = 8, seed: int = 0,
           margin: int = 2, log=None, groups: list[list[int]] | None = None) -> list[tuple[int, int, int, int, int]]:
    """Groups of the given sizes, each target first lowered in rank by fanning earlier products to it.

    For a group, pick d random row combinations y and solve, per output o, for the set of earlier
    products whose sum P makes y^T (X_o + P) = 0 for every y (|Y| d equations in as many unknowns as
    there are products). Those products get o as an extra target (CNOTs only) and the group's
    flattened rows lose d dimensions before `group_features` covers them.

    `groups` (from `low_groups`) plans every product inside the low address bits plus one group of
    low monomials, so that `build_circuit` can cache one group at a time.
    """
    import random
    rng = random.Random(seed)
    X = C[1:, 1:]
    if transpose:
        X = X.transpose(1, 0, 2)
    X = X.copy()
    nr, Y, O = X.shape
    allowed = None
    if groups:
        assert transpose, 'a grouped low cache needs the low monomials on the feature side'
        singles = sum(1 << (q - 1) for q in range(1, Y + 1) if q & (q - 1) == 0)
        allowed = [singles | sum(1 << (q - 1) for q in g) for g in groups]
    vec = lambda v, n: np.array([(v >> i) & 1 for i in range(n)], np.uint8)  # noqa: E731
    terms: list[list] = []        # [r1, y1, r2, y2, outs] in (row, feature) orientation
    mats: list[np.ndarray] = []   # each product's mixed matrix (nr, Y)
    g0 = 0
    for mm in sizes:
        mm = min(mm, O - g0)
        if mm <= 0:
            break
        d = max(0, len(terms) // Y - margin)
        if not X[:, :, g0:g0 + mm].any(axis=(0, 2)).all():
            d = 0   # the group uses only some feature coordinates (e.g. affine bits): fanning products in would spread it
        while d:
            ys = np.array([vec(rng.getrandbits(nr), nr) for _ in range(d)])
            if len(rank_factor([int(''.join(map(str, r[::-1])), 2) for r in ys])[0]) < d:
                continue
            A = np.concatenate([np.stack([y @ P % 2 for P in mats], axis=1) for y in ys], axis=0)  # (Y d, N)
            sols = []
            for o in range(g0, g0 + mm):
                c = np.concatenate([y @ X[:, :, o] % 2 for y in ys])
                x = _solve(A, c)
                if x is None:
                    break
                sols.append(x)
            if len(sols) == mm:
                for i, o in enumerate(range(g0, g0 + mm)):
                    for t in np.flatnonzero(sols[i]):
                        X[:, :, o] ^= mats[t]
                        terms[t][4] ^= 1 << o
                break
            d -= 1
        # Search only the feature coordinates the group uses: outputs whose mixed part lives on a few low
        # monomials (an affine bit: the single address bits only) would otherwise get a span over all Y.
        supp = [y for y in range(Y) if X[:, y, g0:g0 + mm].any()]
        sub = {y: i for i, y in enumerate(supp)}
        Ys = len(supp)
        rows = [sum(1 << (sub[y] * mm + o) for y in supp for o in range(mm) if X[r, y, g0 + o]) for r in range(nr)]
        allowed_s = [sum(1 << sub[y] for y in supp if a >> y & 1) for a in allowed] if allowed else None
        best, extra = None, 0
        for cd in range(Ys * mm, -1, -1):
            for _ in range(trials):
                feats = group_features(rows, Ys, mm, cd, rng, allowed=allowed_s)
                if feats is not None and (best is None or _products(feats) < best[0]):
                    best = (_products(feats), feats)
            if best is not None:
                extra += 1
                if extra == 3:
                    break
        feats = best[1]
        if log:
            log(f'group {g0}+{mm}: shared d={d}, rank {len(rank_factor(rows)[0])}, features {len(feats)}, products {best[0]}'
                + (f', {Ys} of {Y} feature coordinates' if Ys < Y else ''))
        coeffs = express(rows, [f[2] for f in feats])
        full = lambda ys: sum(1 << supp[i] for i in _bits(ys))  # noqa: E731
        by_s: dict[tuple[int, int], list[tuple[int, int]]] = {}
        for j, (y, s, _, g) in enumerate(feats):
            by_s.setdefault((s, g), []).append((sum(1 << r for r in range(nr) if coeffs[r] >> j & 1), full(y)))
        for (s, _), fs in by_s.items():
            for i in range(0, len(fs), 2):
                (r1, y1), (r2, y2) = fs[i], (fs[i + 1] if i + 1 < len(fs) else (0, 0))
                terms.append([r1, y1, r2, y2, s << g0])
                mats.append((np.outer(vec(r1, nr), vec(y1, Y)) ^ np.outer(vec(r2, nr), vec(y2, Y))).astype(np.uint8))
        g0 += mm
    return [tuple(t) if not transpose else (t[1], t[0], t[3], t[2], t[4]) for t in terms]


SIZES = (7, 6, 6, 6, 5, 5)  # groups of output bits for J = 5 at 8 bits (35 bits)


def _one(args):
    """(terms, grouped): the full low cache when its circuit fits in 128 qubits (cheaper: 293 against 313
    Toffolis per pass at 1,032 rows), otherwise the grouped low cache with borrowed top bits."""
    delta, n_sel, brot, lowbits, sizes, trials, seed, perm, full = args
    C = anf_tensor(delta, brot, lowbits, full=full)
    Cp = C[:, :, perm] if perm is not None else C
    back = {i: o for i, o in enumerate(perm)} if perm is not None else None

    def decompose(groups):
        terms = shared(Cp, list(sizes), trials=trials, seed=seed, groups=groups)
        if back is not None:  # the decomposition saw the outputs permuted: map its target masks back
            terms = [(a1, b1, a2, b2, sum(1 << back[i] for i in _bits(s))) for a1, b1, a2, b2, s in terms]
        return terms

    terms = decompose(None)
    if build_circuit(delta, terms, n_sel, brot, lowbits, full=full).num_qubits <= 128:
        return terms, False
    return decompose(low_groups(lowbits, 1 << (lowbits - 2))), True


def coded_layout(coded_words: list[int], J: int, brot: int, coded2_words=()) -> tuple[list[int] | None, list[int]]:
    """Output order and group sizes with the coded bits (bit 0 of the given words, bit 1 of `coded2_words`)
    as the last group, the rest in groups of 7 (the J=5 default sizes are kept when nothing is coded)."""
    O = J * (brot - 1)
    if not coded_words:
        return None, list(SIZES) if O == 35 else [6] * (O // 6) + ([O % 6] if O % 6 else [])
    coded = [j * (brot - 1) for j in coded_words] + [j * (brot - 1) + 1 for j in coded2_words]
    rest = [o for o in range(O) if o not in coded]
    sizes = [7] * (len(rest) // 7) + ([len(rest) % 7] if len(rest) % 7 else []) + [len(coded)]
    return rest + coded, sizes


def pad_affine(delta: np.ndarray, coded_words: list[int], coded2_words=()) -> np.ndarray:
    """Rows past the table (never looked up) padded to whole 16-address blocks, bit 0 of the coded words
    (and bit 1 of `coded2_words`) extended by the block's affine pattern so that the last block costs
    nothing either."""
    A = len(delta)
    out = np.concatenate([delta, np.zeros((-A % 16, delta.shape[1]), delta.dtype)])
    b0 = A - A % 16
    n = A - b0
    if 0 < n < 16:
        affs = [[c ^ (bin(m & a).count('1') & 1) for a in range(16)] for c in (0, 1) for m in range(16)]
        for bit, words in ((0, coded_words), (1, coded2_words)):
            for j in words:
                bits = (out[b0:b0 + n, j] >> bit) & 1
                fit = [f for f in affs if all(f[i] == bits[i] for i in range(n))]
                assert fit, f'bit {bit} of word {j} is not affine on the last block'
                out[b0:b0 + 16, j] = (out[b0:b0 + 16, j] & ~(1 << bit)) | (np.array(fit[0]) << bit)
    return out


def build_family(words: np.ndarray, brot: int = 8, j: int = 5, lowbits: int = 4, sizes=SIZES, trials: int = 6,
                 jobs: int = 8, coded=(), coded2=(), full: bool = False) -> list[km.Circuit]:
    """One circuit per batch of j words (deltas against the previous batch, as fourqrom.batch_deltas;
    words must be in the signed gauge). Each circuit caches every low monomial when that fits in 128
    qubits, and otherwise caches them one group at a time with borrowed top bits (`_one`).

    `coded`: word columns whose bit 0 is affine on every 16-address block (quantize.py --coded). A
    circuit's delta bit is affine when both batches' bits are, and those bits form their own output
    group (SomeJoint's coded bits), which saves about 25 Toffolis per circuit on our tables."""
    from concurrent.futures import ProcessPoolExecutor
    from fourqrom import batch_deltas
    A = len(words)
    n_sel = max(1, (A - 1).bit_length())
    deltas = list(batch_deltas(words, j))   # a list: coded circuits get padded deltas
    coded, coded2 = set(int(c) for c in coded), set(int(c) for c in coded2)
    tasks = []
    for k, d in enumerate(deltas):
        cw = [i for i in range(d.shape[1]) if j * k + i in coded and (k == 0 or j * (k - 1) + i in coded)]
        cw2 = [i for i in range(d.shape[1]) if j * k + i in coded2 and (k == 0 or j * (k - 1) + i in coded2)]
        if full and not cw and not cw2:   # `coded_layout` sizes count brot - 1 outputs; full mode has brot
            O = d.shape[1] * brot
            perm, sz = None, [6] * (O // 6) + ([O % 6] if O % 6 else [])
        else:
            perm, sz = coded_layout(cw, d.shape[1], brot, cw2)
        if cw:
            deltas[k] = d = pad_affine(d, cw, cw2)
        tasks.append((d, n_sel, brot, lowbits, sz, trials, k, perm, full))
    with ProcessPoolExecutor(jobs) as ex:  # decompositions in parallel; circuits do not pickle
        results = list(ex.map(_one, tasks))
    # When the full cache does not fit, the low monomials are cached one group at a time and each word's top
    # bit is borrowed (scratch): that is what keeps a 1,363-row table's circuit at 128 qubits (the cap);
    # caching every low monomial costs 140.
    groups = low_groups(lowbits, 1 << (lowbits - 2))
    return [build_circuit(d, t, n_sel, brot, lowbits, groups=groups, scratch=True, full=full) if grouped
            else build_circuit(d, t, n_sel, brot, lowbits, full=full) for d, (t, grouped) in zip(deltas, results)]
