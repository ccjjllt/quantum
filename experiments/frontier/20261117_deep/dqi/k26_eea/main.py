"""DQI 575b043f: EEA-shape test of the 50-wire pool + a sound restorability bound.

PART 1 (structure).  Is the pool 4x12-bit (r0,r1,u0,u1) of an EEA, so that a
Proos-Zalka variable-length overlap can merge two words?
  S1 group triple census of every gate that touches a pool wire.
  S2 SWAP structure: a positional array shift swaps the SAME bit offset across
     DIFFERENT words; a bit shift inside one word swaps ADJACENT offsets.
  S3 live-bit complementarity: an overlap saves wires only if, at every op,
     live(A) + live(B) <= 12.  Measured per group (window model and
     consumer-trimmed model), plus the total pool peak, which is what a merge buys.

PART 2 (restorability).  The per-episode spill/refill cover needs only a few dozen
refills (kernel qcc-dqi-gaps-575b, qcc-dqi-restore-575b: 28 refills, 259 T for k=1),
so the counting cost is trivial and the whole question is whether a refill can
*restore the value*.  Restoring a value at a refill point R means replaying every
value-changing write into the wire since its window's reset, and every replay needs
its operand to still hold the value it held at the original write.  The FIRST write of
a window is the oldest, so its operands must survive the longest stretch: it is a
*necessary* condition for the whole chain, it is one comparison per gap, and therefore
it is a sound upper bound on what the mechanism can ever cover.  Measured as
`FOK` (first-operand-kept), plus the full-chain check on the intervals the cover
actually picks.

Read-only: no simulation, no verifier, no candidate, no submission.
"""
import hashlib
import lzma
import pathlib
import struct
import time

import numpy as np

REPORT = []
T0 = time.time()


def log(*a):
    s = " ".join(str(x) for x in a)
    s = f"[{time.time() - T0:6.1f}s] {s}"
    REPORT.append(s)
    print(s, flush=True)


MAGIC = bytes.fromhex("d750c7d5c329d326e3cc9f6834f2b8bf")
PINS = {
    "575b043f": "575b043f4fee91a0fc3a9fd6fc1e9290e7b2a0669cae79886be2bf999f7ec155",
    "61c8348d": "61c8348d6e85bb0259c4b89f14be9a2834c77bf8a680cf79959bf5e1089cf5de",
}
PREF = "575b043f"
GROUPS = [(840, 852), (852, 864), (864, 876), (876, 888), (888, 890)]
GNAME = ["W840-851", "W852-863", "W864-875", "W876-887", "F888-889"]
GN = ["syn"] + GNAME
WORK = pathlib.Path("/kaggle/working")
TMP = pathlib.Path("/tmp/dqik26")
TMP.mkdir(exist_ok=True)


def sha256(path, chunk=1 << 24):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


CANDS = [p for p in sorted(pathlib.Path("/kaggle/input").rglob("dqi*.kmb*"))
         if p.is_file() and "sample_submission" not in str(p)]
CANDS.sort(key=lambda p: (PREF not in p.name, p.suffix != ".xz"))
KMB, TAG = None, None
for src in CANDS:
    dst = TMP / "tape.kmb"
    with (lzma.open(src, "rb") if src.suffix == ".xz" else open(src, "rb")) as f, \
            open(dst, "wb") as g:
        while True:
            b = f.read(1 << 24)
            if not b:
                break
            g.write(b)
    sh = sha256(dst)
    tag = next((k for k, v in PINS.items() if v == sh), None)
    log(f"A0 {src.name} bytes {dst.stat().st_size} sha {sh[:16]} -> {tag}")
    if tag == PREF:
        KMB, TAG = dst, tag
        break
    if tag and KMB is None:
        KMB, TAG = dst, tag
if KMB is None:
    (WORK / "report.txt").write_text("\n".join(REPORT) + "\n")
    raise SystemExit("no pinned tape found")


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
            secs[idx] = np.frombuffer(pay, dtype=np.uint8 if idx == 1 else np.uint32).copy()
        pos += 16 + size
    return h, regs, secs


H, REGS, S = unpack(KMB.read_bytes())
ops = S[1]
n = int(len(ops))
base = ops & 127
del S[1]
i3 = np.isin(base, [0x30, 0x31, 0x32])
i2 = np.isin(base, [0x20, 0x21, 0x22])
i1 = np.isin(base, [0x10, 0x11, 0x12, 0x50])
A = np.full(n, -1, np.int32)
B = np.full(n, -1, np.int32)
C = np.full(n, -1, np.int32)
p3, p2, p1 = (np.cumsum(x, dtype=np.int32) for x in (i3, i2, i1))
q3, q2, q1 = (np.flatnonzero(x) for x in (i3, i2, i1))
A[q3] = S[2][p3[q3] - 1]
B[q3] = S[3][p3[q3] - 1]
C[q3] = S[4][p3[q3] - 1]
A[q2] = S[5][p2[q2] - 1]
C[q2] = S[6][p2[q2] - 1]
A[q1] = S[7][p1[q1] - 1]
del S, p3, p2, p1, q3, q2, q1
Q = int(max(A.max(), B.max(), C.max())) + 1
log(f"A1 Q={Q} n={n} staticT={int(i3.sum())}")

TGT = np.zeros(128, bool)
SWP = np.zeros(128, bool)
RST = np.zeros(128, bool)
TOF = np.zeros(128, bool)
TGT[[0x10, 0x12, 0x21, 0x31, 0x32, 0x50]] = True
SWP[0x22] = True
RST[[0x12, 0x50]] = True
TOF[[0x31, 0x32]] = True

GRP = np.full(Q + 1, -1, np.int8)
OFF = np.full(Q + 1, -1, np.int8)
for gi, (lo, hi) in enumerate(GROUPS):
    GRP[lo:hi] = gi
    OFF[lo:hi] = np.arange(hi - lo)


def g_of(arr):
    a = np.clip(arr, 0, Q)
    return np.where(arr >= 0, GRP[a].astype(np.int16), -1)


def o_of(arr):
    a = np.clip(arr, 0, Q)
    return np.where(arr >= 0, OFF[a].astype(np.int16), -1)


GA, GB, GC = g_of(A), g_of(B), g_of(C)
OA, OC = o_of(A), o_of(C)

# =============================================================== PART 1 structure
pool = (np.clip(A, 0, Q) >= 840) | (np.clip(B, 0, Q) >= 840) | (np.clip(C, 0, Q) >= 840)
log(f"B0 ops touching a pool wire {int(pool.sum())}")
for nm, m in (("CCX", base == 0x31), ("CX", base == 0x21), ("SWAP", base == 0x22),
              ("CCZ", base == 0x30), ("CZ", base == 0x20)):
    mm = m & pool
    if not mm.any():
        log(f"B1 {nm}: 0 pool ops")
        continue
    key = (GA[mm] + 1).astype(np.int32) * 49 + (GB[mm] + 1) * 7 + (GC[mm] + 1)
    u, c = np.unique(key, return_counts=True)
    o = np.argsort(-c)[:6]
    parts = []
    for k in o:
        v = int(u[k])
        parts.append(f"({GN[v // 49]},{GN[(v // 7) % 7]},{GN[v % 7]}) {int(c[k])}")
    log(f"B1 {nm}: {int(mm.sum())} pool ops [A,B,C] -> " + " | ".join(parts))

ms = SWP[base] & pool
sw_same_adj = int((ms & (GA == GC) & (np.abs(OA - OC) == 1)).sum())
sw_same_oth = int((ms & (GA == GC) & (np.abs(OA - OC) != 1)).sum())
sw_cross_same = int((ms & (GA != GC) & (GA >= 0) & (GC >= 0) & (OA == OC)).sum())
sw_cross_oth = int((ms & (GA != GC) & (GA >= 0) & (GC >= 0) & (OA != OC)).sum())
sw_mixed = int((ms & (((GA >= 0) & (GC < 0)) | ((GC >= 0) & (GA < 0)))).sum())
log(f"B2 SWAP touching pool {int(ms.sum())}: same word adjacent bit {sw_same_adj}, same word "
    f"other offset {sw_same_oth}, two words same bit {sw_cross_same}, two words other bit "
    f"{sw_cross_oth}, pool<->syndrome {sw_mixed}")
mc = (base == 0x21) & pool
log(f"B3 CX touching pool {int(mc.sum())}: pool->pool "
    f"{int((mc & (GA >= 0) & (GC >= 0)).sum())}, pool->syndrome "
    f"{int((mc & (GA >= 0) & (GC < 0)).sum())}, syndrome->pool "
    f"{int((mc & (GA < 0) & (GC >= 0)).sum())}")
m3 = (base == 0x31) & (GC >= 0)
log(f"B4 CCX targeting the pool {int(m3.sum())}: both controls in pool "
    f"{int((m3 & (GA >= 0) & (GB >= 0)).sum())}, one in pool "
    f"{int((m3 & ((GA >= 0) != (GB >= 0))).sum())}, none in pool "
    f"{int((m3 & (GA < 0) & (GB < 0)).sum())}")

tq = np.concatenate([A[A >= 0], B[B >= 0], C[C >= 0]])
to = np.concatenate([np.flatnonzero(A >= 0), np.flatnonzero(B >= 0), np.flatnonzero(C >= 0)])
o = np.lexsort((to, tq))
tq, to = tq[o], to[o]
del o
same = np.r_[False, (tq[1:] == tq[:-1]) & (to[1:] == to[:-1])]
tq, to = tq[~same], to[~same]
del same
NT = len(tq)
tlo = np.searchsorted(tq, np.arange(Q + 2), "left")
log(f"C0 touch pairs {NT}")
is_tgt = TGT[base[to]] | ((base[to] == 0x22) & (A[to] == tq))
PT = np.zeros(NT + 1, np.int32)
np.cumsum(is_tgt, out=PT[1:])


def n_tgt_between(x, a, b):
    lo, hi = int(tlo[x]), int(tlo[x + 1])
    if hi <= lo:
        return 0
    sub = to[lo:hi]
    j0 = int(np.searchsorted(sub, a, "right"))
    j1 = int(np.searchsorted(sub, b, "left"))
    return int(PT[lo + j1] - PT[lo + j0])


def next_tgt_after(x, a):
    """op of the first value-changing touch of x strictly after a, or a big number."""
    lo, hi = int(tlo[x]), int(tlo[x + 1])
    if hi <= lo:
        return 1 << 62
    sub = to[lo:hi]
    j = int(np.searchsorted(sub, a, "right"))
    while j < hi - lo:
        if PT[lo + j + 1] - PT[lo + j] > 0:
            return int(sub[j])
        j += 1
    return 1 << 62


def group_live(lo, hi, tight):
    d = np.zeros(n + 1, np.int32)
    for w in range(lo, hi):
        lo_i, hi_i = int(tlo[w]), int(tlo[w + 1])
        tp = to[lo_i:hi_i]
        if len(tp) == 0:
            continue
        bt = base[tp]
        tg = TGT[bt] | (SWP[bt] & (A[tp] == w))
        rstd = RST[bt] & tg
        bounds = np.r_[-1, np.flatnonzero(rstd), len(tp) - 1]
        los, his = [], []
        for k in range(len(bounds) - 1):
            a_, b_ = int(bounds[k]) + 1, int(bounds[k + 1])
            if b_ < a_:
                continue
            last = b_ - 1 if rstd[b_] else b_
            if tight:
                idx = np.flatnonzero((~tg[a_:last + 1]) | SWP[bt[a_:last + 1]]
                                     | (bt[a_:last + 1] == 0x50))
                if len(idx) == 0:
                    continue
                last = a_ + int(idx[-1])
            if last < a_:
                continue
            los.append(int(tp[a_])); his.append(int(tp[last]) + 1)
        if los:
            np.add.at(d, np.array(los, np.int32), 1)
            np.add.at(d, np.array(his, np.int32), -1)
    return np.cumsum(d)[:n].astype(np.int8)


for nm, tight in (("window", False), ("consumer-trimmed", True)):
    G = [group_live(lo, hi, tight) for lo, hi in GROUPS]
    tot = np.zeros(n, np.int16)
    for g in G:
        tot += g
    log(f"D0 [{nm}] per-group live peak " +
        ", ".join(f"{GNAME[i]} {int(G[i].max())}" for i in range(5)) +
        f"; TOTAL pool live peak {int(tot.max())} -> Q {840 + int(tot.max())}")
    for i in range(5):
        hist = np.bincount(G[i].astype(np.int64), minlength=13)[:13]
        log(f"D1 [{nm}] {GNAME[i]} live-count histogram " +
            " ".join(f"{k}:{int(hist[k])}" for k in range(13) if hist[k]))
    for i in range(5):
        for j in range(i + 1, 5):
            s = int((G[i].astype(np.int16) + G[j]).max())
            wi = GROUPS[i][1] - GROUPS[i][0]
            wj = GROUPS[j][1] - GROUPS[j][0]
            log(f"D2 [{nm}] {GNAME[i]}+{GNAME[j]}: max simultaneous live {s} -> merged "
                f"{s} wires vs separate {wi + wj} -> saves {wi + wj - s}")
    if not tight:
        mx = int(tot.max())
        mxops = tot == mx
        NPK = int(mxops.sum())
        peak_ops = np.flatnonzero(mxops).astype(np.int32)
        log(f"D3 pool-live peak {mx}, ops at peak {NPK}")
    del G, tot

# ============================================================ PART 2 restorability
GL, GR, GW, GT, GX, GNW, GOK, GFO = [], [], [], [], [], [], [], []
for w in range(840, Q):
    lo_i, hi_i = int(tlo[w]), int(tlo[w + 1])
    tp = to[lo_i:hi_i]
    if len(tp) == 0:
        continue
    bt = base[tp]
    tg = TGT[bt] | (SWP[bt] & (A[tp] == w))
    rstd = RST[bt] & tg
    isw = tg
    tofw = TOF[bt] & tg
    cxw = (bt == 0x21) & tg
    pf_tof = np.zeros(len(tp) + 1, np.int32); np.cumsum(tofw, out=pf_tof[1:])
    pf_cx = np.zeros(len(tp) + 1, np.int32); np.cumsum(cxw, out=pf_cx[1:])
    pf_w = np.zeros(len(tp) + 1, np.int32); np.cumsum(isw, out=pf_w[1:])
    bounds = np.r_[-1, np.flatnonzero(rstd), len(tp) - 1]
    for k in range(len(bounds) - 1):
        a_, b_ = int(bounds[k]) + 1, int(bounds[k + 1])
        if b_ - a_ < 1:
            continue
        j = np.arange(a_, b_)
        if len(j) == 0:
            continue
        Rg = tp[j + 1]
        GL.append(tp[j] + 1); GR.append(Rg)
        GW.append(np.full(len(j), w, np.int32))
        GT.append(pf_tof[j + 1] - pf_tof[a_])
        GX.append(pf_cx[j + 1] - pf_cx[a_])
        GNW.append(pf_w[j + 1] - pf_w[a_])
        # necessary condition: the window's FIRST value-changing write must still have
        # its operands at the refill point.
        idx0 = np.flatnonzero(isw[a_:b_ + 1])
        if len(idx0) == 0:
            allow = np.full(len(j), 1 << 62, np.int64)
        else:
            t0 = int(tp[a_ + int(idx0[0])])
            b0 = int(bt[a_ + int(idx0[0])])
            ops0 = []
            if b0 == 0x31:
                ops0 = [int(A[t0]), int(B[t0])]
            elif b0 == 0x21 or b0 == 0x10:
                ops0 = [int(A[t0])] if b0 == 0x21 else []
            elif b0 == 0x22:
                ops0 = [int(A[t0])] if int(C[t0]) == w else [int(C[t0])]
            allow = np.full(len(j), 1 << 62, np.int64)
            for x in ops0:
                if 0 <= x < Q and x != w:
                    allow = np.minimum(allow, next_tgt_after(x, t0))
        GFO.append(Rg <= allow)
GL = np.concatenate(GL).astype(np.int32)
GR = np.concatenate(GR).astype(np.int32)
GW = np.concatenate(GW).astype(np.int32)
GT = np.concatenate(GT).astype(np.int32)
GX = np.concatenate(GX).astype(np.int32)
GNW = np.concatenate(GNW).astype(np.int32)
GFO = np.concatenate(GFO)
LEN = (GR - GL).astype(np.int32)
log(f"E0 gaps {len(GL)}; length p50 {np.percentile(LEN, 50):.0f} "
    f"p90 {np.percentile(LEN, 90):.0f} p99 {np.percentile(LEN, 99):.0f} max {int(LEN.max())}")
log(f"E1 first-write-operand-kept (necessary for any replay) {int(GFO.sum())}/{len(GFO)} "
    f"({100.0 * GFO.mean():.2f}%)")
for thr in (0, 100, 1000, 10000, 100000):
    m = GFO & (LEN >= thr)
    log(f"E1   gaps kept with length >= {thr:6d}: {int(m.sum()):8d} "
        f"(of {int((LEN >= thr).sum()):8d} gaps that long)")

cov = np.zeros(n + 1, np.int32)
np.add.at(cov, GL, 1); np.add.at(cov, GR, -1)
covd = np.cumsum(cov)[:n]
covf = np.zeros(n + 1, np.int32)
np.add.at(covf, GL[GFO], 1); np.add.at(covf, GR[GFO], -1)
covfd = np.cumsum(covf)[:n]
log(f"E2 plateau ops inside >=1 gap: all gaps {int((covd[mxops] > 0).sum())}/{NPK}; "
    f"first-operand-kept gaps {int((covfd[mxops] > 0).sum())}/{NPK}")
del cov, covd, covf, covfd

order = np.argsort(GL, kind="stable")
Ls = GL[order]
KEY0 = (GR[order].astype(np.int64) << 24) | np.arange(len(Ls), dtype=np.int64)
Ts = GT[order].astype(np.int64)
FOs = GFO[order]
LNs = LEN[order]
Nw = GNW[order]
Ws = GW[order]
MASK = (1 << 24) - 1


def pack(L, R, T):
    o = np.argsort(L, kind="stable")
    return L[o], (R[o].astype(np.int64) << 24) | np.arange(len(o), dtype=np.int64), T[o]


def cover(Larr, key, Tarr):
    runkey = np.maximum.accumulate(key)
    t = int(peak_ops[0]); last = int(peak_ops[-1])
    cnt = tsum = 0
    picks = []
    while t <= last:
        j = int(np.searchsorted(Larr, t, "right")) - 1
        if j < 0:
            return cnt, tsum, picks, -1
        k = int(runkey[j])
        R = k >> 24
        if R <= t:
            return cnt, tsum, picks, -1
        p = k & MASK
        cnt += 1; tsum += int(Tarr[p]); picks.append(p)
        q = int(np.searchsorted(peak_ops, R))
        if q >= len(peak_ops):
            return cnt, tsum, picks, 1
        t = int(peak_ops[q])
    return cnt, tsum, picks, 1


c1, t1, picks1, rc1 = cover(Ls, KEY0, Ts)
log(f"E3 k=1 min cover, ALL gaps: {c1} refills replayT {t1} status {rc1}")
Lf, Kf, Tf = pack(GL[GFO], GR[GFO], GT[GFO])
c1f, t1f, picksf, rc1f = cover(Lf, Kf, Tf)
log(f"E4 k=1 min cover, first-operand-kept gaps only: refills {c1f} replayT {t1f} "
    f"status {rc1f}")
del Lf, Kf, Tf


def win_start(w, L):
    lo_i, hi_i = int(tlo[w]), int(tlo[w + 1])
    tp = to[lo_i:hi_i]
    bt = base[tp]
    tg = TGT[bt] | (SWP[bt] & (A[tp] == w))
    rstd = np.flatnonzero(RST[bt] & tg)
    j = int(np.searchsorted(tp, L - 1, "right")) - 1     # touch index of the gap's left end
    k = int(np.searchsorted(rstd, j, "right")) - 1
    return int(tp[int(rstd[k]) + 1]) if k >= 0 else int(tp[0])


def chain_ok(w, op_from, op_to, cap=60000):
    lo_i, hi_i = int(tlo[w]), int(tlo[w + 1])
    tp = to[lo_i:hi_i]
    j0 = int(np.searchsorted(tp, op_from, "left"))
    j1 = int(np.searchsorted(tp, op_to, "right"))
    tot = bad = 0
    ntof = ncx = 0
    for t in tp[j0:min(j1, j0 + cap)]:
        op = int(t)
        bb = int(base[op])
        if RST[bb]:
            continue
        tg = TGT[bb] or (bb == 0x22 and int(A[op]) == w)
        if not tg:
            continue
        tot += 1
        if TOF[bb]:
            ntof += 1
        elif bb == 0x21:
            ncx += 1
        if bb == 0x31:
            ops_ = (int(A[op]), int(B[op]))
        elif bb == 0x21:
            ops_ = (int(A[op]),)
        elif bb == 0x22:
            ops_ = (int(A[op]),) if int(C[op]) == w else (int(C[op]),)
        else:
            ops_ = ()
        for x in ops_:
            if x < 0 or x == w:
                continue
            if n_tgt_between(x, op, op_to) != 0:
                bad += 1
                break
    return tot, bad, ntof, ncx


log("E5 full-chain replay check on the k=1 picks (chain = the whole window prefix):")
for p in picks1[:14]:
    w = int(Ws[p]); L = int(Ls[p]); R = int(KEY0[p] >> 24)
    ws = win_start(w, L)
    tot, bad, ntof, ncx = chain_ok(w, ws, R)
    log(f"E5   q{w} [{L},{R}) len {R - L} window-from {ws} chain {int(Nw[p])} "
        f"T {int(Ts[p])} | checked writes {tot} (T {ntof} CX {ncx}) operands stale {bad} "
        f"first-op-kept {bool(FOs[p])}")

used = np.zeros(len(Ls), bool)
cum_c = cum_t = 0
log("E6 k-fold cover, all gaps (distinct intervals):")
out = {}
for j in range(1, 51):
    key = np.where(used, -1, KEY0)
    c, t, pk, rc = cover(Ls, key, Ts)
    if rc != 1:
        log(f"E6 layer {j} FAILED (status {rc})")
        break
    for p in pk:
        used[p] = True
    cum_c += c; cum_t += t
    out[j] = (cum_c, cum_t)
    if j <= 3 or j % 5 == 0:
        log(f"E6   k={j:2d}: refills {cum_c} (+{c}) replayT {cum_t} (+{t}) "
            f"-> {cum_t / j:.1f} T/qubit")
log(f"E6 layers completed {len(out)}")

log("")
log("SUMMARY  k  Q   refills  replayT  T/qubit   (all gaps, unconstrained)")
for k in (1, 3, 5, 10, 25, 50):
    if k in out:
        cc, tt = out[k]
        log(f"SUM {k:2d} {890 - k:4d} {cc:8d} {tt:8d} {tt / k:9.1f}")

(WORK / "report.txt").write_text("\n".join(REPORT) + "\n")
log("done")
