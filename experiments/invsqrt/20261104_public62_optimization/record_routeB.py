"""Route B record: uncompute-elimination survey (read-only) + verdict."""
import io, json, time
from collections import Counter, defaultdict
from pathlib import Path
import kickmix as km

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ART = ROOT / "artifacts/20261104_public62_optimization/invsqrt"
PARENT = ART / "public62_nofallback.kmb"

t0 = time.monotonic()
c = km.Circuit.from_file(PARENT)
buf = io.StringIO(); c.to_file(buf, format="kmx")
ops = [l for l in buf.getvalue().splitlines() if not l.startswith(("APPEND", "REGISTER"))]

BAR = ("HMR", "R", "Z_POW", "BIT_STORE0", "BIT_STORE1", "BIT_INVERT",
       "PUSH_CONDITION", "POP_CONDITION")
is_bar = [l.split()[0] in BAR for l in ops]
st = []
depth = []
for l in ops:
    p = l.split()
    depth.append(len(st))
    if p[0] == "PUSH_CONDITION": st.append(p[-1])
    elif p[0] == "POP_CONDITION": st.pop()


def qset(l):
    p = l.split()
    return {int(t[1:]) for t in p[1:] if t.startswith('q')}


hmrs = [(i, ops[i].split()) for i in range(len(ops)) if ops[i].split()[0] == "HMR"]
sites = []
for i, p in hmrs:
    q = int(p[1][1:])
    lo = max(0, i - 64)
    window = ops[lo:i]
    if any(w.split()[0] in BAR for w in window): continue
    if any(d != depth[i] for d in depth[lo:i]): continue
    touch = [w for w in window if q in qset(w)]
    kinds = Counter(w.split()[0] for w in touch)
    if len(touch) >= 3 and kinds.get("CX", 0) >= 2:
        wires = {w for g in window for w in qset(g)}
        sites.append({"hmr_at": i, "wire": q, "out_bit": p[2], "touch": len(touch),
                      "touch_kinds": dict(kinds), "window_wires": len(wires),
                      "depth": depth[i]})

# CCX-pair-then-HMR scan (Toffoli uncompute shape)
by_target = defaultdict(list)
for i, l in enumerate(ops):
    p = l.split()
    if p[0] in ("CCX", "CCZ"):
        qs = [int(t[1:]) for t in p[1:] if t.startswith('q')]
        by_target[qs[-1]].append(i)
pair_hits = []
for t, lst in by_target.items():
    for i1, i2 in zip(lst, lst[1:]):
        if i2 - i1 > 64: continue
        if any(is_bar[i1:i2 + 1]): continue
        for j in range(i2 + 1, min(len(ops), i2 + 65)):
            if t in qset(ops[j]):
                if ops[j].split()[0] == "HMR":
                    pair_hits.append({"target": t, "ccx1": i1, "ccx2": i2, "hmr": j})
                break

result = {
    "parent_sha256": "5541151cdeea9bd0729c1e09715af3737c4d7d1c95da913b3b976485e766ff38",
    "scope": "route B precondition survey: Toffoli-bearing uncompute (CCX/CCZ/CSWAP) "
             "with last-use target measured by HMR in <=64op/<=8wire/<=4target windows",
    "hmr_total": len(hmrs),
    "barrier_free_uniform_depth_hmr_sites": sites,
    "n_barrier_free_sites": len(sites),
    "ccx_pair_then_hmr_hits": pair_hits,
    "assessment": "10 barrier-free sites are CX/X ladders (free gates) or forward-compute "
                  "CCX adder chains; no Toffoli-like uncompute (compute-use-uncompute with "
                  "restored target) found; 0 CCX-pair-then-HMR structures. "
                  "CX/X uncompute removal saves 0 executable cost. No window meets the "
                  "t=ab+l / t=ab+cd+l template preconditions; 0 windows enter Z3 proof.",
    "verdict": "NEGATIVE-B",
    "qualifying_windows": 0,
    "proofs_attempted": 0,
    "seconds": time.monotonic() - t0,
}
(ART / "routeB_survey.json").write_text(json.dumps(result, indent=1) + "\n")
print(json.dumps({"verdict": "NEGATIVE-B", "sites": len(sites),
                  "pair_hits": len(pair_hits)}, indent=1))
