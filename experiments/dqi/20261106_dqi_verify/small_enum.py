"""Small-scale (m=7,n=4,b=3): enumerate weight-2 patterns and find reference failures."""
import itertools
import json
import sys
from pathlib import Path

import numpy as np

VER = Path("/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dqi/data/competition/verifiers")
sys.path.insert(0, str(VER))
import kickmix as km  # noqa: E402
from dqi import verify_submission_dqi as V  # noqa: E402

REF = "/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/ref_small.kmb"
OUT = Path("/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dqi/artifacts/20261106_dqi_verify")


def main():
    m, n, b = 7, 4, 3
    gf = km.GF2Field(b)
    tables = V.FieldTables(gf)
    log, antilog, order = tables.log, tables.antilog, tables.order
    rows = np.arange(1, n + 1, dtype=np.int64)[:, None]
    rng = np.random.default_rng(4)
    pats = []
    for k in (1, 2):
        for pos in itertools.combinations(range(m), k):
            for vals in itertools.product(range(1, 8), repeat=k):
                pats.append((pos, vals))
    N = len(pats)
    print("patterns:", N, flush=True)
    mbuc = rng.integers(0, 7, size=(N, m), endpoint=True, dtype=np.int64)
    syn = np.zeros((N, n), dtype=np.int64)
    ph = np.zeros(N, dtype=bool)
    for i, (pos, vals) in enumerate(pats):
        pos_a = np.array(pos, dtype=np.int64)
        vals_a = np.array(vals, dtype=np.int64)
        exps = (log[vals_a][None, :] + rows * pos_a[None, :]) % order
        syn[i] = np.bitwise_xor.reduce(antilog[exps], axis=1)
        ph[i] = sum(int(x).bit_count() for x in vals_a & mbuc[i, pos_a]) & 1 == 1
    c = km.Circuit.from_file(REF)
    fails = []
    bs = 256
    for start in range(0, N, bs):
        sub_syn = syn[start:start + bs]
        sub_mb = mbuc[start:start + bs]
        sub_ph = ph[start:start + bs]
        k = len(sub_syn)
        if k < bs:
            pad = bs - k
            sub_syn = np.vstack([sub_syn, np.zeros((pad, n), dtype=np.int64)])
            sub_mb = np.vstack([sub_mb, np.zeros((pad, m), dtype=np.int64)])
            sub_ph = np.concatenate([sub_ph, np.zeros(pad, dtype=bool)])
        sim = km.Simulator(batch_size=bs, debug_print=False, seed=999)
        sim.clear_for_shot()
        sim.use_same_registers_as(c)
        regs = c.register_data
        syn_arr = km.array([q for i in range(n) for q in regs["S%d" % i]])
        mb_arr = km.array([bb for j in range(m) for bb in regs["E%d" % j]])
        syn_bits = np.stack([(sub_syn[:, i] >> kk) & 1 for i in range(n) for kk in range(b)], axis=1).astype(bool)
        mb_bits = np.stack([(sub_mb[:, j] >> kk) & 1 for j in range(m) for kk in range(b)], axis=1).astype(bool)
        sim.write_across_shots(syn_arr, syn_bits.T)
        sim.write_across_shots(mb_arr, mb_bits.T)
        sim.do(c)
        pf = sim.read_phase_flipped_across_shots()
        for i in range(min(bs, k)):
            if bool(pf[i]) != bool(sub_ph[i]):
                fails.append((start + i, pats[start + i]))
    print("failures:", len(fails), flush=True)
    for f in fails[:10]:
        print("  ", f, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "small_failures.json").write_text(json.dumps(
        {"m": m, "n": n, "b": b, "patterns": N, "failures": [{"idx": i, "pos": list(p), "vals": list(v)} for i, (p, v) in fails]},
        indent=1) + "\n")


if __name__ == "__main__":
    main()
