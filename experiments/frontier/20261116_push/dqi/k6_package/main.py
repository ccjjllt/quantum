"""Package the DQI dead-write candidate into a submission.zip and verify it.

Builds dqi.kmb (dead-write Toffoli deletion), packs invsqrt.kmb + dqi.kmb + dfthcsos/ from the
Hayato mirror dataset, verifies the packed DQI with the unchanged official verifier, prints hashes.
"""
import base64, io, zipfile, sys, pathlib, os, hashlib, lzma, json, time, struct, importlib.util, shutil

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
MIN_T_SAVING = int(os.environ.get("MIN_T", "300"))

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
    hh = sha256(KMB)
    say(f"A1 {src} size {KMB.stat().st_size} sha {hh} match={hh == PIN}")
    if hh == PIN:
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
nb = int(max(BIT.max(), COND.max())) + 1
say("A3 Q", Q, "n", n, "staticT", int(is3.sum()), "nbits", nb)

bitread = np.zeros(nb + 2, dtype=bool)
np.logical_or.at(bitread, COND[cond], True)
# global touch index: every (wire, op) operand pair, sorted by wire then op
tq = np.concatenate([A[A >= 0], B[B >= 0], C[C >= 0]])
to = np.concatenate([np.flatnonzero(A >= 0), np.flatnonzero(B >= 0), np.flatnonzero(C >= 0)])
o3 = np.lexsort((to, tq)); tq = tq[o3]; to = to[o3]
# dedupe identical (wire, op) pairs (HMR is both read and write of the same wire)
same = np.r_[False, (tq[1:] == tq[:-1]) & (to[1:] == to[:-1])]
tq = tq[~same]; to = to[~same]
tlo = np.searchsorted(tq, np.arange(Q + 2), "left")
say("B0 touch index", len(tq), "pairs")
dead_R = []; dead_H = []
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
say("B1 deadR", len(dead_R), "deadHMR", len(dead_H), "total T saving", len(set(dead_R) | set(dead_H)))
DEL = set(dead_R) | set(dead_H)

if len(DEL) >= MIN_T_SAVING:
    keep = np.ones(n, dtype=bool)
    keep[sorted(DEL)] = False
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
    raw = pack(hh, REGS, secs)
    CAND = TMP / "dqi_cand.kmb"
    CAND.write_bytes(raw)
    say("C0 candidate", CAND.stat().st_size, "sha", sha256(CAND),
        "staticT", int(np.isin(secs[1] & 127, [0x30, 0x31, 0x32]).sum()))
else:
    say("C0 SKIP packaging: T saving", len(DEL), "<", MIN_T_SAVING)
    CAND = KMB

# verify the candidate (or the original when skipped)
so = sorted(ROOT.rglob("kickmix.so"))
sys.path.insert(0, str(so[0].parent))
if "kickmix" in sys.modules:
    del sys.modules["kickmix"]
import kickmix as km
vpath = sorted(ROOT.rglob("verify_submission_dqi.py"))[0]
sp = importlib.util.spec_from_file_location("vdqi", str(vpath))
V = importlib.util.module_from_spec(sp); sys.modules["vdqi"] = V; sp.loader.exec_module(V)
spec = V.ProblemSpecDQI.benchmark_instance()
t = time.time()
res = V.verify(km.Circuit.from_file(str(CAND), format="kmb"), spec, salt="")
say(f"D0 verified {time.time()-t:.0f}s Q {res['num_qubits']} T {res['toffoli_count']:.3f} "
    f"score {res['score']:.3f} err {res['value_errors']}/{res['phase_errors']} sha {res['circuit_sha256']}")
say(f"D1 vs base {BASE_COST:.3f}: {res['score']-BASE_COST:+.3f} ({100*(res['score']/BASE_COST-1):+.6f}%)")

if res["status"] == "PASS" and CAND != KMB:
    SUB = WORK / "submission"
    if SUB.exists():
        shutil.rmtree(SUB)
    SUB.mkdir(parents=True)
    inv = sorted(ROOT.rglob("invsqrt.kmb"))[0]
    shutil.copyfile(inv, SUB / "invsqrt.kmb")
    shutil.copyfile(CAND, SUB / "dqi.kmb")
    chem = sorted(ROOT.rglob("submission.npz"))[0].parent
    (SUB / "dfthcsos").mkdir()
    shutil.copyfile(chem / "submission.npz", SUB / "dfthcsos" / "submission.npz")
    for i in range(15):
        shutil.copyfile(chem / f"angle_k_{i}.kmb", SUB / "dfthcsos" / f"angle_k_{i}.kmb")
    zp = WORK / "submission.zip"
    with zipfile.ZipFile(zp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(SUB.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(SUB).as_posix())
    say("E0 zip", zp.stat().st_size, sha256(zp))
    say("E1 members", {p.relative_to(SUB).as_posix(): sha256(p)[:16] for p in sorted(SUB.rglob("*")) if p.is_file()})
    shutil.rmtree(SUB)

(WORK / "report.txt").write_text("\n".join(REPORT))
say("done")
