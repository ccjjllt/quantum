"""DQI 890Q: test the "borrow the carry bank for the 24 helper bits" hypothesis.

(1) tape-level overlap: for every true use window [write, last read] of a helper wire (864..887),
    does any carry-bank wire (840..863) get touched inside it?
(2) value-level: 256-lane bit-sliced scan of the official DQI input distribution;
    per-ancilla count of ops where the wire holds 0 on every lane, and the semistatic width
    (statically live ancillas that are 0) along the tape.
"""
import base64, io, zipfile, sys, pathlib, os, hashlib, lzma, json, time, struct

t00 = time.time()
def log(*a):
    print(f"[{time.time()-t00:7.1f}s]", *a, flush=True)

WORK = pathlib.Path("/kaggle/working")
TMP = pathlib.Path("/tmp/dqi"); TMP.mkdir(exist_ok=True)
QS = TMP / "pkg"; QS.mkdir(exist_ok=True)
zipfile.ZipFile(io.BytesIO(base64.b64decode(QQB64))).extractall(QS)
sys.path.insert(0, str(QS))
import numpy as np
from qccscope import kmx, liveness as L, values as Vv

REPORT = []
def say(*a):
    s = " ".join(str(x) for x in a)
    REPORT.append(s); print(s, flush=True)

MAGIC = bytes.fromhex("d750c7d5c329d326e3cc9f6834f2b8bf")
ROOT = pathlib.Path("/kaggle/input")
PIN = "ccc2ab84ed713901c5642c58890fc664a16a4842c1ebdc80edb56b11c96d6c8d"

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
is1 = np.isin(base, [0x10, 0x11, 0x12, 0x50])
A = np.full(n, -1, dtype=np.int32); B = np.full(n, -1, dtype=np.int32); C = np.full(n, -1, dtype=np.int32)
pref3 = np.cumsum(is3); pref2 = np.cumsum(is2); pref1 = np.cumsum(is1)
i3a = np.flatnonzero(is3); i2a = np.flatnonzero(is2); i1a = np.flatnonzero(is1)
A[i3a] = S[2][pref3[i3a] - 1]; B[i3a] = S[3][pref3[i3a] - 1]; C[i3a] = S[4][pref3[i3a] - 1]
A[i2a] = S[5][pref2[i2a] - 1]; C[i2a] = S[6][pref2[i2a] - 1]
A[i1a] = S[7][pref1[i1a] - 1]
Q = int(max(A.max(), B.max(), C.max())) + 1
say("A3 Q", Q, "n", n)

CARRY = list(range(840, 864))
HELP = list(range(864, 888))
EXTRA = [888, 889]

# ---------------------------------------------------------------- (1) overlap analysis
say("B0 overlap: helper use windows vs carry-bank touches")
# touch arrays
tq = np.concatenate([A[A >= 0], B[B >= 0], C[C >= 0]])
to = np.concatenate([np.flatnonzero(A >= 0), np.flatnonzero(B >= 0), np.flatnonzero(C >= 0)])
o3 = np.lexsort((to, tq)); tq = tq[o3]; to = to[o3]
same = np.r_[False, (tq[1:] == tq[:-1]) & (to[1:] == to[:-1])]
tq = tq[~same]; to = to[~same]
tlo = np.searchsorted(tq, np.arange(Q + 2), "left")
say("B1 touch pairs", len(tq))

carry_touch = np.zeros(n + 2, dtype=np.int32)
for w in CARRY:
    lo, hi = tlo[w], tlo[w + 1]
    carry_touch[to[lo:hi]] += 1
carry_cum = np.cumsum(carry_touch)
say("B2 carry touches total", int(carry_touch.sum()))

# value-level use windows for helper wires: [write, last read]
WRITE31 = {0x31: 2, 0x30: 2, 0x32: 1}
rows = []
for w in HELP:
    lo, hi = tlo[w], tlo[w + 1]
    ks = to[lo:hi]
    bp = base[ks]; ai = A[ks]; bi = B[ks]; ci = C[ks]
    wr = ((bp == 0x31) & (ci == w)) | ((bp == 0x30) & (ci == w)) | \
         ((bp == 0x21) & (ci == w)) | ((bp == 0x10) & (ai == w)) | ((bp == 0x11) & (ai == w)) | \
         ((bp == 0x12) & (ai == w)) | ((bp == 0x50) & (ai == w))
    rd = np.zeros(len(ks), bool)
    rd |= (bp == 0x21) & (ai == w)
    rd |= (bp == 0x31) & ((ai == w) | (bi == w))
    rd |= (bp == 0x30) | (bp == 0x32) | (bp == 0x20) | (bp == 0x22)
    rd |= ((bp == 0x10) | (bp == 0x11) | (bp == 0x50)) & (ai == w)
    # group into (write -> last read) windows
    wins = []
    cur_w = -1; lastr = -1
    for k, wf, rf in zip(ks.tolist(), wr.tolist(), rd.tolist()):
        if wf:
            if cur_w >= 0 and lastr >= cur_w:
                wins.append((cur_w, lastr))
            cur_w = k; lastr = -1
        if rf:
            lastr = k
    if cur_w >= 0 and lastr >= cur_w:
        wins.append((cur_w, lastr))
    hit = 0; tot = 0; hitlen = 0; tots = 0
    for s, e in wins:
        tot += 1
        tots += e - s + 1
        c = int(carry_cum[e] - carry_cum[s - 1]) if s > 0 else int(carry_cum[e])
        if c > 0:
            hit += 1; hitlen += e - s + 1
    rows.append(dict(w=w, windows=tot, win_ops=tots, windows_with_carry_touch=hit,
                     frac_windows=round(hit / max(tot, 1), 4),
                     ops_inside_carry_touch=hitlen))
    say("B3", json.dumps(rows[-1]))

# ---------------------------------------------------------------- (2) value scan
say("C0 building kmx via kickmix for the value scan")
so = sorted(ROOT.rglob("kickmix.so"))
sys.path.insert(0, str(so[0].parent))
if "kickmix" in sys.modules:
    del sys.modules["kickmix"]
import kickmix as km
KMX = TMP / "dqi.kmx"
t = time.time()
km.Circuit.from_file(str(KMB), format="kmb").to_file(str(KMX), format="kmx")
say(f"C1 kmx {KMX.stat().st_size} in {time.time()-t:.0f}s")
t = time.time()
circ = kmx.parse(str(KMX))
say(f"C2 parse {time.time()-t:.0f}s ops {circ.n_ops} Q {circ.num_qubits} regs {len(circ.regs)} bits {circ.num_bits}")
KMX.unlink()

t = time.time()
lv = L.compute(circ, keep_intervals=False)
wd = lv.width
say(f"C3 liveness {time.time()-t:.0f}s peak {lv.peak}")

LANES = 256
t = time.time()
inp = Vv.inputs_dqi(circ, LANES)
V = Vv.run(circ, inp, S=LANES, min_gap=64)
say(f"C4 value scan {time.time()-t:.0f}s lanes {V.lanes} execT {V.toffoli_exec_mean:.1f} end {V.end_ok}")
say("C5 const0", len(V.const0), "affine", len(V.affine), "repeats", len(V.repeats),
    "zero_gaps", len(V.zero_gaps))

red = Vv.gap_width_reduction(circ.n_ops, V.zero_gaps, wd)
w2 = wd.astype(np.int64) - red
say("C6 static peak", int(wd.max()), "semistatic peak", int(w2.max()),
    "ops where semistatic<=866", int((w2 <= 866).sum()))
grid = np.linspace(0, circ.n_ops, 25).astype(np.int64)
say("C7 width vs semistatic",
    [[int(g), int(wd[g]), int(w2[g])] for g in grid])
say("C8 semistatic peak episodes",
    [(int(a), int(b)) for a, b in
     (lambda o: (np.r_[o[0], o[np.flatnonzero(np.diff(o) > 1) + 1]] if len(o) else [],
                 np.r_[o[np.flatnonzero(np.diff(o) > 1)], o[-1]] if len(o) else []))(
         np.flatnonzero(w2 >= w2.max()))])

# ---------------------------------------------------------------- (3) which ancillas are zero at the peak
pk_ops = np.flatnonzero(wd >= lv.peak)
mid = int(pk_ops[0])
say("D0 peak width", int(lv.peak), "ops at peak", len(pk_ops), "first peak op", mid)
# per-ancilla zero count on sampled lanes: recompute a targeted scan storing per-wire zero-ness is
# expensive; instead reuse zero_gaps: a gap (w, a, b) means w held 0 from a+1..b-1
gap_by_wire = {}
for (w, a, b) in V.zero_gaps:
    gap_by_wire.setdefault(w, []).append((a, b))
cov = []
for w in range(840, circ.num_qubits):
    ivs = gap_by_wire.get(w, [])
    # coverage over the peak plateau
    cov_ops = 0
    for a, b in ivs:
        lo = max(a + 1, int(pk_ops[0])); hi = min(b - 1, int(pk_ops[-1]))
        if hi > lo:
            cov_ops += hi - lo
    cov.append((w, len(ivs), cov_ops, round(cov_ops / max(1, int(pk_ops[-1] - pk_ops[0] + 1)), 3)))
say("D1 ancilla zero-coverage over the plateau (wire, gaps, ops, frac)")
for c in cov:
    say("D2", json.dumps(c))

(WORK / "report.txt").write_text("\n".join(REPORT))
try:
    KMB.unlink()
except OSError:
    pass
say("done")
