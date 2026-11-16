"""DQI 890Q (ccc2ab84) tape analysis: width/liveness/ancilla inventory/structure.

Runs on Kaggle CPU only. Reads the ccc2ab84 dqi.kmb from the Hayato mirror dataset,
checks its sha256, converts to kmx, and dumps:
  S0 file/hash/census, S1 registers, S2 width profile + episodes,
  S3 ancilla inventory (per non-register wire), S4 peak live set,
  S5 one-wire removal effect (peak_without), S6 joint removal for candidate sets,
  S7 structure scan (MBU/dead writes/cancel pairs/retained products),
  S8 op context around each ancilla's open/close.
"""
import base64, io, zipfile, sys, pathlib, os, hashlib, lzma, json, gc, time

t00 = time.time()
def log(*a):
    print(f"[{time.time()-t00:7.1f}s]", *a, flush=True)

WORK = pathlib.Path("/kaggle/working")
QS = WORK / "pkg"
QS.mkdir(exist_ok=True)
zipfile.ZipFile(io.BytesIO(base64.b64decode(QQB64))).extractall(QS)
sys.path.insert(0, str(QS))
import numpy as np
from qccscope import kmx, liveness as L, structure as St

ROOT = pathlib.Path("/kaggle/input")
log("inputs:", sorted(str(p) for p in ROOT.iterdir()))


def sha256(path, chunk=1 << 24):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


# ---------------------------------------------------------------- S0 locate + hash
cands = [p for p in sorted(ROOT.rglob("dqi.kmb*")) if p.name in ("dqi.kmb", "dqi.kmb.xz")]
log("dqi candidates:", [(str(p), p.stat().st_size) for p in cands])
PIN = "ccc2ab84ed713901c5642c58890fc664a16a4842c1ebdc80edb56b11c96d6c8d"
KMB = WORK / "dqi.kmb"
h = None
for src in sorted(cands, key=lambda p: "sample_submission" in str(p)):
    if "sample_submission" in str(src):
        continue
    if src.suffix == ".xz":
        with lzma.open(src, "rb") as f, open(KMB, "wb") as g:
            while True:
                b = f.read(1 << 24)
                if not b:
                    break
                g.write(b)
    else:
        KMB.write_bytes(src.read_bytes())
    h = sha256(KMB)
    log(f"tried {src}: size {KMB.stat().st_size} sha {h[:16]}")
    if h == PIN or KMB.stat().st_size == 455590024:
        break
PIN = "ccc2ab84ed713901c5642c58890fc664a16a4842c1ebdc80edb56b11c96d6c8d"
log(f"dqi.kmb {KMB.stat().st_size} sha256 {h} is_ccc2ab84={h == PIN}")
print("S0", json.dumps(dict(size=KMB.stat().st_size, sha256=h)), flush=True)

# ---------------------------------------------------------------- S1 kmb -> kmx
so = sorted(ROOT.rglob("kickmix.so"))
log("kickmix.so:", [str(p) for p in so])
sys.path.insert(0, str(so[0].parent))
if "kickmix" in sys.modules:
    del sys.modules["kickmix"]
import kickmix as km
log("kickmix", km.__file__, [n for n in dir(km) if not n.startswith("_")][:12])
t = time.time()
circ_km = km.Circuit.from_file(str(KMB), format="kmb")
log(f"kickmix load {time.time()-t:.0f}s qubits {circ_km.num_qubits} ops {len(circ_km)} bits {circ_km.num_bits}")
KMX = WORK / "dqi.kmx"
t = time.time()
circ_km.to_file(str(KMX), format="kmx")
log(f"kmx dump {time.time()-t:.0f}s size {KMX.stat().st_size}")
del circ_km
gc.collect()

t = time.time()
circ = kmx.parse(str(KMX))
log(f"qccscope parse {time.time()-t:.0f}s ops {circ.n_ops} qubits {circ.num_qubits} bits {circ.num_bits}")
print("S1", json.dumps(dict(n_ops=circ.n_ops, num_qubits=circ.num_qubits, num_bits=circ.num_bits,
                            registers={k: len(v) for k, v in circ.regs.items() if k in ("S0", "S1", "S69")},
                            n_registers=len(circ.regs), ang=len(circ.angles), tags=len(circ.tags))), flush=True)

cen = St.census(circ)
print("S1census", json.dumps(cen), flush=True)

reg = np.array(sorted({q for v in circ.regs.values() for q in v}), dtype=np.int64)
log(f"register qubits {len(reg)} min {reg.min()} max {reg.max()}")
allq = np.zeros(circ.num_qubits, dtype=bool)
allq[reg] = True
anc = np.flatnonzero(~allq)
log(f"non-register wires {len(anc)}: {anc.tolist()[:60]}")
print("S1reg", json.dumps(dict(n_reg=int(len(reg)), n_anc=int(len(anc)), anc=anc.tolist())), flush=True)

# ---------------------------------------------------------------- S2 width
t = time.time()
lv = L.compute(circ, keep_intervals=False)
log(f"liveness {time.time()-t:.0f}s peak {lv.peak}")
n = circ.n_ops
wd = lv.width
print("S2", json.dumps(dict(peak=int(lv.peak), ops_at_peak=int((wd >= lv.peak).sum()),
                            eps_peak=[(int(a), int(b)) for a, b in lv.episodes()][:20],
                            n_ep_peak=len(lv.episodes()),
                            eps_m1=[(int(a), int(b)) for a, b in lv.episodes(lv.peak - 1)][:20],
                            n_ep_m1=len(lv.episodes(lv.peak - 1)),
                            eps_m10=[(int(a), int(b)) for a, b in lv.episodes(lv.peak - 10)][:20],
                            n_ep_m10=len(lv.episodes(lv.peak - 10)),
                            width_mean=float(wd.mean()))), flush=True)
# width histogram at 1% bins over the tape
edges = np.linspace(0, n, 21).astype(np.int64)
print("S2tl", json.dumps([dict(s=int(edges[i]), e=int(edges[i+1]), wmax=int(wd[edges[i]:edges[i+1]].max()),
                               wmean=round(float(wd[edges[i]:edges[i+1]].mean()), 1)) for i in range(20)]), flush=True)

# ---------------------------------------------------------------- S3 ancilla inventory
READPOS = {kmx.CX: (0,), kmx.CCX: (0, 1), kmx.CZ: (0, 1), kmx.CCZ: (0, 1, 2), kmx.CSWAP: (0, 1, 2),
           kmx.SWAP: (0, 1), kmx.Z: (0,), kmx.ZPOW: (0,), kmx.HMR: (0,)}
WRITEPOS = {kmx.CX: (1,), kmx.CCX: (2,), kmx.CSWAP: (1, 2), kmx.SWAP: (0, 1), kmx.X: (0,),
            kmx.HMR: (0,), kmx.R: (0,)}


def wire_idx(w):
    return np.flatnonzero((circ.a == w) | (circ.b == w) | (circ.c == w))


def parts(idx, w):
    """per-touch (op, is_read, is_write, is_close)"""
    out = []
    A = circ.a.tolist() if False else circ.a
    for k in idx.tolist():
        o = int(circ.op[k])
        cond = circ.cond[k] >= 0 or circ.depth[k] > 0
        pos = []
        if circ.a[k] == w:
            pos.append(0)
        if circ.b[k] == w:
            pos.append(1)
        if circ.c[k] == w:
            pos.append(2)
        rd = any(p in READPOS.get(o, ()) for p in pos)
        wr = any(p in WRITEPOS.get(o, ()) for p in pos)
        close = (o in (kmx.HMR, kmx.R)) and (0 in pos) and not cond
        out.append((k, o, rd, wr, close))
    return out


def cons_intervals(w, idx):
    iv = []
    start = None
    for (k, o, rd, wr, close) in parts(idx, w):
        if start is None:
            if not close:
                start = k
        if close:
            if start is not None:
                iv.append((start, k))
                start = None
    if start is not None:
        iv.append((start, n))
    return iv


def peak_without(ivs):
    """peak of width when the wires with these intervals are removed"""
    mask = np.ones(n, dtype=bool)
    for iv in ivs:
        for s, e in iv:
            mask[s:e] = False
    p = int(wd[mask].max()) if mask.any() else 0
    for iv in ivs:
        for s, e in iv:
            if e > s:
                p = max(p, int((wd[s:e] - 1).max()))
    return p


inv = []
for w in anc.tolist():
    idx = wire_idx(w)
    if len(idx) == 0:
        inv.append(dict(w=w, nops=0))
        continue
    ps = parts(idx, w)
    iv = cons_intervals(w, idx)
    reads = [k for (k, o, rd, wr, cl) in ps if rd]
    writes = [k for (k, o, rd, wr, cl) in ps if wr]
    ccx_c = int(sum(1 for k in idx.tolist() if int(circ.op[k]) == kmx.CCX and circ.c[k] == w))
    ccx_ab = int(sum(1 for k in idx.tolist() if int(circ.op[k]) == kmx.CCX and (circ.a[k] == w or circ.b[k] == w)))
    cx_b = int(sum(1 for k in idx.tolist() if int(circ.op[k]) == kmx.CX and circ.b[k] == w))
    hmr = int(sum(1 for k in idx.tolist() if int(circ.op[k]) in (kmx.HMR, kmx.R)))
    first = int(idx[0]); last = int(idx[-1])
    kind0 = kmx.OPS[int(circ.op[first])] + ("->target" if circ.c[first] == w or circ.b[first] == w else "->control")
    inv.append(dict(w=w, nops=int(len(idx)), first=first, last=last, n_int=len(iv),
                    first_iv=[int(iv[0][0]), int(iv[0][1])] if iv else None,
                    live_ops=int(sum(e - s for s, e in iv)),
                    reads=int(len(reads)), last_read=int(reads[-1]) if reads else -1,
                    writes=int(len(writes)), ccx_target=ccx_c, ccx_control=ccx_ab, cx_target=cx_b,
                    hmr=hmr, kind0=kind0, peak_without=peak_without([iv]) if iv else int(lv.peak),
                    ivs=[[int(a), int(b)] for a, b in iv][:40]))
log("ancilla inventory done")
print("S3", json.dumps(inv, indent=0), flush=True)

# ---------------------------------------------------------------- S4 peak live set
pk = lv.peak
pk_ops = np.flatnonzero(wd >= pk)
mid = int(pk_ops[0])
live_anc = [r["w"] for r in inv if any(s <= mid < e for s, e in r["ivs"])]
print("S4", json.dumps(dict(peak=int(pk), n_ops_at_peak=len(pk_ops), first_peak_op=mid,
                            last_peak_op=int(pk_ops[-1]),
                            live_anc_at_first_peak=live_anc,
                            n_live_anc=len(live_anc))), flush=True)

# ---------------------------------------------------------------- S5/S6 joint removal
cand = sorted([r for r in inv if r.get("peak_without", pk) < pk], key=lambda r: r["peak_without"])
print("S5", json.dumps([dict(w=r["w"], peak_without=r["peak_without"], nops=r["nops"], first=r["first"],
                             last=r["last"], kind0=r["kind0"], ccx_target=r["ccx_target"],
                             ccx_control=r["ccx_control"], hmr=r["hmr"], live_ops=r["live_ops"],
                             last_read=r["last_read"]) for r in cand]), flush=True)


def joint(ws):
    ivs = []
    for r in inv:
        if r["w"] in ws:
            ivs.append([tuple(x) for x in r["ivs"]])
    mask = np.ones(n, dtype=bool)
    for iv in ivs:
        for s, e in iv:
            mask[s:e] = False
    cnt = np.zeros(n, dtype=np.int16)
    for iv in ivs:
        for s, e in iv:
            cnt[s:e] += 1
    p = int((wd - cnt).max())
    return p


if cand:
    # greedy: add the candidate that lowers the joint peak most, up to 14 wires
    chosen = []
    cur = peak_without([])
    for step in range(14):
        best = None
        for r in cand:
            if r["w"] in chosen:
                continue
            p = joint(set(chosen) | {r["w"]})
            if best is None or p < best[1]:
                best = (r["w"], p)
        if best is None or best[1] >= cur:
            break
        chosen.append(best[0]); cur = best[1]
        log(f"greedy step {step}: +{best[0]} -> peak {cur}")
        if cur <= 840:
            break
    print("S6", json.dumps(dict(chosen=chosen, joint_peak=int(cur))), flush=True)

# ---------------------------------------------------------------- S7 structure
t = time.time()
S = St.scan(circ, max_list=100000)
log(f"structure scan {time.time()-t:.0f}s")
print("S7", json.dumps(dict(census=S.census, toffoli_kinds=dict(S.toffoli_kinds),
                            cond_toffolis=int(S.cond_toffolis),
                            n_cancel=len(S.cancel_pairs), n_uncompute=len(S.toffoli_uncompute),
                            n_dead=len(S.dead_writes), n_const_control=len(S.const_control),
                            n_same_operands=len(S.same_operands), mbu_erasures=int(S.mbu_erasures),
                            n_and_compute=int(S.n_and_compute),
                            ladders_top=[(int(a), int(b)) for a, b in S.ladders[:10]])), flush=True)
print("S7sample", json.dumps(dict(cancel=S.cancel_pairs[:5], uncompute=S.toffoli_uncompute[:5],
                                  dead=S.dead_writes[:5], same=S.same_operands[:5])), flush=True)

# ---------------------------------------------------------------- S8 context around ancilla events
def ctx(k, r=5):
    out = []
    for j in range(max(0, k - r), min(n, k + r + 1)):
        out.append(f"{j}{'*' if j == k else ''}:{kmx.OPS[int(circ.op[j])]}"
                   f"({circ.a[j]},{circ.b[j]},{circ.c[j]}|b{circ.bit[j]}{'c' if circ.cond[j]>=0 else ''}"
                   f"{'d' if circ.depth[j]>0 else ''})")
    return " ".join(out)


lines = []
for r in inv[:60]:
    if not r.get("ivs"):
        continue
    for (s, e) in r["ivs"][:3]:
        lines.append(f"W{r['w']} open@{s}: {ctx(s)}")
        if e < n:
            lines.append(f"W{r['w']} close@{e}: {ctx(e)}")
(WORK / "s8_context.txt").write_text("\n".join(lines))
log(f"S8 wrote {len(lines)} context lines")
print("S8done", flush=True)
log("analysis complete; peak", lv.peak, "static T", cen.get("_static_toffoli"))
