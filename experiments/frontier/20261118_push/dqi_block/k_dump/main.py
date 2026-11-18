"""One multiply block, op by op: what is the tape's 42-CCX unit actually made of?

Dumps [21,385,877, 21,387,169) - the first block of the 132-block cluster, words (66, 1, 67),
42 CCX - as a symbolic listing with qubit, word (q//12) and bit (q%12) labels, plus a count
census. Tiny output, no simulation. CPU only.
"""
import importlib.util
import json
import lzma
import pathlib
import sys
import time

WORK = pathlib.Path("/kaggle/working")
T0 = time.time()
LO, HI = 21_385_877, 21_387_169


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
xz = find("dqi_575b043f.kmb.xz")
RAW = WORK / "dqi.kmb"
with lzma.open(xz, "rb") as fi, open(RAW, "wb") as fo:
    while True:
        b = fi.read(1 << 23)
        if not b:
            break
        fo.write(b)
c = ir.Circuit.read(str(RAW))
say("read", c.num_ops)

rows = []
t = c.types
L3, L2, L1, LB, LC, LA = ir.L3Q, ir.L2Q, ir.L1Q, ir.L1B, ir.LCOND, ir.LANGLE
i3 = c._before(LO)["qqq0"]
i2 = c._before(LO)["qq0"]
i1 = c._before(LO)["q0"]
ib = c._before(LO)["b0"]
ic = c._before(LO)["bc"]
for k in range(LO, HI):
    ty = int(t[k])
    nm = ir.name(ty)
    q = []
    if L3[ty]:
        q = [int(c.qqq0[i3]), int(c.qqq1[i3]), int(c.qqq2[i3])]
        i3 += 1
    elif L2[ty]:
        q = [int(c.qq0[i2]), int(c.qq1[i2])]
        i2 += 1
    elif L1[ty]:
        q = [int(c.q0[i1])]
        i1 += 1
    bs = []
    if LB[ty]:
        bs.append(int(c.b0[ib]))
        ib += 1
    cond = None
    if LC[ty]:
        cond = int(c.bc[ic])
        ic += 1
    rows.append([k - LO, nm, [[q_, q_ // 12, q_ % 12] for q_ in q], bs, cond])

census = {}
for r in rows:
    census[r[1]] = census.get(r[1], 0) + 1
ccx = [r for r in rows if r[1] == "CCX"]
pairs = sorted((tuple(sorted((r[2][0][0], r[2][1][0]))), r[2][2][0]) for r in ccx)
from collections import Counter
tri = Counter((r[2][0][2], r[2][1][2], r[2][2][2]) for r in ccx)
data = {
    "range": [LO, HI],
    "census": census,
    "n_ccx": len(ccx),
    "ccx_word_triples": Counter((r[2][0][1], r[2][1][1], r[2][2][1]) for r in ccx).most_common(),
    "ccx_bit_triples_top": tri.most_common(12),
    "ccx_bit_triple_distinct": len(tri),
    "ccx_repeated_bit_triples": sum(v - 1 for v in tri.values() if v > 1),
    "xorer_first_ops": rows[:40],
    "rows": rows,
}
with open(WORK / "block_dump.json", "w") as f:
    json.dump(data, f)
print(json.dumps({k: v for k, v in data.items() if k != "rows"}, indent=1))
RAW.unlink()
say("done")
