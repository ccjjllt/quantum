"""CSWAP/CCZ completion scan of the v12 889Q build (option-2 patch test).

Builds the pinned source (expect sha 7cbe8ecf...), then runs the EXACT
sound-deletion scans that the k4/k9 CCX-only pass did not cover:

  C0  CCX cancel pairs with CANONICALIZED control order (catches (a,b)/(b,a))
  C0z CCZ cancel pairs (CCZ is fully symmetric; diagonal => no read-check needed,
      only equal write-versions + unconditional on both gates)
  C0s CSWAP cancel pairs (same (f,a,b) write-versions, no touch of a/b between,
      unconditional on both gates) -- the patch-version of the CSWAP lever:
      any hit here is a same-Q T deletion with no redesign.
  C1  degenerate operands (CCX a==b, CSWAP b==t)
  C2  |0>-control Toffoli-likes
  C3  dead writes to R / unused HMR

If total saving >= 200 a candidate is packed and verified with the unchanged
official verifier (default salt). Otherwise no candidate (expected).
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
m30 = base == 0x30; m32 = base == 0x32
m1 = np.isin(base, [0x10, 0x11, 0x12]); m50 = base == 0x50
# WRITE index: CCX/CX targets, both SWAP operands, all 1q wires, HMR wires,
# plus both CSWAP targets (tape order is cswap(f,a,b) -> A=f,B=a,C=b, so the
# targets are B[m32],C[m32]). CCZ writes nothing. (k9 omitted CSWAP writes.)
wq = np.concatenate([C[m31], C[m21], A[m22], C[m22], B[m32], C[m32], A[m1], A[m50]])
wo = np.concatenate([np.flatnonzero(m31), np.flatnonzero(m21), np.flatnonzero(m22), np.flatnonzero(m22),
                     np.flatnonzero(m32), np.flatnonzero(m32), np.flatnonzero(m1), np.flatnonzero(m50)])
o1 = np.lexsort((wo, wq)); wq = wq[o1]; wo = wo[o1]
# READ index: k9's set plus CCZ (all three operands) and CSWAP (all three)
# operands as readers (k9 missed these: a CCZ/CSWAP read of a CCX target
# between two CCX would have made a C0 pair unsound).
rq = np.concatenate([A[m31], B[m31], A[m21], A[m20], C[m20], A[m22], C[m22],
                     A[m30], B[m30], C[m30], A[m32], B[m32], C[m32], A[m1], A[m50]])
ro = np.concatenate([np.flatnonzero(m31), np.flatnonzero(m31), np.flatnonzero(m21), np.flatnonzero(m20),
                     np.flatnonzero(m20), np.flatnonzero(m22), np.flatnonzero(m22),
                     np.flatnonzero(m30), np.flatnonzero(m30), np.flatnonzero(m30),
                     np.flatnonzero(m32), np.flatnonzero(m32), np.flatnonzero(m32),
                     np.flatnonzero(m1), np.flatnonzero(m50)])
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
    ca = (a, nwr(a, k)); cb = (b, nwr(b, k))
    if ca > cb:
        ca, cb = cb, ca
    key = (ca, cb, t, nwr(t, k))
    prev = seen.pop(key, None)
    if prev is not None:
        if nrd(t, prev, k) == 0 and not COND[prev] and not COND[k]:
            cancel.append((prev, k))
        continue
    seen[key] = k
say("C0 canonical-CCX cancel pairs", len(cancel), cancel[:8])

# CCZ cancel pairs: CCZ is diagonal and fully symmetric in its three operands,
# so equal write-versions on all three + unconditional on both gates suffices.
m30 = base == 0x30
seen_z = {}; cancel_z = []
for k in np.flatnonzero(m30).tolist():
    a = int(A[k]); b = int(B[k]); t = int(C[k])
    key = tuple(sorted(((a, nwr(a, k)), (b, nwr(b, k)), (t, nwr(t, k)))))
    prev = seen_z.pop(key, None)
    if prev is not None:
        if not COND[prev] and not COND[k]:
            cancel_z.append((prev, k))
        continue
    seen_z[key] = k
say("C0z CCZ cancel pairs", len(cancel_z), cancel_z[:8])

# CSWAP cancel pairs: two identical cswap(f,a,b) with equal write-versions and
# no touch of either target a/b strictly between (f is a pure control), both
# unconditional. Any hit is a same-Q T deletion needing no redesign.
m32 = base == 0x32
seen_s = {}; cancel_s = []
for k in np.flatnonzero(m32).tolist():
    f = int(A[k]); a = int(B[k]); b = int(C[k])
    key = (f, nwr(f, k), a, nwr(a, k), b, nwr(b, k))
    prev = seen_s.pop(key, None)
    if prev is not None:
        blocked = False
        for w in (a, b):
            lo, hi = TLO[w], TLO[w + 1]
            seg = TO[lo:hi]
            if int(np.searchsorted(seg, k, "left") - np.searchsorted(seg, prev, "right")):
                blocked = True
                break
        if not blocked and not COND[prev] and not COND[k]:
            cancel_s.append((prev, k))
        continue
    seen_s[key] = k
say("C0s CSWAP cancel pairs", len(cancel_s), cancel_s[:8])

# Degenerate operand sets. Two distinct classes (k9 lumped them; split here):
#  - FOLDs (need a rewrite, not a deletion, so NOT added to DEL):
#      CCX(a,a->t) == CX(a->t); CCZ with any two equal operands == CZ on the
#      distinct pair. Both fold 1 T -> 0 T but must be rewritten, not dropped.
#  - DELs (sound deletions): CSWAP(f,a,a) == identity.
fold = []
deg_del = []
for k in np.flatnonzero(is3).tolist():
    o = int(base[k]); a = int(A[k]); b = int(B[k]); t = int(C[k])
    if o == 0x31 and a == b:
        fold.append((k, "ccx-a==b->cx"))
    elif o == 0x30 and (a == b or b == t or a == t):
        fold.append((k, "ccz-dup->cz"))
    elif o == 0x32 and b == t:
        deg_del.append((k, "swap-same"))
say("C1 folds (rewrite, not counted)", len(fold), fold[:8])
say("C1b degenerate deletions", len(deg_del), deg_del[:8])

# |0>-control
bitread = np.zeros(int(max(BIT.max(), COND.max())) + 2, dtype=bool)
np.logical_or.at(bitread, COND[cond], True)
zero_ctl = []
for k in np.flatnonzero(is3).tolist():
    o = int(base[k]); a = int(A[k]); b = int(B[k]); t = int(C[k])
    if cond[k]:
        continue
    for w in ((a, b, t) if o == 0x30 else ((a, b) if o == 0x31 else (a,))):
        lo, hi = WLO[w], WLO[w + 1]
        j = int(np.searchsorted(wo[lo:hi], k, "left"))
        if j and int(base[wo[lo + j - 1]]) in (0x12, 0x50):
            zero_ctl.append(k); break
say("C2 |0>-control Toffolis", len(zero_ctl), zero_ctl[:8])

# dead writes (CCX/CCZ only). CSWAP is EXCLUDED: cswap(f,a,b) followed by R(a)
# is not deletable (it also moved b); k9's C3 would have misfired there.
# CCX(a,b->t) then R(t) with no touch of t between: sound (controls untouched).
# CCZ(a,b,c) then R(c) with no touch of c between: sound (diagonal phases are
# invisible to the CPTP reset: Tr_c(D.rho.D) = Tr_c(rho) for diagonal D).
dead_R = []; dead_H = []
for k in np.flatnonzero(is3 & (base != 0x32)).tolist():
    o = int(base[k])
    targets = (int(C[k]),) if o == 0x31 else (int(A[k]), int(B[k]), int(C[k]))
    for t in targets:
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
            dead_R.append(k); break
        elif o2_ == 0x50 and not bitread[int(BIT[nk])]:
            dead_H.append(k); break
say("C3 dead to R", len(dead_R), "dead to unused HMR", len(dead_H))

DEL = set()
for a, b in cancel:
    DEL.add(a); DEL.add(b)
for a, b in cancel_z:
    DEL.add(a); DEL.add(b)
for a, b in cancel_s:
    DEL.add(a); DEL.add(b)
DEL |= {k for k, _ in deg_del}
DEL |= set(zero_ctl) | set(dead_R) | set(dead_H)
saving = (2 * (len(cancel) + len(cancel_z) + len(cancel_s)) + len(deg_del)
          + len(zero_ctl) + len(dead_R) + len(dead_H))
say("C4 total sound deletions", len(DEL), "implied T saving", saving,
    "=> T ~", int(is3.sum()) - saving)
say("C4b folds available (need rewrite, not packaged here)", len(fold))
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
