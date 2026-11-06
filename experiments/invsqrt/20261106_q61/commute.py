"""Exact pairwise commutation for the KMB gate set (basis-state permutation + phase).

Two gates commute iff for every basis state of their combined support the composed action
(final bits and accumulated phase) is the same in both orders.  Supports are <=3 qubits
each, so at most 64 states -- exhaustive and exact, no sampling.

Barriers: HMR and R are treated as non-commuting with everything (their random outcome /
reset order is not reordered here).  Z_POW is diagonal: it commutes with all diagonal gates
and is otherwise only moved past disjoint supports.
"""
from __future__ import annotations

import cmath
import itertools

DIAGONAL = {"Z", "CZ", "CCZ", "NEG", "Z_POW"}
SINGLE = {"X", "Z", "NEG", "Z_POW"}
TWO = {"CX", "CZ", "SWAP"}
THREE = {"CCX", "CCZ", "CSWAP"}


def _apply(kind, qs, p, bits, phase):
    """Apply one gate to a dict qubit->bit; return new phase (complex)."""
    if kind == "X":
        bits[qs[0]] ^= 1
    elif kind == "Z":
        if bits[qs[0]]:
            phase = -phase
    elif kind == "NEG":
        phase = -phase
    elif kind == "Z_POW":
        # exponent in turns; phase = exp(2*pi*i*theta*bit)
        theta = float(p[1])
        if bits[qs[0]]:
            phase = phase * cmath.exp(2j * cmath.pi * theta)
    elif kind == "CX":
        bits[qs[1]] ^= bits[qs[0]]
    elif kind == "CZ":
        if bits[qs[0]] and bits[qs[1]]:
            phase = -phase
    elif kind == "SWAP":
        bits[qs[0]], bits[qs[1]] = bits[qs[1]], bits[qs[0]]
    elif kind == "CCX":
        if bits[qs[0]] and bits[qs[1]]:
            bits[qs[2]] ^= 1
    elif kind == "CCZ":
        if bits[qs[0]] and bits[qs[1]] and bits[qs[2]]:
            phase = -phase
    elif kind == "CSWAP":
        if bits[qs[0]]:
            bits[qs[1]], bits[qs[2]] = bits[qs[2]], bits[qs[1]]
    else:
        raise ValueError(kind)
    return phase


def commutes(g1, g2, tol=1e-9):
    k1, q1, p1 = g1
    k2, q2, p2 = g2
    if k1 in {"HMR", "R"} or k2 in {"HMR", "R"}:
        return False
    if k1 in DIAGONAL and k2 in DIAGONAL:
        return True
    support = sorted(set(q1) | set(q2))
    if not (set(q1) & set(q2)):
        return True
    if k1 == "Z_POW" or k2 == "Z_POW":
        return False  # diagonal vs non-diagonal sharing a qubit: assume no
    if len(support) > 6:
        return False
    for values in itertools.product((0, 1), repeat=len(support)):
        base = dict(zip(support, values))
        b1 = dict(base)
        ph1 = 1 + 0j
        ph1 = _apply(k1, q1, p1, b1, ph1)
        ph1 = _apply(k2, q2, p2, b1, ph1)
        b2 = dict(base)
        ph2 = 1 + 0j
        ph2 = _apply(k2, q2, p2, b2, ph2)
        ph2 = _apply(k1, q1, p1, b2, ph2)
        if b1 != b2 or abs(ph1 - ph2) > tol:
            return False
    return True


def gate(gates, i):
    return (gates[i][0], gates[i][1], gates[i][2])
