"""Manual full-domain numerical probe of an alternative phase representation.

Dyadic mantissa intervals, interpolating polynomials, rounded coefficients,
integer floor-truncated Horner. This is not a quantum circuit or an official
verification. No measured branches, reversibility or hardware cost are checked.
"""
import json
import math
import platform
import time
from pathlib import Path

import numpy as np
from numpy.polynomial import Chebyshev, Polynomial

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'artifacts/20261106_direction_research/numeric'
MAX_X = 3133452


def main():
    start = time.monotonic()
    xs = np.arange(1, MAX_X+1, dtype=np.int64)
    exponents = np.floor(np.log2(xs)).astype(np.int64)
    shifts = (21-exponents)//2
    normalized = xs << (2*shifts)
    groups = (normalized >= 1 << 21).astype(np.int64)
    roots = [math.isqrt((1 << 130)//int(x)) for x in xs]
    target = np.array([((r+1)>>1) & ((1<<64)-1) for r in roots],dtype=np.uint64)
    tolerance = np.array([r>>25 for r in roots],dtype=np.uint64)
    del roots
    rows = []
    for degree, address_bits in ((2,5),(2,6),(2,7),(3,3),(3,4),(3,5),(4,2),(4,3)):
        segments_per_group = 1 << address_bits
        residual_bits = 20+groups-address_bits
        address = (normalized >> residual_bits)-segments_per_group + groups*segments_per_group
        residual = normalized - ((normalized >> residual_bits) << residual_bits)
        coeffs = []
        for group in (0,1):
            for j in range(segments_per_group):
                a = (1+j/segments_per_group)*2**group
                h = 2**group/segments_per_group
                polynomial = Chebyshev.interpolate(lambda u: 1/np.sqrt(a+h*u), degree, domain=[0,1]).convert(kind=Polynomial)
                coeffs.append(polynomial.coef)
        coeffs = np.array(coeffs)
        for width in (26,28,30):
            table = np.rint(coeffs*2**width).astype(np.int64)
            acc = table[address,degree]
            for j in reversed(range(degree)):
                acc = table[address,j] + ((acc*residual) >> residual_bits)
            phase = acc.astype(np.uint64) << (54-width+shifts).astype(np.uint64)
            error = (phase-target).view(np.int64)
            used = np.abs(error).astype(np.uint64)
            failures = int(np.count_nonzero(used > tolerance))
            ratios = used/tolerance
            worst = int(np.argmax(ratios))
            min_margin_units = int((tolerance.astype(np.int64)-used.astype(np.int64)).min())
            row = dict(degree=degree,segments=2*segments_per_group,coefficient_fraction_bits=width,
                       residual_bits_max=int(residual_bits.max()),inputs=MAX_X,
                       tolerance_failures=failures,worst_error_over_tolerance=float(ratios[worst]),
                       worst_x=worst+1,min_margin_units=min_margin_units,
                       raw_coefficient_table_bits=(degree+1)*(width+2),
                       note='Full-domain numerical check only. No circuit, qubit count, gate count, or restoration proof.')
            rows.append(row)
            if not failures:
                name=f'd{degree}_segments{2*segments_per_group}_w{width}'
                (OUT/f'{name}.json').write_text(json.dumps(dict(parameters=row,integer_coefficients=table.tolist()),indent=2)+'\n')
            print(json.dumps(row),flush=True)
    result=dict(scope='Full x domain, exact official target/tolerance integer formula and a proposed deterministic fixed-point arithmetic model; not an official quantum validation',
                generator='Chebyshev.interpolate over [0,1] for each dyadic mantissa interval, rounded coefficients, signed floor Horner',
                python=platform.python_version(),numpy=np.__version__,seconds=time.monotonic()-start,rows=rows)
    (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__ == '__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    main()
