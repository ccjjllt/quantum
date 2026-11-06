"""Run the official reference decoder (1893q) on the failing k=35 pattern."""
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
N = 256


def main():
    pat = json.load(open(ART / "failing_pattern.json"))
    fail = json.load(open(ART / "failures.json"))[0]
    syn = np.array(pat["syndrome"], dtype=np.int64)[None, :].repeat(N, axis=0)
    mbuc = np.array(fail["mbuc"], dtype=np.int64)[None, :].repeat(N, axis=0)
    phases = np.array([pat["phase"]], dtype=bool).repeat(N)
    c = km.Circuit.from_file(REF)
    print("reference circuit: qubits", c.num_qubits, "ops", len(c), flush=True)
    spec = V.ProblemSpecDQI(m=4095, n=70, degree=12, r=2016, num_shots=N)
    try:
        r = V.verify(c, spec, salt="ref-a", batch_size=N, shots=(syn, mbuc, phases))
        rec = {"value_errors": r["value_errors"], "phase_errors": r["phase_errors"],
               "toffoli": r["toffoli_count"], "qubits": r["num_qubits"]}
    except AssertionError as ex:
        rec = {"raised": str(ex)}
    print(json.dumps(rec), flush=True)
    (ART / "reference_on_failure.json").write_text(json.dumps(rec, indent=1) + "\n")


if __name__ == "__main__":
    main()
