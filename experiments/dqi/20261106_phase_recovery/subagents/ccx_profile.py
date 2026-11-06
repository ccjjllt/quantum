"""Summarise a kernel's CCX list: control degrees and affine forms.

Usage:
    python ccx_profile.py <kernel.kmx>
"""
import sys
from collections import Counter

from kernel_anf import parse, propagate, monomial_vars


def fmt(poly, wires):
    terms = []
    for m in sorted(poly, key=lambda x: (x.bit_count(), x)):
        vs = monomial_vars(m, wires)
        terms.append('*'.join(map(str, vs)) if vs else '1')
    return '+'.join(terms) or '0'


def main():
    path = sys.argv[1]
    info = propagate(parse(path))
    print(f'{path}: gates={info["counts"]}')
    deg_hist = Counter()
    for rec in info['ccx_records']:
        da = max((m.bit_count() for m in rec['a']), default=0)
        db = max((m.bit_count() for m in rec['b']), default=0)
        deg_hist[(da, db)] += 1
        print(f'{rec["line"]:26s} deg=({da},{db}) '
              f'a={fmt(rec["a"], info["wires"])} | b={fmt(rec["b"], info["wires"])}')
    print('control degree histogram:', dict(deg_hist))


if __name__ == '__main__':
    main()
