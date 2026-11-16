"""DQI 890Q (ccc2ab84) : tape analysis + Q-reduction surgery + official verification.

A file id / kmb -> kmx -> parsed arrays
B census, conservative width, ancilla def-use inventory
C true (last-read) liveness of the 50 ancillas
D droppability per ancilla
E greedy joint drop set
F emit transformed kmx, renumber, reparse, width check
G official verifier at the default salt
"""
import base64, io, zipfile, sys, pathlib, os, hashlib, lzma, json, gc, time, importlib.util

t00 = time.time()
def log(*a):
    print(f"[{time.time()-t00:7.1f}s]", *a, flush=True)

WORK = pathlib.Path("/kaggle/working")
TMP = pathlib.Path("/tmp/dqi"); TMP.mkdir(exist_ok=True)
QS = TMP / "pkg"; QS.mkdir(exist_ok=True)
zipfile.ZipFile(io.BytesIO(base64.b64decode(QQB64))).extractall(QS)
sys.path.insert(0, str(QS))
import numpy as np
from qccscope import kmx, liveness as L, structure as St

ROOT = pathlib.Path("/kaggle/input")
REPORT = []
def say(*a):
    s = " ".join(str(x) for x in a)
    REPORT.append(s); print(s, flush=True)

def sha256(path, chunk=1 << 24):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()

PIN = "ccc2ab84ed713901c5642c58890fc664a16a4842c1ebdc80edb56b11c96d6c8d"
so = sorted(ROOT.rglob("kickmix.so"))
sys.path.insert(0, str(so[0].parent))
if "kickmix" in sys.modules:
    del sys.modules["kickmix"]
import kickmix as km

# ---------------------------------------------------------------- A
srcs = [p for p in sorted(ROOT.rglob("dqi.kmb*")) if p.name in ("dqi.kmb", "dqi.kmb.xz")
        and "sample_submission" not in str(p)]
say("A0 candidates", [(str(p), p.stat().st_size) for p in srcs])
KMB = TMP / "dqi.kmb"
h = None
for src in srcs:
    op = lzma.open(src, "rb") if src.suffix == ".xz" else open(src, "rb")
    with op as f, open(KMB, "wb") as g:
        while True:
            b = f.read(1 << 24)
            if not b:
                break
            g.write(b)
    h = sha256(KMB)
    say(f"A1 {src} size {KMB.stat().st_size} sha {h}")
    if h == PIN:
        break
say("A2 is_ccc2ab84", h == PIN)

t = time.time()
circ_km = km.Circuit.from_file(str(KMB), format="kmb")
say(f"A3 kickmix Q {circ_km.num_qubits} bits {circ_km.num_bits} ops {len(circ_km)} load {time.time()-t:.0f}s")
say("A4 stats", dict(circ_km.operation_statistics()))
KMX = TMP / "dqi.kmx"
t = time.time()
circ_km.to_file(str(KMX), format="kmx")
say(f"A5 kmx {KMX.stat().st_size} in {time.time()-t:.0f}s")
del circ_km; gc.collect()

t = time.time()
circ = kmx.parse(str(KMX))
n = circ.n_ops
say(f"A6 parse {time.time()-t:.0f}s ops {n} Q {circ.num_qubits} bits {circ.num_bits} regs {len(circ.regs)}")

# preserve the original declaration header verbatim
HEADER = []
with open(KMX) as f:
    for line in f:
        t0 = line.split()[0] if line.split() else ""
        if t0 in ("REGISTER", "APPEND_TO_REGISTER"):
            HEADER.append(line.rstrip("\n"))
        elif t0 not in ("INFO_TAG", "DEBUG_PRINT"):
            break
say("A7 header lines", len(HEADER), HEADER[:2], HEADER[-2:])

# ---------------------------------------------------------------- B
cen = St.census(circ)
say("B0 census", json.dumps(cen))
reg = np.array(sorted({q for v in circ.regs.values() for q in v}), dtype=np.int64)
allq = np.zeros(circ.num_qubits, dtype=bool); allq[reg] = True
anc = np.flatnonzero(~allq)
say("B1 register qubits", len(reg), "range", int(reg.min()), int(reg.max()), "ancillas", len(anc), anc.tolist())
t = time.time()
lv = L.compute(circ, keep_intervals=False)
wd = lv.width
say(f"B2 conservative peak {lv.peak} ({(wd >= lv.peak).sum()} ops) in {time.time()-t:.0f}s")
say("B2b peak episodes", [(int(a), int(b)) for a, b in lv.episodes()][:12], "count", len(lv.episodes()))
say("B2c eps peak-1", [(int(a), int(b)) for a, b in lv.episodes(lv.peak - 1)][:12])
say("B2d eps peak-8", [(int(a), int(b)) for a, b in lv.episodes(lv.peak - 8)][:12])
say("B2e width quantiles", [int(np.percentile(wd, q)) for q in (1, 5, 25, 50, 75, 95, 99, 100)])

# ---------------------------------------------------------------- C
A_, B_, C_ = circ.a, circ.b, circ.c
OP, COND, DEP, BIT = circ.op, circ.cond, circ.depth, circ.bit
READPOS = {kmx.CX: (0,), kmx.CCX: (0, 1), kmx.CZ: (0, 1), kmx.CCZ: (0, 1, 2), kmx.CSWAP: (0, 1, 2),
           kmx.SWAP: (0, 1), kmx.Z: (0,), kmx.ZPOW: (0,), kmx.HMR: (0,)}
WRITEPOS = {kmx.CX: (1,), kmx.CCX: (2,), kmx.CSWAP: (1, 2), kmx.SWAP: (0, 1), kmx.X: (0,),
            kmx.HMR: (0,), kmx.R: (0,)}

def touches(w):
    return np.flatnonzero((A_ == w) | (B_ == w) | (C_ == w))

def classify(w, idx):
    out = []
    for k in idx.tolist():
        o = int(OP[k]); cond = COND[k] >= 0 or DEP[k] > 0
        pos = []
        if A_[k] == w: pos.append(0)
        if B_[k] == w: pos.append(1)
        if C_[k] == w: pos.append(2)
        rd = any(p in READPOS.get(o, ()) for p in pos)
        wr = any(p in WRITEPOS.get(o, ()) for p in pos)
        close = (o in (kmx.HMR, kmx.R)) and (0 in pos) and not cond
        out.append((k, o, rd, wr, close, pos, cond))
    return out

def cons_iv(ps):
    iv = []; start = None
    for (k, o, rd, wr, close, pos, cond) in ps:
        if start is None:
            if not close: start = k
        if close:
            if start is not None:
                iv.append((start, k)); start = None
    if start is not None: iv.append((start, n))
    return iv

def true_iv(ps):
    iv = []; start = None; lastread = None
    for (k, o, rd, wr, close, pos, cond) in ps:
        if start is None:
            if wr or rd: start = k
        elif wr:
            if lastread is not None and lastread >= start: iv.append((start, lastread))
            start = k; lastread = None
        if rd: lastread = k
    if start is not None and lastread is not None and lastread >= start:
        iv.append((start, lastread))
    return iv

inv = []
for w in anc.tolist():
    idx = touches(w)
    if len(idx) == 0:
        inv.append(dict(w=w, nops=0)); continue
    ps = classify(w, idx)
    civ = cons_iv(ps); tiv = true_iv(ps)
    reads = [k for (k, o, rd, wr, cl, po, cd) in ps if rd]
    writes = [k for (k, o, rd, wr, cl, po, cd) in ps if wr]
    ccx_t = [(k, int(A_[k]), int(B_[k])) for k in idx.tolist() if int(OP[k]) == kmx.CCX and C_[k] == w]
    cx_r = [(k, int(B_[k])) for k in idx.tolist() if int(OP[k]) == kmx.CX and A_[k] == w]
    hmr = [k for k in idx.tolist() if int(OP[k]) in (kmx.HMR, kmx.R)]
    other_reads = [k for (k, o, rd, wr, cl, po, cd) in ps if rd and not (o == kmx.CX and A_[k] == w)]
    inv.append(dict(w=w, nops=int(len(idx)), first=int(idx[0]), last=int(idx[-1]),
                    n_civ=len(civ), live_ops=int(sum(e - s for s, e in civ)),
                    civ=[[int(a), int(b)] for a, b in civ],
                    tiv=[[int(a), int(b)] for a, b in tiv],
                    true_live=int(sum(e - a + 1 for a, e in tiv)),
                    first_read=int(reads[0]) if reads else -1,
                    last_read=int(reads[-1]) if reads else -1,
                    n_writes=len(writes), ccx_target=ccx_t, n_ccx_target=len(ccx_t),
                    cx_reads=cx_r, n_cx_read=len(cx_r), n_other_reads=len(other_reads),
                    other_reads=other_reads[:6], hmr=hmr, n_hmr=len(hmr),
                    define=dict(op=kmx.OPS[int(OP[idx[0]])], a=int(A_[idx[0]]), b=int(B_[idx[0]]),
                                c=int(C_[idx[0]]))))
for r in inv:
    if r.get("civ"):
        r["peak_without"] = None
    else:
        r["peak_without"] = int(lv.peak)
say("C0 ancilla inventory")
for r in inv:
    rr = dict(r); rr.pop("civ", None); rr.pop("tiv", None)
    say("C1", json.dumps(rr))

ev = []
for r in inv:
    for a, e in r["tiv"]:
        ev.append((a, 1)); ev.append((e + 1, -1))
ev.sort(); cur = 0; best = 0
for _, d in ev:
    cur += d; best = max(best, cur)
say("C2 true ancilla-live max", best, "conservative ancilla peak", int((wd - len(reg)).max()),
    "=> true Q est", 840 + best)

PLATEAU = np.flatnonzero(wd >= lv.peak)
ps, pe = int(PLATEAU[0]), int(PLATEAU[-1])
say("C3 plateau", ps, pe, "len", len(PLATEAU))

mask = np.ones(n, dtype=bool)
for r in inv:
    for a, e in r["civ"]:
        mask[a:e] = False
for r in inv:
    if not r.get("civ"):
        continue
    m2 = mask.copy()
    for a, e in r["civ"]:
        m2[a:e] = True
    p = int(wd[m2].max()) if m2.any() else 0
    for a, e in r["civ"]:
        if e > a:
            p = max(p, int((wd[a:e] - 1).max()))
    r["peak_without"] = p
say("C4 peak_without", sorted([(r["w"], r["peak_without"]) for r in inv], key=lambda x: x[1])[:20])

# ---------------------------------------------------------------- D
for r in inv:
    r["drop"] = None
    w = r["w"]
    if r.get("nops", 0) == 0:
        continue
    if r["n_other_reads"]:
        r["drop"] = "reads-not-cx"; continue
    if r["n_hmr"] > 1:
        r["drop"] = "multi-hmr"; continue
    if r["n_ccx_target"] not in (0, 1, 2):
        r["drop"] = "ccx-targets"; continue
    if r["n_ccx_target"] >= 1:
        (dk, da, db) = r["ccx_target"][0]
        if dk != r["first"]:
            r["drop"] = "define-not-first"; continue
        if r["n_ccx_target"] == 2:
            (k2, a2, b2) = r["ccx_target"][1]
            if (a2, b2) != (da, db) or r["last_read"] > k2:
                r["drop"] = "second-ccx"; continue
        kind = "and"
    elif int(OP[r["first"]]) == kmx.CX and B_[r["first"]] == w:
        dk, da, db = r["first"], int(A_[r["first"]]), -1
        kind = "copy"
    else:
        r["drop"] = "define-kind"; continue
    pre = [k for (k, t) in r["cx_reads"] if k <= pe]
    post = [k for (k, t) in r["cx_reads"] if k > pe]
    r["drop"] = dict(kind=kind, define=dk, da=da, db=db, n_read=len(r["cx_reads"]),
                     n_pre=len(pre), n_post=len(post), cost=len(pre) if post else len(pre) + 1)
droppable = [r for r in inv if isinstance(r["drop"], dict)]
say("D0 droppable", json.dumps([dict(w=r["w"], kind=r["drop"]["kind"], cost=r["drop"]["cost"],
                                      n_read=r["drop"]["n_read"], n_pre=r["drop"]["n_pre"],
                                      n_post=r["drop"]["n_post"], peak_without=r["peak_without"])
                                 for r in droppable]))
say("D1 rejected", json.dumps([(r["w"], r["drop"]) for r in inv if isinstance(r["drop"], str)]))

# ---------------------------------------------------------------- E
def joint_peak(ws):
    ivs = [[tuple(x) for x in r["civ"]] for r in inv if r["w"] in ws]
    cnt = np.zeros(n, dtype=np.int16)
    for iv in ivs:
        for s, e in iv:
            cnt[s:e] += 1
    return int((wd - cnt).max())

TARGET = int(os.environ.get("TARGET_Q", "884"))
chosen = []
cur = int(lv.peak)
while cur > TARGET and len(chosen) < 24:
    best = None
    for r in droppable:
        if r["w"] in chosen: continue
        p = joint_peak(set(chosen) | {r["w"]})
        if best is None or p < best[1]:
            best = (r["w"], p)
    if best is None or best[1] >= cur:
        break
    chosen.append(best[0]); cur = best[1]
    say(f"E1 +w{best[0]} -> peak {cur}")
say("E2 chosen", chosen, "joint peak", cur, "target", TARGET)

# ---------------------------------------------------------------- F
perm = np.full(circ.num_qubits, -1, dtype=np.int64)
for q in reg.tolist():
    perm[q] = q
nxt = 840
for w in anc.tolist():
    if w in chosen: continue
    perm[w] = nxt; nxt += 1
NEWQ = nxt
say("F0 new Q", NEWQ)

drop_ops = set(); insert_before = {}; patch = {}
for r in inv:
    if r["w"] not in chosen or not isinstance(r["drop"], dict):
        continue
    d = r["drop"]; rds = r["cx_reads"]
    drop_ops.add(d["define"])
    if r["n_ccx_target"] == 2:
        drop_ops.add(r["ccx_target"][1][0])
    moved = False
    for (k, t) in rds:
        if k > pe:
            if not moved and d["n_pre"] >= 0:
                insert_before.setdefault(k, []).append(d["define"]); moved = True
        else:
            if d["kind"] == "and":
                patch[k] = (kmx.CCX, d["da"], d["db"], t, -1, int(COND[k]))
            else:
                patch[k] = (kmx.CX, d["da"], t, -1, -1, int(COND[k]))
    if not moved:
        for k in r["hmr"]:
            drop_ops.add(k)
        if len(r["hmr"]) == 1 and int(OP[r["hmr"][0]]) == kmx.HMR:
            b = int(BIT[r["hmr"][0]]); hk = r["hmr"][0]
            for j in range(hk + 1, min(hk + 64, n)):
                if int(OP[j]) == kmx.PUSH and int(BIT[j]) == b:
                    k2 = j + 1
                    while k2 < n and int(OP[k2]) != kmx.POP:
                        k2 += 1
                    inner = list(range(j + 1, k2))
                    ok = k2 < n and all(int(OP[x]) in (kmx.CZ, kmx.Z, kmx.CCZ) for x in inner)
                    if ok:
                        drop_ops.update(range(j, k2 + 1))
                    else:
                        say("F0b skip-correction-block", r["w"], "inner", [kmx.OPS[int(OP[x])] for x in inner][:6])
                    break
say("F1 drop_ops", len(drop_ops), "patched", len(patch), "moved", sum(len(v) for v in insert_before.values()))

NAMES = kmx.OPS
def line_for(o, a, b, c, bit, cond):
    if o == kmx.PUSH:
        return f"PUSH_CONDITION b{bit}" + (f" if b{cond}" if cond >= 0 else "")
    if o == kmx.POP:
        return "POP_CONDITION"
    if o >= kmx.BINV:
        return f"{NAMES[o]} b{bit}"
    if o == kmx.HMR:
        s = f"HMR q{perm[a]} b{bit}"
    elif o == kmx.ZPOW:
        s = f"Z_POW q{perm[a]} {circ.angles[bit]}"
    else:
        parts = [f"q{perm[x]}" for x in (a, b, c) if x >= 0]
        s = NAMES[o] + (" " + " ".join(parts) if parts else "")
    if cond >= 0:
        s += f" if b{cond}"
    return s

OUT = TMP / "edited.kmx"
with open(OUT, "w") as f:
    f.write("\n".join(HEADER) + "\n")
    buf = []
    for k in range(n):
        if k in insert_before:
            for dk in insert_before[k]:
                buf.append(line_for(int(OP[dk]), int(A_[dk]), int(B_[dk]), int(C_[dk]), int(BIT[dk]), int(COND[dk])))
        if k in drop_ops:
            continue
        if k in patch:
            o, a, b, c, bit, cond = patch[k]
            buf.append(line_for(o, a, b, c, bit, cond))
        else:
            buf.append(line_for(int(OP[k]), int(A_[k]), int(B_[k]), int(C_[k]), int(BIT[k]), int(COND[k])))
        if len(buf) > 400000:
            f.write("\n".join(buf) + "\n"); buf = []
    if buf:
        f.write("\n".join(buf) + "\n")
say("F2 wrote", OUT, OUT.stat().st_size)
del wd, lv; gc.collect()

t = time.time()
new = kmx.parse(str(OUT))
say(f"F3 reparse {time.time()-t:.0f}s ops {new.n_ops} Q {new.num_qubits} bits {new.num_bits} regs {len(new.regs)}")
say("F4 registers equal", {k: len(v) for k, v in new.regs.items()} == {k: len(v) for k, v in circ.regs.items()},
    "Q", new.num_qubits, "expected", NEWQ, "op delta", new.n_ops - n)
lv2 = L.compute(new, keep_intervals=False)
say("F5 new conservative peak", lv2.peak, "ops at peak", int((lv2.width >= lv2.peak).sum()))
say("F6 new census", json.dumps(St.census(new)))
del circ, A_, B_, C_, OP, COND, DEP, BIT, inv, droppable, reg, anc
gc.collect()
say("F7 freed analysis arrays")

# ---------------------------------------------------------------- G
try:
    vpath = sorted(ROOT.rglob("verify_submission_dqi.py"))[0]
    sp = importlib.util.spec_from_file_location("vdqi", str(vpath))
    V = importlib.util.module_from_spec(sp); sp.loader.exec_module(V)
    spec = V.ProblemSpecDQI.benchmark_instance()
    t = time.time()
    res = V.verify(new, spec, salt="")
    say(f"G0 verified in {time.time()-t:.0f}s")
    say("G1", json.dumps(res))
    base = 347375470571.73334
    say("G2 score", res["score"], "base", base, "delta_pct", round(100 * (res["score"] / base - 1), 5))
except Exception as ex:
    import traceback
    say("G9 FAILED", repr(ex)); say(traceback.format_exc()[-2500:])

(WORK / "report.txt").write_text("\n".join(REPORT))
for p in (KMB, KMX, OUT):
    try: p.unlink()
    except OSError: pass
say("done")
