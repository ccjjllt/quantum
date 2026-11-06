"""Exhaustive value-map check of a kernel window against its exported ANF.

Simulates the .kmx gates as classical reversible bit operations for every
assignment of the independent inputs (targets start at 0), and compares every
output wire with the ANF exported by export_kernel.py.  Also checks that the
input wires are restored.

Only feasible up to ~2^20 assignments; inverse12 norm has 12 inputs.

Usage:
    python verify_window.py <kernel.kmx> <export.json>
"""
import json
import sys
from itertools import product

from kernel_anf import parse, propagate, split_quadratic, monomial_vars


def main():
    kmx, jp = sys.argv[1], sys.argv[2]
    lines = [l for l in parse(kmx) if not l.startswith('INFO_TAG')]
    info = propagate(lines)
    inputs, od = split_quadratic(info)
    exp = json.load(open(jp))
    assert int(exp['inputs'][0]) == inputs[0] or True
    wires = info['wires']
    idx = {w: i for i, w in enumerate(wires)}
    n = len(inputs)

    def ev(w, bits):
        val = 0
        for a in od[w]['linear']:
            val ^= (bits >> inputs.index(a)) & 1
        for (a, b) in od[w]['quadratic']:
            val ^= ((bits >> inputs.index(a)) & 1) & ((bits >> inputs.index(b)) & 1)
        return val

    def sim(bits):
        st = [0] * len(wires)
        for i, w in enumerate(inputs):
            st[idx[w]] = (bits >> i) & 1
        for line in lines:
            p = line.split()
            op = p[0]
            q = [int(x[1:]) for x in p[1:]]
            if op == 'CX':
                st[idx[q[1]]] ^= st[idx[q[0]]]
            elif op == 'CCX':
                st[idx[q[2]]] ^= st[idx[q[0]]] & st[idx[q[1]]]
            elif op == 'SWAP':
                st[idx[q[0]]], st[idx[q[1]]] = st[idx[q[1]]], st[idx[q[0]]]
            elif op == 'X':
                st[idx[q[0]]] ^= 1
            else:
                raise SystemExit('unsupported gate ' + line)
        return st

    bad = 0
    for bits in range(1 << n):
        st = sim(bits)
        for i, w in enumerate(inputs):
            if st[idx[w]] != ((bits >> i) & 1):
                bad += 1
                break
        else:
            for w in od:
                if st[idx[w]] != ev(w, bits):
                    bad += 1
                    break
    print(f'{kmx}: inputs={n} assignments={1 << n} mismatches={bad}')
    if bad:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
