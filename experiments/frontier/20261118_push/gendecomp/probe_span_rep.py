"""KEY EXPERIMENT: is the 75-dim target span R spanned by "replicated" vectors?

A product contributes  outer(L, v) = v placed on every low coordinate in L to the
525-bit slice space (L a subset of the 15 low monomials, v a 35-bit output mask).
If R (dim 75) has a basis of such vectors, the loader needs only ~75 products.

For every L with |L| <= LMAX: compute V_L = { v : outer(L,v) in R } (a subspace of
GF(2)^35) exactly, accumulate W = span of all replicated vectors found, and report
dim W vs dim R.
"""
import sys, json, itertools
import common as C

NOUT = C.NOUT


def outer(l, v):
    out = 0
    for i in range(15):
        if (l >> i) & 1:
            out ^= v << (NOUT * i)
    return out


def rref(vecs):
    d = {}
    for x in vecs:
        while x:
            p = x.bit_length() - 1
            if p in d:
                x ^= d[p]
            else:
                d[p] = x
                break
    return d


def reduce_to(x, d):
    for p in sorted(d, reverse=True):
        if x & (1 << p):
            x ^= d[p]
    return x


def kernel_basis(rows, n):
    """rows: list of (mask over n vars, syndrome-int).  Return basis of the kernel
    of the linear map v -> XOR_{j in v} syndrome_j, as masks over n vars."""
    piv = {}                      # pivot var -> (syndrome, coefficient mask over vars)
    for j, s in rows:
        x = s
        co = 1 << j
        while x:
            p = x.bit_length() - 1
            if p in piv:
                x ^= piv[p][0]
                co ^= piv[p][1]
            else:
                piv[p] = (x, co)
                break
        # if x == 0: this variable is already dependent (ignored)
    used = set()
    for p, (x, co) in piv.items():
        used.add(co.bit_length() - 1)
    free = [j for j in range(n) if j not in used]
    out = []
    for j in free:
        v = 1 << j
        # back-substitute: for pivot p with coefficient mask co, need
        # syndrome(co) . v == 0, i.e. parity(syndrome of (co & v)) -- solve for the
        # pivot variable of co.
        for p, (x, co) in sorted(piv.items(), reverse=True):
            pc = co.bit_length() - 1
            # value of the constraint: XOR of syndromes of vars in (co & v)
            acc = 0
            m = co & v
            k = 0
            while m:
                if m & 1:
                    acc ^= synd[co & v & ((1 << k) - 1) and 0]
                m >>= 1
                k += 1
            out.append((acc, v))
        out.append((0, v))
    return out


def main(k, lmax=2, ka=None):
    import common
    Wt, Wc, target, cells = common.build(k)
    R = rref([int(x) for x in target[1:77]])
    dimR = len(R)
    Wb = {}
    for size in range(1, lmax + 1):
        for L in itertools.combinations(range(15), size):
            lmask = sum(1 << i for i in L)
            # constraint matrix: rows = syndromes of e_j
            synd = [reduce_to(outer(lmask, 1 << j), R) for j in range(NOUT)]
            # gaussian elimination over the 35 variables with syndrome values
            piv = {}
            for j in range(NOUT):
                x = synd[j]
                co = 1 << j
                while x:
                    p = x.bit_length() - 1
                    if p in piv:
                        x ^= piv[p][0]
                        co ^= piv[p][1]
                    else:
                        piv[p] = (x, co)
                        break
            pivvars = {co.bit_length() - 1 for (x, co) in piv.values()}
            free = [j for j in range(NOUT) if j not in pivvars]
            for jf in free:
                v = 1 << jf
                for p, (x, co) in sorted(piv.items(), reverse=True):
                    pc = co.bit_length() - 1
                    # need XOR_{k in co & v} synd[k] == 0 ; solve for bit pc
                    acc = 0
                    m = co & v & ~(1 << pc)
                    while m:
                        b = m & -m
                        acc ^= synd[b.bit_length() - 1]
                        m ^= b
                    if acc:
                        v |= 1 << pc
                z = outer(lmask, v)
                assert reduce_to(z, R) == 0, 'kernel solve failed'
                Wb = rref(list(Wb.values()) + [z])
        print(json.dumps({'k': k, 'lmax': size, 'dimW': len(Wb), 'dimR': dimR}), flush=True)
        if len(Wb) == dimR:
            break
    print(json.dumps({'k': k, 'dimR': dimR, 'dimW': len(Wb), 'spans': len(Wb) == dimR}), flush=True)


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 4,
         int(sys.argv[2]) if len(sys.argv) > 2 else 2)
