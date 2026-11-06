"""Rank-1 span analysis for a bipartite quadratic kernel.

The kernel computes out_j ^= f_j(x,y), f_j homogeneous quadratic and bipartite
between input groups X and Y.  Write f_j as a |X| x |Y| GF(2) matrix M_j.
A CCX whose two controls are linear forms u.x and v.y contributes the rank-1
matrix u v^T, and CNOT fan-out adds that one matrix to any subset of outputs.

Lower bound: #CCX >= rank(M_j as vectors in GF(2)^{|X|*|Y|}).
This script also searches for a basis of the output span made only of rank-1
matrices, which would realise the bound.

Usage:
    python rank1_span.py <export.json> [--max-enumerate 20]
"""
import json
import sys
from itertools import product


def build(exp):
    inputs = exp['inputs']
    outs = exp['outputs']
    xs = sorted({a for o in outs.values() for p in o['quadratic'] for a in p if a in inputs})
    # caller supplies groups through the natural order: first half / second half
    # determined from the quadratic terms themselves (must be bipartite)
    adj = {}
    for o in outs.values():
        for a, b in o['quadratic']:
            adj.setdefault(a, set()).add(b)
            adj.setdefault(b, set()).add(a)
    color = {}
    for v in sorted(adj):
        if v in color:
            continue
        color[v] = 0
        stack = [v]
        while stack:
            a = stack.pop()
            for b in adj[a]:
                if b not in color:
                    color[b] = 1 - color[a]
                    stack.append(b)
                elif color[b] == color[a]:
                    raise SystemExit('not bipartite')
    X = sorted([v for v in adj if color[v] == 0])
    Y = sorted([v for v in adj if color[v] == 1])
    xi = {v: i for i, v in enumerate(X)}
    yi = {v: i for i, v in enumerate(Y)}
    vecs = {}
    for w, o in outs.items():
        v = 0
        for a, b in o['quadratic']:
            if a in yi:
                a, b = b, a
            v ^= 1 << (xi[a] * len(Y) + yi[b])
        vecs[int(w)] = v
    return X, Y, vecs


def rank_basis(rows, nbits):
    basis = []  # (pivot position, vector)
    for r in rows:
        x = r
        for p, b in basis:
            if x >> p & 1:
                x ^= b
        if x:
            p = x.bit_length() - 1
            basis.append((p, x))
            basis.sort(reverse=True)
    return basis


def membership(x, basis):
    for p, b in basis:
        if x >> p & 1:
            x ^= b
    return x == 0


def main():
    exp = json.load(open(sys.argv[1]))
    max_enum = 20
    if '--max-enumerate' in sys.argv:
        max_enum = int(sys.argv[sys.argv.index('--max-enumerate') + 1])
    X, Y, vecs = build(exp)
    n = len(X) * len(Y)
    basis = rank_basis(list(vecs.values()), n)
    r = len(basis)
    print(f'X ({len(X)}): {X}')
    print(f'Y ({len(Y)}): {Y}')
    print(f'output matrices: {len(vecs)}, span rank r = {r}, ambient dim {n}')
    if max(len(X), len(Y)) <= max_enum:
        found = {}
        for u in range(1, 1 << len(X)):
            for v in range(1, 1 << len(Y)):
                m = 0
                for i in range(len(X)):
                    if u >> i & 1:
                        for j in range(len(Y)):
                            if v >> j & 1:
                                m |= 1 << (i * len(Y) + j)
                if membership(m, basis):
                    found[(u, v)] = m
        print(f'rank-1 matrices inside W: {len(found)}')
        # greedy basis from rank-1 elements
        picked = []
        b2 = []
        for (u, v), m in sorted(found.items(), key=lambda kv: (kv[0][0].bit_count() + kv[0][1].bit_count(), kv[0])):
            x = m
            for p, b in b2:
                if x >> p & 1:
                    x ^= b
            if x:
                b2.append((x.bit_length() - 1, x))
                b2.sort(reverse=True)
                picked.append((u, v))
        print(f'rank-1 basis found: {len(picked)} of r={r}')
        for u, v in picked:
            fu = '+'.join(str(X[i]) for i in range(len(X)) if u >> i & 1)
            fv = '+'.join(str(Y[j]) for j in range(len(Y)) if v >> j & 1)
            print(f'  ({fu})*({fv})')
    else:
        print('too large to enumerate all rank-1 matrices')


if __name__ == '__main__':
    main()
