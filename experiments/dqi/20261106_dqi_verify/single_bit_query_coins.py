"""Is the single-bit M query phase coin-independent? Test a few true positions x seeds."""
import json
import sys
from pathlib import Path

import numpy as np

VER = Path("/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dqi/data/competition/verifiers")
sys.path.insert(0, str(VER))
import kickmix as km  # noqa: E402

ROOT = Path("/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dqi")
ART = ROOT / "artifacts" / "20261106_dqi_verify"
REF = "/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/ref_dqi.kmb"


def bits_of(values, width):
    v = np.asarray(values, dtype=np.int64)
    flat = np.array([(int(x) >> k) & 1 for x in v for k in range(width)], dtype=bool)
    return flat[:, None]


def main():
    pat = json.load(open(ART / "failing_pattern.json"))
    c = km.Circuit.from_file(REF)
    regs = c.register_data
    syn = km.array([q for i in range(70) for q in regs["S%d" % i]])
    mb = km.array([b for j in range(4095) for b in regs["E%d" % j]])
    true = dict(zip(pat["pos"], pat["vals"]))
    tests = []
    for p in (3567, 2076, 28):
        for k in (0, 5):
            tests.append((p, k))
    res = {}
    for (p, k) in tests:
        mbuc = np.zeros(4095, dtype=np.int64)
        mbuc[p] = 1 << k
        expected = bool((true[p] >> k) & 1)
        row = {}
        for seed in (1, 777, 12345):
            sim = km.Simulator(batch_size=1, debug_print=False, seed=seed)
            sim.clear_for_shot()
            sim.use_same_registers_as(c)
            sim.write_across_shots(syn, bits_of(pat["syndrome"], 12))
            sim.write_across_shots(mb, bits_of(mbuc, 12))
            sim.do(c)
            row[seed] = bool(sim.read_phase_flipped_across_shots()[0])
        res["p%d_k%d" % (p, k)] = {"expected": expected, "phase": row}
        print("p=%-5d k=%d expected=%s  phases=%s" % (p, k, expected, row), flush=True)
    (ART / "single_bit_query_coins.json").write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main()
