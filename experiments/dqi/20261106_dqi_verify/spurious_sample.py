"""Sample non-true positions for spurious e' values (one 4096-shot chunk)."""
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
N = 4096


def main():
    sm = importlib.util.spec_from_file_location("rd3", RD)
    rd = importlib.util.module_from_spec(sm)
    sys.modules["rd3"] = rd
    sm.loader.exec_module(rd)
    pat = json.load(open(ART / "failing_pattern.json"))
    true_pos = set(pat["pos"])
    rng = np.random.default_rng(55)
    others = [p for p in range(4095) if p not in true_pos]
    pick = rng.choice(len(others), size=341, replace=False)
    positions = [others[i] for i in pick]
    queries = [(p, k) for p in positions for k in range(12)][:N]
    syn1 = np.array(pat["syndrome"], dtype=np.int64)
    mbuc = np.zeros((N, 4095), dtype=np.int64)
    phases = np.zeros(N, dtype=bool)
    for i, (p, k) in enumerate(queries):
        mbuc[i, p] = 1 << k
    syn = syn1[None, :].repeat(N, axis=0)
    c = km.Circuit.from_file(REF)
    spec = rd.ProblemSpecDQI(m=4095, n=70, degree=12, r=2016, num_shots=N)
    try:
        rd.verify(c, spec, salt="spur", batch_size=256, shots=(syn, mbuc, phases))
    except AssertionError as ex:
        print("raised:", str(ex)[:110])
    fails = set(json.load(open(ART / "readout_failures.json")))
    print("queries:", len(queries), "failures:", len(fails))
    eprime = {}
    for i, (p, k) in enumerate(queries):
        if i in fails:
            eprime[p] = eprime.get(p, 0) | (1 << k)
    nz = {p: v for p, v in eprime.items() if v}
    print("sampled positions:", len(positions), "with spurious e':", len(nz))
    for p, v in list(nz.items())[:10]:
        print("  p", p, "e' =", v)
    (ART / "spurious_sample.json").write_text(json.dumps({"n_positions": len(positions), "spurious": {str(p): int(v) for p, v in nz.items()}}, indent=1) + "\n")


if __name__ == "__main__":
    main()
