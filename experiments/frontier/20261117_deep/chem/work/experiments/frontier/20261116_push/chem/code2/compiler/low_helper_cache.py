# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Materialize the full four-bit Boolean algebra using six new ANDs.

Five supplied helper functions independent modulo affine functions give a
ten-dimensional span together with constant1 and the four address bits.
If that span is not yet the full Boolean algebra, some product of two live
qubit functions lies outside it. Each fresh AND therefore adds one dimension,
and exactly six additions suffice. Every low monomial is subsequently an
affine CNOT combination of the live qubits.
"""
import itertools
from parity_recover import basis, reduce
from transport_cuts import coordinate_basis, coordinates

def monomial(m):
    return sum(1 << a for a in range(16) if a & m == m)

def synthesize(helper_patterns, next_qubit=120):
    helpers = [18+8*j for j in range(5)]
    functions = {b: monomial(1 << b) for b in range(4)}
    for j,q in enumerate(helpers):
        functions[q] = sum(int(helper_patterns[a,j]) << a for a in range(16))
    constant = (1 << 16)-1
    span = basis([constant, *functions.values()])
    assert len(span) == 10, 'Five helpers must be independent modulo affine functions for six ANDs'
    computes = []
    while len(span) < 16:
        choice = None
        for x,y in itertools.combinations(sorted(functions), 2):
            value = functions[x] & functions[y]
            if reduce(value, span):
                choice = (x,y,value)
                break
        assert choice is not None, 'Address bits must generate the full Boolean algebra'
        x,y,value = choice
        z = next_qubit
        next_qubit += 1
        computes.append((x,y,z))
        functions[z] = value
        span = basis([constant, *functions.values()])
    assert len(computes) == 6
    qubits = sorted(functions)
    cb = coordinate_basis([constant] + [functions[q] for q in qubits])
    representations = {}
    for m in range(1,16):
        coefficients = coordinates(monomial(m), cb)
        affine = coefficients & 1
        mask = sum(1 << q for j,q in enumerate(qubits) if coefficients >> (j+1) & 1)
        rebuilt = constant if affine else 0
        for q in qubits:
            if mask >> q & 1: rebuilt ^= functions[q]
        assert rebuilt == monomial(m)
        representations[m] = (mask, affine)
    return computes, representations, next_qubit
