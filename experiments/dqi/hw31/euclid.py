"""Field and polynomial arithmetic over GF(4096)."""

from collections import Counter
from functools import cache, reduce
from operator import xor


MOD = 0x1053


def mul(a, b):
    c = 0
    while b:
        if b & 1:
            c ^= a
        b >>= 1
        a <<= 1
        if a & 4096:
            a ^= MOD
    return c


def power(a, n):
    out = 1
    while n:
        if n & 1:
            out = mul(out, a)
        a = mul(a, a)
        n >>= 1
    return out


def indices(mask):
    while mask:
        low = mask & -mask
        yield low.bit_length() - 1
        mask ^= low


def pack(p):
    return sum(x << (12*i) for i, x in enumerate(p))


def trim(p):
    p = list(p)
    while p and not p[-1]:
        p.pop()
    return p


def add(a, b):
    out = list(a) + [0] * max(0, len(b) - len(a))
    for i, x in enumerate(b):
        out[i] ^= x
    return trim(out)


def coeff_product(a, b):
    if not a or not b:
        return []
    c = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            c[i + j] ^= mul(x, y)
    return trim(c)


def ev(c, u):
    out = 0
    for x in reversed(c):
        out = mul(out, u) ^ x
    return out


@cache
def lagrange(points):
    """Coefficients of the polynomial that selects each node."""
    result = []
    for u in points:
        f = [1]
        d = 1
        for v in points:
            if u != v:
                f = coeff_product(f, [v, 1])
                d = mul(d, u ^ v)
        result.append([mul(x, power(d, 4094)) for x in f])
    return result


def interp_product(a, b):
    if not a or not b:
        return []
    points = tuple(range(len(a) + len(b) - 1))
    out = []
    for u, sel in zip(points, lagrange(points)):
        y = mul(ev(a, u), ev(b, u))
        out = add(out, [mul(y, s) for s in sel])
    return out


def euclid(a, b):
    """Full Bezout, including the last division to zero, like the historical loop.

    This is a field-operation schedule with classical degree discovery.
    Inverses, quantum degree handling and in-place quotient storage are distinct.
    """
    s0, s1, t0, t1 = [1], [], [], [1]
    cost = Counter()
    while b:
        if len(a) < len(b):
            raise ValueError("degree order")
        d = len(b) - 1
        q = [0] * (len(a) - d)
        work = list(a)
        inv = power(b[-1], 4094)
        cost['inverses'] += 1
        # Only high coefficients are used while discovering quotient words.
        for k in range(len(q) - 1, -1, -1):
            q[k] = mul(work[k + d], inv)
            cost['quotient_gf'] += 1
            for j in range(max(0, d - k), d):
                work[j + k] ^= mul(q[k], b[j])
                cost['quotient_gf'] += 1
        # Low coefficients of q*b[:d] suffice for the remainder. Interpolating
        # at r+s-1 points or using triangular truncated schoolbook, pick cheapest.
        if d:
            ranks = [len(q)+d-1, sum(max(0, d-i) for i in range(len(q)))]
            cost['remainder_gf'] += min(ranks)
        r = add(a[:d], interp_product(q, b[:d])[:d])
        assert a == add(coeff_product(q, b), r)
        for name, u in [('left_bezout_gf', s1), ('right_bezout_gf', t1)]:
            if u and u != [1]:
                cost[name] += len(q)+len(u)-1
        ns = add(s0, interp_product(q, s1))
        nt = add(t0, interp_product(q, t1))
        s0,s1,t0,t1 = s1,ns,t1,nt
        a,b = b,r
    return a, s0, t0, dict(cost)


def tower_terms():
    # F_8 = F_2[z]/(z^3+z+1), embedded into the verifier field.
    root = next(x for x in range(2, 4096) if power(x,3)^x^1 == 0)
    sub = [reduce(xor, (power(root,k) for k in indices(i)), 0) for i in range(8)]
    inverse_sub = {v:i for i,v in enumerate(sub)}
    cols = [mul(sub[1<<k],power(2,j)) for j in range(4) for k in range(3)]
    coords = {reduce(xor, (cols[k] for k in indices(i)), 0):i for i in range(4096)}
    assert len(coords) == 4096
    masks = []
    for u in range(7):
        output = []
        for k in range(12):
            p = coords[1<<k]
            vals = [sub[(p >> (3*j)) & 7] for j in range(4)]
            output.append(inverse_sub[ev(vals,sub[u])])
        for mask in [1,2,4,3,5,6]:
            masks.append(sum(((y & mask).bit_count() % 2) << k for k,y in enumerate(output)))
    pivots = {}
    for i in range(12):
        for j in range(i,12):
            row = sum(((m>>i)&(m>>j)&1) << k for k,m in enumerate(masks))
            rhs = mul(1<<i,1<<j)
            while row:
                k = (row & -row).bit_length()-1
                if k not in pivots:
                    pivots[k] = row,rhs
                    break
                a,b = pivots[k]
                row ^= a
                rhs ^= b
            assert row or rhs == 0
    out = [0]*len(masks)
    for k,(row,rhs) in sorted(pivots.items(),reverse=True):
        out[k] = reduce(xor,(out[j] for j in indices(row^(1<<k))),rhs)
    assert all(out)
    return list(zip(masks,out))


def lift_form(point, words, mask):
    return sum(((mul(1<<j,power(point,i)) & mask).bit_count() % 2) << (12*i+j)
               for i in range(words) for j in range(12))


def product_terms(a_words,b_words,out_words,field_terms):
    nodes = tuple(range(a_words+b_words-1))
    for point,coefs in zip(nodes,lagrange(nodes)):
        for mask,w in field_terms:
            out = pack([mul(c,w) for c in coefs[:out_words]])
            if out:
                yield lift_form(point,a_words,mask),lift_form(point,b_words,mask),out
