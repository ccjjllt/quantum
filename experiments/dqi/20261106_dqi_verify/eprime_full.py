"""Full e' readout: query every (position, bit) of the failing syndrome and rebuild
the circuit's internal error pattern from the MBUC phase channel."""
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
CIRC = "/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi891.kmx"
RD = ROOT / "experiments/dqi/20261106_dqi_verify/verify_readout.py"
CHUNK = 4096  # shots per verify call (16 batches of 256)


def load_rd():
    spec = importlib.util.spec_from_file_location("rd_dqi", RD)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["rd_dqi"] = mod
    spec.loader.exec_module(mod)
    return mod


def main():
    rd = load_rd()
    pat = json.load(open(ART / "failing_pattern.json"))
    syn1 = np.array(pat["syndrome"], dtype=np.int64)
    c = km.Circuit.from_file(CIRC)
    spec = rd.ProblemSpecDQI(m=4095, n=70, degree=12, r=2016, num_shots=CHUNK)
    queries = [(p, k) for p in range(4095) for k in range(12)]
    eprime = {}
    done = 0
    for start in range(0, len(queries), CHUNK):
        part = queries[start:start + CHUNK]
        n = CHUNK
        mbuc = np.zeros((n, 4095), dtype=np.int64)
        for i, (p, k) in enumerate(part):
            mbuc[i, p] = 1 << k
        phases = np.zeros(n, dtype=bool)
        syn = syn1[None, :].repeat(n, axis=0)
        try:
            rd.verify(c, spec, salt="readout", batch_size=256, shots=(syn, mbuc, phases))
        except AssertionError:
            pass
        fails = set(json.load(open(ART / "readout_failures.json")))
        for i, (p, k) in enumerate(part):
            if i in fails:
                eprime[p] = eprime.get(p, 0) | (1 << k)
        done += len(part)
        print("readout %d/%d positions, nonzero e' so far: %d" %
              (done // 12, 4095, sum(1 for v in eprime.values() if v)), flush=True)
    # full e' vector
    e = [eprime.get(p, 0) for p in range(4095)]
    nz = [(p, v) for p, v in enumerate(e) if v]
    # check syndrome consistency
    tables = rd.FieldTables(km.GF2Field(12))
    log, antilog, order = tables.log, tables.antilog, tables.order
    rows = np.arange(1, 71, dtype=np.int64)[:, None]
    pos = np.array([p for p, _ in nz], dtype=np.int64)
    vals = np.array([v for _, v in nz], dtype=np.int64)
    if len(nz):
        exps = (log[vals][None, :] + rows * pos[None, :]) % order
        syn_e = np.bitwise_xor.reduce(antilog[exps], axis=1)
        consistent = bool(np.array_equal(syn_e, syn1))
    else:
        consistent = False
    true_pos = set(pat["pos"])
    out = {"n_positions": 4095, "weight": len(nz), "syndrome_consistent": consistent,
           "matches_true_positions": sorted(set(pos.tolist()) & true_pos) if len(nz) else [],
           "true_weight": 35,
           "eprime": {str(p): int(v) for p, v in nz}}
    (ART / "eprime_full.json").write_text(json.dumps(out, indent=1) + "\n")
    print("e' weight:", len(nz), "syndrome consistent:", consistent,
          "true-position overlap:", len(set(pos.tolist()) & true_pos) if len(nz) else 0)


if __name__ == "__main__":
    main()
