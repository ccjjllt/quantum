"""Exact word polish of the one-body rows: lower error_1 at a given word width.

The verifier pairs each one-body row v_j (decoded from its words) with an eigenpair (lambda_j, e_j)
of h1' and reports error_1 = ||sum_j lambda_j v_j v_j^T - h1'||_F. Rounding the eigenvectors to
8-bit words leaves error_1 far above the 20 mHa gate; moving single words by +-1 fixes most of it.
With M the current residual, replacing v_j by v' changes error_1^2 exactly by

    2 lambda_j (v'^T M v' - v_j^T M v_j) + lambda_j^2 ||v' v'^T - v_j v_j^T||^2,

so all moves of a row are scored at once; the best improving move is applied and M updated.
(mrmeows' `refresh_one_body8.py` fills this role in the public 8-bit pipeline; this is our own.)
"""
from __future__ import annotations

import numpy as np

import encode


def polish(words: np.ndarray, h1p: np.ndarray, edges: np.ndarray, brot: int, sweeps: int = 20,
           steps=(-1, 1), even=(), quad=()) -> np.ndarray:
    """Signed-gauge one-body words (N, N-1) with row j meant for the j-th eigenvector of h1' (ascending).
    Columns in `even` only move by even steps (their low bit is a code bit), those in `quad` by multiples
    of 4 (two code bits)."""
    even, quad_cols = set(even), set(quad)   # (`quad` below is the quadratic form)
    lam, _ = np.linalg.eigh(h1p)
    mod, lo, hi = 1 << brot, -(1 << (brot - 2)), (1 << (brot - 2)) - 1
    k = np.where(words > hi, words - mod, words).astype(np.int64)
    V = encode.decode(k % mod, edges, brot)                       # (N, N) rows v_j
    M = (V.T * lam) @ V - h1p
    for _ in range(sweeps):
        moved = 0
        for j in range(len(k)):
            cands, moves = [], []
            for t in range(k.shape[1]):
                for s in steps:
                    if (t in even and s % 2) or (t in quad_cols and s % 4) or not lo <= k[j, t] + s <= hi:
                        continue
                    row = k[j].copy()
                    row[t] += s
                    cands.append(row)
                    moves.append((t, s))
            U = encode.decode(np.array(cands) % mod, edges, brot)   # (n, N)
            v = V[j]
            quad = np.einsum('np,pq,nq->n', U, M, U) - v @ M @ v
            ov = U @ v
            dd = 2 - 2 * ov ** 2                                     # ||u u^T - v v^T||^2 for unit vectors
            gain = 2 * lam[j] * quad + lam[j] ** 2 * dd
            i = int(np.argmin(gain))
            if gain[i] < -1e-15:
                t, s = moves[i]
                k[j, t] += s
                u = U[i]
                M += lam[j] * (np.outer(u, u) - np.outer(v, v))
                V[j] = u
                moved += 1
        if not moved:
            break
    return k % mod


def signed_gauge(words: np.ndarray, edges: np.ndarray, brot: int) -> np.ndarray:
    """The same unit vectors up to sign, with every angle in [-pi/2, pi/2) (exact, integer only).

    Walk the tree backwards (the decoder applies rotation 0 first): a node whose sign was flipped
    negates the angles that mix it in, and an angle outside the gauge moves by pi, which negates
    its first node. The decoded row changes at most by an overall sign.
    """
    mod = 1 << brot
    half, quarter = mod >> 1, mod >> 2
    out = np.asarray(words, np.int64).copy() % mod
    sign = np.ones((len(out), edges.shape[0] + 1), np.int8)
    for k in reversed(range(edges.shape[0])):
        p, q = edges[k]
        a = np.where(sign[:, p] != sign[:, q], (-out[:, k]) % mod, out[:, k])
        flip = (a >= quarter) & (a < 3 * quarter)
        out[:, k] = np.where(flip, (a + half) % mod, a)
        sign[flip, p] *= -1
        sign[:, q] = 1
    return out


def error(words: np.ndarray, h1p: np.ndarray, edges: np.ndarray, brot: int) -> float:
    """error_1 with row j assigned to the j-th eigenvalue of h1' (ascending)."""
    lam = np.linalg.eigvalsh(h1p)
    V = encode.decode(words % (1 << brot), edges, brot)
    return float(np.linalg.norm((V.T * lam) @ V - h1p))


AFFINE = np.array([[c ^ (bin(mask & a).count('1') & 1) for a in range(16)] for c in (0, 1) for mask in range(16)],
                  dtype=np.int64)   # the 32 patterns of a bit affine in the 4 low address bits (RM(1,4))


def code_bits(words: np.ndarray, cols, following: np.ndarray, h1p: np.ndarray | None = None,
              edges: np.ndarray | None = None, brot: int | None = None, sweeps: int = 2) -> np.ndarray:
    """Bit 0 of the given columns made affine on every 16-address block (the one-body rows are addresses
    0..N-1; `following` holds the two-body rows that complete the last block, whose pattern they fix).
    Each word moves to the nearest value of the required parity, which `polish` and `signed_gauge` keep
    (steps of +-2, negation and half turns). With h1p, the pattern of every (block, column) is chosen
    by coordinate descent on error_1 (a few sweeps over the 32 patterns); else the closest in Hamming
    distance."""
    out = np.asarray(words, np.int64).copy()
    N = len(out)
    mod = 1 << (brot if brot else 8)

    def apply(table, b0, col, pattern):
        n = min(16, N - b0)
        bits = table[b0:b0 + n, col] & 1
        want = np.asarray(pattern[:n])
        move = np.where(bits != want, np.where((table[b0:b0 + n, col] % mod) >= mod // 2, -1, 1), 0)  # toward 0
        table[b0:b0 + n, col] += move

    choices = {}
    for col in cols:
        bits = np.concatenate([out[:, col] & 1, following[:, col] & 1])
        for b0 in range(0, N, 16):
            fixed = [(a - b0, bits[a]) for a in range(N, min(b0 + 16, len(bits)))]
            cands = [f for f in AFFINE if all(f[i] == v for i, v in fixed)] or list(AFFINE)  # free if the
            n = min(16, N - b0)                                                              # column is not coded there
            best = min(cands, key=lambda f: int(np.sum(f[:n] != bits[b0:b0 + n])))
            choices[b0, col] = (cands, best)
            apply(out, b0, col, best)
    if h1p is None:
        return out
    cur = error(out, h1p, edges, brot)
    for _ in range(sweeps):
        improved = 0
        for (b0, col), (cands, best) in list(choices.items()):
            if len(cands) == 1:
                continue
            for f in cands:
                if f is best:
                    continue
                trial = out.copy()
                apply(trial, b0, col, f)
                e = error(trial, h1p, edges, brot)
                if e < cur - 1e-12:
                    cur, out, best, improved = e, trial, f, improved + 1
            choices[b0, col] = (cands, best)
        if not improved:
            break
    return out


def refresh(h1p: np.ndarray, edges: np.ndarray, brot: int, start: np.ndarray | None = None, kicks: int = 40,
            seed: int = 0, coded=None, following: np.ndarray | None = None, coded2=None) -> np.ndarray:
    """One-body words for h1': the better of rounded eigenvectors and `start`, polished, then improved
    by random kicks (a few words of a few rows moved by +-1, re-polished, kept if better).
    With `coded` columns, their bit 0 is kept affine per 16-address block (see `code_bits`), so the
    polish and the kicks move those words by +-2 only."""
    coded = [] if coded is None else list(coded)
    coded2 = [] if coded2 is None else list(coded2)
    mod, lo, hi = 1 << brot, -(1 << (brot - 2)), (1 << (brot - 2)) - 1
    _, vecs = np.linalg.eigh(h1p)
    cands = [encode.signed_words(vecs.T, edges, brot)] + ([start] if start is not None else [])
    k = min((polish(c, h1p, edges, brot, steps=(-2, -1, 1, 2)) for c in cands),
            key=lambda c: error(c, h1p, edges, brot))
    # Progressive rounding (onebody_quant: freeze the angles whose rounding hurts most, refit the rest) beats the
    # polished rounded eigenvectors uncoded too (6.4 vs 11 mHa at 8 bits), and it is what makes coded bits and
    # 7-bit words affordable on the one-body rows (projecting polished words onto the codes costs like 7-bit).
    import onebody_quant
    cands = [onebody_quant.quantize_coded(h1p, edges, brot, coded, following if coded else np.zeros((16, k.shape[1]), np.int64),
                                          coded2=coded2)]
    if coded and not coded2:
        cands.append(code_bits(k, coded, following, h1p, edges, brot))
    if not coded:
        cands.append(k)
    k = min((polish(c, h1p, edges, brot, steps=(-4, -2, -1, 1, 2, 4), even=coded, quad=coded2) for c in cands),
            key=lambda c: error(c, h1p, edges, brot))
    best = error(k, h1p, edges, brot)
    rng = np.random.default_rng(seed)
    N = len(k)
    for _ in range(kicks):
        trial = k.copy()
        for r in rng.choice(N, 4, replace=False):
            cols = rng.choice(trial.shape[1], 6, replace=False)
            step = np.where(np.isin(cols, coded2), 4, np.where(np.isin(cols, coded), 2, 1))
            moved = trial[r, cols] + rng.choice([-1, 1], 6) * step
            signed = np.where(moved > hi, moved - mod, moved)
            trial[r, cols] = np.where((signed >= lo) & (signed <= hi), moved, trial[r, cols])  # stay in the gauge
        trial = polish(trial % mod, h1p, edges, brot, even=coded, quad=coded2)
        e = error(trial, h1p, edges, brot)
        if e < best:
            best, k = e, trial
    out = signed_gauge(k, edges, brot)
    if coded:
        assert np.array_equal(out[:, coded] & 1, k[:, coded] & 1), 'the gauge changed a coded bit'
    if coded2:
        assert np.array_equal(out[:, coded2] & 3, k[:, coded2] & 3), 'the gauge changed a second coded bit'
    return out
