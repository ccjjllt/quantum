"""Clean full e' readout with freshness-validated failure files per chunk."""
import importlib.util
import json
import os
import sys
from pathlib import Path

import numpy as np

VER = Path("/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dqi/data/competition/verifiers")
sys.path.insert(0, str(VER))
import kickmix as km  # noqa: E402

ROOT = Path("/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dqi")
ART = ROOT / "artifacts" / "20261106_dqi_verify"
REF = "/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi891.kmx"
RD = ROOT / "experiments/dqi/20261106_dqi_verify/verify_readout.py"
FAILF = ART / "readout_failures.json"
CHUNK = 4096


def main():
    sm = importlib.util.spec_from_file_location("rd4", RD)
    rd = importlib.util.module_from_spec(sm)
    sys.modules["rd4"] = rd
    sm.loader.exec_module(rd)
    pat = json.load(open(ART / "failing_pattern.json"))
    syn1 = np.array(pat["syndrome"], dtype=np.int64)
    true = dict(zip(pat["pos"], pat["vals"]))
    c = km.Circuit.from_file(REF)
    spec = rd.ProblemSpecDQI(m=4095, n=70, degree=12, r=2016, num_shots=CHUNK)
    queries = [(p, k) for p in range(4095) for k in range(12)]
    eprime = {}
    for start in range(0, len(queries), CHUNK):
        part = queries[start:start + CHUNK]
        n = CHUNK
        mbuc = np.zeros((n, 4095), dtype=np.int64)
        for i, (p, k) in enumerate(part):
            mbuc[i, p] = 1 << k
        syn = syn1[None, :].repeat(n, axis=0)
        phases = np.zeros(n, dtype=bool)
        if FAILF.exists():
            FAILF.unlink()
        try:
            rd.verify(c, spec, salt="full2", batch_size=256, shots=(syn, mbuc, phases))
        except AssertionError:
            pass
        if not FAILF.exists():
            print("chunk %d: NO FRESH FAILURE FILE" % start, flush=True)
            continue
        fails = set(json.load(open(FAILF)))
        for i, (p, k) in enumerate(part):
            if i in fails:
                eprime[p] = eprime.get(p, 0) | (1 << k)
        done = min(start + CHUNK, len(queries))
        print("chunk %d/%d nonzeros %d" % (done, len(queries), sum(1 for v in eprime.values() if v)), flush=True)
    nz = {p: v for p, v in eprime.items() if v}
    true_mism = [(p, true[p], nz.get(p, 0)) for p in true if nz.get(p, 0) != true[p]]
    spurious = {p: v for p, v in nz.items() if p not in true}
    print("e' weight:", len(nz), "true mismatches:", len(true_mism), "spurious positions:", len(spurious))
    for p, v in list(spurious.items())[:10]:
        print("  spurious p", p, "e'=", v)
    for r in true_mism[:5]:
        print("  true mismatch", r)
    (ART / "eprime_submission_clean.json").write_text(json.dumps(
        {"weight": len(nz), "true_mismatches": len(true_mism),
         "spurious": {str(p): int(v) for p, v in spurious.items()},
         "nz": {str(p): int(v) for p, v in nz.items()}}, indent=1) + "\n")


if __name__ == "__main__":
    main()
