"""Extended full-domain numerical scan of the dyadic piecewise model.

Manual probe only: exact official target/tolerance integer formula, but a
proposed deterministic fixed-point arithmetic model.  No circuit, no qubit
count, no scratch restoration, no official verification.

Same arithmetic as 20261106_direction_research/piecewise_numeric.py, with the
parameter grid widened and per-coefficient magnitudes recorded so that the
cost model can size operands.
"""
import json
import math
import platform
import time
from pathlib import Path

import numpy as np
from numpy.polynomial import Chebyshev, Polynomial

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'artifacts/20261106_piecewise_cost/numeric'
MAX_X = 3133452


def scan(xs, shifts, normalized, groups, target, tolerance, degree, address_bits, width):
    segments_per_group = 1 << address_bits
    residual_bits = 20 + groups - address_bits
    address = (normalized >> residual_bits) - segments_per_group + groups * segments_per_group
    residual = normalized - ((normalized >> residual_bits) << residual_bits)
    u = residual.astype(np.float64) / (1 << residual_bits)
    coeffs = []
    for group in (0, 1):
        for j in range(segments_per_group):
            a = (1 + j / segments_per_group) * 2 ** group
            h = 2 ** group / segments_per_group
            polynomial = Chebyshev.interpolate(lambda v: 1 / np.sqrt(a + h * v), degree, domain=[0, 1]).convert(kind=Polynomial)
            coeffs.append(polynomial.coef)
    coeffs = np.array(coeffs)
    table = np.rint(coeffs * 2 ** width).astype(np.int64)
    acc = table[address, degree]
    for j in reversed(range(degree)):
        acc = table[address, j] + ((acc * residual) >> residual_bits)
    phase = acc.astype(np.uint64) << (54 - width + shifts).astype(np.uint64)
    error = (phase - target).view(np.int64)
    used = np.abs(error).astype(np.uint64)
    failures = int(np.count_nonzero(used > tolerance))
    ratios = used / tolerance
    worst = int(np.argmax(ratios))
    min_margin_units = int((tolerance.astype(np.int64) - used.astype(np.int64)).min())
    # Tailored fixed-point widths: smallest w_j with max|c_j| rounding error
    # 2^-(w_j+1) times max u^j bounded by one unit of the 2^-width coefficient grid.
    mags = np.abs(coeffs).max(axis=0)
    tailored = []
    for j in range(degree + 1):
        need = max(0, width - int(math.floor(math.log2(mags[j]))) - 1) if mags[j] > 0 else 0
        tailored.append(int(need))
    return dict(
        degree=degree, segments=2 * segments_per_group, address_bits=address_bits,
        residual_bits_group0=int(residual_bits.min()), residual_bits_group1=int(residual_bits.max()),
        coefficient_fraction_bits=width, inputs=MAX_X, tolerance_failures=failures,
        worst_error_over_tolerance=float(ratios[worst]), worst_x=worst + 1,
        min_margin_units=min_margin_units, min_margin_turns=min_margin_units / 2 ** 64,
        raw_coefficient_table_bits=(degree + 1) * (width + 2),
        max_abs_coefficients=[float(v) for v in mags],
        tailored_fraction_bits=tailored,
        stored_table_bits=int(sum(tailored) + degree + 1),
        note='Full-domain numerical check only. No circuit, qubit count, gate count, or restoration proof.',
    )


def main():
    start = time.monotonic()
    xs = np.arange(1, MAX_X + 1, dtype=np.int64)
    exponents = np.floor(np.log2(xs)).astype(np.int64)
    shifts = (21 - exponents) // 2
    normalized = xs << (2 * shifts)
    groups = (normalized >= 1 << 21).astype(np.int64)
    roots = [math.isqrt((1 << 130) // int(x)) for x in xs]
    target = np.array([((r + 1) >> 1) & ((1 << 64) - 1) for r in roots], dtype=np.uint64)
    tolerance = np.array([r >> 25 for r in roots], dtype=np.uint64)
    del roots
    rows = []
    configs = []
    for degree in (1, 2, 3, 4):
        for segments in (16, 32, 64, 128, 256, 512):
            if segments < 2 ** (degree - 1):
                continue
            configs.append((degree, int(math.log2(segments // 2))))
    for degree, address_bits in configs:
        for width in (24, 26, 27, 28, 29, 30, 31, 32):
            row = scan(xs, shifts, normalized, groups, target, tolerance, degree, address_bits, width)
            rows.append(row)
            if not row['tolerance_failures']:
                name = f"d{degree}_segments{row['segments']}_w{width}"
                (OUT / f'{name}.json').write_text(json.dumps(dict(parameters=row), indent=2) + '\n')
            print(json.dumps({k: row[k] for k in ('degree', 'segments', 'coefficient_fraction_bits',
                                                  'tolerance_failures', 'worst_error_over_tolerance',
                                                  'min_margin_turns', 'raw_coefficient_table_bits')}), flush=True)
    passing = [r for r in rows if not r['tolerance_failures']]
    # Cheapest passing width per (degree, segments); the cost model consumes this.
    best = {}
    for r in passing:
        key = (r['degree'], r['segments'])
        if key not in best or r['coefficient_fraction_bits'] < best[key]['coefficient_fraction_bits']:
            best[key] = r
    doc = dict(
        scope='Full x domain, exact official target/tolerance integer formula and a proposed deterministic fixed-point arithmetic model; not an official quantum validation',
        generator='Chebyshev.interpolate over [0,1] for each dyadic mantissa interval, rounded coefficients, signed floor Horner',
        python=platform.python_version(), numpy=np.__version__, seconds=time.monotonic() - start,
        configs_tested=len(rows), configs_passing=len(passing),
        cheapest_passing_per_degree_segments=sorted(best.values(), key=lambda r: (r['degree'], r['segments'])),
        rows=rows)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'results.json').write_text(json.dumps(doc, indent=2) + '\n')
    print(json.dumps({'seconds': doc['seconds'], 'configs_tested': len(rows),
                      'configs_passing': len(passing)}, indent=2))


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    main()
