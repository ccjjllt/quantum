"""Measure the intrinsic weight-35 phase-error rate: random k=35 patterns through the circuit."""
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
NB = int(sys.argv[1]) if len(sys.argv) > 1 else 512
K = 35


def main():
    c = km.Circuit.from_file(CIRC)
    spec = V.ProblemSpecDQI(m=4095, n=70, degree=12, r=2016, num_shots=NB)
    tables = V.FieldTables(km.GF2Field(spec.degree))
    rng = np.random.default_rng(20261106)
    max_value = (1 << spec.degree) - 1
    rows = np.arange(1, spec.n + 1, dtype=np.int64)[:, None]
    mbuc = rng.integers(0, max_value, size=(NB, spec.m), endpoint=True, dtype=np.int64)
    syn = np.zeros((NB, spec.n), dtype=np.int64)
    phases = np.zeros(NB, dtype=bool)
    for shot in range(NB):
        pos = rng.choice(spec.m, size=K, replace=False)
        vals = rng.integers(1, max_value, size=K, endpoint=True, dtype=np.int64)
        exps = (tables.log[vals][None, :] + rows * pos[None, :]) % tables.order
        syn[shot] = np.bitwise_xor.reduce(tables.antilog[exps], axis=1)
        phases[shot] = sum(int(x).bit_count() for x in vals & mbuc[shot, pos]) & 1 == 1
    print("generated", NB, "random weight-%d shots" % K, flush=True)
    res = {}
    for salt in ("w35-a", "w35-b"):
        try:
            r = V.verify(c, spec, salt=salt, batch_size=256, shots=(syn, mbuc, phases))
            res[salt] = {"value_errors": r["value_errors"], "phase_errors": r["phase_errors"],
                         "n": NB}
        except AssertionError as ex:
            msg = str(ex)
            res[salt] = {"raised": msg}
        print(json.dumps({salt: res[salt]}), flush=True)
    (ART / "w35_rate.json").write_text(json.dumps({"n": NB, "k": K, "rexp": res}, indent=1) + "\n")
    print("DONE")


if __name__ == "__main__":
    main()
