import sys, pathlib, json, math
import numpy as np

sys.path.insert(0, str(pathlib.Path("/Users/zhaohuaxiang/ccjjllt/quantum/data/competition/verifiers")))
sys.path.insert(0, str(pathlib.Path("/Users/zhaohuaxiang/ccjjllt/quantum/experiments/frontier/20261118_push/invsqrt/k1_rotlp")))
import body  # noqa

WORK = pathlib.Path("/tmp/rotlp_local")
WORK.mkdir(exist_ok=True)
body.WORK = WORK
body.KMB = WORK / "invsqrt.kmb"

import kickmix as km

kmb = pathlib.Path("/Users/zhaohuaxiang/ccjjllt/quantum/artifacts/20261118_inv_sweep/invsqrt_563d0583.kmb")
c = km.Circuit.from_file(str(kmb), format="kmb")
segs, rots = body.split_segments(c)
print("segments", len(segs), "rots", len(rots))
print("first rot", rots[0], "last", rots[-1])
print("qubits", sorted(set(r[0] for r in rots)))
print("seg lens", [len(s) for s in segs][:5], "...", [len(s) for s in segs][-3:])
# check every segment parses as a Circuit and conditionals are balanced
for i, s in enumerate(segs):
    d = 0
    for l in s:
        if l.startswith("PUSH_CONDITION"):
            d += 1
        elif l.startswith("POP_CONDITION"):
            d -= 1
        assert d >= 0, (i, l)
    assert d == 0, (i, d)
    cc = km.Circuit("\n".join(s))
print("all segments parse, conditionals balanced")
print("n fine", sum(1 for r in rots if abs(r[1]) % 0.25 not in (0.0,)))

# ---- LP machinery smoke test with synthetic data (no simulation) ----
rng = np.random.default_rng(7)
n, N = len(rots), 20000
B = (rng.random((n, N)) < 0.5).astype(np.uint8)
w_true = np.array([a / 2.0 for (_, a, _) in rots])
tgt = body.phase_of(w_true, B) + rng.normal(0, 3e-12, N)
tol = np.full(N, 2e-8)
lo_b, hi_b = w_true * 0.9, w_true * 1.1
r = body.lp_full(np.zeros(N), B, tgt, tol, w_true, lo_b, hi_b, np.arange(N)[::-1], iters=8, verbose=True)
print("lp result", None if r is None else (r[1], np.abs(r[0] - w_true).max()))
print("rot_cost", body.rot_cost(int(3.0e7), 33))
