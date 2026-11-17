"""Rank structure of the target: per-low-column and per-row rank profiles.

Cells are (h,l), h in 1..76, l in 1..15, minus the 12 free padding cells
(h=76, l>=4).  Values are 35-bit vectors.

Y_l  : 76 x 35 matrix whose rows are the values of column l over h   -> rank
Z_h  : 15 x 35 matrix whose rows are the values of row h over l      -> rank
"""
import sys, json
from collections import Counter
import common as C

FREE = {(76, l) for l in range(4, 16)}


def required(k):
    W, Wc, target, cl = C.build(k)
    req = {c: v for c, v in cl.items() if c[0] >= 1 and c not in FREE}
    return cl, req


def main(ks):
    for k in ks:
        cl, req = required(k)
        print(json.dumps({'k': k, 'nonzero_all': len(cl), 'required': len(req),
                          'rank_slices': C.gf2_rank([int(x) for x in C.build(k)[2][1:76]])}), flush=True)
        # per-column ranks
        rl = {}
        for l in range(1, 16):
            vecs = [req.get((h, l), 0) for h in range(1, 77)]
            nz = [v for v in vecs if v]
            rl[l] = {'rank': C.gf2_rank(nz), 'nnz': len(nz), 'distinct': len(set(nz))}
        print(' per column:', json.dumps(rl), flush=True)
        print(' sum ranks', sum(v['rank'] for v in rl.values()), flush=True)
        # per-row ranks
        rh = {}
        for h in range(1, 77):
            vecs = [req.get((h, l), 0) for l in range(1, 16)]
            nz = [v for v in vecs if v]
            rh[h] = (C.gf2_rank(nz), len(nz))
        print(' per row rank hist', dict(sorted(Counter(x[0] for x in rh.values()).items())),
              'sum ranks', sum(x[0] for x in rh.values()), flush=True)
        print(' per row nnz hist', dict(sorted(Counter(x[1] for x in rh.values()).items())), flush=True)


if __name__ == '__main__':
    ks = [int(x) for x in (sys.argv[1].split(',') if len(sys.argv) > 1 else '2,4')]
    main(ks)
