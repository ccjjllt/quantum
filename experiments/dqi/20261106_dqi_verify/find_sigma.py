"""Locate sigma/omega registers in the submission circuit by prefix simulation + matching."""
import io
import json
import sys
from pathlib import Path

import numpy as np

VER = Path("/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dqi/data/competition/verifiers")
sys.path.insert(0, str(VER))
import kickmix as km  # noqa: E402
from dqi import verify_submission_dqi as V  # noqa: E402

ROOT = Path("/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dqi")
ART = ROOT / "artifacts" / "20261106_dqi_verify"
KMX = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi891.kmx")


def bm_coeffs(S, tables):
    log, antilog, order = tables.log, tables.antilog, tables.order

    def mul(a, b):
        if a == 0 or b == 0:
            return 0
        return int(antilog[(int(log[a]) + int(log[b])) % order])

    def inv(a):
        return int(antilog[(-int(log[a])) % order])

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
    return C[:L + 1], L


def main():
    tables = V.FieldTables(km.GF2Field(12))
    pat = json.load(open(ART / "failing_pattern.json"))
    S = list(map(int, pat["syndrome"]))
    sigma, L = bm_coeffs(S, tables)
    print("sigma degree", L, "coeffs[:6]", sigma[:6], flush=True)
    # distinctive coefficients
    targets = [(i, sigma[i]) for i in range(len(sigma)) if sigma[i] not in (0, 1)]
    print("distinct targets:", targets[:6], flush=True)

    fracs = [int(x) for x in (sys.argv[1:] or ["29000000"])]
    c0 = km.Circuit.from_file(KMX)
    n_ops = len(c0)
    regs = c0.register_data
    syn_arr = km.array([q for i in range(70) for q in regs["S%d" % i]])
    syn_vals = np.array(pat["syndrome"], dtype=np.int64)
    bits = np.array([(int(x) >> k) & 1 for x in syn_vals for k in range(12)], dtype=bool)[:, None]
    tmp = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/sigma_prefix.kmx")
    for stop in fracs:
        stop = min(stop, n_ops)
        with open(KMX) as f, open(tmp, "w") as out:
            n = 0
            for line in f:
                if line.startswith(("APPEND", "REGISTER")):
                    out.write(line)
                else:
                    if n >= stop:
                        break
                    out.write(line)
                    n += 1
        c = km.Circuit.from_file(tmp)
        sim = km.Simulator(batch_size=1, debug_print=False, seed=777)
        sim.clear_for_shot()
        sim.use_same_registers_as(c)
        sim.write_across_shots(syn_arr, bits)
        sim.do(c)
        qs = sim.read_within_shot(km.array([km.q(i) for i in range(c.num_qubits)]), shot_index=0).astype(np.int64)
        def rev12(v):
            r = 0
            for k in range(12):
                if (v >> k) & 1:
                    r |= 1 << (11 - k)
            return r
        vals = []
        for start in range(0, len(qs) - 11):
            v = 0
            for k in range(12):
                if qs[start + k]:
                    v |= 1 << k
            vals.append(v)
        best = None
        for variant, sig in (("plain", sigma), ("rev", [rev12(x) for x in sigma]),
                             ("revorder", list(reversed(sigma)))):
            for stride in (12, -12):
                for start in range(0, len(vals)):
                    run = 0
                    for j in range(len(sig)):
                        p2 = start + stride * j
                        if p2 < 0 or p2 >= len(vals):
                            break
                        if vals[p2] != sig[j]:
                            break
                        run += 1
                    if run >= 3 and (best is None or run > best[1]):
                        best = (variant, run, start, stride)
        print("stop %d qubits %d best-run %s" % (stop, c.num_qubits, best), flush=True)


if __name__ == "__main__":
    main()
