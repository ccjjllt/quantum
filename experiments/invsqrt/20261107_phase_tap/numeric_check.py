"""Full-domain check of the *direct phase-tap* model (variants A and B).

Manual probe only.  The model is the 20261106 dyadic piecewise polynomial,
evaluated exactly the way the proposed circuit evaluates it:

    c_j(v) = sum_b  bit_b(c_j) * 2^-b
    v      = sum_i  v_i * 2^-i
    phase  = 2^-s * sum_j sign_j * sum_{b, monomial}  bit_b * mult * 2^-(b+k)

where (monomial, mult, k) enumerates v^j (k = sum of the v-bit indices).
The circuit builds one Z_POW per kept (aligned coefficient bit, monomial) tap;
a tap is kept only if its absolute phase weight mult*2^-(b+k+s) >= 2^-K_abs.
This is *not* a bit truncation of the product: carries inside c_j*v^j do not
exist in the phase (the Z_POW angles add without carries), so every dropped
monomial adds its full weight to the truncation error.

Target/tolerance are the official integer formulas, identical to
data/competition/verifiers/invsqrt/verify_submission_invsqrt.py and to
20261106_piecewise_cost/numeric_scan.py.  This is a classical fixed-point
model: no circuit is built, no scratch restoration, no measurement branch is
checked.
"""
import json
import math
import platform
import time
from fractions import Fraction
from pathlib import Path

import numpy as np
from numpy.polynomial import Chebyshev, Polynomial

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'artifacts/20261107_phase_tap'
MAX_X = 3133452
MASK64 = (1 << 64) - 1
CUTOFFS = {'A': (41, 42, 43, 44, 70), 'B': (41, 42, 43, 44, 70)}


def build_table(segments, degree, width):
    """Two-group dyadic Chebyshev table, coefficients rounded to 2^-width."""
    per_group = segments // 2
    coeffs = []
    for group in (0, 1):
        for j in range(per_group):
            a = (1 + j / per_group) * 2 ** group
            h = 2 ** group / per_group
            poly = Chebyshev.interpolate(
                lambda v: 1 / np.sqrt(a + h * v), degree, domain=[0, 1]
            ).convert(kind=Polynomial)
            coeffs.append(poly.coef)
    coeffs = np.array(coeffs)
    ints = np.rint(coeffs * 2 ** width).astype(np.int64)
    return ints, coeffs


def monomials(degree, rbits):
    """Monomials of v^degree: (index tuple, multiplicity, sum of indices)."""
    out = []
    if degree == 0:
        return [((), 1, 0)]

    def rec(start, depth, chosen):
        if depth == degree:
            counts = {}
            for i in chosen:
                counts[i] = counts.get(i, 0) + 1
            mult = math.factorial(degree)
            for c in counts.values():
                mult //= math.factorial(c)
            out.append((tuple(chosen), mult, sum(chosen)))
            return
        for i in range(start, rbits + 1):
            rec(i, depth + 1, chosen + [i])

    rec(1, 0, [])
    return out


def zpow_class(weight):
    """Official z_pow_class on a phase weight in turns (half_turns = 2*weight)."""
    half = Fraction(weight) * 2
    if half % Fraction(1, 2) == 0:
        return 'clifford'
    if half % Fraction(1, 4) == 0:
        return 't'
    return 'rotation'


def main():
    start = time.monotonic()
    xs = np.arange(1, MAX_X + 1, dtype=np.int64)
    exponents = np.floor(np.log2(xs)).astype(np.int64)
    s = exponents // 2                       # integer phase scale, 0..10
    g = exponents & 1                        # group / sqrt(2) parity
    m = 21 - exponents                       # shift so N in [2^21, 2^22)
    N = xs << m
    f = N - (1 << 21)                        # 21 mantissa bits below hidden one

    roots = [math.isqrt((1 << 130) // int(x)) for x in xs]
    target = np.array([((r + 1) >> 1) & MASK64 for r in roots], dtype=np.uint64)
    tolerance = np.array([r >> 25 for r in roots], dtype=np.uint64)
    del roots

    variants = {}
    for name, segments, degree in (('A', 128, 2), ('B', 32, 3)):
        address_bits = int(math.log2(segments))
        rbits = 22 - address_bits             # 21 fraction bits minus in-group address
        address = (g << (address_bits - 1)) | (f >> rbits)
        V = f & ((1 << rbits) - 1)            # residual, all bits real
        ints, coeffs = build_table(segments, degree, 28)
        mags = np.abs(coeffs).max(axis=0)
        signs = []
        for j in range(degree + 1):
            col = coeffs[:, j]
            signs.append(dict(min=float(col.min()), max=float(col.max()),
                              uniform_sign=bool(np.all(col > 0) or np.all(col < 0))))
        stored = []
        for j in range(degree + 1):
            lo = int(-math.floor(math.log2(mags[j])))
            stored.append((max(1, lo), 28))
        cint = [np.abs(ints[address, j]).astype(np.int64) for j in range(degree + 1)]
        sign = [1 if signs[j]['min'] > 0 else -1 for j in range(degree + 1)]
        mons = {j: monomials(j, rbits) for j in range(degree + 1)}
        # boolean "monomial fires" per index tuple is recomputed per cutoff (memory)

        def evaluate(cutoff):
            """Circuit phase in 2^-64 units (mod 1) for absolute tap cutoff 2^-cutoff."""
            acc = np.zeros(MAX_X, dtype=np.float64)
            for j in range(degree + 1):
                for (idx, mult, k) in mons[j]:
                    # tap weight mult*2^-(b+k+s) >= 2^-cutoff  <=>  b <= m_eff
                    m_eff = cutoff - s - k + int(math.floor(math.log2(mult)))
                    if m_eff.max() < stored[j][0]:
                        continue
                    drop = np.clip(28 - m_eff, 0, 28)
                    R = (cint[j] >> drop) << drop
                    fire = np.ones(MAX_X, dtype=bool)
                    for i in idx:
                        fire &= ((V >> (rbits - i)) & 1).astype(bool)
                    acc += (sign[j] * mult * 2.0 ** (-k - 28)) * (R * fire)
            U = acc * np.exp2(64.0 - s)
            U = np.mod(np.round(U), 2.0 ** 64).astype(np.uint64)
            return U

        rows = {}
        for cutoff in CUTOFFS[name]:
            U = evaluate(cutoff)
            error = (U - target).view(np.int64)
            used = np.abs(error).astype(np.uint64)
            failures = int(np.count_nonzero(used > tolerance))
            ratios = used.astype(np.float64) / tolerance.astype(np.float64)
            worst = int(np.argmax(ratios))
            margin_units = int((tolerance.astype(np.int64) - used.astype(np.int64)).min())
            rows[str(cutoff)] = dict(
                cutoff=cutoff, tolerance_failures=failures,
                worst_error_over_tolerance=float(ratios[worst]), worst_x=worst + 1,
                min_margin_units=margin_units,
                min_margin_turns=margin_units / 2 ** 64,
            )
            print(name, cutoff, rows[str(cutoff)], flush=True)

        # Tap census: one Z_POW per (reachable aligned coefficient-bit position,
        # monomial), weight mult*2^-(p+k) >= 2^-cutoff.
        census = {}
        for cutoff in CUTOFFS[name]:
            by_degree, by_exponent = {}, {}
            classes = {'clifford': 0, 't': 0, 'rotation': 0}
            for j in range(degree + 1):
                lo, hi = stored[j]
                for (idx, mult, k) in mons[j]:
                    for p in range(lo, min(hi + 10, 38) + 1):
                        if mult * (1 << cutoff) >= (1 << (p + k)):
                            by_degree[j] = by_degree.get(j, 0) + 1
                            e = p + k
                            by_exponent[e] = by_exponent.get(e, 0) + 1
                            classes[zpow_class(Fraction(mult, 2 ** (p + k)))] += 1
            census[str(cutoff)] = dict(
                taps=sum(by_degree.values()), by_degree=by_degree,
                by_exponent=by_exponent, **classes)
            print(name, 'census', cutoff, {k: census[str(cutoff)][k]
                                           for k in ('taps', 'by_degree', 'clifford', 't', 'rotation')},
                  flush=True)

        variants[name] = dict(
            segments=segments, degree=degree,
            tables=dict(max_abs_coefficients=[float(x) for x in mags],
                        coefficient_signs=signs, stored_bit_ranges=stored,
                        stored_bits=int(sum(hi - lo + 1 for lo, hi in stored)),
                        qrom_entries=segments, residual_bits=rbits),
            numeric=rows, tap_census=census)

    doc = dict(
        scope=('Full 3,133,452-x classical fixed-point check of the direct phase-tap model; '
               'official integer target/tolerance; monomial-level tap truncation exactly as '
               'the circuit applies it; no circuit, no Q, no official validation'),
        python=platform.python_version(), numpy=np.__version__,
        seconds=time.monotonic() - start,
        normalization=dict(N='x << (21-e)', e='floor(log2 x)', hidden_bit=21,
                           address='(e&1)<<6 | (f>>15)', residual='f & 0x7fff',
                           residual_fraction_bits=15, phase_scale='2^-(e//2)',
                           note='identical address/residual to the 20261106 piecewise scan'),
        model=('phase = 2^-s * sum_j sign_j * sum_{b,monomial} bit_b * mult * 2^-(b+k); '
               'taps with mult*2^-(b+k+s) < 2^-K_abs are absent; float64 evaluation, '
               'resolution ~2^-52 turn'),
        variants=variants,
    )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'numeric_check.json').write_text(json.dumps(doc, indent=2, default=str) + '\n')
    print(json.dumps({'seconds': doc['seconds']}, indent=2))


if __name__ == '__main__':
    main()
