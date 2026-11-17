# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Block cut planner for coded loaders (our own), on top of the v18 compiler's
pairing (parity_recover.candidates/probe) and matching (extract_matching.matching).

products = (525 - sum c) / 2 when the selected cuts admit a perfect pairing.
Forced cuts: every payload relation g placed on every nonlinear low coordinate.
"""
import sys, time, json, random
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT / 'inputs/chem_goal_v18/deliverables/six_cache_words_combined_v18/compiler'
sys.path.insert(0, str(COMP))
from parity_recover import basis, nullspace, reduce, candidates, alternating_field, gf_rank, NOUT, NDIM
from transport_cuts import local, complete_forced, rref
from gauge_plan_fit import cross_tensor

REL_LSB = [1 << (7 * z) for z in range(5)]
REL_P1 = sum(1 << (7 * z + 1) for z in range(5))


def _addr_shape(rows):
    """Rows -> (nh, rem, N, hbits) for the (h, l) address decomposition.

    1220 -> nh 77, rem 4, N 1232, hbits 7 (the shipped shape; the historical constants).
    """
    nh = (rows + 15) // 16
    rem = rows - 16 * (nh - 1)
    return nh, rem, nh * 16, (nh - 1).bit_length()


def complete_words(words, rows=None):
    """rebuild.py's completion: zero ANF at (h=nh-1, l>=rem).

    `rows` defaults to len(words); at rows=1220 this is byte-identical to the historical
    hard-coded 1232/77/76/4 version (verified), and it generalises to other row counts
    (791 -> nh 50 rem 7, 756 -> nh 48 rem 4, 648 -> nh 41 rem 8).
    """
    words = np.asarray(words, dtype=np.uint8)
    rows = len(words) if rows is None else rows
    nh, rem, N, hbits = _addr_shape(rows)
    a = np.zeros((N, 75), dtype=np.uint8); a[:rows] = words
    f = a.reshape(nh, 16, 75)
    for b in range(4):
        for l in range(16):
            if l & (1 << b): f[:, l] ^= f[:, l ^ (1 << b)]
    for b in range(hbits):
        for h in range(nh):
            if h & (1 << b): f[h] ^= f[h ^ (1 << b)]
    f[nh - 1, rem:] = 0
    for b in range(hbits):
        for h in range(nh):
            if h & (1 << b): f[h] ^= f[h ^ (1 << b)]
    for b in range(4):
        for l in range(16):
            if l & (1 << b): f[:, l] ^= f[:, l ^ (1 << b)]
    assert np.array_equal(a[:rows], words)
    return a


def forced(part, rels):
    return [g << (NOUT * j) for j, m in enumerate(part) if (m + 1) & m for g in rels]


def coord_relations(target, m, hmax=77):
    """payload functionals annihilating low coordinate m (0..14) of the target for h < hmax."""
    sl = [(x >> (NOUT * m)) & ((1 << NOUT) - 1) for x in target[1:hmax]]
    return nullspace(sl, NOUT)


class BlockPlan:
    def __init__(self, target, parts, rels, per_coord=False, hmax=77):
        """hmax=76 uses only the 75 fully determined high slices; the off-domain slice h=76 is then
        fixed afterwards by a padding solve (solve_padding)."""
        self.target = target; self.parts = parts; self.rels = rels; self.hmax = hmax
        self.F, self.Q, self.full = [], [], []
        for part in parts:
            loc = [local(x, part) for x in target[1:hmax]]
            full = nullspace(loc, len(part) * NOUT)
            F = forced(part, rels)
            if per_coord:
                for j, m in enumerate(part):
                    F += [g << (NOUT * j) for g in coord_relations(target, m, hmax)]
            fb = basis(full)
            for f in F:
                assert reduce(f, fb) == 0, 'forced cut is not an annihilator'
            F = list(basis(F).values())
            Q = complete_forced(full, F)
            self.F.append(F); self.Q.append(Q); self.full.append(full)

    def state(self, cuts):
        return {'parts': self.parts, 'cuts': cuts}

    def check(self, cuts, rng, repeats=1):
        s = self.state(cuts)
        pairs, hist = candidates(s, cuts)
        dim = NDIM - sum(len(c) for c in cuts)
        span = len(basis([x for p in pairs for x in p[:2]]))
        if span < dim:
            return dim, span, 0
        r = max(gf_rank(alternating_field(pairs, rng)) for _ in range(repeats))
        return dim, span, r

    def greedy(self, init=None, seed=1, extra_random=60, verbose=True, time_limit=600):
        rng = random.Random(seed)
        cuts = [list(c) for c in (init if init is not None else self.F)]
        t0 = time.time()
        dim, span, r = self.check(cuts, rng)
        if verbose:
            print(f'   start sum c {sum(map(len, cuts))} dim {dim} span {span} alt-rank {r}', flush=True)
        if r < 2 * (dim // 2):
            return None
        self.best = [list(c) for c in cuts] if dim % 2 == 0 else None
        order = []
        for i, Q in enumerate(self.Q):
            for q in Q:
                order.append((i, q))
        rng.shuffle(order)
        tried = 0
        def try_add(i, q):
            b = basis(cuts[i])
            if reduce(q, b) == 0:
                return False
            cuts[i].append(q)
            d, sp, rk = self.check(cuts, rng)
            if sp == d and rk >= 2 * (d // 2):
                if d % 2 == 0:
                    self.best = [list(c) for c in cuts]
                return True
            cuts[i].pop()
            return False
        for i, q in order:
            if time.time() - t0 > time_limit: break
            tried += 1
            if try_add(i, q) and verbose:
                print(f'   + block {i}: sum c {sum(map(len, cuts))} products {(NDIM - sum(map(len, cuts))) // 2} ({time.time()-t0:.0f}s)', flush=True)
        # random combinations within each block's Q
        for it in range(extra_random):
            if time.time() - t0 > time_limit: break
            i = rng.randrange(len(self.Q))
            if not self.Q[i]: continue
            q = 0
            for v in self.Q[i]:
                if rng.getrandbits(1): q ^= v
            if q and try_add(i, q) and verbose:
                print(f'   + rand block {i}: sum c {sum(map(len, cuts))} products {(NDIM - sum(map(len, cuts))) // 2} ({time.time()-t0:.0f}s)', flush=True)
        return self.best


def local_search(bp, cuts, seconds=300, seed=7, tries_per_move=12, verbose=True, p_down=0.08, restart_every=150):
    """Swap search: drop one non-forced cut, try to re-add up to two annihilators."""
    rng = random.Random(seed)
    cuts = [list(c) for c in cuts]
    best = [list(c) for c in cuts] if (NDIM - sum(map(len, cuts))) % 2 == 0 else bp.best
    bestc = sum(map(len, best)) if best else 0
    t0 = time.time()
    nF = [len(f) for f in bp.F]
    def feasible(cs):
        d, sp, rk = bp.check(cs, rng)
        return sp == d and rk >= 2 * (d // 2), d
    def rand_cut(i):
        q = 0
        while not q:
            for v in bp.Q[i]:
                if rng.getrandbits(1): q ^= v
            if not bp.Q[i]: return 0
        return q
    moves = 0
    while time.time() - t0 < seconds:
        moves += 1
        cur = sum(map(len, cuts))
        i = rng.randrange(len(cuts))
        trial = [list(c) for c in cuts]
        if len(trial[i]) > nF[i] and rng.random() < 0.7:
            j = rng.randrange(nF[i], len(trial[i]))
            trial[i].pop(j)
        added = 0
        for _ in range(tries_per_move):
            bi = rng.randrange(len(trial)) if rng.random() < 0.5 else i
            q = rand_cut(bi)
            if not q or reduce(q, basis(trial[bi])) == 0:
                continue
            trial[bi].append(q)
            ok, d = feasible(trial)
            if ok:
                added += 1
                if added >= 2:
                    break
            else:
                trial[bi].pop()
        new = sum(map(len, trial))
        if moves % restart_every == 0 and best is not None:
            cuts = [list(c) for c in best]
            continue
        if new >= cur or (new == cur - 1 and rng.random() < p_down):
            ok, d = feasible(trial)
            if ok:
                cuts = trial
                if d % 2 == 0 and new > bestc:
                    best = [list(c) for c in trial]; bestc = new
                    if verbose:
                        print(f'   LS move {moves}: sum c {new} products {(NDIM - new) // 2} ({time.time()-t0:.0f}s)', flush=True)
    return best


def top_down(bp, seed=3, trials=30, verbose=True, time_limit=900):
    """Start from the full annihilator in every block; repeatedly drop the codim-1 subspace
    (of the non-forced part of one block) that maximizes (span - dim), until span == dim and
    the pairing is perfect or near-perfect. Then return the last even perfect state."""
    rng = random.Random(seed)
    t0 = time.time()
    R = [list(q) for q in bp.Q]                      # non-forced basis per block
    def cuts_of(Rs):
        return [list(bp.F[i]) + list(Rs[i]) for i in range(len(Rs))]
    def span_dim(Rs):
        cs = cuts_of(Rs)
        pairs, _ = candidates({'parts': bp.parts, 'cuts': cs}, cs)
        d = NDIM - sum(map(len, cs))
        return len(basis([x for p in pairs for x in p[:2]])), d, pairs
    def hyper(Ri):
        y = rng.getrandbits(len(Ri))
        if y == 0:
            y = 1
        p = (y & -y).bit_length() - 1
        return [Ri[i] ^ (Ri[p] if (y >> i) & 1 else 0) for i in range(len(Ri)) if i != p]
    sp, d, pairs = span_dim(R)
    while time.time() - t0 < time_limit:
        if sp == d:
            r = gf_rank(alternating_field(pairs, rng))
            if r >= 2 * (d // 2):
                if verbose:
                    print(f'   top-down feasible: sum c {NDIM - d} products {d - r // 2} ({time.time()-t0:.0f}s)', flush=True)
                break
        best = None
        for _ in range(trials):
            i = rng.randrange(len(R))
            if not R[i]:
                continue
            Rn = [list(x) for x in R]; Rn[i] = hyper(R[i])
            s2, d2, p2 = span_dim(Rn)
            score = s2 - d2
            if best is None or score > best[0]:
                best = (score, Rn, s2, d2, p2)
        if best is None:
            return None
        _, R, sp, d, pairs = best
        if verbose:
            print(f'   drop: sum c {NDIM - d} span {sp} dim {d} ({time.time()-t0:.0f}s)', flush=True)
    cs = cuts_of(R)
    d = NDIM - sum(map(len, cs))
    if d % 2:
        # drop one more non-forced cut to make the dimension even, keeping feasibility
        for _ in range(60):
            i = rng.randrange(len(R))
            if not R[i]:
                continue
            Rn = [list(x) for x in R]; Rn[i] = hyper(R[i])
            c2 = cuts_of(Rn); d2, s2, r2 = bp.check(c2, rng)
            if s2 == d2 and r2 == d2:
                return c2
        return None
    return cs


M35 = (1 << NOUT) - 1


def proj(phi, l):
    """constraint vector of cut phi (local 3*35 bits) on low form l (3 bits)."""
    v = 0
    for j in range(3):
        if (l >> j) & 1:
            v ^= (phi >> (NOUT * j)) & M35
    return v


def aligned_candidates(bp, cuts, i, S):
    """Annihilators of block i (not already cuts) whose constraint on every form l in S
    lies in the current constraint span K_l of that form (so those forms keep their outs)."""
    Ci = cuts[i]
    K = {l: basis([proj(c, l) for c in Ci]) for l in range(1, 8)}
    pool = list(bp.F[i]) + list(bp.Q[i])
    # residues of each pool vector on the forms in S
    rows = []
    for q in pool:
        r = 0; sh = 0
        for l in S:
            r |= reduce(proj(q, l), K[l]) << sh; sh += NOUT
        rows.append(r)
    # find combinations x with sum x_i rows_i = 0
    combos = []
    d = {}
    for idx, r in enumerate(rows):
        co = 1 << idx; x = r
        while x:
            p = x.bit_length() - 1
            if p in d:
                x ^= d[p][0]; co ^= d[p][1]
            else:
                d[p] = (x, co); break
        if not x:
            combos.append(co)
    cb = basis(Ci)
    out = []
    for co in combos:
        phi = 0
        for idx in range(len(pool)):
            if (co >> idx) & 1:
                phi ^= pool[idx]
        if phi and reduce(phi, cb):
            out.append(phi)
    return out


def aligned_greedy(bp, cuts, seconds=300, seed=5, verbose=True):
    rng = random.Random(seed)
    cuts = [list(c) for c in cuts]
    best = [list(c) for c in cuts] if (NDIM - sum(map(len, cuts))) % 2 == 0 else getattr(bp, 'best', None)
    t0 = time.time()
    import itertools
    improved = True
    while improved and time.time() - t0 < seconds:
        improved = False
        for size in (6, 5, 4):
            order = [(i, S) for i in range(len(cuts)) for S in itertools.combinations(range(1, 8), size)]
            rng.shuffle(order)
            for i, S in order:
                if time.time() - t0 > seconds:
                    break
                cands = aligned_candidates(bp, cuts, i, S)
                rng.shuffle(cands)
                for phi in cands[:3]:
                    cuts[i].append(phi)
                    d, sp, rk = bp.check(cuts, rng)
                    if sp == d and rk >= 2 * (d // 2):
                        improved = True
                        if d % 2 == 0:
                            best = [list(c) for c in cuts]
                        if verbose:
                            print(f'   aligned +block {i} |S|={size}: sum c {sum(map(len, cuts))} products {(NDIM - sum(map(len, cuts)) + 1) // 2} ({time.time()-t0:.0f}s)', flush=True)
                        break
                    cuts[i].pop()
            if improved:
                break
    return best


def solve_gf2(rows, rhs, nvar):
    """rows: list of int masks over nvar unknowns; rhs: list of 0/1. Returns a solution int or None."""
    piv = {}
    for r, b in zip(rows, rhs):
        x = r | (b << nvar)
        while x & ((1 << nvar) - 1):
            p = (x & ((1 << nvar) - 1)).bit_length() - 1
            if p in piv:
                x ^= piv[p]
            else:
                piv[p] = x; break
        else:
            if x >> nvar & 1:
                return None
    sol = 0
    for p in sorted(piv):
        x = piv[p]
        val = (x >> nvar) & 1
        rest = x & ((1 << p) - 1)
        if bin(rest & sol).count('1') & 1:
            val ^= 1
        if val:
            sol |= 1 << p
    return sol


def physical_cuts(parts, cuts, Binv=None):
    """block-local cuts -> functionals on the physical 15 x 35 space (525-bit ints)."""
    out = []
    M = (1 << NOUT) - 1
    for part, cs in zip(parts, cuts):
        for c in cs:
            phi_new = [0] * 15
            for j, i in enumerate(part):
                phi_new[i] = (c >> (NOUT * j)) & M
            if Binv is None:
                phys = phi_new
            else:
                phys = [0] * 15
                for i in range(15):
                    if phi_new[i]:
                        for m in range(15):
                            if (Binv[i] >> m) & 1:
                                phys[m] ^= phi_new[i]
            out.append(sum(phys[m] << (NOUT * m) for m in range(15)))
    return out


def solve_padding(phys_cuts, D):
    """Find F (free part of the h=76 slice on monomial coordinates 3..14, 12 x 35 bits) with
    every cut annihilating D + F. D is the default-completed slice (zero on free coordinates)."""
    nvar = 12 * NOUT
    rows = [c >> (3 * NOUT) for c in phys_cuts]
    rhs = [bin(c & D).count('1') & 1 for c in phys_cuts]
    sol = solve_gf2(rows, rhs, nvar)
    return None if sol is None else sol << (3 * NOUT)


def padded_words(W, k, F, rows=None):
    """Completed N x 75 table whose loader-k delta has ANF coefficients F on (nh-1, l' >= rem)."""
    W = np.asarray(W, dtype=np.uint8)
    rows = len(W) if rows is None else rows
    nh, rem, N, _ = _addr_shape(rows)
    Wc = complete_words(W, rows=rows).astype(np.int64)
    M = (1 << NOUT) - 1
    Fm = {m + 1: (F >> (NOUT * m)) & M for m in range(3, 15)}       # low monomial l' -> 35-bit vector
    for l in range(rem, 16):
        acc = 0
        for lp, v in Fm.items():
            if (lp & l) == lp:
                acc ^= v
        if not acc:
            continue
        a = 16 * (nh - 1) + l
        for j in range(5):
            t = 5 * k + j
            old = int(Wc[a, t]); helper = ((old >> 7) ^ (old >> 6)) & 1
            pay = (old & 127) ^ ((acc >> (7 * j)) & 127)
            Wc[a, t] = pay | ((((pay >> 6) & 1) ^ helper) << 7)
    return Wc.astype(np.uint8)


def top_down_rank(bp, seed=3, trials=30, verbose=True, time_limit=900, patience=3):
    """Top-down with the true objective. State = non-forced cut basis per block. Each step drops one
    random hyperplane (one cut) and keeps the trial with the fewest products = d - rank/2.
    Stops when no trial keeps products from growing. Returns (cuts, d, rank)."""
    rng = random.Random(seed)
    t0 = time.time()
    R = [list(q) for q in bp.Q]
    def cuts_of(Rs):
        return [list(bp.F[i]) + list(Rs[i]) for i in range(len(Rs))]
    def evalR(Rs):
        cs = cuts_of(Rs)
        pairs, _ = candidates({'parts': bp.parts, 'cuts': cs}, cs)
        d = NDIM - sum(map(len, cs))
        r = gf_rank(alternating_field(pairs, rng))
        return d, r
    def hyper(Ri):
        y = rng.getrandbits(len(Ri)) or 1
        p = (y & -y).bit_length() - 1
        return [Ri[i] ^ (Ri[p] if (y >> i) & 1 else 0) for i in range(len(Ri)) if i != p]
    d, r = evalR(R)
    prod = d - r // 2
    best = (prod, [list(x) for x in R], d, r)
    if verbose:
        print(f'   saturation: d {d} rank {r} products {prod}', flush=True)
    bad = 0
    while time.time() - t0 < time_limit:
        cand = None
        for _ in range(trials):
            i = rng.randrange(len(R))
            if not R[i]:
                continue
            Rn = [list(x) for x in R]; Rn[i] = hyper(R[i])
            d2, r2 = evalR(Rn)
            p2 = d2 - r2 // 2
            if cand is None or p2 < cand[0]:
                cand = (p2, Rn, d2, r2)
        if cand is None:
            break
        prod, R, d, r = cand
        if prod < best[0] or (prod == best[0] and r == d):
            best = (prod, [list(x) for x in R], d, r); bad = 0
        else:
            bad += 1
        if verbose:
            print(f'   drop: sum c {NDIM - d} d {d} rank {r} products {prod} ({time.time()-t0:.0f}s)', flush=True)
        if bad >= patience or r >= d - 1 and prod > best[0]:
            break
    prod, R, d, r = best
    return cuts_of(R), d, r


def descend_path(bp, seed=3, trials=30, until_perfect=True, time_limit=600, verbose=False, topk=12):
    """Greedy rank-guided descent from saturation; returns {sum_c: (R_state, d, rank)} along the path.
    Each step screens `trials` random one-cut drops by pair-span and ranks the best `topk`."""
    rng = random.Random(seed)
    t0 = time.time()
    R = [list(q) for q in bp.Q]
    def cuts_of(Rs):
        return [list(bp.F[i]) + list(Rs[i]) for i in range(len(Rs))]
    def pairs_of(Rs):
        cs = cuts_of(Rs)
        pairs, _ = candidates({'parts': bp.parts, 'cuts': cs}, cs)
        return pairs, NDIM - sum(map(len, cs))
    def hyper(Ri):
        y = rng.getrandbits(len(Ri)) or 1
        p = (y & -y).bit_length() - 1
        return [Ri[i] ^ (Ri[p] if (y >> i) & 1 else 0) for i in range(len(Ri)) if i != p]
    pairs, d = pairs_of(R)
    r = gf_rank(alternating_field(pairs, rng))
    path = {NDIM - d: ([list(x) for x in R], d, r)}
    while time.time() - t0 < time_limit and r < 2 * (d // 2):
        scr = []
        for _ in range(trials):
            i = rng.randrange(len(R))
            if not R[i]:
                continue
            Rn = [list(x) for x in R]; Rn[i] = hyper(R[i])
            pr, d2 = pairs_of(Rn)
            sp = len(basis([x for p in pr for x in p[:2]]))
            scr.append((sp, Rn, pr, d2))
        scr.sort(key=lambda x: -x[0])
        cand = None
        for sp, Rn, pr, d2 in scr[:topk]:
            r2 = gf_rank(alternating_field(pr, rng))
            if cand is None or r2 > cand[2]:
                cand = (Rn, d2, r2)
        R, d, r = cand
        path[NDIM - d] = ([list(x) for x in R], d, r)
        if verbose:
            print(f'   descend: sum c {NDIM - d} rank {r}/{d} ({time.time()-t0:.0f}s)', flush=True)
    return path


def rank_climb(bp, R, seconds=300, seed=9, verbose=True, block_weights=None):
    """Fixed cut count. Swap one non-forced cut direction for another annihilator in the same block;
    accept if the pairing rank does not decrease. Returns (R, d, rank)."""
    rng = random.Random(seed)
    t0 = time.time()
    R = [list(x) for x in R]
    def cuts_of(Rs):
        return [list(bp.F[i]) + list(Rs[i]) for i in range(len(Rs))]
    def evalR(Rs):
        cs = cuts_of(Rs)
        pairs, _ = candidates({'parts': bp.parts, 'cuts': cs}, cs)
        return NDIM - sum(map(len, cs)), gf_rank(alternating_field(pairs, rng))
    def hyper(Ri):
        y = rng.getrandbits(len(Ri)) or 1
        p = (y & -y).bit_length() - 1
        return [Ri[i] ^ (Ri[p] if (y >> i) & 1 else 0) for i in range(len(Ri)) if i != p]
    d, r = evalR(R)
    it = 0
    while time.time() - t0 < seconds and r < 2 * (d // 2):
        it += 1
        i = rng.randrange(len(R))
        if len(R[i]) >= len(bp.Q[i]) or not R[i]:
            continue                                   # block saturated: nothing to swap in
        Rn = [list(x) for x in R]
        Rn[i] = hyper(R[i])
        cb = basis(list(bp.F[i]) + Rn[i])
        q = 0
        for _ in range(20):
            q = 0
            for v in bp.Q[i]:
                if rng.getrandbits(1):
                    q ^= v
            if q and reduce(q, cb):
                break
        if not q or not reduce(q, cb):
            continue
        Rn[i].append(q)
        d2, r2 = evalR(Rn)
        if r2 >= r:
            if verbose and r2 > r:
                print(f'   climb it {it}: rank {r2}/{d2} ({time.time()-t0:.0f}s)', flush=True)
            R, r = Rn, r2
    return R, d, r


def _span_array(vs):
    out = np.zeros(1, dtype=np.int64)
    for v in vs:
        out = np.concatenate([out, out ^ v])
    return out


def drop_scores(bp, R, b):
    """Score every one-cut drop y (nonzero mask over the non-forced cut basis of block b):
    number of cross-block form pairs (l in b, l' elsewhere) that gain a pair dimension.
    A drop y gains one for (l, l') iff y lies in the row space of [proj(r_i, l) mod (forced_l + K_l')]."""
    n = len(R[b])
    cuts = [list(bp.F[i]) + list(R[i]) for i in range(len(R))]
    other = []
    for b2 in range(len(R)):
        if b2 == b:
            continue
        for l2 in range(1, 8):
            other.append([proj(c, l2) for c in cuts[b2]])
    total = np.zeros(1 << n, dtype=np.int32)
    for l in range(1, 8):
        forced_l = [proj(f, l) for f in bp.F[b]]
        p = [proj(r, l) for r in R[b]]
        for K in other:
            base = basis(K + forced_l)
            pbar = [reduce(v, base) for v in p]
            rows = []
            for j in range(NOUT):
                m = 0
                for i, v in enumerate(pbar):
                    if (v >> j) & 1:
                        m |= 1 << i
                if m:
                    rows.append(m)
            rb = list(basis(rows).values())
            if not rb or len(rb) > 16:
                if len(rb) > 16:
                    total += 1                     # nearly every drop helps this pair
                continue
            idx = _span_array(rb)
            total[idx] += 1
    total[0] = -1
    return total


def descend_smart(bp, seed=3, per_block=6, extra_random=6, time_limit=900, verbose=False):
    """Rank-guided descent with scored drops (drop_scores) instead of random hyperplanes."""
    rng = random.Random(seed)
    t0 = time.time()
    R = [list(q) for q in bp.Q]
    def cuts_of(Rs):
        return [list(bp.F[i]) + list(Rs[i]) for i in range(len(Rs))]
    def evalR(Rs):
        cs = cuts_of(Rs)
        pairs, _ = candidates({'parts': bp.parts, 'cuts': cs}, cs)
        return NDIM - sum(map(len, cs)), gf_rank(alternating_field(pairs, rng))
    def drop(Ri, y):
        p = (y & -y).bit_length() - 1
        return [Ri[i] ^ (Ri[p] if (y >> i) & 1 else 0) for i in range(len(Ri)) if i != p]
    d, r = evalR(R)
    path = {NDIM - d: ([list(x) for x in R], d, r)}
    while time.time() - t0 < time_limit and r < 2 * (d // 2):
        cands = []
        for b in range(len(R)):
            n = len(R[b])
            if n == 0:
                continue
            sc = drop_scores(bp, R, b)
            top = np.argsort(-sc)[:per_block]
            for y in top:
                cands.append((int(sc[y]), b, int(y)))
            for _ in range(extra_random // len(R) + 1):
                cands.append((0, b, rng.randrange(1, 1 << n)))
        best = None
        for sc, b, y in cands:
            Rn = [list(x) for x in R]; Rn[b] = drop(R[b], y)
            d2, r2 = evalR(Rn)
            if best is None or r2 > best[2]:
                best = (Rn, d2, r2, sc, b)
        R, d, r, sc, b = best
        path[NDIM - d] = ([list(x) for x in R], d, r)
        if verbose:
            print(f'   smart: sum c {NDIM - d} rank {r}/{d} (block {b}, score {sc}; {time.time()-t0:.0f}s)', flush=True)
    return path
