"""Simulate the debug-print reference circuit on the failing shot and dump degree registers."""
import json
import sys
from pathlib import Path

import numpy as np

VER = Path("/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dqi/data/competition/verifiers")
sys.path.insert(0, str(VER))
import kickmix as km  # noqa: E402

ROOT = Path("/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dqi")
ART = ROOT / "artifacts" / "20261106_dqi_verify"
CIRC = "/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/ref_dbg.kmb"


def bits_of(values, width):
    v = np.asarray(values, dtype=np.int64)
    # shape (len(values)*width, 1): index order matches the concatenated registers
    flat = np.array([(int(x) >> k) & 1 for x in v for k in range(width)], dtype=bool)
    return flat[:, None]


def main():
    pat = json.load(open(ART / "failing_pattern.json"))
    fail = json.load(open(ART / "failures.json"))[0]
    c = km.Circuit.from_file(CIRC)
    regs = c.register_data
    print("registers", len(regs), "qubits", c.num_qubits, flush=True)
    syn = km.array([q for i in range(70) for q in regs["S%d" % i]])
    mb = km.array([b for j in range(4095) for b in regs["E%d" % j]])
    sim = km.Simulator(batch_size=1, debug_print=True, seed=12345)
    sim.clear_for_shot()
    sim.use_same_registers_as(c)
    sim.write_across_shots(syn, bits_of(pat["syndrome"], 12))
    sim.write_across_shots(mb, bits_of(fail["mbuc"], 12))
    sim.do(c)
    ph = sim.read_phase_flipped_across_shots()
    print("phase_flipped", ph, "expected", pat["phase"], flush=True)


if __name__ == "__main__":
    main()
