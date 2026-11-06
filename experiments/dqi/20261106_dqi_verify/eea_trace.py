"""Classical EEA degree trace for the failing DQI syndrome (GF(2^12)).

Determines which degree sequence reaches 73 and where the unique-decoding bound
(deg sigma <= n/2 = 35) is crossed, to target the circuit's halting register.
"""
import json
import sys
from pathlib import Path

import numpy as np

VER = Path("/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dqi/data/competition/verifiers")
sys.path.insert(0, str(VER))
import kickmix as km  # noqa: E402
from dqi import verify_submission_dqi as V  # noqa: E402


def main():
    tables = V.FieldTables(km.GF2Field(12))
    log, antilog, order = tables.log, tables.antilog, tables.order

    def mul(a, b):
        if a == 0 or b == 0:
            return 0
        return int(antilog[(int(log[a]) + int(log[b])) % order])

    def inv(a):
        return int(antilog[(-int(log[a])) % order])

    def deg(p):
        for i in range(len(p) - 1, -1, -1):
            if p[i]:
                return i
        return -1

    def divmod_poly(a, b):
        a = a[:]
        db = deg(b)
        q = [0] * max(1, deg(a) - db + 1)
        binv = inv(b[db])
        while deg(a) >= db and deg(a) >= 0:
            da = deg(a)
            c = mul(a[da], binv)
            shift = da - db
            q[shift] = c
            for i in range(db + 1):
                a[shift + i] ^= mul(c, b[i])
        return q, a

    pat = json.load(open(Path("/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dqi/artifacts/20261106_dqi_verify/failing_pattern.json")))
    S = list(map(int, pat["syndrome"]))
    n = len(S)
    t = n // 2
    # r0 = x^n, r1 = S(x)
    r0 = [0] * (n + 1)
    r0[n] = 1
    r1 = S[:]
    t0 = [0]
    t1 = [1]
    print("step  deg(r0) deg(r1) deg(t0) deg(t1)")
    for step in range(60):
        print("%3d   %5d  %5d  %5d  %5d" % (step, deg(r0), deg(r1), deg(t0), deg(t1)))
        if deg(r1) < 0:
            break
        q, r = divmod_poly(r0, r1)
        # t = t0 - q*t1
        prod = [0] * (deg(q) + deg(t1) + 2)
        for i, qi in enumerate(q):
            if qi:
                for j, tj in enumerate(t1):
                    if tj:
                        prod[i + j] ^= mul(qi, tj)
        size = max(len(t0), len(prod))
        tnew = [0] * size
        for i in range(size):
            a = t0[i] if i < len(t0) else 0
            b = prod[i] if i < len(prod) else 0
            tnew[i] = a ^ b
        r0, r1 = r1, r
        t0, t1 = t1, tnew
        if deg(r1) != -1 and deg(r1) < t:
            print("=== STOP at deg(r) < %d: deg(sigma)=%d deg(omega)=%d" % (t, deg(t1), deg(r1)))
            break


if __name__ == "__main__":
    main()
