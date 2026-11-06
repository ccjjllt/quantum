"""Clean e' readout for the 35 true positions using the lean readout verifier."""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

VER = Path("/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dqi/data/competition/verifiers")
sys.path.insert(0, str(VER))
import kickmix as km  # noqa: E402

ROOT = Path("/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dqi")
ART = ROOT / "artifacts" / "20261106_dqi_verify"
REF = "/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/ref_dqi.kmb"
RD = ROOT / "experiments/dqi/20261106_dqi_verify/verify_readout.py"
N = 512


def main():
    spec_mod = importlib.util.spec_from_file_location("rd2", RD)
    rd = importlib.util.module_from_spec(spec_mod)
    sys.modules["rd2"] = rd
    spec_mod.loader.exec_module(rd)
    pat = json.load(open(ART / "failing_pattern.json"))
    pos = list(pat["pos"])
    vals = list(pat["vals"])
    syn1 = np.array(pat["syndrome"], dtype=np.int64)
    queries = [(p, k) for p in pos for k in range(12)]
    mbuc = np.zeros((N, 4095), dtype=np.int64)
    phases = np.zeros(N, dtype=bool)
    exp = {}
    for i, (p, k) in enumerate(queries):
        mbuc[i, p] = 1 << k
        exp[i] = (int(vals[i // 12]) >> k) & 1
        phases[i] = bool(exp[i])
    for i in range(len(queries), N):
        mbuc[i] = mbuc[0]
        phases[i] = phases[0]
        exp[i] = exp[0]
    syn = syn1[None, :].repeat(N, axis=0)
    c = km.Circuit.from_file(REF)
    spec = rd.ProblemSpecDQI(m=4095, n=70, degree=12, r=2016, num_shots=N)
    try:
        rd.verify(c, spec, salt="readout2", batch_size=256, shots=(syn, mbuc, phases))
    except AssertionError as ex:
        print("raised:", str(ex)[:120])
    fails = set(json.load(open(ART / "readout_failures.json")))
    print("failures:", len(fails), "queries:", len(queries))
    mism = 0
    rows = []
    for i, (p, k) in enumerate(queries):
        actual = bool(exp[i]) ^ (i in fails)
        if actual != bool(exp[i]):
            mism += 1
        rows.append({"p": p, "k": k, "expected": int(exp[i]), "actual": int(actual)})
    print("mismatches vs true e bits:", mism, "/", len(queries))
    for r in rows[:8]:
        print(r)
    (ART / "eprime_clean.json").write_text(json.dumps({"mismatches": mism, "n": len(queries), "rows": rows}, indent=1) + "\n")


if __name__ == "__main__":
    main()
