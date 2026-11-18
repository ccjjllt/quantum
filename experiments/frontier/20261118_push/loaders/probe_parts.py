"""Price the block-partition trade for the product count.

products = (525 - sum_cuts)/2,  cut ceiling per block = 35*|part| - rank(block target).

More coords per block  ->  a higher cut ceiling  ->  fewer products,
but the product *pairing* (a form in block b1 with a form in block b2 sharing an
output vector v) has to stay perfect.  This script measures, at full saturation
(all cuts taken), the span and the randomized alternating rank of the candidate
pairing, which is the quantity that decides whether the ceiling is reachable.

Pure GF(2) / GF(2^8) arithmetic on the table; no circuit simulation.
"""
import json, random, sys, itertools, time
import numpy as np
from common import load_words, gf2_basis, gf2_rank, NOUT, NDIM, M35

from planner import complete_words, cross_tensor
from lowbasis import inverse15, transform_target
from parity_recover import nullspace, MUL, INV, gf_rank, basis


def local(x, part):
    return sum(((x >> (NOUT * i)) & M35) << (NOUT * j) for j, i in enumerate(part))


def proj(phi, l, n):
    v = 0
    for j in range(n):
        if (l >> j) & 1:
            v ^= (phi >> (NOUT * j)) & M35
    return v


def block_cuts(tt, parts, lo=1, hi=76):
    cuts = []
    for part in parts:
        loc = [local(x, part) for x in tt[lo:hi]]
        cuts.append(nullspace(loc, NOUT * len(part)))
    return cuts


def forms_constraint(cuts, l, n):
    out = []
    for c in cuts:
        v = proj(c, l, n)
        if v:
            out.append(v)
    return list(basis(out).values())


def alt_rank_vec(cands, dim, rng, repeats=1):
    """Randomized alternating rank over GF(2^8); cands = list of (a,b) index lists.

    Indices live in the physical NDIM=525 space (as in parity_recover.alternating_field),
    so the witness matrix is NDIM x NDIM; the target rank is dim.
    """
    best = 0
    for _ in range(repeats):
        A = np.zeros((NDIM, NDIM), dtype=np.uint8)
        for a, b in cands:
            if not a or not b:
                continue
            v = rng.randrange(1, 256)
            ia = np.array(a)
            ib = np.array(b)
            A[np.ix_(ia, ib)] ^= v
            A[np.ix_(ib, ia)] ^= v
        r = gf_rank(A)
        best = max(best, r)
    return best


def bits(x):
    out = []
    while x:
        b = x & -x
        x ^= b
        out.append(b.bit_length() - 1)
    return out


def evaluate(tt, parts, k, max_v_per_pair=24, repeats=2, seed=7, verbose=True):
    rng = random.Random(seed)
    cuts = block_cuts(tt, parts)
    dim = NDIM - sum(len(c) for c in cuts)
    ranks = [NOUT * len(p) - len(c) for p, c in zip(parts, cuts)]
    if verbose:
        print(f'  k{k} parts={[len(p) for p in parts]} block_ranks={ranks} cuts={sum(len(c) for c in cuts)} dim={dim} '
              f'-> products {dim/2:.1f}', flush=True)
    if dim <= 0:
        return None
    # candidate products at saturation
    nforms = [1 << len(p) for p in parts]
    K = [[forms_constraint(cuts[b], l, len(parts[b])) for l in range(1, nforms[b])] for b in range(len(parts))]
    cols = []
    ncand = 0
    for b1, b2 in itertools.combinations(range(len(parts)), 2):
        for l1 in range(1, nforms[b1]):
            m1 = sum(((1 << parts[b1][j]) if (l1 >> j) & 1 else 0) for j in range(len(parts[b1])))
            for l2 in range(1, nforms[b2]):
                m2 = sum(((1 << parts[b2][j]) if (l2 >> j) & 1 else 0) for j in range(len(parts[b2])))
                vs = nullspace(K[b1][l1 - 1] + K[b2][l2 - 1], NOUT)
                if not vs:
                    continue
                ncand += 1
                pool = vs if len(vs) <= max_v_per_pair else rng.sample(vs, max_v_per_pair)
                ia = bits(m1)
                ib = bits(m2)
                for v in pool:
                    a = [NOUT * m + b for m in ia for b in bits(v)]
                    bb = [NOUT * m + b for m in ib for b in bits(v)]
                    cols.append((a, bb))
    r = alt_rank_vec(cols, dim, rng, repeats=repeats)
    if verbose:
        print(f'  k{k} candidate form-pairs {ncand} product-candidates {len(cols)} alt-rank {r}/{dim} '
              f'-> /2 pairs {r//2}  deficiency {dim - r}', flush=True)
    return {'k': k, 'dim': dim, 'alt_rank': r, 'products_ceiling': dim / 2, 'deficiency': dim - r}


def main():
    W = load_words()
    Wc = complete_words(W)
    k = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    t = cross_tensor(Wc, k)
    rid = [1 << i for i in range(15)]
    tt = transform_target(t, inverse15(rid))
    plan = [{'name': '5x3', 'parts': [[3 * i, 3 * i + 1, 3 * i + 2] for i in range(5)]},
            {'name': '4x4+3', 'parts': [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11], [12, 13, 14]]},
            {'name': '3x5', 'parts': [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9], [10, 11, 12, 13, 14]]},
            {'name': '2x7+8', 'parts': [[0, 1, 2, 3, 4, 5, 6], [7, 8, 9, 10, 11, 12, 13, 14]]}]
    out = []
    for p in plan:
        t0 = time.time()
        print(p['name'], flush=True)
        r = evaluate(tt, p['parts'], k)
        if r:
            r['name'] = p['name']
            r['seconds'] = round(time.time() - t0, 1)
            out.append(r)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
