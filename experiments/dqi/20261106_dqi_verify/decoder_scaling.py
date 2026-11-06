"""Measure small BM/EEA reference decoders with the official verifier and project Q^2*T."""
import json
import sys
from pathlib import Path

import numpy as np

VER = Path("/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dqi/data/competition/verifiers")
sys.path.insert(0, str(VER))
import kickmix as km  # noqa: E402
from dqi import verify_submission_dqi as V  # noqa: E402

OUT = Path("/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dqi/artifacts/20261106_dqi_verify")


def run(m, n, b, path, shots=4096):
    c = km.Circuit.from_file(path)
    spec = V.ProblemSpecDQI(m=m, n=n, degree=b, r=V.default_num_accepted_values(b), num_shots=shots)
    try:
        r = V.verify(c, spec, salt="scale", batch_size=256)
        return {"status": r["status"], "T": r["toffoli_count"], "Q": r["num_qubits"],
                "score": r["score"], "phase_errors": r["phase_errors"]}
    except AssertionError as ex:
        return {"raised": str(ex)[:120]}


def main():
    rows = []
    for (m, n, b, path) in [
        (7, 4, 3, "/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/ref_small.kmb"),
        (15, 6, 4, "/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/ref_15.kmb"),
    ]:
        r = run(m, n, b, path)
        if "T" in r:
            r["Q2T"] = r["Q"] ** 2 * r["T"]
        rows.append({"m": m, "n": n, "b": b, **r})
        print(json.dumps(rows[-1]), flush=True)
    # full-scale reference (measured statically) and current submission
    full_Q, full_T = 1893, 5725461
    cur_Q, cur_T = 891, 396904.556
    print(json.dumps({"full_reference": {"Q": full_Q, "T": full_T, "Q2T": full_Q**2*full_T}}, indent=1))
    print(json.dumps({"current_submission": {"Q": cur_Q, "T": cur_T, "Q2T": cur_Q**2*cur_T}}, indent=1))
    print("ratio full_reference/current:", (full_Q**2*full_T)/(cur_Q**2*cur_T))
    (OUT / "decoder_scaling.json").write_text(json.dumps(
        {"small": rows, "full_reference_Q2T": full_Q**2*full_T,
         "current_Q2T": cur_Q**2*cur_T,
         "ratio": (full_Q**2*full_T)/(cur_Q**2*cur_T)}, indent=1) + "\n")


if __name__ == "__main__":
    main()
