"""Bilinear rank of GF(2^n) multiplication: machinery, verification, construction census.

Standalone maths side of experiments/dqi/20261112_mulrank.  Ground truth field is
kickmix's GF2Field so that every check is against the *same* field the circuit uses.

Term format follows the DQI source: (mask, out) meaning  z ^= parity(mask,x)*parity(mask,y)*out.
Symmetric in x,y (the Toom/extension construction is symmetric by construction).
"""
import sys
from functools import lru_cache
from itertools import combinations

import numpy as np
import kickmix as km

sys.modules.setdefault('circ', km)


class F:
    """GF(2^n) with log/exp tables plus numpy vector helpers."""

    def __init__(self, n):
        self.n = n
        self.q = 1 << n
        self.f = km.GF2Field(n)
        g = self.f.primitive_element
        self.exp = np.zeros(self.q, dtype=np.uint32)
        self.log = np.zeros(self.q, dtype=np.uint32)
        e = 1
        for i in range(self.q - 1):
            self.exp[i] = e
            self.log[e] = i
            e = self.f.mul(e, g)
        assert e == 1
        self.mul_np = self._mul_table() if n <= 12 else None

    def mul(self, a, b):
        if a == 0 or b == 0:
            return 0
        return int(self.exp[(int(self.log[a]) + int(self.log[b])) % (self.q - 1)])

    def _mul_table(self):
        q = self.q
        li = self.log.astype(np.int64)
        s = li[:, None] + li[None, :]
        out = self.exp[s % (q - 1)].astype(np.uint16)
        z = np.zeros(q, dtype=bool)
        z[0] = True
        out[z, :] = 0
        out[:, z] = 0
        return out

    def rows_mul(self, xs, ys):
        """xs: (A,) ints, ys: (B,) ints -> (A,B) uint8 product table (n<=12 only)."""
        return self.mul_np[np.ix_(xs, ys)]


def bits(x):
    while x:
        t = x & -x
        yield t.bit_length() - 1
        x ^= t


def parity(mask, v):
    return (mask & v).bit_count() & 1


def check_basis_pairs(f, terms, n):
    """Exact proof: both sides bilinear => checking all (i,j) basis pairs suffices."""
    for i in range(n):
        for j in range(i, n):
            got = 0
            for mask, out in terms:
                if parity(mask, 1 << i) & parity(mask, 1 << j):
                    got ^= out
            want = f.mul(1 << i, 1 << j)
            if got != want:
                return False, (i, j, got, want)
    return True, None


def eval_terms_np(terms, n, xs, ys):
    """Return (len(xs), len(ys)) uint16 array of products computed through the decomposition."""
    masks = np.array([m for m, _ in terms], dtype=np.uint32)
    outs = np.array([o for _, o in terms], dtype=np.uint32)
    ux = np.zeros((len(xs), len(terms)), dtype=np.uint8)
    uy = np.zeros((len(ys), len(terms)), dtype=np.uint8)
    for t, m in enumerate(masks):
        for i in bits(int(m)):
            ux[:, t] ^= (xs >> i) & 1
            uy[:, t] ^= (ys >> i) & 1
    res = np.zeros((len(xs), len(ys)), dtype=np.uint32)
    for t in range(len(terms)):
        if outs[t] == 0:
            continue
        res ^= np.outer(ux[:, t], uy[:, t]).astype(np.uint32) * outs[t]
    return res


def mul_pairs(f, xs, ys):
    """Vectorised product of paired elements (any n): array of ints."""
    xs = np.asarray(xs, dtype=np.int64)
    ys = np.asarray(ys, dtype=np.int64)
    s = (f.log[xs] + f.log[ys]) % (f.q - 1)
    out = f.exp[s].astype(np.int64)
    out[(xs == 0) | (ys == 0)] = 0
    return out


def eval_terms_pairs(terms, xs, ys):
    """Paired (not outer-product) evaluation of the decomposition."""
    xs = np.asarray(xs, dtype=np.int64)
    ys = np.asarray(ys, dtype=np.int64)
    res = np.zeros(len(xs), dtype=np.int64)
    for mask, out in terms:
        ux = np.zeros(len(xs), dtype=np.int64)
        uy = np.zeros(len(ys), dtype=np.int64)
        for i in bits(mask):
            ux ^= (xs >> i) & 1
            uy ^= (ys >> i) & 1
        res ^= (ux & uy) * out
    return res


def verify_random(f, terms, n, count=1_000_000, seed=1, extra=None):
    """Random + structured paired checks. Returns (ok, count, first bad)."""
    rng = np.random.default_rng(seed)
    q = 1 << n
    xs = rng.integers(0, q, count)
    ys = rng.integers(0, q, count)
    checked = 0
    for a, b in [(xs, ys)] + (extra or []):
        got = eval_terms_pairs(terms, a, b)
        want = mul_pairs(f, a, b)
        if not np.array_equal(got, want):
            i = int(np.argwhere(got != want)[0][0])
            return False, checked, (int(a[i]), int(b[i]), int(got[i]), int(want[i]))
        checked += len(a)
    return True, checked, None


def verify_exhaustive(f, terms, n, chunk=512):
    """All 2^n x 2^n inputs. Returns (ok, n_checked)."""
    q = 1 << n
    xs = np.arange(q, dtype=np.uint32)
    ys = np.arange(q, dtype=np.uint32)
    truth = f.mul_np  # (q,q) uint8
    for s in range(0, q, chunk):
        sub = xs[s:s + chunk]
        got = eval_terms_np(terms, n, sub, ys)
        want = truth[np.ix_(sub, ys)].astype(np.uint32)
        if not np.array_equal(got, want):
            bad = np.argwhere(got != want)[0]
            return False, (int(sub[bad[0]]), int(bad[1]), int(got[tuple(bad)]), int(want[tuple(bad)]))
    return True, q * q


# ---------------------------------------------------------------- constructions
def extension_tensor_generic(n, k, d, subterms, verbose=False):
    """Toom/extension tensor: GF(2^n) as degree-d extension of GF(2^k), 2d-1 points.

    Mirrors field.py:extension / mul99/kernels.py:extension_tensor but with (k,d)
    chosen by the caller, and it refuses point counts the subfield cannot supply.
    Returns (terms, points_used) or (None, reason).
    """
    if 2 ** k < 2 * d - 1:
        return None, f'{2**k} points in GF(2^{k}) < {2*d-1} needed'
    f = F(n)
    sub = F(k)
    fld = f.f
    subf = sub.f
    gen = fld.pow(fld.primitive_element, (2 ** n - 1) // (2 ** k - 1))

    def ev(v, p):
        out = 0
        for i in reversed(range(k + 1)):
            out = fld.mul(out, p) ^ ((v >> i) & 1)
        return out

    root = next(fld.pow(gen, i) for i in range(1, 2 ** k) if ev(subf.modulus, fld.pow(gen, i)) == 0)
    embed = [fld.pow(root, i) for i in range(k)]
    cols = [fld.mul(v, fld.pow(fld.primitive_element, j)) for j in range(d) for v in embed]
    inv = inverse_columns(cols)
    masks = []
    for point in list(range(2 * d - 2)) + [None]:
        outcols = []
        for extbit in range(n):
            coord = inv[extbit]
            if point is None:
                value = (coord >> (k * (d - 1))) & ((1 << k) - 1)
            else:
                value = 0
                for j in reversed(range(d)):
                    value = subf.mul(value, point) ^ ((coord >> (k * j)) & ((1 << k) - 1))
            outcols.append(value)
        for lm, _ in subterms:
            masks.append(sum(((v & lm).bit_count() % 2) << i for i, v in enumerate(outcols)))
    outs = solve_outputs(fld, masks, n)
    if outs is None:
        return None, 'output solve failed'
    return tuple(zip(masks, outs)), 'ok'


def inverse_columns(columns):
    n = len(columns)
    rows = [sum(((c >> i) & 1) << j for j, c in enumerate(columns)) | (1 << (n + i)) for i in range(n)]
    for j in range(n):
        p = next(i for i in range(j, n) if rows[i] >> j & 1)
        rows[j], rows[p] = rows[p], rows[j]
        for i in range(n):
            if i != j and rows[i] >> j & 1:
                rows[i] ^= rows[j]
    return [sum(((rows[i] >> (n + j)) & 1) << i for i in range(n)) for j in range(n)]


def solve_outputs(fld, masks, n):
    rank = len(masks)
    piv = {}
    for i in range(n):
        for j in range(i, n):
            row = sum((((m >> i) & 1) & ((m >> j) & 1)) << r for r, m in enumerate(masks))
            rhs = fld.mul(1 << i, 1 << j)
            while row:
                p = (row & -row).bit_length() - 1
                if p in piv:
                    row ^= piv[p][0]
                    rhs ^= piv[p][1]
                else:
                    piv[p] = (row, rhs)
                    break
            if row == 0 and rhs != 0:
                return None
    out = [0] * rank
    for p, (row, rhs) in sorted(piv.items(), reverse=True):
        for j in bits(row ^ (1 << p)):
            rhs ^= out[j]
        out[p] = rhs
    return out if all(out) else None
