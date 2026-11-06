"""Coin dependence of the real reference circuit's phase on the failing pattern."""
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
REF = "/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/ref_dqi.kmb"


def bits_of(values, width):
    v = np.asarray(values, dtype=np.int64)
    flat = np.array([(int(x) >> k) & 1 for x in v for k in range(width)], dtype=bool)
    return flat[:, None]


def main():
    pat = json.load(open(ART / "failing_pattern.json"))
    fail = json.load(open(ART / "failures.json"))[0]
    c = km.Circuit.from_file(REF)
    regs = c.register_data
    syn = km.array([q for i in range(70) for q in regs["S%d" % i]])
    mb = km.array([b for j in range(4095) for b in regs["E%d" % j]])
    res = {}
    for seed in (1, 2, 3, 777, 12345, 999):
        sim = km.Simulator(batch_size=1, debug_print=False, seed=seed)
        sim.clear_for_shot()
        sim.use_same_registers_as(c)
        sim.write_across_shots(syn, bits_of(pat["syndrome"], 12))
        sim.write_across_shots(mb, bits_of(fail["mbuc"], 12))
        sim.do(c)
        ph = bool(sim.read_phase_flipped_across_shots()[0])
        res[seed] = ph
        print("seed %-6d phase=%s (expected %s)" % (seed, ph, pat["phase"]), flush=True)
    (ART / "ref_coin_dependence.json").write_text(json.dumps(
        {"seeds": res, "expected": pat["phase"]}, indent=1) + "\n")


if __name__ == "__main__":
    main()
