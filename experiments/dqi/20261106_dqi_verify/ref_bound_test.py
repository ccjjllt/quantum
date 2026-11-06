"""Test the bounded-distance reference circuit on the failing pattern and random patterns."""
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
CIRC = "/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/ref_bound.kmb"
N = 256


def bits_of(values, width):
    v = np.asarray(values, dtype=np.int64)
    flat = np.array([(int(x) >> k) & 1 for x in v for k in range(width)], dtype=bool)
    return flat[:, None]


def main():
    pat = json.load(open(ART / "failing_pattern.json"))
    fail = json.load(open(ART / "failures.json"))[0]
    c = km.Circuit.from_file(CIRC)
    print("circuit qubits", c.num_qubits, "toffolis", c.operation_statistics().num_toffoli_like, flush=True)
    spec = V.ProblemSpecDQI(m=4095, n=70, degree=12, r=2016, num_shots=N)
    syn = np.array(pat["syndrome"], dtype=np.int64)[None, :].repeat(N, axis=0)
    mbuc = np.array(fail["mbuc"], dtype=np.int64)[None, :].repeat(N, axis=0)
    phases = np.array([pat["phase"]], dtype=bool).repeat(N)
    try:
        r = V.verify(c, spec, salt="bound-a", batch_size=N, shots=(syn, mbuc, phases))
        rec = {"failing_pattern": {"value_errors": r["value_errors"], "phase_errors": r["phase_errors"]}}
    except AssertionError as ex:
        rec = {"failing_pattern_raised": str(ex)}
    print(json.dumps(rec), flush=True)

    # random weight-35 patterns
    tables = V.FieldTables(km.GF2Field(12))
    rng = np.random.default_rng(4242)
    maxv = 4095
    rows = np.arange(1, 71, dtype=np.int64)[:, None]
    syn2 = np.zeros((N, 70), dtype=np.int64)
    mbuc2 = rng.integers(0, maxv, size=(N, 4095), endpoint=True, dtype=np.int64)
    ph2 = np.zeros(N, dtype=bool)
    for shot in range(N):
        pos = rng.choice(4095, size=35, replace=False)
        vals = rng.integers(1, maxv, size=35, endpoint=True, dtype=np.int64)
        exps = (tables.log[vals][None, :] + rows * pos[None, :]) % tables.order
        syn2[shot] = np.bitwise_xor.reduce(tables.antilog[exps], axis=1)
        ph2[shot] = sum(int(x).bit_count() for x in vals & mbuc2[shot, pos]) & 1 == 1
    try:
        r2 = V.verify(c, spec, salt="bound-b", batch_size=N, shots=(syn2, mbuc2, ph2))
        rec["random_w35"] = {"value_errors": r2["value_errors"], "phase_errors": r2["phase_errors"]}
    except AssertionError as ex:
        rec["random_w35_raised"] = str(ex)
    print(json.dumps(rec.get("random_w35", rec.get("random_w35_raised"))), flush=True)
    (ART / "ref_bound_test.json").write_text(json.dumps(rec, indent=1) + "\n")


if __name__ == "__main__":
    main()
