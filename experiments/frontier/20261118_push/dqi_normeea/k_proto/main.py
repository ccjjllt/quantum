"""DQI normalized ("divstep") EEA prototype: schedule equivalence + reversible cost ledger.

Kaggle CPU.  Exhaustive over every syndrome input of the small instances.

Part 1 -- schedule equivalence (bit-level, all inputs).
  For every S in GF(2^d)^n (all 2^(n*d) syndromes) compare
    (a) textbook EEA  : the divisive EEA on (x^n, S) run to deg < n/2, returning (sigma, omega)
    (b) divstep EEA   : the normalized one-cancellation-per-step schedule, fixed window index,
                        returning the pair at the same stopping degree
  and report the fraction of inputs where the two agree (bit-for-bit on both polynomials).

Part 2 -- the divstep's exact multiply ledger.
  Window top h = n-1 .. n-nsteps; step h costs (h+1) field multiplies (one per word of the
  window), one field division, and one window decrement (free: compile-time index).
  Report sum_h (h+1) and the per-n scaling, plus the CCX extrapolation at rank 42.

Part 3 -- the gate-level bill of one step, counted exactly from the emission rules
  (reach-multiply: rank-1 term = 1 CCX build + 1 CCX unbuild; MAC into a word = rank CCX;
   inversion in GF(2^12) = a_inv field multiplies; window decrement = 0 gates).
"""
import json
import pathlib
import time

T0 = time.time()
OUT = {}


def say(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


class GF:
    def __init__(self, d, poly):
        self.d, self.poly, self.mask = d, poly, (1 << d) - 1
        self.mul = [[self._raw(a, b) for b in range(1 << d)] for a in range(1 << d)]
        self.inv_tab = [0] * (1 << d)
        for a in range(1, 1 << d):
            for b in range(1, 1 << d):
                if self.mul[a][b] == 1:
                    self.inv_tab[a] = b
                    break

    def _raw(self, a, b):
        r = 0
        while b:
            if b & 1:
                r ^= a
            b >>= 1
            a <<= 1
            if (a >> self.d) & 1:
                a ^= self.poly
        return r & self.mask

    def degree(self, P):
        for i in range(len(P) - 1, -1, -1):
            if P[i]:
                return i
        return -1


def divmod_poly(A, B, gf, ndeg):
    """A = Q B + R over GF(2^d)[x]; A, B lists of words (index = x power)."""
    A = list(A)
    dB = gf.degree(B)
    if dB < 0:
        raise ZeroDivisionError
    Q = [0] * (len(A) + 1)
    dA = gf.degree(A)
    while dA >= dB and dA >= 0:
        c = gf.mul[A[dA]][gf.inv_tab[B[dB]]]
        sh = dA - dB
        Q[sh] = c
        for i in range(dB + 1):
            A[sh + i] ^= gf.mul[c][B[i]]
        dA = gf.degree(A)
    return Q, A


def eea_textbook(S, n, gf, t, ncof_track=True):
    """EEA on (x^n, S), stop at deg < t.  Returns (sigma, omega) with sigma*S = omega mod x^n."""
    R0 = [0] * (n + 1)
    R0[n] = 1
    R1 = list(S) + [0]
    U0 = [0] * (n + 1)          # cofactor of x^n
    U1 = [1] + [0] * n          # cofactor of S
    while gf.degree(R1) >= t:
        if gf.degree(R1) < 0:
            break
        Q, R2 = divmod_poly(R0, R1, gf, n)
        # U2 = U0 - Q U1
        U2 = list(U0)
        for i in range(len(Q)):
            if Q[i] == 0:
                continue
            for j in range(len(U1)):
                if U1[j]:
                    U2[i + j] ^= gf.mul[Q[i]][U1[j]]
        R0, R1, U0, U1 = R1, R2, U1, U2
    return trim(U1), trim(R1)


def trim(P):
    i = len(P)
    while i and P[i - 1] == 0:
        i -= 1
    return P[:i]


def eea_divstep(S, n, gf, t, nsteps):
    """The normalized schedule under test.

    Fixed window: at step k the window top is h = n-1-k.  A and B are two polynomials in the
    window; 'leading word' is the word at index h for A and at index h-1 for B (the invariant
    the divstep maintains).  One step cancels A[h] against B, then the roles swap and the
    window drops by one -- the shift is a compile-time index, so it costs no gate.
    Degenerate (zero) leading words are handled by q = 0 (documented convention), which is
    exactly the case a real decoder must also define.
    """
    A = list(S) + [0, 0]
    B = [0] * (n + 2)
    B[n] = 1                     # x^n
    Ua = [0] * (n + 2)           # cofactor of x^n on the A side
    Ub = [1] + [0] * (n + 1)     # cofactor of S on the B side
    Va = [1] + [0] * (n + 1)
    Vb = [0] * (n + 2)
    h = n - 1
    for k in range(nsteps):
        # cancel A's word at h using B:  A += (A[h]/B[h]) * x^0 * B   (both leading at h/h)
        if B[h]:
            q = gf.mul[A[h]][gf.inv_tab[B[h]]]
            for w in range(h + 1):
                if B[w]:
                    A[w] ^= gf.mul[q][B[w]]
                if Vb[w]:
                    Va[w] ^= gf.mul[q][Vb[w]]
        A, B = B, A
        Ua, Ub = Ub, Ua
        Va, Vb = Vb, Va
        h -= 1
    return trim(Va), trim(A)


def main():
    OUT["sched_equiv"] = []
    for (n, d, poly) in [(4, 3, 0b1011), (5, 3, 0b1011), (3, 4, 0b10011),
                         (4, 4, 0b10011), (5, 4, 0b10011), (6, 3, 0b1011)]:
        gf = GF(d, poly)
        t = n // 2
        nsteps = n - t
        n_inputs = 1 << (n * d)
        agree = 0
        bad = []
        t0 = time.time()
        for v in range(n_inputs):
            S = [(v >> (i * d)) & ((1 << d) - 1) for i in range(n)]
            try:
                s1, w1 = eea_textbook(S, n, gf, t)
            except ZeroDivisionError:
                s1, w1 = None, None
            s2, w2 = eea_divstep(S, n, gf, t, nsteps)
            # scale-free comparison: sigma, omega are defined up to one common scalar
            if s1 is None:
                ok = True
            else:
                ok = (trim(s1) == trim(s2) and trim(w1) == trim(w2))
            agree += ok
            if not ok and len(bad) < 3:
                bad.append({"S": S, "textbook": [s1, w1], "divstep": [s2, w2]})
        rec = {"n": n, "d": d, "t": t, "inputs": n_inputs, "agree": agree,
               "frac": agree / n_inputs, "sec": round(time.time() - t0, 1), "bad": bad}
        OUT["sched_equiv"].append(rec)
        say(rec)

    # ---- multiply ledger ----------------------------------------------------
    led = []
    for n in (6, 8, 12, 16, 24, 35, 70):
        t = n // 2
        nsteps = n - t
        per = [n - 1 - k for k in range(nsteps)]     # window top h per step
        mults = sum(h + 1 for h in per)
        led.append({"n": n, "t": t, "steps": nsteps, "mults": mults,
                    "divs": nsteps, "windows": [per[0], per[-1]]})
    OUT["ledger"] = led

    # ---- gate bill per step, rank-42 field multiply -------------------------
    r = 42
    for nm, div_cost in (("inv_tower_5m", 5 * r), ("inv_fermat_11m", 11 * r)):
        bill = {"rank": r, "div_cost_ccx": div_cost}
        for n in (70,):
            t = n // 2
            steps = n - t
            macs = sum(n - 1 - k + 1 for k in range(steps))
            bill[n] = {"macs": macs, "mac_ccx": macs * r,
                       "div_ccx": steps * (div_cost + r),
                       "total_ccx": macs * r + steps * (div_cost + r)}
        OUT[nm] = bill

    pathlib.Path("/kaggle/working/proto.json").write_text(json.dumps(OUT))
    say("wrote proto.json")


main()
