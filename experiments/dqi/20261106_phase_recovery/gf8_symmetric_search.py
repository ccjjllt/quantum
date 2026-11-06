"""Beam search for a small symmetric rank-one span of GF(2^8) multiplication.

W is the 8-dimensional bit-slice space of GF(2^8) multiplication.  A symmetric
decomposition with k terms exists iff W is contained in the span of k matrices
u u^T.  The quotient Sym_8/W has dimension 28; for a class subspace S of
dimension d, the preimage has dimension 8+d.  If the pool matrices whose class
lies in S span that whole preimage, the decomposition needs 8+d terms.
"""
import json
import sys
from pathlib import Path

import kickmix as km

N = 8
PAIRS = [(i, j) for j in range(N) for i in range(j + 1)]
IDX = {p: k for k, p in enumerate(PAIRS)}
DIM_SYM = len(PAIRS)


def sym_vec(bits):
    v = 0
    for i in range(N):
        if bits >> i & 1:
            for j in range(N):
                if bits >> j & 1:
                    a, b = (i, j) if i <= j else (j, i)
                    v |= 1 << IDX[(a, b)]
    return v


def rank_basis(vecs):
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


def rank_of(vecs):
    return len(rank_basis(vecs))


def reduce_(x, basis):
    for p, b in basis:
        if x >> p & 1:
            x ^= b
    return x


def main():
    f = km.GF2Field(N)
    W = []
    for k in range(N):
        v = 0
        for i in range(N):
            for j in range(N):
                if (f.mul(1 << i, 1 << j) >> k) & 1:
                    a, b = (i, j) if i <= j else (j, i)
                    v |= 1 << IDX[(a, b)]
        W.append(v)
    Wb = rank_basis(W)
    print('W rank', len(Wb))
    full = rank_basis([1 << i for i in range(DIM_SYM)] + [b for _, b in Wb])
    wpiv = {p for p, _ in Wb}
    comp = [p for p, _ in full if p not in wpiv]
    print('quotient dim', len(comp))

    pool = []
    for u in range(1, 1 << N):
        v = sym_vec(u)
        c = 0
        r = reduce_(v, Wb)
        for k, p in enumerate(comp):
            if r >> p & 1:
                c |= 1 << k
        pool.append((u, v, c))
    present = sorted({c for _, _, c in pool})
    print('pool', len(pool), 'distinct classes', len(present))

    def pool_in_S(Sb):
        Sbasis = rank_basis(Sb)
        out = []
        for u, v, c in pool:
            if reduce_(c, Sbasis) == 0:
                out.append((u, v))
        return out

    # beam state: (score, dim, Sbasis, chosen)
    beams = [(0, 0, [], [])]
    best = None
    for depth in range(1, 17):
        cand = []
        for _, dim, Sb, chosen in beams:
            for c in present:
                if reduce_(c, rank_basis(Sb)) == 0:
                    continue
                Sb2 = [b for _, b in rank_basis(Sb + [c])]
                dim2 = len(Sb2)
                if dim2 != dim + 1:
                    continue
                members = pool_in_S(Sb2)
                r = rank_of([v for _, v in members])
                need = len(Wb) + dim2
                if r == need:
                    best = (need, Sb2, members)
                    print(f'FOUND k={need} at dim={dim2}', flush=True)
                    break
                cand.append((r - dim2, r, dim2, Sb2, members))
            if best:
                break
        if best:
            break
        cand.sort(key=lambda x: (-x[0], -x[1], x[2]))
        seen = set()
        beams = []
        for score, r, dim2, Sb2, members in cand:
            key = tuple(sorted(Sb2))
            if key in seen:
                continue
            seen.add(key)
            beams.append((score, dim2, Sb2, members))
            if len(beams) >= 40:
                break
        print(f'depth {depth}: beams {len(beams)} best score {beams[0][0] if beams else None}', flush=True)

    if best:
        k, Sb, members = best
        # pick a rank-k basis from members
        basis = []
        chosen = []
        for u, v in members:
            r = reduce_(v, basis)
            if r:
                basis.append((r.bit_length() - 1, r))
                basis.sort(reverse=True)
                chosen.append(u)
            if len(chosen) == k:
                break
        print('chosen k', len(chosen), 'u', chosen)
        out = {'k': len(chosen), 'u': chosen}
    else:
        out = {'k': None, 'note': 'no filling class subspace up to dim 16'}
    target = Path(__file__).resolve().parents[3] / 'artifacts/20261106_phase_recovery/gf8_symmetric_search.json'
    target.write_text(json.dumps(out, indent=1))
    print(json.dumps(out))


if __name__ == '__main__':
    main()
