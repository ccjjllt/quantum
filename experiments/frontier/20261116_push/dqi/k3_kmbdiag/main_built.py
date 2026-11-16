"""DQI 890Q fast diagnostic on the raw .kmb format (numpy only, no kickmix / kmx).

kmb: MAGIC(16) + "<4I9Q"(88) + chunks "<QQ" idx,size + payload
     idx0 register blob, secs[1]=ops secs[2..4]=a3,b3,t3 secs[5,6]=a2,t2 secs[7]=a1 secs[8]=cb secs[9]=conds
"""
import base64, io, zipfile, sys, pathlib, os, hashlib, lzma, json, time, struct

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

def sha256(path, chunk=1 << 24):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()

def unpack(raw):
    assert raw[:16] == MAGIC
    h = struct.unpack_from("<4I9Q", raw, 16)
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
h = None
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

t = time.time()
H, REGS, S = unpack(KMB.read_bytes())
log(f"unpack {time.time()-t:.0f}s regs {len(REGS)}")
say("A2 header", list(H))
say("A3 seclen", {k: len(v) for k, v in sorted(S.items())})
ops = S[1]; n = len(ops); base = ops & 127; cond = (ops & 128) != 0
nb = int(max(S[8].max(initial=0), S[9].max(initial=-1)) + 1)
say("A4 n_ops", n, "cond_ops", int(cond.sum()), "nbits", nb)
vals, cnts = np.unique(base, return_counts=True)
say("A5 opcodes", {hex(int(v)): int(c) for v, c in zip(vals, cnts)})
say("A6 cond-per-opcode", {hex(int(v)): int(cond[base == v].sum()) for v in vals})

is3 = np.isin(base, [0x30, 0x31, 0x32])
is2 = np.isin(base, [0x20, 0x21, 0x22])
is1 = np.isin(base, [0x10, 0x11, 0x12, 0x50])
say("A7 3q/2q/1q", int(is3.sum()), int(is2.sum()), int(is1.sum()))
A = np.full(n, -1, dtype=np.int32); B = np.full(n, -1, dtype=np.int32); C = np.full(n, -1, dtype=np.int32)
pref3 = np.cumsum(is3); pref2 = np.cumsum(is2); pref1 = np.cumsum(is1)
i3a = np.flatnonzero(is3); i2a = np.flatnonzero(is2); i1a = np.flatnonzero(is1)
A[i3a] = S[2][pref3[i3a] - 1]; B[i3a] = S[3][pref3[i3a] - 1]; C[i3a] = S[4][pref3[i3a] - 1]
A[i2a] = S[5][pref2[i2a] - 1]; C[i2a] = S[6][pref2[i2a] - 1]
A[i1a] = S[7][pref1[i1a] - 1]
Q = int(max(A.max(), B.max(), C.max())) + 1
say("A8 Q", Q)
say("A9 h-vs-derived", dict(h0=H[0], h1=H[1], h2=H[2], h3=H[3], Q=Q, nb=nb, n=n,
                             static=int(np.isin(base, [0x30, 0x31, 0x32]).sum())))
say("A10 register blob head", repr(b"".join(REGS)[:400]))

# registers: assume 0..839 (builder allocates registers first); verify with the blob text
blob = b"".join(REGS)
ql = sorted({int(t[1:]) for t in blob.replace(b"\x00", b" ").replace(b",", b" ").split()
             if t.startswith(b"q") and t[1:].isdigit()})
say("A11 blob q ids", len(ql), ql[:5], ql[-5:] if ql else None)
REG = np.arange(840, dtype=np.int64)
anc = np.arange(840, Q, dtype=np.int64)
say("A12 assumed registers 0..839, ancillas", anc.tolist())

# ---------------------------------------------------------------- B per-ancilla profile
cnt_w = np.bincount(np.concatenate([A[A >= 0], B[B >= 0], C[C >= 0]]).astype(np.int64), minlength=Q)
say("B0 op count per wire: least", sorted(zip(cnt_w.tolist(), range(Q)))[:6],
    "most", sorted(zip(cnt_w.tolist(), range(Q)))[-6:])
say("B1 ancilla op counts", [(int(w), int(cnt_w[w])) for w in anc])

READ1 = np.isin(base, [0x10, 0x11, 0x12, 0x50])
hmr = base == 0x50
ev = []
INFO = {}
for w in anc.tolist():
    m = (A == w) | (B == w) | (C == w)
    ks = np.flatnonzero(m)
    if len(ks) == 0:
        say("B2 wire", w, "UNUSED"); continue
    bp = base[ks]; ai = A[ks]; bi = B[ks]; ci = C[ks]; cd = cond[ks]
    close_k = ks[(bp == 0x50) & (ai == w) & ~cd]
    # reads / writes
    rd = np.zeros(len(ks), dtype=bool); wr = np.zeros(len(ks), dtype=bool)
    rd |= np.isin(bp, [0x10, 0x11, 0x12, 0x50]) & (ai == w)                     # 1q read (X/Z/HMR)
    rd |= (bp == 0x20)                                                          # CZ both read
    rd |= (bp == 0x21) & (ai == w)                                              # CX control
    rd |= (bp == 0x22)                                                          # SWAP both read
    rd |= (bp == 0x30)                                                          # CCZ all read
    rd |= (bp == 0x31) & ((ai == w) | (bi == w))                                # CCX controls
    rd |= (bp == 0x32)                                                          # CSWAP all read
    wr |= np.isin(bp, [0x10, 0x11, 0x12]) & (ai == w)                            # X flips
    wr |= (bp == 0x21) & (ci == w)                                              # CX target
    wr |= (bp == 0x31) & (ci == w)                                              # CCX target
    wr |= (bp == 0x30) & (ci == w)
    wr |= (bp == 0x32) & ((bi == w) | (ci == w))
    wr |= (bp == 0x22)
    wr |= (bp == 0x50) & (ai == w)
    rd_idx = ks[rd]; wr_idx = ks[wr]
    # conservative intervals: open at first touch after a close
    segs = []
    close_idx = np.searchsorted(ks, close_k)
    start_idx = 0
    for j in close_idx.tolist():
        if start_idx < j:
            segs.append((int(ks[start_idx]), int(ks[j])))
        start_idx = j + 1
    if start_idx < len(ks):
        segs.append((int(ks[start_idx]), n))
    for s, e in segs:
        ev.append((s, 1)); ev.append((e, -1))
    INFO[w] = dict(n=int(len(ks)), first=int(ks[0]), last=int(ks[-1]),
                   n_wr=int(wr.sum()), n_rd=int(rd.sum()),
                   last_rd=int(rd_idx[-1]) if len(rd_idx) else -1,
                   first_wr=int(wr_idx[0]) if len(wr_idx) else -1,
                   n_ccx_t=int(((bp == 0x31) & (ci == w)).sum()),
                   n_cx_t=int(((bp == 0x21) & (ci == w)).sum()),
                   n_1q_t=int((np.isin(bp, [0x10, 0x11, 0x12]) & (ai == w)).sum()),
                   n_hmr=int(len(close_k)),
                   n_ccx_c=int(((bp == 0x31) & ((ai == w) | (bi == w))).sum()),
                   n_2q=int(is2[ks].sum()), n_3q=int(is3[ks].sum()), n_1q=int(is1[ks].sum()),
                   define=dict(op=hex(int(base[ks[0]])), a=int(A[ks[0]]), b=int(B[ks[0]]), c=int(C[ks[0]])),
                   segs=[[int(s), int(e)] for s, e in segs][:8])
    say("B3", w, json.dumps(INFO[w]))
np.save(TMP / "meta.npy", np.array([json.dumps(INFO)], dtype=object))

ev.sort()
starts = np.array([x[0] for x in ev]); deltas = np.array([x[1] for x in ev])
cum = np.cumsum(deltas)
say("B4 conservative ancilla peak", int(cum.max()) if len(cum) else 0, "=> Q", 840 + int(cum.max() if len(cum) else 0))
grid = np.unique(np.r_[np.linspace(0, n, 41).astype(np.int64), [0, n - 1]])
idx = np.searchsorted(starts, grid, side="right") - 1
say("B5 ancilla live profile", [[int(g), int(cum[i]) if i >= 0 else 0] for g, i in zip(grid, idx)])

# true liveness: [first write, last read] per wire (single interval, upper bound on nothing)
ev2 = sorted([(INFO[w]["first_wr"], 1) for w in INFO] + [(max(INFO[w]["last_rd"], INFO[w]["first_wr"]) + 1, -1) for w in INFO])
cur = 0; best = 0
for k, d in ev2:
    cur += d; best = max(best, cur)
say("B6 single-interval true ancilla peak", best, "=> Q", 840 + best)

# ---------------------------------------------------------------- C what the peak looks like
pk = int(cum.max())
at = int(np.flatnonzero(cum >= pk)[0])
op_at = int(starts[max(at, 0)])
say("C0 peak op", op_at, "context")
for j in range(max(0, op_at - 6), min(n, op_at + 7)):
    say("C1", j, hex(int(base[j])), "cond" if cond[j] else "", int(A[j]), int(B[j]), int(C[j]))
live_anc = [w for w in INFO if any(s <= op_at < e for s, e in INFO[w]["segs"])]
say("C2 ancillas live at peak", live_anc, "count", len(live_anc))
say("C3 which ancillas have a segment covering the peak",
    [(w, [s for s in INFO[w]["segs"] if s[0] <= op_at < s[1]]) for w in live_anc])

(WORK / "report.txt").write_text("\n".join(REPORT))
try:
    KMB.unlink()
except OSError:
    pass
say("done")
