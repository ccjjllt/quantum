"""Random boundary-weight test of a reference decoder at (m,n,b)."""
import json
import sys
from pathlib import Path

import numpy as np

VER = Path("/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dqi/data/competition/verifiers")
sys.path.insert(0, str(VER))
import kickmix as km  # noqa: E402
from dqi import verify_submission_dqi as V  # noqa: E402


def main():
    m, n, b = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    k = int(sys.argv[4])
    N = int(sys.argv[5])
    circ = sys.argv[6]
    tables = V.FieldTables(km.GF2Field(b))
    log, antilog, order = tables.log, tables.antilog, tables.order
    rows = np.arange(1, n + 1, dtype=np.int64)[:, None]
    maxv = (1 << b) - 1
    rng = np.random.default_rng(11)
    pos = np.array([rng.choice(m, size=k, replace=False) for _ in range(N)])
    vals = rng.integers(1, maxv, size=(N, k), endpoint=True, dtype=np.int64)
    mbuc = rng.integers(0, maxv, size=(N, m), endpoint=True, dtype=np.int64)
    syn = np.zeros((N, n), dtype=np.int64)
    ph = np.zeros(N, dtype=bool)
    for i in range(N):
        exps = (log[vals[i]][None, :] + rows * pos[i][None, :]) % order
        syn[i] = np.bitwise_xor.reduce(antilog[exps], axis=1)
        ph[i] = sum(int(x).bit_count() for x in vals[i] & mbuc[i, pos[i]]) & 1 == 1
    c = km.Circuit.from_file(circ)
    regs = c.register_data
    syn_arr = km.array([q for i in range(n) for q in regs["S%d" % i]])
    mb_arr = km.array([bb for j in range(m) for bb in regs["E%d" % j]])
    bs = 256
    fails = 0
    for start in range(0, N, bs):
        kk = min(bs, N - start)
        ss = syn[start:start + bs]
        mm = mbuc[start:start + bs]
        pp = ph[start:start + bs]
        pad = bs - kk
        if pad:
            ss = np.vstack([ss, np.zeros((pad, n), dtype=np.int64)])
            mm = np.vstack([mm, np.zeros((pad, m), dtype=np.int64)])
            pp = np.concatenate([pp, np.zeros(pad, dtype=bool)])
        sim = km.Simulator(batch_size=bs, debug_print=False, seed=123)
        sim.clear_for_shot()
        sim.use_same_registers_as(c)
        sb = np.stack([(ss[:, i] >> x) & 1 for i in range(n) for x in range(b)], axis=0)
        mb_ = np.stack([(mm[:, j] >> x) & 1 for j in range(m) for x in range(b)], axis=0)
        sim.write_across_shots(syn_arr, sb.astype(bool))
        sim.write_across_shots(mb_arr, mb_.astype(bool))
        sim.do(c)
        pf = sim.read_phase_flipped_across_shots()
        for i in range(kk):
            if bool(pf[i]) != bool(pp[i]):
                fails += 1
    print("m=%d n=%d b=%d k=%d samples=%d failures=%d" % (m, n, b, k, N, fails))


if __name__ == "__main__":
    main()
