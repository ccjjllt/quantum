"""Map the Proos-Zalka degree registers by running the debug reference circuit on
patterns with known classical EEA degrees (k = 5, 20, 35)."""
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
CIRC = "/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/ref_dbg.kmb"


def bits_of(values, width):
    v = np.asarray(values, dtype=np.int64)
    flat = np.array([(int(x) >> k) & 1 for x in v for k in range(width)], dtype=bool)
    return flat[:, None]


def main():
    tables = V.FieldTables(km.GF2Field(12))
    log, antilog, order = tables.log, tables.antilog, tables.order
    rows = np.arange(1, 71, dtype=np.int64)[:, None]
    rng = np.random.default_rng(2026)
    pats = {}
    for k in (5, 20, 35):
        pos = rng.choice(4095, size=k, replace=False)
        vals = rng.integers(1, 4095, size=k, endpoint=True, dtype=np.int64)
        exps = (log[vals][None, :] + rows * pos[None, :]) % order
        syn = np.bitwise_xor.reduce(antilog[exps], axis=1)
        mbuc = rng.integers(0, 4095, size=4095, endpoint=True, dtype=np.int64)
        phase = sum(int(x).bit_count() for x in vals & mbuc[pos]) & 1 == 1
        pats[k] = {"syndrome": syn.tolist(), "mbuc": mbuc.tolist(), "phase": bool(phase)}
    pats[35]["syndrome"] = json.load(open(ART / "failing_pattern.json"))["syndrome"]
    pats[35]["phase"] = False

    c = km.Circuit.from_file(CIRC)
    regs = c.register_data
    syn_arr = km.array([q for i in range(70) for q in regs["S%d" % i]])
    mb_arr = km.array([b for j in range(4095) for b in regs["E%d" % j]])
    out = {}
    for k, pat in pats.items():
        sim = km.Simulator(batch_size=1, debug_print=True, seed=777)
        sim.clear_for_shot()
        sim.use_same_registers_as(c)
        sim.write_across_shots(syn_arr, bits_of(pat["syndrome"], 12))
        sim.write_across_shots(mb_arr, bits_of(pat["mbuc"], 12))
        print("=== pattern k=%d syndrome[0:3]=%s" % (k, pat["syndrome"][:3]), flush=True)
        sim.do(c)
        ph = bool(sim.read_phase_flipped_across_shots()[0])
        print("k=%d phase=%s expected=%s" % (k, ph, pat["phase"]), flush=True)
        out[k] = {"phase": ph, "expected": pat["phase"]}
    (ART / "degree_map.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
