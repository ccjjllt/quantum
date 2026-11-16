"""T-axis audit of the v12 889Q build: build it, then scan the tape for every sound Toffoli
deletion class and, if any exist, verify the patched circuit.

Arithmetic that decides whether this line can matter at all:
  today  (890Q, T=368,139.49) = 347.375e9
  a v12-derived 889Q circuit ties that only if T <= 368,940  (-3.7% vs 383,156)
"""
import hashlib, os, pathlib, shutil, subprocess, sys, zipfile, time, struct, json, importlib.util

t0 = time.time()
def log(*a):
    print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)

ROOT = pathlib.Path("/kaggle/input")
WORK = pathlib.Path("/kaggle/working")
TMP = pathlib.Path("/tmp/build"); TMP.mkdir(parents=True, exist_ok=True)
PIN = "7cbe8ecf6f6e9743529b574f019504bb1712ce06fbb570c719ce9d9e2c914cd9"
BASE_COST = 347375470571.73334
MAGIC = bytes.fromhex("d750c7d5c329d326e3cc9f6834f2b8bf")
import numpy as np

REPORT = []
def say(*a):
    s = " ".join(str(x) for x in a)
    REPORT.append(s); print(s, flush=True)

# ---------------------------------------------------------------- 1. build v12
tree = sorted(ROOT.rglob("build.sh"))[0].parent
SRC = TMP / "src"
if SRC.exists():
    shutil.rmtree(SRC)
shutil.copytree(tree, SRC)
ENGINE = sorted(ROOT.rglob("kickmix.so"))[0].parent
VERIF = sorted(ROOT.rglob("verify_submission_dqi.py"))[0].parent.parent
OUT = TMP / "out"; OUT.mkdir(exist_ok=True)
for rel, srcp in (("pro1_controller_bundle/1_task/official/kickmix.so", ENGINE / "kickmix.so"),
                  ("pro1_controller_bundle/1_task/verifiers/dqi/verify_submission_dqi.py",
                   VERIF / "dqi" / "verify_submission_dqi.py")):
    dst = SRC / "src" / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists():
        shutil.copyfile(srcp, dst)
env = dict(os.environ); env["PY"] = "python3.13"; env["WORK"] = str(TMP / "work")
p = subprocess.run(["bash", "build.sh", str(ENGINE), str(VERIF), str(OUT)], cwd=str(SRC),
                   env=env, capture_output=True, text=True, timeout=7200)
KMB = OUT / "dqi.kmb"
say("BUILD", p.returncode, KMB.stat().st_size if KMB.exists() else None,
    hashlib.sha256(KMB.read_bytes()).hexdigest() if KMB.exists() else None)
if not KMB.exists():
    print((p.stderr or "")[-3000:], flush=True); raise SystemExit(1)

# ---------------------------------------------------------------- 2. unpack
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
    st = int(np.isin(ops & 127, [0x30, 0x31, 0x32]).sum())
    hh = list(h); hh[4] = len(ops); hh[5] = st
    hh[6] = len(secs[5]); hh[7] = len(secs[7]); hh[8] = len(secs[8]); hh[9] = len(secs[9])
    hdr = MAGIC + struct.pack("<4I9Q", *[int(x) for x in hh[:13]])
    chunks = [hdr] + [struct.pack("<QQ", 0, len(r)) + r for r in regs]
    for i in range(1, 12):
        pay = secs[i].tobytes() if i <= 9 else secs[i]
        chunks.append(struct.pack("<QQ", i, len(pay)) + pay)
    return b"".join(chunks)

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
vals, cnts = np.unique(base, return_counts=True)
say("A4 opcodes", {hex(int(v)): int(c) for v, c in zip(vals, cnts)})

# ---------------------------------------------------------------- 3. scans
def touch_index():
    tq = np.concatenate([A[A >= 0], B[B >= 0], C[C >= 0]])
    to = np.concatenate([np.flatnonzero(A >= 0), np.flatnonzero(B >= 0), np.flatnonzero(C >= 0)])
    o = np.lexsort((to, tq)); tq = tq[o]; to = to[o]
    same = np.r_[False, (tq[1:] == tq[:-1]) & (to[1:] == to[:-1])]
    return tq[~same], to[~same]

TQ, TO = touch_index()
TLO = np.searchsorted(TQ, np.arange(Q + 2), "left")
say("B0 touch pairs", len(TQ))

m31 = base == 0x31; m21 = base == 0x21; m22 = base == 0x22; m20 = base == 0x20
m1 = np.isin(base, [0x10, 0x11, 0x12]); m50 = base == 0x50
wq = np.concatenate([C[m31], C[m21], A[m22], C[m22], A[m1], A[m50]])
wo = np.concatenate([np.flatnonzero(m31), np.flatnonzero(m21), np.flatnonzero(m22), np.flatnonzero(m22),
                     np.flatnonzero(m1), np.flatnonzero(m50)])
o1 = np.lexsort((wo, wq)); wq = wq[o1]; wo = wo[o1]
rq = np.concatenate([A[m31], B[m31], A[m21], A[m20], C[m20], A[m22], C[m22], A[m1], A[m50]])
ro = np.concatenate([np.flatnonzero(m31), np.flatnonzero(m31), np.flatnonzero(m21), np.flatnonzero(m20),
                     np.flatnonzero(m20), np.flatnonzero(m22), np.flatnonzero(m22), np.flatnonzero(m1),
                     np.flatnonzero(m50)])
o2 = np.lexsort((ro, rq)); rq = rq[o2]; ro = ro[o2]
WLO = np.searchsorted(wq, np.arange(Q + 1), "left")
RLO = np.searchsorted(rq, np.arange(Q + 1), "left")

def nwr(w, k):
    lo, hi = WLO[w], WLO[w + 1]
    return int(np.searchsorted(wo[lo:hi], k, "left"))
def nrd(w, k1, k2):
    lo, hi = RLO[w], RLO[w + 1]
    seg = ro[lo:hi]
    return int(np.searchsorted(seg, k2, "left") - np.searchsorted(seg, k1, "right"))

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
say("C0 exact cancel pairs", len(cancel), cancel[:8])

# Toffolis with a degenerate operand set
deg = []
for k in np.flatnonzero(is3).tolist():
    o = int(base[k]); a = int(A[k]); b = int(B[k]); t = int(C[k])
    if o in (0x30, 0x31) and a == b:
        deg.append((k, "a==b"))
    elif o == 0x32 and b == t:
        deg.append((k, "swap-same"))
say("C1 degenerate Toffolis", len(deg), deg[:8])

# |0>-control
bitread = np.zeros(int(max(BIT.max(), COND.max())) + 2, dtype=bool)
np.logical_or.at(bitread, COND[cond], True)
zero_ctl = []
for k in np.flatnonzero(is3).tolist():
    o = int(base[k]); a = int(A[k]); b = int(B[k])
    if cond[k]:
        continue
    for w in ((a, b) if o in (0x30, 0x31) else (a,)):
        lo, hi = WLO[w], WLO[w + 1]
        j = int(np.searchsorted(wo[lo:hi], k, "left"))
        if j and int(base[wo[lo + j - 1]]) in (0x12, 0x50):
            zero_ctl.append(k); break
say("C2 |0>-control Toffolis", len(zero_ctl), zero_ctl[:8])

# dead writes
dead_R = []; dead_H = []
for k in np.flatnonzero(is3).tolist():
    t = int(C[k])
    lo, hi = TLO[t], TLO[t + 1]
    seg = TO[lo:hi]
    j = int(np.searchsorted(seg, k, "right"))
    if j >= len(seg):
        continue
    nk = int(seg[j])
    if cond[nk] or A[nk] != t:
        continue
    o2_ = int(base[nk])
    if o2_ == 0x12:
        dead_R.append(k)
    elif o2_ == 0x50 and not bitread[int(BIT[nk])]:
        dead_H.append(k)
say("C3 dead to R", len(dead_R), "dead to unused HMR", len(dead_H))

DEL = set()
for a, b in cancel:
    DEL.add(a); DEL.add(b)
DEL |= {k for k, _ in deg}
DEL |= set(zero_ctl) | set(dead_R) | set(dead_H)
saving = 2 * len(cancel) + len(deg) + len(zero_ctl) + len(dead_R) + len(dead_H)
say("C4 total sound deletions", len(DEL), "implied T saving", saving,
    "=> T ~", int(is3.sum()) - saving)
say("C5 needed for v12 to tie the 890 tape: T <= 368940 (saving >= %d)" % (int(is3.sum()) - 368940))

# ---------------------------------------------------------------- 4. verify the patched circuit if it can matter
if saving >= 200:
    keep = np.ones(n, dtype=bool); keep[sorted(DEL)] = False
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
    hh = list(H); hh[1] = Q
    CAND = TMP / "cand.kmb"; CAND.write_bytes(pack(hh, REGS, secs))
    say("D0 candidate", CAND.stat().st_size, hashlib.sha256(CAND.read_bytes()).hexdigest()[:16])
    sys.path.insert(0, str(ENGINE))
    if "kickmix" in sys.modules:
        del sys.modules["kickmix"]
    import kickmix as km
    sp = importlib.util.spec_from_file_location("vdqi", str(VERIF / "dqi" / "verify_submission_dqi.py"))
    V = importlib.util.module_from_spec(sp); sys.modules["vdqi"] = V; sp.loader.exec_module(V)
    spec = V.ProblemSpecDQI.benchmark_instance()
    r = V.verify(km.Circuit.from_file(str(CAND), format="kmb"), spec, salt="")
    say("D1", {k: r[k] for k in ("status", "score", "num_qubits", "toffoli_count",
                                 "value_errors", "phase_errors")})
    say("D2 vs the 890 tape", BASE_COST, r["score"] - BASE_COST, 100 * (r["score"] / BASE_COST - 1))
else:
    say("D0 no candidate: the v12 T surface is saturated too")

(WORK / "report.txt").write_text("\n".join(REPORT))
say("done")
