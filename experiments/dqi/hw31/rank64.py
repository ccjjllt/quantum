"""Fifteen-term symmetric multiplication on the inverse tower's GF(64) layer."""

from functools import cache, reduce
from operator import xor

from . import tower_inverse as tower
from .euclid import ev, indices, mul, power


@cache
def rank6():
    bases, tables, coordinates, _ = tower.fields()
    small = tables[6]
    z = next(u for u in small if mul(u, u) ^ u ^ 1 == 0)
    subfield = [0, 1, z, 1 ^ z]
    symbols = {u: i for i, u in enumerate(subfield)}
    y = next(u for u in small if u not in subfield)
    cubic = [mul(c, power(y, j)) for j in range(3) for c in (1, z)]
    cubic_coords = {u: i for i, u in enumerate(tower.table(cubic))}
    assert len(cubic_coords) == 64
    input_coords = [cubic_coords[v] for v in bases[6]]

    forms = []
    for point in [*subfield, None]:
        evaluations = []
        for value in input_coords:
            polynomial = [subfield[(value >> (2 * j)) & 3] for j in range(3)]
            output = polynomial[-1] if point is None else ev(polynomial, point)
            evaluations.append(symbols[output])
        for linear in (1, 2, 3):
            mask = sum(((a & linear).bit_count() & 1) << j for j, a in enumerate(evaluations))
            forms.append(mask)

    # The symmetric bilinear combination of the 15 products is recovered
    # in the existing tower basis from the products of the six basis vectors.
    pivots = {}
    for i in range(6):
        for j in range(i, 6):
            row = sum(((mask >> i) & (mask >> j) & 1) << k for k, mask in enumerate(forms))
            result = coordinates[6][mul(bases[6][i], bases[6][j])]
            while row:
                k = next(indices(row))
                if k not in pivots:
                    pivots[k] = row, result
                    break
                equation, rhs = pivots[k]
                row ^= equation
                result ^= rhs
            assert row or result == 0
    outputs = [0] * len(forms)
    for k, (row, result) in sorted(pivots.items(), reverse=True):
        outputs[k] = reduce(xor, (outputs[j] for j in indices(row ^ (1 << k))), result)
    terms = tuple(zip(forms, outputs))
    assert len(terms) == 15 and all(outputs)

    for i, a in enumerate(small):
        for j, b in enumerate(small):
            result = reduce(xor, (value for mask, value in terms
                                  if ((i & mask).bit_count() & 1) and ((j & mask).bit_count() & 1)), 0)
            assert result == coordinates[6][mul(a, b)]
    return terms


def install():
    original = tower.rank_terms
    terms = rank6()

    def rank_terms(bits):
        return terms if bits == 6 else original(bits)

    tower.rank_terms = rank_terms
    return {"rank6_terms": len(terms), "field_products_checked": 4096}
