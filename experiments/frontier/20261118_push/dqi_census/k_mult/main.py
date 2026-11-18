"""Decisive multiply census: how many 12x12 field multiplies does the tape really do?

The two models disagree: one counts 7,661 x 42 CCX (grouping by word triple, target word
included), the other sees only 2,007 full-width >=24-CCX blocks per pass plus 47% partials.
A field multiply `C ^= A*B` writes its 42 ANDs into one or two accumulator words, so grouping
the CCX by the *operand pair* (wa, wb) and summing is the model-free test: a full multiply
must come out as 42 (or 42+42 for a split accumulator), a partial as less.

CPU only, static IR, tape deleted before exit.
"""
import importlib.util
import json
import lzma
import pathlib
import sys
import time
from collections import Counter, defaultdict

import numpy as np

WORK = pathlib.Path("/kaggle/working")
T0 = time.time()
REGIONS = {"fwd": (17_576_206, 30_151_421), "chien": (30_151_421, 35_627_262),
           "rev": (35_627_262, 57_520_821)}


def say(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def find(pattern):
    for p in pathlib.Path("/kaggle/input").rglob(pattern):
        return p
    raise SystemExit(f"missing {pattern}")


ir = load("vqcc_ir", str(find("vqcc_ir.py")))
RAW = WORK / "dqi.kmb"
with lzma.open(find("dqi_575b043f.kmb.xz"), "rb") as fi, open(RAW, "wb") as fo:
    while True:
        b = fi.read(1 << 23)
        if not b:
            break
        fo.write(b)
c = ir.Circuit.read(str(RAW))
say("read", c.num_ops)
t = c.types
ccx = np.flatnonzero((t & 0x7F) == 0x31)
q3 = np.cumsum(ir.L3Q[t])[ccx + 1] - 1
qa = c.qqq0[q3].astype(np.int64)
qb = c.qqq1[q3].astype(np.int64)
qc = c.qqq2[q3].astype(np.int64)
wa, wb, wc = qa // 12, qb // 12, qc // 12
say("ccx", len(ccx))

out = {"n_ccx": int(len(ccx)), "regions": {}}
for rn, (lo, hi) in REGIONS.items():
    m = (ccx >= lo) & (ccx < hi)
    say(rn, int(m.sum()))
    # group by operand pair (unordered) and by operand pair + target word
    pair = defaultdict(int)
    triple = defaultdict(int)
    for a, b, z in zip(wa[m].tolist(), wb[m].tolist(), wc[m].tolist()):
        pair[(min(a, b), max(a, b))] += 1
        triple[(min(a, b), max(a, b), z)] += 1
    ph = Counter(pair.values())
    th = Counter(triple.values())
    out["regions"][rn] = {
        "ccx": int(m.sum()),
        "n_pairs": len(pair),
        "n_triples": len(triple),
        "pair_sum_hist": dict(sorted(ph.items())),
        "triple_sum_hist": dict(sorted(th.items())),
        # a multiply = a pair whose total is 42 or 84 (split accumulator)
        "mults_pair42": int(sum(v // 42 for v in pair.values() if v >= 42)),
        "mults_triple42": int(sum(v // 42 for v in triple.values() if v >= 42)),
        "ccx_in_pairs_ge42": int(sum(v for v in pair.values() if v >= 42)),
        "ccx_in_pairs_lt42": int(sum(v for v in pair.values() if v < 42)),
    }
    say(rn, "pairs", len(pair), "triples", len(triple),
        "mult(pair>=42)", out["regions"][rn]["mults_pair42"],
        "ccx>=42", out["regions"][rn]["ccx_in_pairs_ge42"],
        "ccx<42", out["regions"][rn]["ccx_in_pairs_lt42"])

with open(WORK / "mult_census.json", "w") as f:
    json.dump(out, f, indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "regions"}, indent=1))
for rn, d in out["regions"].items():
    print(rn, {kk: vv for kk, vv in d.items() if kk.endswith("hist") is False})
RAW.unlink()
say("done")
