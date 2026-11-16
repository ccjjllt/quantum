"""DQI 890Q: delete Toffolis whose target value is provably discarded.

A CCX/CCZ at op k writing t, with the *next* touch of t being an unconditional
  * R (reset, no measurement)                 -> deleting the gate is exact, -1 T
  * HMR whose measured bit is never used      -> deleting the gate is exact, -1 T
Both candidates verified with the unchanged official verifier at the default salt.
CAND_0 (null repack) is verified first to prove the container writer is faithful.
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
say("A3 Q", Q, "n", n, "staticT", int(is3.sum()), "nbits", int(max(BIT.max(), COND.max())) + 1)

# bit-use census: which bits are read (as a gate condition or as a BIT op operand)?
bitread = np.zeros(int(max(BIT.max(), COND.max())) + 2, dtype=bool)
np.logical_or.at(bitread, COND[cond], True)
say("A5 bits referenced by conditions", int(bitread.sum()))

# per-wire touch lists
def touchmask(w):
    return (A == w) | (B == w) | (C == w)

# ---------------------------------------------------------------- dead-write scan
say("B0 dead-write scan (target's next touch is an unconditional R, or an HMR with an unused bit)")
dead_R = []; dead_H = []
tq = np.concatenate([A[A >= 0], B[B >= 0], C[C >= 0]])
to = np.concatenate([np.flatnonzero(A >= 0), np.flatnonzero(B >= 0), np.flatnonzero(C >= 0)])
o3 = np.lexsort((to, tq)); tq = tq[o3]; to = to[o3]
same = np.r_[False, (tq[1:] == tq[:-1]) & (to[1:] == to[:-1])]
tq = tq[~same]; to = to[~same]
tlo = np.searchsorted(tq, np.arange(Q + 2), "left")
say("B0 touch index", len(tq), "pairs")
for k in np.flatnonzero(is3).tolist():
    t = int(C[k])
    lo, hi = tlo[t], tlo[t + 1]
    seg = to[lo:hi]
    j = int(np.searchsorted(seg, k, "right"))
    if j >= len(seg):
        continue
    nk = int(seg[j])
    if cond[nk] or A[nk] != t:
        continue
    o2 = int(base[nk])
    if o2 == 0x12:
        dead_R.append(k)
    elif o2 == 0x50 and not bitread[int(BIT[nk])]:
        dead_H.append(k)
say("B1 dead to R", len(dead_R), dead_R[:10])
say("B2 dead to unused HMR", len(dead_H), dead_H[:10])
say("B3 total T saving", len(set(dead_R) | set(dead_H)))

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
    return {1: o.astype(np.uint8),
            2: a_[i3_].astype(np.uint32), 3: b_[i3_].astype(np.uint32), 4: c_[i3_].astype(np.uint32),
            5: a_[i2_].astype(np.uint32), 6: c_[i2_].astype(np.uint32), 7: a_[i1_].astype(np.uint32),
            8: bt[ib_].astype(np.uint32), 9: cd[ic_].astype(np.uint32),
            10: S.get(10, b""), 11: S.get(11, b"")}

so = sorted(ROOT.rglob("kickmix.so"))
sys.path.insert(0, str(so[0].parent))
if "kickmix" in sys.modules:
    del sys.modules["kickmix"]
import kickmix as km
say("C0 kickmix", km.__file__, hasattr(km, "Circuit"))

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
    say(f"D {label} {time.time()-t:.0f}s Q {res['num_qubits']} T {res['toffoli_count']:.3f} "
        f"score {res['score']:.3f} err {res['value_errors']}/{res['phase_errors']} "
        f"sha {res['circuit_sha256'][:16]} dscore {res['score']-BASE_COST:+.3f} "
        f"({100*(res['score']/BASE_COST-1):+.6f}%)")
    return res

cands = [("CAND_0_null", set()), ("CAND_A_deadR", set(dead_R)),
         ("CAND_B_deadR_plus_deadHMR", set(dead_R) | set(dead_H))]
for label, ds in cands:
    try:
        secs = build(ds)
        p = TMP / f"{label}.kmb"
        hh = list(H); hh[1] = Q
        p.write_bytes(pack(hh, REGS, secs))
        say(f"C1 {label} bytes {p.stat().st_size} ops {len(secs[1])} deleted {len(ds)} "
            f"staticT {int(np.isin(secs[1] & 127, [0x30, 0x31, 0x32]).sum())}")
        verify(p, label)
        os.remove(p)
    except Exception as ex:
        import traceback; say(f"C9 {label} FAILED", repr(ex)); say(traceback.format_exc()[-1800:])

(WORK / "report.txt").write_text("\n".join(REPORT))
say("done")
