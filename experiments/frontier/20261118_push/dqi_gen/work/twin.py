"""Classical twin of the normalized divstep EEA decoder (pure python; no simulation).

Used only to validate the *algebra* and the slot/phase conventions before the
same recurrence is emitted as a reversible circuit in ``dqi_fast.py``.

Layout convention (shared with the circuit):
    slot j of a polynomial array holds the coefficient of x**(p + 1 - j),
    where p is that array's phase counter.  Slot 0 is therefore always a dead
    "coefficient above the degree" slot (value 0) and slot 1 holds the leading
    coefficient.  With this convention both the slot-aligned subtraction and the
    (free, cyclic) down-rotation used to decrement the phase are safe: the
    rotation wraps the always-zero slot 0 into the always-dead top slot.
"""
from __future__ import annotations


def gf_mul(a, b, degree, modulus):
    r = 0
    while b:
        if b & 1:
            r ^= a
        b >>= 1
        a <<= 1
        if a >> degree:
            a ^= modulus
    return r


def gf_pow(a, e, degree, modulus):
    r = 1
    while e:
        if e & 1:
            r = gf_mul(r, a, degree, modulus)
        a = gf_mul(a, a, degree, modulus)
        e >>= 1
    return r


def gf_inv(a, degree, modulus):
    return gf_pow(a, (1 << degree) - 2, degree, modulus)


class Twin:
    def __init__(self, n, degree, modulus, primitive):
        self.n, self.b, self.mod = n, degree, modulus
        self.t = n // 2
        self.NS = n + 3
        self.prim = primitive

    def mul(self, a, b):
        return gf_mul(a, b, self.b, self.mod)

    def inv(self, a):
        return gf_inv(a, self.b, self.mod)

    def div(self, a, b):
        return 0 if b == 0 else self.mul(a, self.inv(b))

    # ---------------------------------------------------------------- EEA
    def eea(self, S, niter=None, trace=False):
        n, t, NS = self.n, self.t, self.NS
        A = [0] * NS
        B = [0] * NS
        U = [0] * NS
        V = [0] * NS
        A[1] = 1                      # x^n
        B[1] = 1                      # x^n
        for j in range(2, n + 2):     # + f
            B[j] = S[n + 1 - j]
        V[n + 1] = 1                  # cofactor 1
        pA = pB = n
        NIT = niter if niter is not None else 3 * (n + 1)
        nsub = nshift = nswap = 0
        nsteps = 0
        for step in range(NIT):
            nsteps = step+1
            if pA < pB:
                A, B, U, V, pA, pB = B, A, V, U, pB, pA
                nswap += 1
            if pB < t:
                break
            if B[1] == 0:
                # divisor normalisation: one shift
                B = B[1:] + [0]
                V = V[1:] + [0]
                pB -= 1
                nshift += 1
                if trace:
                    print(f'  step {step}: shift B -> pB={pB}')
                continue
            c = self.div(A[1], B[1])
            for j in range(NS):
                A[j] ^= self.mul(c, B[j])
                U[j] ^= self.mul(c, V[j])
            A = A[1:] + [A[0]]
            U = U[1:] + [U[0]]
            pA -= 1
            nsub += 1
            if trace:
                print(f'  step {step}: sub pA={pA} pB={pB} c={c}')
        assert A[0] == 0 and U[0] == 0, 'slot 0 must stay dead'
        if trace:
            print(f'  steps: sub={nsub} shift={nshift} swap={nswap}')
        return dict(omega=B, sigma=V, p=pB, stats=(nsub, nshift, nswap, nsteps))

    def poly(self, arr, p):
        """dense coefficients in ascending order"""
        return [arr[p + 1 - i] if 0 <= p + 1 - i < len(arr) else 0 for i in range(p + 1)]

    def horner(self, arr, xj, spurious_power=None):
        acc = 0
        for j in range(len(arr)):
            acc = self.mul(acc, xj) ^ arr[j]
        return acc

    # ------------------------------------------------------- chien/forney
    def decode(self, S):
        n, t, b = self.n, self.t, self.b
        L = (1 << b) - 1
        r = self.eea(S)
        omega, sigma, p = r['omega'], r['sigma'], r['p']
        errs = {}
        for j in range(min(L, 1 << 30)):
            xj = gf_pow(self.prim, (-j) % L, b, self.mod)
            s = self.horner(sigma, xj)
            if s == 0:
                w = self.horner(omega, xj)
                d = self.horner_deriv(sigma, xj, p)
                errs[j] = self.div(self.mul(w, xj), d)
        return errs, r

    def horner_deriv(self, arr, xj, p):
        NS = len(arr)
        acc = 0
        for j in range(NS):
            acc = self.mul(acc, xj)
            i = p + 1 - j
            if i & 1:
                acc ^= arr[j]
        return acc


def reference_decode(S, n, degree, modulus, primitive, m):
    """Standard textbook EEA (descending, monic-normalised) as ground truth."""
    t = n // 2
    L = (1 << degree) - 1

    def mul(a, b):
        return gf_mul(a, b, degree, modulus)

    # polynomials ascending, lists
    r0 = [0] * (n + 1)
    r0[n] = 1
    r1 = [S[i] if i < n else 0 for i in range(n + 1)]
    u0, u1 = [0], [1]

    def deg(p):
        d = len(p) - 1
        while d >= 0 and p[d] == 0:
            d -= 1
        return d

    def trim(p):
        while len(p) > 1 and p[-1] == 0:
            p.pop()
        return p

    while deg(r1) >= t:
        d1 = deg(r1)
        d0 = deg(r0)
        q = [0] * (d0 - d1 + 1)
        rem = r0[:]
        lc1 = r1[d1]
        for k in range(d0 - d1, -1, -1):
            coef = rem[d1 + k]
            q[k] = gf_mul(coef, gf_inv(lc1, degree, modulus), degree, modulus)
            if q[k]:
                for i in range(d1 + 1):
                    rem[i + k] ^= gf_mul(q[k], r1[i], degree, modulus)
        # u0 -= q*u1
        nu = [0] * (deg(u1) + len(q))
        for i, a in enumerate(u1):
            for k, c in enumerate(q):
                nu[i + k] ^= gf_mul(a, c, degree, modulus)
        newu = u0 + [0] * max(0, len(nu) - len(u0))
        for i, a in enumerate(nu):
            newu[i] ^= a
        r0, r1 = r1, trim(rem)
        u0, u1 = u1, trim(newu)
    omega = trim(r1[:])
    sigma = trim(u1[:])
    errs = {}
    for j in range(min(L, m)):
        xj = gf_pow(primitive, (-j) % L, degree, modulus)
        sv = 0
        for i in range(len(sigma) - 1, -1, -1):
            sv = gf_mul(sv, xj, degree, modulus) ^ sigma[i]
        if sv == 0:
            wv = 0
            for i in range(len(omega) - 1, -1, -1):
                wv = gf_mul(wv, xj, degree, modulus) ^ omega[i]
            dv = 0
            for i in range(1, len(sigma), 2):
                dv ^= gf_mul(sigma[i], gf_pow(xj, i - 1, degree, modulus), degree, modulus)
            errs[j] = gf_mul(wv, gf_inv(dv, degree, modulus), degree, modulus)
    return errs, sigma, omega
