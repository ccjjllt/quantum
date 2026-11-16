"""DQI 890Q direct-.kmb Toffoli peephole + ancilla live-range report.

CAND A : exact CCX cancel pairs deleted (identical product twice, operands unchanged in version,
         target never read in between)  -> -2 T each
CAND B : A + CCX/CCZ with a provably |0> control deleted -> -1 T each
Both verified with the unchanged official verifier at the default salt.
"""
import base64, io, zipfile, sys, pathlib, os, hashlib, lzma, json, time, struct, importlib.util

t00 = time.time()
def log(*a):
    print(f"[{time.time()-t00:7.1f}s]", *a, flush=True)

WORK = pathlib.Path("/kaggle/working")
TMP = pathlib.Path("/tmp/dqi"); TMP.mkdir(exist_ok=True)
import numpy as np

REPORT = []
def say(*a):
    s = " ".join(str(x) for x in a)
    REPORT.append(s); print(s, flush=True)

MAGIC = bytes.fromhex("d750c7d5c329d326e3cc9f6834f2b8bf")
ROOT = pathlib.Path("/kaggle/input")
PIN = "ccc2ab84ed713901c5642c58890fc664a16a4842c1ebdc80edb56b11c96d6c8d"
BASE_COST = 347375470571.73334

def sha256(path, chunk=1 << 24):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()

def unpack(raw):
    assert raw[:16] == MAGIC
    h = list(struct.unpack_from("<4I9Q", raw, 16))
    pos, regs, secs = 104, [], {}
    while pos < len(raw):
        idx, size = struct.unpack_from("<QQ", raw, pos)
        pay = raw[pos + 16: pos + 16 + size]
        if idx == 0:
            regs.append(pay)
        else:
            secs[idx] = np.frombuffer(pay, dtype=np.uint8 if idx == 1 else np.uint32).copy() if idx <= 9 else pay
        pos += 16 + size
    return h, regs, secs

def pack(h, regs, secs):
    ops = secs[1]
    static_t = int(np.isin(ops & 127, [0x30, 0x31, 0x32]).sum())
    hh = list(h)
    hh[4] = len(ops); hh[5] = static_t
    hh[6] = len(secs[5]); hh[7] = len(secs[7]); hh[8] = len(secs[8]); hh[9] = len(secs[9])
    hdr = MAGIC + struct.pack("<4I9Q", *[int(x) for x in hh[:13]])
    chunks = [hdr] + [struct.pack("<QQ", 0, len(r)) + r for r in regs]
    for i in range(1, 12):
        pay = secs[i].tobytes() if i <= 9 else secs[i]
        chunks.append(struct.pack("<QQ", i, len(pay)) + pay)
    return b"".join(chunks)

srcs = [p for p in sorted(ROOT.rglob("dqi.kmb*")) if p.name in ("dqi.kmb", "dqi.kmb.xz")
        and "sample_submission" not in str(p)]
KMB = TMP / "dqi.kmb"
for src in srcs:
    with (lzma.open(src, "rb") if src.suffix == ".xz" else open(src, "rb")) as f, open(KMB, "wb") as g:
        while True:
            b = f.read(1 << 24)
            if not b:
                break
            g.write(b)
    h = sha256(KMB)
    say(f"A1 {src} size {KMB.stat().st_size} sha {h} match={h == PIN}")
    if h == PIN:
        break

H, REGS, S = unpack(KMB.read_bytes())
ops = S[1]; n = len(ops); base = ops & 127; cond = (ops & 128) != 0
say("A2 header", H)
is3 = np.isin(base, [0x30, 0x31, 0x32]); is2 = np.isin(base, [0x20, 0x21, 0x22])
is1 = np.isin(base, [0x10, 0x11, 0x12, 0x50]); isb = np.isin(base, [0x40, 0x41, 0x42, 0x50])
A = np.full(n, -1, dtype=np.int32); B = np.full(n, -1, dtype=np.int32); C = np.full(n, -1, dtype=np.int32)
BIT = np.full(n, -1, dtype=np.int32); COND = np.full(n, -1, dtype=np.int32)
pref3 = np.cumsum(is3); pref2 = np.cumsum(is2); pref1 = np.cumsum(is1); prefb = np.cumsum(isb); prefc = np.cumsum(cond)
i3a = np.flatnonzero(is3); i2a = np.flatnonzero(is2); i1a = np.flatnonzero(is1)
A[i3a] = S[2][pref3[i3a] - 1]; B[i3a] = S[3][pref3[i3a] - 1]; C[i3a] = S[4][pref3[i3a] - 1]
A[i2a] = S[5][pref2[i2a] - 1]; C[i2a] = S[6][pref2[i2a] - 1]
A[i1a] = S[7][pref1[i1a] - 1]
BIT[isb] = S[8][prefb[isb] - 1]
COND[cond] = S[9][prefc[cond] - 1]
Q = int(max(A.max(), B.max(), C.max())) + 1
say("A3 Q", Q, "n", n, "staticT", int(is3.sum()))
vals, cnts = np.unique(base, return_counts=True)
say("A4 opcodes", {hex(int(v)): int(c) for v, c in zip(vals, cnts)})
anc = np.arange(840, Q, dtype=np.int64)

# ---------------------------------------------------------------- ancilla live ranges (report)
say("B0 ancilla live ranges")
READ1 = np.isin(base, [0x10, 0x11, 0x12])
for w in anc.tolist():
    ks = np.flatnonzero((A == w) | (B == w) | (C == w))
    bp = base[ks]; ai = A[ks]; bi = B[ks]; ci = C[ks]; cd = cond[ks]
    close_k = ks[(bp == 0x50) & (ai == w) & ~cd]
    ccx_t = int(((bp == 0x31) & (ci == w)).sum())
    cx_t = int(((bp == 0x21) & (ci == w)).sum())
    say("B1", json.dumps(dict(w=w, nops=int(len(ks)), first=int(ks[0]), last=int(ks[-1]),
                              ccx_target=ccx_t, cx_target=cx_t, hmr=int(len(close_k)),
                              span_frac=round(float(len(ks)) / n, 6))))

# ---------------------------------------------------------------- write/read event index
m31 = base == 0x31; m21 = base == 0x21; m20 = base == 0x20; m22 = base == 0x22
m1 = READ1; m50 = base == 0x50
wq = np.concatenate([C[m31], C[m21], A[m22], C[m22], A[m1], A[m50]])
wo = np.concatenate([np.flatnonzero(m31), np.flatnonzero(m21), np.flatnonzero(m22), np.flatnonzero(m22),
                     np.flatnonzero(m1), np.flatnonzero(m50)])
wk = np.concatenate([np.full(int(m31.sum()), 0x31), np.full(int(m21.sum()), 0x21),
                     np.full(int(m22.sum()), 0x22), np.full(int(m22.sum()), 0x22),
                     base[m1], base[m50]])
rq = np.concatenate([A[m31], B[m31], A[m21], A[m20], C[m20], A[m22], C[m22], A[m1], A[m50]])
ro = np.concatenate([np.flatnonzero(m31), np.flatnonzero(m31), np.flatnonzero(m21), np.flatnonzero(m20),
                     np.flatnonzero(m20), np.flatnonzero(m22), np.flatnonzero(m22), np.flatnonzero(m1),
                     np.flatnonzero(m50)])
o1 = np.lexsort((wo, wq)); wq = wq[o1]; wo = wo[o1]; wk = wk[o1]
o2 = np.lexsort((ro, rq)); rq = rq[o2]; ro = ro[o2]
wlo = np.searchsorted(wq, np.arange(Q + 1), "left")
rlo = np.searchsorted(rq, np.arange(Q + 1), "left")
say("C1 events", len(wq), len(rq))

def nwr(w, k):
    lo, hi = wlo[w], wlo[w + 1]
    return int(np.searchsorted(wo[lo:hi], k, "left"))
def nrd(w, k1, k2):
    lo, hi = rlo[w], rlo[w + 1]
    seg = ro[lo:hi]
    return int(np.searchsorted(seg, k2, "left") - np.searchsorted(seg, k1, "right"))
def last_write_kind(w, k):
    lo, hi = wlo[w], wlo[w + 1]
    j = int(np.searchsorted(wo[lo:hi], k, "left"))
    if j == 0:
        return None
    return int(wk[lo + j - 1])

# ---------------------------------------------------------------- A: cancel pairs
say("D0 cancel-pair scan")
seen = {}; cancel = []
for k in np.flatnonzero(m31).tolist():
    a = int(A[k]); b = int(B[k]); t = int(C[k])
    key = (a, nwr(a, k), b, nwr(b, k), t, nwr(t, k))
    prev = seen.pop(key, None)
    if prev is not None:
        if nrd(t, prev, k) == 0 and not COND[prev] and not COND[k]:
            cancel.append((prev, k))
        continue
    seen[key] = k
say("D1 cancel pairs", len(cancel), cancel[:10])
delA = set()
for a, b in cancel:
    if a in delA or b in delA:
        continue
    delA.add(a); delA.add(b)
say("D2 ops to delete (A)", len(delA), "T saving", len(delA))

# ---------------------------------------------------------------- B: |0> control gates
say("E0 |0>-control scan")
delB = set()
for k in np.flatnonzero(is3).tolist():
    o = int(base[k]); a = int(A[k]); b = int(B[k]); t = int(C[k])
    ctrls = [a, b] if o in (0x30, 0x31) else [a]
    for w in ctrls:
        lk = last_write_kind(w, k)
        if lk in (0x12, 0x50) and not cond[k]:
            delB.add(k); break
say("E1 |0>-control gates", len(delB), sorted(delB)[:10])

# ---------------------------------------------------------------- build + verify
def build(del_set):
    keep = np.ones(n, dtype=bool)
    if del_set:
        keep[sorted(del_set)] = False
    o = ops[keep]; a_ = A[keep]; b_ = B[keep]; c_ = C[keep]; bt = BIT[keep]; cd = COND[keep]
    bb = o & 127
    i3_ = np.isin(bb, [0x30, 0x31, 0x32]); i2_ = np.isin(bb, [0x20, 0x21, 0x22])
    i1_ = np.isin(bb, [0x10, 0x11, 0x12, 0x50]); ib_ = np.isin(bb, [0x40, 0x41, 0x42, 0x50])
    ic_ = (o & 128) != 0
    secs = {1: o.astype(np.uint8),
            2: a_[i3_].astype(np.uint32), 3: b_[i3_].astype(np.uint32), 4: c_[i3_].astype(np.uint32),
            5: a_[i2_].astype(np.uint32), 6: c_[i2_].astype(np.uint32), 7: a_[i1_].astype(np.uint32),
            8: bt[ib_].astype(np.uint32), 9: cd[ic_].astype(np.uint32),
            10: S.get(10, b""), 11: S.get(11, b"")}
    return secs

import kickmix as km
def verify(path, label):
    circ = km.Circuit.from_file(str(path), format="kmb")
    vpath = sorted(ROOT.rglob("verify_submission_dqi.py"))[0]
    sp = importlib.util.spec_from_file_location("vdqi", str(vpath))
    V = importlib.util.module_from_spec(sp)
    sys.modules["vdqi"] = V
    sp.loader.exec_module(V)
    spec = V.ProblemSpecDQI.benchmark_instance()
    t = time.time()
    res = V.verify(circ, spec, salt="")
    say(f"F {label} {time.time()-t:.0f}s Q {res['num_qubits']} T {res['toffoli_count']:.3f} "
        f"score {res['score']:.3f} err {res['value_errors']}/{res['phase_errors']} "
        f"sha {res['circuit_sha256'][:16]} dscore {res['score']-BASE_COST:+.3f} "
        f"({100*(res['score']/BASE_COST-1):+.6f}%)")
    return res

for label, ds in (("CAND_0_null", set()), ("CAND_A_cancel", delA), ("CAND_B_cancel_zeroctl", delA | delB)):
    try:
        secs = build(ds)
        p = TMP / f"{label}.kmb"
        hh = list(H); hh[1] = Q
        p.write_bytes(pack(hh, REGS, secs))
        say(f"F0 {label} bytes {p.stat().st_size} ops {len(secs[1])} (deleted {len(ds)})")
        verify(p, label)
        os.remove(p)
    except Exception as ex:
        import traceback; say(f"F9 {label} FAILED", repr(ex)); say(traceback.format_exc()[-1800:])

(WORK / "report.txt").write_text("\n".join(REPORT))
say("done")
