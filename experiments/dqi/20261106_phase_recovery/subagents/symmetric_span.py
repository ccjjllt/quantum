"""Exact minimum number of symmetric rank-1 products for a bipartite kernel.

For a kernel out_j ^= sum_{i,l} M_j[i,l] x_i y_l with all M_j symmetric, a CCX
with the *same* linear form u on both halves contributes u u^T.  This script
computes the minimum k such that the output span W is contained in the span of
k of the 63 matrices u u^T (u != 0), and returns a witness basis.

Method: quotient Sym_6/W (dim 21-10=11).  For d=1,2,3,... enumerate the span S
of d pool classes (only classes actually present can matter) and test whether
the pool vectors whose class lies in S fill the whole preimage of S.

Usage:
    python symmetric_span.py <export.json>
"""
import json
import sys
from itertools import combinations


def pairs(n):
    return [(i, j) for i in range(n) for j in range(i, n)]


IDX = {p: k for k, p in enumerate(pairs(6))}


def sym_vec(M, n=6):
    v = 0
    for i in range(n):
        for j in range(i, n):
            if M[i][j]:
                v |= 1 << IDX[(i, j)]
    return v


def rank_basis(vecs, nbits):
    basis = []
    for r in vecs:
        x = r
        for p, b in basis:
            if x >> p & 1:
                x ^= b
        if x:
            basis.append((x.bit_length() - 1, x))
            basis.sort(reverse=True)
    return basis


def rank(vecs):
    return len(rank_basis(vecs, 0))


def reduce_(x, basis):
    for p, b in basis:
        if x >> p & 1:
            x ^= b
    return x


def main():
    exp = json.load(open(sys.argv[1]))
    inputs = exp['inputs']
    outs = exp['outputs']
    # bipartition
    adj = {}
    for o in outs.values():
        for a, b in o['quadratic']:
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)
    color = {}
    for v in sorted(adj):
        if v in color:
            continue
        color[v] = 0
        st = [v]
        while st:
            a = st.pop()
            for b in adj[a]:
                if b not in color:
                    color[b] = 1 - color[a]
                    st.append(b)
    X = sorted(v for v in adj if color[v] == 0)
    Y = sorted(v for v in adj if color[v] == 1)
    xi = {v: i for i, v in enumerate(X)}
    yi = {v: i for i, v in enumerate(Y)}
    Ms = []
    names = []
    for w, o in sorted(outs.items(), key=lambda kv: int(kv[0])):
        M = [[0] * 6 for _ in range(6)]
        for a, b in o['quadratic']:
            if a in yi:
                a, b = b, a
            M[xi[a]][yi[b]] ^= 1
        names.append(int(w))
        Ms.append(M)
    assert all(M[i][j] == M[j][i] for M in Ms for i in range(6) for j in range(6)), 'not symmetric'
    W = [sym_vec(M) for M in Ms]
    Wb = rank_basis(W, 21)
    print(f'outputs={names} span rank={len(Wb)} (symmetric verified)')

    pool = []
    for u in range(1, 64):
        bits = [i for i in range(6) if u >> i & 1]
        M = [[0] * 6 for _ in range(6)]
        for i in bits:
            for j in bits:
                M[i][j] = 1
        pool.append((u, sym_vec(M)))
    print(f'pool: {len(pool)} symmetric rank-1 matrices u u^T')

    # quotient coordinates: complete Wb to basis of full 21-dim space
    full = rank_basis([1 << i for i in range(21)] + [b for _, b in Wb], 21)
    # full is a basis of the whole space; take pivots not used by W
    wpiv = {p for p, _ in Wb}
    comp_piv = [p for p, _ in full if p not in wpiv]
    # build quotient map: coordinates on complement pivots after reducing by W
    classes = []
    for u, v in pool:
        r = reduce_(v, Wb)
        c = 0
        for k, p in enumerate(comp_piv):
            if r >> p & 1:
                c |= 1 << k
        classes.append((u, v, c))
    from collections import defaultdict
    byclass = defaultdict(list)
    for u, v, c in classes:
        byclass[c].append((u, v))
    print(f'distinct pool classes in Sym/W: {len(byclass)} of 2^{len(comp_piv)}-1')
    hist = sorted((len(v) for v in byclass.values()), reverse=True)
    print('class sizes:', hist)
    present = sorted(c for c in byclass if c)
    print('rational classes (nonzero):', len(present))

    # rank of preimage test
    def fill_check(vecs):
        """True iff vecs span the full preimage of their class span, and W inside."""
        r = rank(vecs)
        rw = rank(vecs + W)
        return r, rw

    for d in (1, 2, 3):
        sols = []
        for combo in combinations(present, d):
            # span of combo classes
            cb = rank_basis(list(combo), 0)
            members = []
            for c, lst in byclass.items():
                if reduce_(c, cb) == 0:
                    members.extend(lst)
            if not members:
                continue
            r, rw = fill_check([v for _, v in members])
            if rw == 10 + d and r == 10 + d:
                sols.append((combo, members))
                if len(sols) >= 5:
                    break
        print(f'd={d}: solutions={len(sols)} (need k={10+d})')
        if sols:
            combo, members = sols[0]
            Us = sorted({u for u, _ in members})
            print(f'  first solution class combo={combo}; pool u values ({len(Us)}):',
                  [bin(u) for u in Us])
            # greedy independent subset of size 10+d
            chosen = []
            cb2 = list(Wb)
            for u, v in members:
                r = reduce_(v, cb2)
                if r:
                    cb2.append((r.bit_length() - 1, r))
                    cb2.sort(reverse=True)
                    chosen.append(u)
            print(f'  greedy witness size {len(chosen)}: u={chosen}')
            json.dump({'k': 10 + d, 'u': chosen,
                       'names': names,
                       'X': X, 'Y': Y},
                      open('artifacts/20261106_phase_recovery/subagents/inverse12_norm_witness.json', 'w'), indent=1)
            return
    print('no solution found for d<=3')


if __name__ == '__main__':
    main()
