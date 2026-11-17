"""DQI 575b043f: per-episode spill/refill = exact k-fold interval cover of the
peak-live plateau by the tape's real touch gaps.  Read-only.

WHY THIS KERNEL
---------------
Q = 890 = 840 syndrome + 50 pool wires, and the pool-live peak is 50 at every op of
a 961-episode plateau (2,760,326 ops).  To run with Q = 890-k we must make >= k pool
wires *absent* at every one of those ops, and a wire can only be absent at an op where
it is not touched.  A wire is free only inside a gap between two consecutive touches of
the same reset-delimited window; a gap that straddles a reset is already free in the
width model.  Dropping a wire over a gap costs refills, so the minimum number of
refills that buys k qubits is the k-fold interval cover of the plateau point set by the
family of all such gaps.  This is the "per-episode spill/refill" mechanism: a wire is
recomputed just often enough to be absent at every plateau op, and is allowed to be
dirty in between - unlike the full-window recompute table, which charges one rebuild
per whole window.

Refill cost model (exact integer count from the tape): a wire w dropped after touch j
must be restored before touch j+1.  Its value is the XOR-accumulation of every write
since the window's reset, so an honest restore replays every Toffoli write into w in
[window start .. j].  CX replays cost 0 T but need the source to still hold its value,
so a conservative feasibility fraction is measured, not assumed.

No simulation, no verifier run, no candidate, no submission.
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
PREF = "575b043f"
PINS = {
    "575b043f": "575b043f4fee91a0fc3a9fd6fc1e9290e7b2a0669cae79886be2bf999f7ec155",
    "61c8348d": "61c8348d6e85bb0259c4b89f14be9a2834c77bf8a680cf79959bf5e1089cf5de",
}
WORK = pathlib.Path("/kaggle/working")
TMP = pathlib.Path("/tmp/dqigap")
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
log(f"A0 candidates {[p.name for p in CANDS]}")
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
    log(f"A1 {src.name} bytes {dst.stat().st_size} sha {sh[:16]} -> {tag}")
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
del S, p3, p2, p1
Q = int(max(A.max(), B.max(), C.max())) + 1
staticT = int(i3.sum())
log(f"A2 header Q={H[1]} nregs={H[3]} nops={H[4]} staticT={H[5]} | parsed Q={Q} n={n} "
    f"staticT={staticT}")

TGT = np.zeros(128, bool)
TOF = np.zeros(128, bool)
RST = np.zeros(128, bool)
SWP = np.zeros(128, bool)
TGT[[0x10, 0x12, 0x21, 0x31, 0x32, 0x50]] = True
TOF[[0x31, 0x32]] = True
RST[[0x12, 0x50]] = True
SWP[0x22] = True

# ------------------------------------------------------- touch index, all wires
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
log(f"C0 touch pairs {NT} (deduped), wires {Q}")
is_tgt = TGT[base[to]] | ((base[to] == 0x22) & (A[to] == tq))
PT = np.zeros(NT + 1, np.int32)
np.cumsum(is_tgt, out=PT[1:])
log(f"C1 write/target touches {int(is_tgt.sum())}")


def n_tgt_between(x, a, b):
    """number of value-changing touches of wire x in the open interval (a, b)."""
    lo, hi = int(tlo[x]), int(tlo[x + 1])
    if hi <= lo:
        return 0
    sub = to[lo:hi]
    j0 = int(np.searchsorted(sub, a, "right"))
    j1 = int(np.searchsorted(sub, b, "left"))
    return int(PT[lo + j1] - PT[lo + j0])


def windows_of(w):
    lo_i, hi_i = int(tlo[w]), int(tlo[w + 1])
    tp = to[lo_i:hi_i]
    if len(tp) == 0:
        return None
    bt = base[tp]
    tg = TGT[bt] | (SWP[bt] & (A[tp] == w))
    rstd = RST[bt] & tg
    bounds = np.r_[-1, np.flatnonzero(rstd), len(tp) - 1]
    return tp, bt, tg, rstd, bounds


# ------------------------------------------------- per-wire windows (all wires)
LOS, HIS, NRES, NTCH = [], [], [], []
diff = np.zeros(n + 1, np.int32)
for w in range(Q):
    g = windows_of(w)
    if g is None:
        LOS.append(np.zeros(0, np.int32)); HIS.append(np.zeros(0, np.int32))
        NRES.append(0); NTCH.append(0)
        continue
    tp, bt, tg, rstd, bounds = g
    NTCH.append(len(tp)); NRES.append(int(rstd.sum()))
    los, his = [], []
    for k in range(len(bounds) - 1):
        a_, b_ = int(bounds[k]) + 1, int(bounds[k + 1])
        if b_ < a_:
            continue
        los.append(int(tp[a_])); his.append(int(tp[b_]) + 1)
    los = np.array(los, np.int32); his = np.array(his, np.int32)
    LOS.append(los); HIS.append(his)
    if len(los):
        np.add.at(diff, los, 1)
        np.add.at(diff, his, -1)
log("D0 windows built for all wires")

POOL = list(range(840, Q))
resets_on = np.flatnonzero(np.array(NRES) > 0)
log(f"D1 wires with >=1 reset {len(resets_on)} [{resets_on.min()}..{resets_on.max()}] "
    f"contiguous={bool(len(resets_on) == resets_on.max() - resets_on.min() + 1)}; "
    f"wires 0..839 have 0 resets -> their single window spans the tape")
log(f"D2 pool windows {sum(len(LOS[w]) for w in POOL)} "
    f"pool touches {sum(NTCH[w] for w in POOL)}")

live_all = np.cumsum(diff)[:n]
mx_all = int(live_all.max())
log(f"D3 TOTAL live peak (all {Q} wires, window model) {mx_all} -> Q {mx_all} "
    f"at {int((live_all == mx_all).sum())} ops")

d2 = np.zeros(n + 1, np.int32)
for w in POOL:
    if len(LOS[w]):
        np.add.at(d2, LOS[w], 1)
        np.add.at(d2, HIS[w], -1)
POOLONLY = np.cumsum(d2)[:n]
mxp = int(POOLONLY.max())
mxops = POOLONLY == mxp
NPK = int(mxops.sum())
log(f"D4 pool-live peak {mxp} -> Q {840 + mxp}; ops at peak {NPK}; "
    f"total live at those ops min/max {int(live_all[mxops].min())}/{int(live_all[mxops].max())}")
d = np.diff(np.r_[0, mxops.view(np.int8), 0])
st = np.flatnonzero(d == 1)
en = np.flatnonzero(d == -1)
log(f"D5 peak episodes {len(st)} span {int(st.min())}..{int(en.max())} "
    f"mean len {float((en - st).mean()):.1f} max len {int((en - st).max())}")
peak_ops = np.flatnonzero(mxops).astype(np.int32)
del d, st, en, live_all, POOLONLY, diff, d2

touchcnt = np.zeros(n, np.int16)
sel = (tq >= 840) & (tq < Q)
np.add.at(touchcnt, to[sel], 1)
maxtouch = int(touchcnt[mxops].max())
log(f"D6 pool wires touched at a peak op: max {maxtouch}, "
    f"mean {float(touchcnt[mxops].mean()):.4f} -> k <= {50 - maxtouch} by touch alone")
del touchcnt, sel

# ------------------------------------------- refined liveness: trim dead tails
diff3 = np.zeros(n + 1, np.int32)
trimmed_T = 0
for w in POOL:
    g = windows_of(w)
    if g is None or not len(LOS[w]):
        continue
    tp, bt, tg, rstd, bounds = g
    los2, his2 = [], []
    for k in range(len(bounds) - 1):
        a_, b_ = int(bounds[k]) + 1, int(bounds[k + 1])
        if b_ < a_:
            continue
        seg_tg = tg[a_:b_ + 1]
        seg_sw = SWP[bt[a_:b_ + 1]]
        consumer = (~seg_tg) | seg_sw
        idx = np.flatnonzero(consumer)
        if len(idx) == 0:
            trimmed_T += int(TOF[bt[a_:b_ + 1]].sum())
            continue
        last = a_ + int(idx[-1])
        los2.append(int(tp[a_])); his2.append(int(tp[last]) + 1)
        trimmed_T += int(TOF[bt[last + 1:b_ + 1]].sum())
    if los2:
        np.add.at(diff3, np.array(los2, np.int32), 1)
        np.add.at(diff3, np.array(his2, np.int32), -1)
live3 = np.cumsum(diff3)[:n]
log(f"E0 dead-tail trim (last consumer ends the live range): peak {int(live3.max())}, "
    f"ops at peak {int((live3 == live3.max()).sum())}, deleted Toffoli {trimmed_T}")
del live3, diff3

# ------------------------------------------------------------- the gap family
GL, GR, GW, GT, GTW = [], [], [], [], []
NET1 = np.zeros(Q, np.int64)
NETC = np.zeros(Q, np.int64)
for w in POOL:
    g = windows_of(w)
    if g is None:
        continue
    tp, bt, tg, rstd, bounds = g
    tof_w = TOF[bt] & tg
    NETC[w] = int(tof_w.sum())
    pref = np.zeros(len(tp) + 1, np.int32)
    np.cumsum(tof_w, out=pref[1:])
    run = np.maximum.accumulate(np.where(tof_w, np.arange(len(tp)), -1))
    lasttof = np.where(run >= 0, tp[np.clip(run, 0, None)], -1).astype(np.int32)
    for k in range(len(bounds) - 1):
        a_, b_ = int(bounds[k]) + 1, int(bounds[k + 1])
        if b_ - a_ < 1:
            continue
        if tof_w[a_:b_ + 1].any():
            NET1[w] += 1
        j = np.arange(a_, b_)
        if len(j) == 0:
            continue
        GL.append(tp[j] + 1)
        GR.append(tp[j + 1])
        GW.append(np.full(len(j), w, np.int32))
        GT.append(pref[j + 1] - pref[a_])
        GTW.append(lasttof[j])
GL = np.concatenate(GL).astype(np.int32)
GR = np.concatenate(GR).astype(np.int32)
GW = np.concatenate(GW).astype(np.int32)
GT = np.concatenate(GT).astype(np.int32)
GTW = np.concatenate(GTW).astype(np.int32)
log(f"F0 gaps total {len(GL)}")
ok = (GR > int(peak_ops[0])) & (GL < int(peak_ops[-1])) & (GR > GL)
GL, GR, GW, GT, GTW = GL[ok], GR[ok], GW[ok], GT[ok], GTW[ok]
LEN = (GR - GL).astype(np.int32)
log(f"F1 gaps intersecting the peak span {len(GL)}; length p50 {np.percentile(LEN, 50):.0f} "
    f"p90 {np.percentile(LEN, 90):.0f} p99 {np.percentile(LEN, 99):.0f} max {int(LEN.max())}")

cov = np.zeros(n + 1, np.int32)
np.add.at(cov, GL, 1)
np.add.at(cov, GR, -1)
covered = np.cumsum(cov)[:n]
log(f"F2 peak ops inside >=1 gap {int((covered[mxops] > 0).sum())}/{NPK}; "
    f"max simultaneous gaps at a peak op {int(covered[mxops].max())}")
del cov, covered

log(f"F3 refill Toffoli replay per gap: mean {GT.mean():.3f} p50 {np.percentile(GT, 50):.0f} "
    f"p90 {np.percentile(GT, 90):.0f} p99 {np.percentile(GT, 99):.0f} max {int(GT.max())}")
log(f"F4 full-window recompute per wire: min net1 {int(NET1[POOL].min())} "
    f"min netC {int(NETC[POOL].min())} sum net1 {int(NET1[POOL].sum())} "
    f"sum netC {int(NETC[POOL].sum())}")

# ---------------------------------------------------------------- the covers
order = np.argsort(GL, kind="stable")
Ls = GL[order]
MASK = (1 << 24) - 1
KEY0 = (GR[order].astype(np.int64) << 24) | np.arange(len(Ls), dtype=np.int64)
Ts = GT[order].astype(np.int64)
Ws = GW[order]
TW = GTW[order]


def cover(key, Larr, Tarr, limit=0):
    runkey = np.maximum.accumulate(key)
    t = int(peak_ops[0])
    last = int(peak_ops[-1])
    cnt = 0
    tsum = 0
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
        cnt += 1
        tsum += int(Tarr[p])
        picks.append(p)
        q = int(np.searchsorted(peak_ops, R))
        if q >= len(peak_ops):
            return cnt, tsum, picks, 1
        t = int(peak_ops[q])
        if limit and cnt > limit:
            return cnt, tsum, picks, -2
    return cnt, tsum, picks, 1


c1, t1, picks1, rc1 = cover(KEY0, Ls, Ts)
log(f"G0 k=1 exact min cover: refills {c1} replayT {t1} (avg {t1 / max(c1, 1):.2f} T/refill) "
    f"status {rc1}; at 1 T/refill -> {c1} T")
for cap in (826, 861, 900):
    log(f"G0   allowance {cap} T/qubit -> {'PASS' if c1 <= cap else 'FAIL'} "
        f"({c1 / cap:.2f}x)")

best = []
for w in POOL:
    m = Ws == w
    if not m.any():
        continue
    cw, tw, _, rcw = cover(KEY0[m], Ls[m], Ts[m])
    best.append((cw, tw, w, rcw))
best.sort()
log("G1 per-wire cover (one wire carries the whole plateau) best 8:")
for cw, tw, w, rcw in best[:8]:
    log(f"G1   q{w}: refills {cw} replayT {tw} status {rcw} "
        f"(full-window: net1 {int(NET1[w])} netC {int(NETC[w])})")
log(f"G1   worst q{best[-1][2]}: refills {best[-1][0]} replayT {best[-1][1]} "
    f"status {best[-1][3]}")

log("G2 k-fold cover (layered greedy, distinct intervals; LP bound k*C1):")
used = np.zeros(len(Ls), bool)
cum_c = 0
cum_t = 0
out = {}
for j in range(1, 26):
    key = np.where(used, -1, KEY0)
    c, t, picks, rc = cover(key, Ls, Ts)
    if rc != 1:
        log(f"G2 layer {j} FAILED (status {rc})")
        break
    for p in picks:
        used[p] = True
    cum_c += c
    cum_t += t
    out[j] = (cum_c, cum_t)
    log(f"G2   k={j:2d}: refills {cum_c} (+{c}) replayT {cum_t} (+{t}) "
        f"-> {cum_t / j:.1f} T/qubit (1 T/refill: {cum_c / j:.1f})")

# can the plateau still be covered if every refill must be <= cap Toffoli?
for cap in (0, 1, 2, 4):
    m = GT <= cap
    if not m.any():
        log(f"G2b cap {cap} T/refill: {int(m.sum())} gaps usable -> FAIL")
        continue
    cc, tt, _, rc = cover(KEY0[m], Ls[m], Ts[m])
    log(f"G2b cap {cap} T/refill: {int(m.sum())} gaps usable -> refills {cc} replayT {tt} "
        f"status {rc}")
    del m

# refill feasibility for the k=1 picks
feas = 0
tot = 0
nocheck = 0
for p in picks1:
    op = int(TW[p])
    R = int(KEY0[p] >> 24)
    tot += 1
    if op < 0:
        feas += 1
        continue
    if base[op] != 0x31:
        nocheck += 1
        continue
    a_, b_ = int(A[op]), int(B[op])
    if n_tgt_between(a_, op, R) == 0 and n_tgt_between(b_, op, R) == 0:
        feas += 1
log(f"G3 refill feasibility of the k=1 picks: last Toffoli operator holds its value "
    f"{feas}/{tot} ({100.0 * feas / max(tot, 1):.1f}%), unchecked {nocheck}")

log("")
log("SUMMARY k  Q  refills  replayT  T/qubit  replayT/qubit  1T/qubit")
for k in (1, 3, 5, 10, 25):
    if k in out:
        cc, tt = out[k]
        log(f"SUM {k:2d} {890 - k:4d} {cc:7d} {tt:8d} {tt / k:9.1f} {cc / k:8.1f}")

(WORK / "report.txt").write_text("\n".join(REPORT) + "\n")
log("done")
