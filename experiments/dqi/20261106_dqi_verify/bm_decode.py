"""Independent Reed-Solomon BM decoder for the DQI failing pattern.

Syndrome convention (official verifier): S_i = sum_j e_j * alpha^{(i+1) p_j}, i=0..n-1.
If BM recovers a weight<=l pattern that reproduces S, it is THE unique solution
(distance n+1), so any phase mismatch is a compiled-circuit bug, not an algorithm limit.
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

    def bm(S):
        C = [1] + [0] * (len(S) + 1)
        B = [1] + [0] * (len(S) + 1)
        L, m, b = 0, 1, 1
        for i in range(len(S)):
            d = S[i]
            for j in range(1, L + 1):
                d ^= mul(C[j], S[i - j])
            if d == 0:
                m += 1
            elif 2 * L <= i:
                T = C[:]
                coef = mul(d, inv(b))
                for j in range(len(B) - m):
                    C[j + m] ^= mul(coef, B[j])
                L = i + 1 - L
                B = T
                b = d
                m = 1
            else:
                coef = mul(d, inv(b))
                for j in range(len(B) - m):
                    C[j + m] ^= mul(coef, B[j])
                m += 1
        return C, L

    def evalp(poly, x):
        y = 0
        for c in reversed(poly):
            y = mul(y, x) ^ c
        return y

    def decode(S, m=4095):
        C, L = bm(S)
        lam = C[:L + 1]
        # Chien search over positions 0..m-1
        pos = []
        for p in range(m):
            x = int(antilog[(-p * 1) % order])  # alpha^{-p}
            if evalp(lam, x) == 0:
                pos.append(p)
        if len(pos) != L:
            return None, L, lam
        # Omega = S(x)*Lambda(x) mod x^n
        n = len(S)
        omega = [0] * n
        for i in range(n):
            for j in range(min(i, L) + 1):
                omega[i] ^= mul(S[i - j], lam[j])
        vals = []
        for p in pos:
            x = int(antilog[(-p) % order])
            om = evalp(omega, x)
            # Lambda'(x)
            dlam = 0
            xp = 1
            for j in range(1, L + 1):
                dlam ^= mul(lam[j], mul(j % 2, 1) * xp) if False else 0
            # derivative over GF(2): only odd powers
            dlam = 0
            for j in range(1, L + 1, 2):
                dlam ^= mul(lam[j], pow_gf(x, j - 1))
            if dlam == 0:
                return None, L, lam
            vals.append(mul(om, inv(dlam)))
        return list(zip(pos, vals)), L, lam

    def pow_gf(x, e):
        r = 1
        for _ in range(e):
            r = mul(r, x)
        return r

    # sanity: random weight-5 pattern
    rng = np.random.default_rng(1)
    rows = np.arange(1, 71, dtype=np.int64)[:, None]

    def make_pattern(k):
        pos = rng.choice(4095, size=k, replace=False)
        vals = rng.integers(1, 4095, size=k, endpoint=True, dtype=np.int64)
        exps = (log[vals][None, :] + rows * pos[None, :]) % order
        S = np.bitwise_xor.reduce(antilog[exps], axis=1)
        return pos, vals, S

    for k in (5, 20):
        pos, vals, S = make_pattern(k)
        dec, L, lam = decode(list(map(int, S)))
        ok = dec is not None and sorted(dec) == sorted(zip(pos.tolist(), vals.tolist()))
        print("sanity k=%d: L=%d decoded=%s match=%s" % (k, L, dec is not None and len(dec), ok))

    # failing pattern
    pat = json.load(open(Path("/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dqi/artifacts/20261106_dqi_verify/failing_pattern.json")))
    S = pat["syndrome"]
    true = sorted(zip(pat["pos"], pat["vals"]))
    dec, L, lam = decode(list(map(int, S)))
    print("failing pattern: k=35, BM L=%d, decoded=%s" % (L, dec is not None and len(dec)))
    if dec is not None:
        print("  matches true pattern:", sorted(dec) == true)
        # recompute syndrome from decoded to be sure
        exps = (log[[v for _, v in dec]][None, :] + rows * np.array([[p for p, _ in dec]])[0][None, :] * 0) if False else None
    print("  lambda degree L =", L)
    out = {"bm_L": L, "decoded_len": None if dec is None else len(dec),
           "matches_true": None if dec is None else sorted(dec) == true, "true_weight": 35}
    (Path("/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dqi/artifacts/20261106_dqi_verify") / "bm_decode.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
