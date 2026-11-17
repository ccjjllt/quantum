"""Per-block chunk-vector census and greedy spanning-set size (pure GF(2)).

A product column is always  e_L (x) v  ("v replicated on the low-monomial subset L").
For a block B of low coords, pi_B(R) is the projection of the 76-dim slice space.
Chunk-vectors live inside it only when the block is small; the number of such vectors
is the design pool.  Greedy spanning set size = terms needed for that block.
"""
import sys, json, itertools
import common as C

NOUT = C.NOUT
FREE = {(76, l) for l in range(4, 16)}


def outer_restricted(L, v, base):
    out = 0
    for i in range(len(base)):
        if (L >> i) & 1:
            out ^= v << (NOUT * base[i])
    return out


def reduce_to(x, d):
    for p in sorted(d, reverse=True):
        if x & (1 << p):
            x ^= d[p]
    return x


def add_to(x, d):
    while x:
        p = x.bit_length() - 1
        if p in d:
            x ^= d[p]
        else:
            d[p] = x
            return True
    return False


def kernel_basis(imgs, n):
    """{v in GF(2)^n : XOR_{j in v} imgs[j] == 0} as a list of masks.

    Standard elimination: every column whose image reduces to zero yields one
    independent kernel vector (its dependency mask)."""
    piv = {}
    out = []
    for j in range(n):
        x = imgs[j]
        co = 1 << j
        while x:
            p = x.bit_length() - 1
            if p in piv:
                x ^= piv[p][0]
                co ^= piv[p][1]
            else:
                piv[p] = (x, co)
                break
        if not x:
            out.append(co)
    for co in out:                      # sanity: the relation really vanishes
        acc = 0
        m = co
        while m:
            b = m & -m
            acc ^= imgs[b.bit_length() - 1]
            m ^= b
        assert acc == 0
    return out


def projection(R, base):
    mask = 0
    for i in base:
        mask |= ((1 << NOUT) - 1) << (NOUT * i)
    proj = {}
    for x in R.values():
        y = x & mask
        if y:
            add_to(y, proj)
    return proj


def block_census(proj, base, want_span=None):
    pool = []
    per_L = {}
    for L in range(1, 1 << len(base)):
        imgs = [reduce_to(outer_restricted(L, 1 << j, base), proj) for j in range(NOUT)]
        vs = kernel_basis(imgs, NOUT)
        per_L[bin(L)] = len(vs)
        for v in vs:
            z = outer_restricted(L, v, base)
            assert z and reduce_to(z, proj) == 0
            pool.append((L, v, z))
    return pool, per_L


def greedy_span(proj, pool):
    span = {}
    used = []
    for L, v, z in pool:
        if reduce_to(z, span):
            add_to(z, span)
            used.append((L, v))
            if len(span) == len(proj):
                break
    return used, span


def main(k, block_sizes=(1, 2, 3)):
    W, Wc, target, cells = C.build(k)
    R = {}
    for h in range(1, 77):
        x = 0
        for l in range(1, 16):
            if (h, l) not in FREE:
                x ^= cells.get((h, l), 0) << (NOUT * (l - 1))
        if x:
            add_to(x, R)
    out = {'k': k, 'dimR': len(R), 'blocks': []}
    for b in block_sizes:
        blocks = [list(range(i, min(i + b, 15))) for i in range(0, 15, b)]
        if len(blocks[-1]) != b and len(blocks) > 1:
            # merge a short tail into the previous block
            blocks[-2] += blocks[-1]
            blocks.pop()
        tot = 0
        info = []
        for base in blocks:
            proj = projection(R, base)
            if len(base) > 3:
                info.append({'base': base, 'dim_proj': len(proj), 'pool': None, 'note': 'skipped'})
                continue
            pool, per_L = block_census(proj, base)
            used, span = greedy_span(proj, pool)
            info.append({'base': base, 'dim_proj': len(proj), 'pool': len(pool),
                         'per_L': per_L, 'greedy_terms': len(used), 'covered': len(span)})
            tot += len(used)
        out['blocks'].append({'size': b, 'per_block': info, 'total_terms': tot})
        print(json.dumps({'k': k, 'size': b, 'total_terms': tot, 'per_block': info}), flush=True)
    return out


if __name__ == '__main__':
    ks = [int(x) for x in (sys.argv[1].split(',') if len(sys.argv) > 1 else '4')]
    for k in ks:
        main(k)
