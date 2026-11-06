"""Reduce the explicit 27-term GF(2^8) tower to a smaller symmetric rank-one span.

If a subset of <=18 terms still spans the GF(2^8) multiplication slice space,
the k=8 tower gives a 5*18=90-term GF(2^24) multiplier.
"""
import json
import random
import sys
from pathlib import Path

import kickmix as km

WORK = Path(__file__).resolve().parents[3]
KIT = WORK / 'artifacts/20261106_phase_recovery/old_build/blocks/dqi/pro-q18-900/source/playbook/kit/decoder'
sys.path.insert(0, str(KIT))
sys.modules['circ'] = km
sys.path.insert(0, str(KIT / 'exp/arithmetic'))
import field as ar
from exp.mul99 import kernels as mk

N = 8


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


def contains_W(matrices, W):
    return rank_of(list(matrices) + W) == rank_of(matrices)


def main():
    t4 = mk.tensor4()
    terms = mk.extension_tensor(8, 4, 2, t4)
    print('tower terms', len(terms))
    mats = []
    for mask, v in terms:
        m = 0
        for i in range(N):
            if mask >> i & 1:
                for j in range(N):
                    if mask >> j & 1:
                        m |= 1 << (i * N + j)
        mats.append(m)
    f = km.GF2Field(N)
    W = []
    for k in range(N):
        m = 0
        for i in range(N):
            for j in range(N):
                if (f.mul(1 << i, 1 << j) >> k) & 1:
                    m |= 1 << (i * N + j)
        W.append(m)
    W = [x for x in W if x]
    print('W rank', rank_of(W))
    assert contains_W(mats, W)

    best = None
    rng = random.Random(12345)
    for trial in range(2000):
        order = list(range(len(terms)))
        rng.shuffle(order)
        kept = list(range(len(terms)))
        for idx in order:
            cand = [i for i in kept if i != idx]
            if contains_W([mats[i] for i in cand], W):
                kept = cand
        if best is None or len(kept) < len(best):
            best = kept
            print(f'trial {trial}: reduced to {len(kept)} terms', flush=True)
            if len(kept) <= 18:
                break
    print('best size', len(best), 'terms', best)
    out = {
        'source': 'extension_tensor(8,4,2,tensor4())',
        'initial_terms': len(terms),
        'best_terms': len(best),
        'selected': [{'mask': terms[i][0], 'v': terms[i][1]} for i in best],
    }
    target = WORK / 'artifacts/20261106_phase_recovery/gf8_reduced.json'
    target.write_text(json.dumps(out, indent=1))

    # verify the selected terms compute GF(2^8) multiplication
    ok = True
    for a in range(1 << N):
        for b in range(1 << N):
            got = 0
            for i in best:
                mask, v = terms[i]
                if ((mask & a).bit_count() & 1) and ((mask & b).bit_count() & 1):
                    got ^= v
            if got != f.mul(a, b):
                ok = False
                print('mismatch', a, b, got, f.mul(a, b))
                break
        if not ok:
            break
    out['verified_all_inputs'] = ok
    target.write_text(json.dumps(out, indent=1))
    print('verified all 65536 inputs:', ok)


if __name__ == '__main__':
    main()
