"""Replay the recovered k=35 failing pattern under several salts/seeds.

Uses the official verifier's `shots=` hook so the decoded input is fixed while the
HMR/R coin seed changes. Reports phase errors per run.
"""
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
    syn = np.array(pat["syndrome"], dtype=np.int64)[None, :].repeat(N, axis=0)
    # mbuc: the recorded full 4095 array is in failures.json
    fail = json.load(open(ART / "failures.json"))[0]
    mbuc = np.array(fail["mbuc"], dtype=np.int64)[None, :].repeat(N, axis=0)
    phases = np.array([pat["phase"]], dtype=bool).repeat(N)
    print("pattern k=%d expected_phase=%s syndrome[:4]=%s" % (pat["k"], pat["phase"], syn[0][:4]), flush=True)
    c = km.Circuit.from_file(CIRC)
    spec = V.ProblemSpecDQI(m=4095, n=70, degree=12, r=2016, num_shots=N)
    results = []
    def one(tag, **kw):
        try:
            r = V.verify(c, spec, batch_size=N, shots=(syn, mbuc, phases), **kw)
            rec = {"tag": tag, "value_errors": r["value_errors"], "phase_errors": r["phase_errors"],
                   "meanT": r["toffoli_count"], "score": r["score"]}
        except AssertionError as ex:
            msg = str(ex)
            rec = {"tag": tag, "raised": msg}
        results.append(rec)
        print(json.dumps(rec), flush=True)

    for salt in ("rp-a", "rp-b", "rp-c"):
        one("salt:" + salt, salt=salt)
    for seed in (12345, 999, 424242):
        one("seed:%d" % seed, seed=seed)
    (ART / "boundary_replay.json").write_text(json.dumps(results, indent=1) + "\n")
    print("DONE")


if __name__ == "__main__":
    main()
