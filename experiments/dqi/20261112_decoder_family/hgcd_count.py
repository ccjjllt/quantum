"""Classical field-multiplication counts for EEA variants over GF(2^12).

One counted field multiplication is exactly one `field.mul_xor0` call in the
public circuit = 42 static Toffoli-like gates (measured, see
20261112_mulrank).  Inversions are counted separately because the circuit
uses a dedicated 65T inverse gadget, not a 42T multiplier.

The point of the experiment: the current convert already runs an extended
Euclid on degree-17 polynomials (the short-H Hankel split) with ~1,247
multiplications measured.  A half-gcd can only beat that if its combinatorial
matrix products use fewer field multiplications *at n=17*; asymptotics are
irrelevant at this size.

Usage: .venv/bin/python hgcd_count.py [--trials 8]
"""
import argparse
import json
import random
from pathlib import Path

MOD = 0x1053  # kickmix.GF2Field(12).modulus


# ---------- GF(2^12) ----------
def gmul(a, b, counts):
    counts['mul'] += 1
    out = 0
    while b:
        if b & 1:
            out ^= a
        b >>= 1
        a <<= 1
        if a & 0x1000:
            a ^= MOD
    return out


INV_TABLE = None


def _build_inv_table():
    global INV_TABLE
    if INV_TABLE is not None:
        return INV_TABLE
    c = {'mul': 0, 'inv': 0}
    table = [0] * 4096
    for a in range(1, 4096):
        out, base, e = 1, a, (1 << 12) - 2
        while e:
            if e & 1:
                out = gmul(out, base, c)
            base = gmul(base, base, c)
            e >>= 1
        table[a] = out
    INV_TABLE = table
    return table


def ginv(a, counts):
    counts['inv'] += 1
    return 0 if a == 0 else _build_inv_table()[a]


# ---------- polynomials (low -> high) ----------
def trim(p):
    p = list(p)
    while len(p) > 1 and p[-1] == 0:
        p.pop()
    return p


def deg(p):
    return len(trim(p)) - 1


def psub(a, b):
    n = max(len(a), len(b))
    return trim([(a[i] if i < len(a) else 0) ^ (b[i] if i < len(b) else 0) for i in range(n)])


def pmul_school(a, b, counts):
    if len(a) == 1 or len(b) == 1:
        # scalar multiply: still one field multiplication per coefficient
        c = a[0] if len(a) == 1 else b[0]
        other = b if len(a) == 1 else a
        return trim([gmul(c, x, counts) for x in other])
    out = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        if x:
            for j, y in enumerate(b):
                if y:
                    out[i + j] ^= gmul(x, y, counts)
    return trim(out)


def pmul_karatsuba(a, b, counts, threshold=8):
    a, b = trim(a), trim(b)
    if len(a) < threshold or len(b) < threshold:
        return pmul_school(a, b, counts)
    n = max(len(a), len(b))
    h = (n + 1) // 2
    a0, a1 = a[:h], a[h:]
    b0, b1 = b[:h], b[h:]
    z0 = pmul_karatsuba(a0, b0, counts, threshold)
    z2 = pmul_karatsuba(a1, b1, counts, threshold)
    z1 = pmul_karatsuba(psub(a0, a1), psub(b0, b1), counts, threshold)
    z1 = psub(psub(z0, z1), z2)  # (a0+a1)(b0+b1) - z0 - z2  (GF(2): +)
    out = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(z0):
        out[i] ^= x
    for i, x in enumerate(z1):
        out[i + h] ^= x
    for i, x in enumerate(z2):
        out[i + 2 * h] ^= x
    return trim(out)


def pdivmod(a, b, counts):
    a = trim(a)
    b = trim(b)
    if deg(a) < deg(b):
        return [0], a
    q = [0] * (len(a) - len(b) + 1)
    inv = ginv(b[-1], counts)
    r = list(a)
    for k in range(len(a) - len(b), -1, -1):
        t = gmul(r[k + len(b) - 1], inv, counts)
        q[k] = t
        if t:
            for j, v in enumerate(b):
                if v:
                    r[k + j] ^= gmul(t, v, counts)
    return trim(q), trim(r)


# ---------- algorithms ----------
def eea_plain(a, b, counts):
    """Bare Euclid: quotient + remainder only (no Bezout cofactors)."""
    steps = 0
    while deg(b) > 0 or b != [0]:
        q, r = pdivmod(a, b, counts)
        steps += 1
        a, b = b, r
        if b == [0]:
            break
    return steps


def eea_extended(a, b, counts):
    """Standard extended Euclid, two Bezout cofactors (classical model)."""
    r0, r1 = trim(a), trim(b)
    s0, s1 = [1], [0]
    t0, t1 = [0], [1]
    steps = 0
    while r1 != [0]:
        q, r2 = pdivmod(r0, r1, counts)
        s2 = psub(s0, pmul_school(q, s1, counts))
        t2 = psub(t0, pmul_school(q, t1, counts))
        r0, r1 = r1, r2
        s0, s1 = s1, s2
        t0, t1 = t1, t2
        steps += 1
    return steps


def mat_id():
    return ([[1], [0]], [[0], [1]])


def mat_vec(M, v, counts, mul):
    (a, b), (c, d) = M
    x, y = v
    return (psub(mul(a, x, counts), mul(b, y, counts)),
            psub(mul(c, x, counts), mul(d, y, counts)))


def mat_mat(A, B, counts, mul):
    (a, b), (c, d) = A
    (e, f), (g, h) = B
    return ([[psub(mul(a, e, counts), mul(b, g, counts)),
              psub(mul(a, f, counts), mul(b, h, counts))],
             [psub(mul(c, e, counts), mul(d, g, counts)),
              psub(mul(c, f, counts), mul(d, h, counts))]])


def hgcd(a, b, n, counts, mul):
    """Half-gcd: reduce (a,b) to deg < n/2; returns the 2x2 transition matrix."""
    if n <= 2 or deg(b) < n // 2:
        return mat_id()
    m = n // 2
    R = hgcd(a, b, m, counts, mul)
    c, d = mat_vec(R, (a, b), counts, mul)
    if deg(d) < m // 2:
        return R
    q, e = pdivmod(c, d, counts)
    # S = [[0,1],[1,-q]] * R  -> only 2 polynomial products by q
    (r00, r01), (r10, r11) = R
    S = ([[r10, r11],
          [psub(r00, pmul_school(q, r10, counts)), psub(r01, pmul_school(q, r11, counts))]])
    T = hgcd(d, e, m, counts, mul)
    return mat_mat(T, S, counts, mul)


def hgcd_count(a, b, counts, mul):
    n = max(deg(a), deg(b))
    return hgcd(a, b, n, counts, mul)


def random_poly(d, rng):
    return trim([rng.randrange(1 << 12) for _ in range(d)] + [rng.randrange(1, 1 << 12)])


def run(trials=8):
    rng = random.Random(20261112)
    rows = []
    for n in (8, 12, 16, 17, 24, 32, 34, 48, 64, 96, 128, 192, 256, 384, 512):
        acc = {}
        for trial in range(trials):
            a = random_poly(n, rng)
            b = random_poly(n - 1, rng)
            for tag, fn, mul in (
                    ('euclid', eea_plain, pmul_school),
                    ('ext_school', eea_extended, pmul_school),
                    ('hgcd_school', hgcd_count, pmul_school),
                    ('hgcd_karat', hgcd_count, pmul_karatsuba),
            ):
                c = {'mul': 0, 'inv': 0}
                fn(a, b, c, mul) if tag.startswith('hgcd') else fn(a, b, c)
                d = acc.setdefault(tag, {'mul': 0, 'inv': 0, 'trials': 0})
                d['mul'] += c['mul']
                d['inv'] += c['inv']
                d['trials'] += 1
        row = {'n': n}
        for tag, d in acc.items():
            row[tag + '_mul'] = round(d['mul'] / d['trials'], 1)
            row[tag + '_inv'] = round(d['inv'] / d['trials'], 1)
        rows.append(row)
        print(f"n={n:4d}  euclid={row['euclid_mul']:9.1f}  "
              f"ext={row['ext_school_mul']:9.1f}  hgcd_school={row['hgcd_school_mul']:9.1f}  "
              f"hgcd_karat={row['hgcd_karat_mul']:9.1f}  "
              f"(inv ext={row['ext_school_inv']:.1f})")
    return rows


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--trials', type=int, default=8)
    ap.add_argument('--out', default=str(Path(__file__).resolve().parents[3] /
                                         'artifacts/20261112_decoder_family/hgcd_count.json'))
    a = ap.parse_args()
    rows = run(a.trials)
    Path(a.out).write_text(json.dumps(rows, indent=1))
