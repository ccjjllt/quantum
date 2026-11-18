"""Does the 5-low-bit split leave any product-pairing candidate at full saturation?

L=5: 32 low slots, 31 low coords, nh=39 -> 38 high slices, 10 three-coord blocks
+ 1 leftover.  Cut ceiling 686 -> dim 399 -> products 199.5 (nominal).
products are only realisable if, at that saturation, some (block,form)x(block,form)
pair still has a non-empty output nullspace.
"""
import json, itertools
from common import load_words, gf2_rank, NOUT, M35
from parity_recover import nullspace, basis
from probe_split import complete, cross_tensor


def local(x, part):
    return sum(((x >> (NOUT * i)) & M35) << (NOUT * j) for j, i in enumerate(part))


def proj(phi, l, n):
    v = 0
    for j in range(n):
        if (l >> j) & 1:
            v ^= (phi >> (NOUT * j)) & M35
    return v


def run(L, k, blocksize=3):
    M = 1 << L
    a, _ = complete(load_words(), M)
    t = cross_tensor(a, k, M)
    S = [int(x) for x in t[1:]]
    nc = M - 1
    parts = [list(range(i, min(i + blocksize, nc))) for i in range(0, nc, blocksize)]
    cuts, ranks = [], []
    for part in parts:
        loc = [local(x, part) for x in S]
        c = nullspace(loc, NOUT * len(part))
        cuts.append(c)
        ranks.append(NOUT * len(part) - len(c))
    dim = (nc * NOUT) - sum(len(c) for c in cuts)
    K = []
    for b, part in enumerate(parts):
        row = []
        for l in range(1, 1 << len(part)):
            row.append(list(basis([v for v in (proj(c, l, len(part)) for c in cuts[b]) if v]).values()))
        K.append(row)
    npair = 0
    for b1, b2 in itertools.combinations(range(len(parts)), 2):
        for l1 in range(1, 1 << len(parts[b1])):
            for l2 in range(1, 1 << len(parts[b2])):
                if nullspace(K[b1][l1 - 1] + K[b2][l2 - 1], NOUT):
                    npair += 1
    out = {'L': L, 'k': k, 'blocks': [len(p) for p in parts], 'block_ranks': ranks,
           'cuts_at_saturation': sum(len(c) for c in cuts), 'dim': dim,
           'products_ceiling': dim / 2, 'form_pairs_with_a_candidate': npair,
           'block_pairs': len(list(itertools.combinations(range(len(parts)), 2)))}
    return out


if __name__ == '__main__':
    res = [run(4, 4), run(5, 4), run(5, 2), run(3, 4)]
    for r in res:
        print(json.dumps(r), flush=True)
    json.dump(res, open('/tmp/split_pairs.json', 'w'), indent=1)
