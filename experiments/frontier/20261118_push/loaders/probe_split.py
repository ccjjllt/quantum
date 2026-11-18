"""Price the (h,l) address split, and test row-permutation legality for the emitter.

Split: L low address bits (M = 2**L low slots, coords = M-1 low monomials),
       nh = ceil(1220/M) high slices (nh-1 determined slices),
       high cache = (nh-1) - #{powers of two <= nh-1}   CCX,
       products  = (NDIM - cuts)/2 with NDIM = (M-1)*35,
       cuts per 3-coord block = 105 - rank(block local target).

Row permutation legality: emit_plan.separate_helpers asserts the word bit7^bit6
helper table is low(16) xor high; a permutation that breaks it cannot be emitted.

Pure arithmetic only.
"""
import json, sys
import numpy as np
from common import load_words, gf2_rank, NOUT, M35


def addr_shape(rows, M):
    nh = (rows + M - 1) // M
    rem = rows - M * (nh - 1)
    return nh, rem, nh * M, (nh - 1).bit_length()


def complete(words, M, rows=None):
    words = np.asarray(words, dtype=np.uint8)
    rows = len(words) if rows is None else rows
    nh, rem, N, hb = addr_shape(rows, M)
    a = np.zeros((N, 75), dtype=np.uint8)
    a[:rows] = words
    f = a.reshape(nh, M, 75)
    lb = (M - 1).bit_length()
    for b in range(lb):
        for l in range(M):
            if l & (1 << b):
                f[:, l] ^= f[:, l ^ (1 << b)]
    for b in range(hb):
        for h in range(nh):
            if h & (1 << b):
                f[h] ^= f[h ^ (1 << b)]
    f[nh - 1, rem:] = 0
    for b in range(hb):
        for h in range(nh):
            if h & (1 << b):
                f[h] ^= f[h ^ (1 << b)]
    for b in range(lb):
        for l in range(M):
            if l & (1 << b):
                f[:, l] ^= f[:, l ^ (1 << b)]
    return a.reshape(nh * M, 75), f


def cross_tensor(words_completed, k, M):
    nh = len(words_completed) // M
    w = np.asarray(words_completed)
    delta = w[:, 5 * k:5 * k + 5].copy()
    if k:
        delta ^= w[:, 5 * k - 5:5 * k]
    packed = np.zeros(nh * M, dtype=np.uint64)
    for j in range(5):
        packed[:len(delta)] |= (delta[:, j].astype(np.uint64) & 127) << (7 * j)
    f = packed.reshape(nh, M).copy()
    hb = (nh - 1).bit_length()
    lb = (M - 1).bit_length()
    for b in range(lb):
        for l in range(M):
            if l & (1 << b):
                f[:, l] ^= f[:, l ^ (1 << b)]
    for b in range(hb):
        for h in range(nh):
            if h & (1 << b):
                f[h] ^= f[h ^ (1 << b)]
    return [sum(int(f[h, l]) << ((l - 1) * NOUT) for l in range(1, M)) for h in range(nh)]


def block_stats(target, M, blocksize=3):
    """Per-block local rank over all determined slices, blocks of `blocksize` coords."""
    nc = M - 1
    S = [int(x) for x in target[1:len(target)]]
    parts = [list(range(i, min(i + blocksize, nc))) for i in range(0, nc, blocksize)]
    out = []
    for part in parts:
        loc = []
        for x in S:
            v = 0
            for j, i in enumerate(part):
                v |= ((x >> (NOUT * i)) & M35) << (NOUT * j)
            loc.append(v)
        r = gf2_rank(loc)
        out.append({'n': len(part), 'dim': NOUT * len(part), 'rank': r, 'nullity': NOUT * len(part) - r})
    return out


def main():
    W = load_words()
    res = []
    for L in (3, 4, 5):
        M = 1 << L
        a, _anf = complete(W, M)
        for k in (4,):
            t = cross_tensor(a, k, M)
            nh = len(t)
            hb = (nh - 1).bit_length()
            nslice = nh - 1
            high_cache = nslice - len([h for h in range(1, nh) if h & (h - 1) == 0])
            S = [int(x) for x in t[1:]]
            rank = gf2_rank(S)
            bs = block_stats(t, M)
            cuts = sum(b['nullity'] for b in bs)
            ndim = (M - 1) * NOUT
            products = (ndim - cuts) / 2
            row = {'L': L, 'M': M, 'nh': nh, 'n_slices': nslice, 'coords': M - 1,
                   'high_cache': high_cache, 'target_rank': rank, 'blocks': bs,
                   'cut_ceiling': cuts, 'NDIM': ndim, 'products_ceiling': products,
                   'toffoli_est': products + high_cache, 'k': k}
            print(json.dumps(row), flush=True)
            res.append(row)
    json.dump(res, open('/tmp/split_probe.json', 'w'), indent=1)


if __name__ == '__main__':
    main()
