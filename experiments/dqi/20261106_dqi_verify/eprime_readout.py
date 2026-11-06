"""Read out the circuit's internal error values e' through the MBUC phase channel.

For position p and bit k, set M_p = 2^k and all other M = 0.  The circuit's phase
flip then equals bit k of its internal e'_p.  Compare with the true error values.
"""
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
INSTR = ROOT / "experiments/dqi/20261106_dqi_verify/verify_instrumented.py"


def load_instr():
    spec = importlib.util.spec_from_file_location("vi_dqi", INSTR)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["vi_dqi"] = mod
    spec.loader.exec_module(mod)
    return mod


def main():
    pat = json.load(open(ART / "failing_pattern.json"))
    pos = np.array(pat["pos"], dtype=np.int64)
    vals = np.array(pat["vals"], dtype=np.int64)
    syn1 = np.array(pat["syndrome"], dtype=np.int64)
    queries = [(int(p), k) for p in pos for k in range(12)]
    N = 512
    mbuc = np.zeros((N, 4095), dtype=np.int64)
    phases = np.zeros(N, dtype=bool)
    true_of_shot = {}
    for i, (p, k) in enumerate(queries):
        mbuc[i, p] = 1 << k
        bit = (int(vals[i // 12]) >> k) & 1
        phases[i] = bool(bit)
        true_of_shot[i] = bit
    # padding
    for i in range(len(queries), N):
        mbuc[i] = mbuc[0]
        phases[i] = phases[0]
    syn = syn1[None, :].repeat(N, axis=0)
    vi = load_instr()
    c = km.Circuit.from_file(CIRC)
    spec = vi.ProblemSpecDQI(m=4095, n=70, degree=12, r=2016, num_shots=N)
    try:
        r = vi.verify(c, spec, salt="readout-a", batch_size=256, shots=(syn, mbuc, phases))
        rec = {"value_errors": r["value_errors"], "phase_errors": r["phase_errors"]}
    except AssertionError as ex:
        rec = {"raised": str(ex)}
    print(json.dumps(rec), flush=True)
    fails = json.load(open(ART / "failures.json"))
    fail_shots = {int(f["shot"]) for f in fails}
    # reconstruct e' for the queried positions
    eprime = {}
    for i, (p, k) in enumerate(queries):
        actual = bool(true_of_shot[i]) ^ (i in fail_shots)
        eprime.setdefault(p, 0)
        if actual:
            eprime[p] |= 1 << k
    rows = []
    for p in pos.tolist():
        true_v = int(vals[list(pos).index(p)])
        e_v = eprime.get(p, 0)
        rows.append({"pos": p, "true": true_v, "read": e_v, "match": true_v == e_v})
    nmatch = sum(1 for r in rows if r["match"])
    print("positions read: %d, exact matches: %d" % (len(rows), nmatch))
    for r in rows[:12]:
        print("  p=%-5d true=%-5d read=%-5d %s" % (r["pos"], r["true"], r["read"], "OK" if r["match"] else "DIFF"))
    out = {"queries": len(queries), "n_positions": len(rows), "exact_matches": nmatch, "rows": rows}
    (ART / "eprime_readout.json").write_text(json.dumps(out, indent=1) + "\n")
    print("wrote", ART / "eprime_readout.json")


if __name__ == "__main__":
    main()
