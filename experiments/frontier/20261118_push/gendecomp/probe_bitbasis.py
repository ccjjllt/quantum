"""Basis-label construction.

Restrict to products whose 35-bit label v is a single basis vector e_j of GF(2)^35
(the "bit" decomposition) and whose low set L is arbitrary.  Then the achievable
target space is the product over j of  span{1_L : generators with label e_j} inside
GF(2)^15, and the minimum generator count for bit j is

    d_j = dim( proj_j(R) ),   proj_j : r -> (r_1[j], ..., r_15[j]) in GF(2)^15 .

So M = sum_j d_j generators, and (pairing two generators with the same label into
one product) about M/2 products.  Report sum_j d_j and the free per-bit list.
"""
import sys, json
import common as C

NOUT = C.NOUT
FREE = {(76, l) for l in range(4, 16)}


def slices(k):
    W, Wc, target, cells = C.build(k)
    rows = {}
    for h in range(1, 77):
        chunks = []
        for l in range(1, 16):
            v = 0 if (h, l) in FREE else cells.get((h, l), 0)
            chunks.append(v)
        rows[h] = chunks
    return rows


def main(k):
    rows = slices(k)
    # basis of R: the 76 row vectors as 525-bit ints
    vecs = []
    for h in range(1, 77):
        x = 0
        for i, v in enumerate(rows[h]):
            x ^= v << (NOUT * i)
        if x:
            vecs.append(x)
    d = {}
    for x in vecs:
        while x:
            p = x.bit_length() - 1
            if p in d:
                x ^= d[p]
            else:
                d[p] = x
                break
    basisR = list(d.values())
    print(json.dumps({'k': k, 'dimR': len(basisR), 'nrows_used': len(vecs)}), flush=True)
    # proj_j(R): bit j of every chunk across the 15 coords
    dj = []
    for j in range(NOUT):
        pats = []
        for x in basisR:
            pat = 0
            for i in range(15):
                if ((x >> (NOUT * i)) >> j) & 1:
                    pat |= 1 << i
            pats.append(pat)
        dj.append(C.gf2_rank([p for p in pats if p]))
    print(json.dumps({'k': k, 'd_j': dj, 'sum': sum(dj), 'max': max(dj),
                      'products_if_paired': sum((x + 1) // 2 for x in dj)}), flush=True)


if __name__ == '__main__':
    for k in [int(x) for x in (sys.argv[1].split(',') if len(sys.argv) > 1 else '4')]:
        main(k)
