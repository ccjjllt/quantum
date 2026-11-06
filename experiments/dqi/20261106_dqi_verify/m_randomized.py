"""Isolate the failing-pattern bug: same syndrome/errors, randomized MBUC M."""
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
CIRC = "/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi891.kmx"
N = 256


def main():
    pat = json.load(open(ART / "failing_pattern.json"))
    pos = np.array(pat["pos"], dtype=np.int64)
    vals = np.array(pat["vals"], dtype=np.int64)
    syn1 = np.array(pat["syndrome"], dtype=np.int64)
    syn = syn1[None, :].repeat(N, axis=0)
    rng = np.random.default_rng(777)
    mbuc = rng.integers(0, 4095, size=(N, 4095), endpoint=True, dtype=np.int64)
    phases = np.array([sum(int(x).bit_count() for x in vals & mbuc[i, pos]) & 1 == 1
                       for i in range(N)], dtype=bool)
    print("fixed syndrome, random M: expected phase true fraction = %.3f" % phases.mean(), flush=True)
    c = km.Circuit.from_file(CIRC)
    spec = V.ProblemSpecDQI(m=4095, n=70, degree=12, r=2016, num_shots=N)
    try:
        r = V.verify(c, spec, salt="mrand-a", batch_size=N, shots=(syn, mbuc, phases))
        rec = {"value_errors": r["value_errors"], "phase_errors": r["phase_errors"], "n": N}
    except AssertionError as ex:
        rec = {"raised": str(ex)}
    print(json.dumps(rec), flush=True)
    (ART / "m_randomized.json").write_text(json.dumps(rec, indent=1) + "\n")


if __name__ == "__main__":
    main()
