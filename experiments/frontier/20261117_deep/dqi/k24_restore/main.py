"""DQI 575b043f: per-episode spill/refill, v2 - exact cover + exact refill feasibility.

v1 finding (kernel zhuating/qcc-dqi-gaps-575b): the plateau point set is coverable by a
few dozen touch gaps, because most of the pool's liveness is *held* values (a wire can be
live and untouched for millions of ops).  So the counting cost of the per-episode
mechanism is two orders of magnitude below the width break-even.  The blocker is not the
number of refills, it is whether a refill can *restore the value*.

v2 therefore measures both halves exactly:
  (1) window model, tight (a window ends at the last non-reset touch, so the stretch
      between a wire's last use and its own reset is dead) -- this reproduces the
      established 2,760,326 plateau ops / 961 episodes; the loose model is kept as a
      sensitivity check,
  (2) for every within-window touch gap: chain length (writes to replay), Toffoli and CX
      counts in the chain, and whether every replay operand still holds its value at the
      refill point (conservative: no value-changing touch in between),
  (3) min covers under a ladder of restrictions: all gaps, physically-restorable gaps
      only, and replay chains capped at c writes,
  (4) k-fold covers up to k = 50 and the touched-wire cap on feasible k.

A refill of a gap costs GT Toffoli (CX replays are 0 T) and is admissible only if every
operand of every replayed write is unchanged from the original write up to the refill
point.  Read-only: no simulation, no verifier, no candidate, no submission.
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
CHAIN_CAP = 12
WORK = pathlib.Path("/kaggle/working")
TMP = pathlib.Path("/tmp/dqigap2")
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
log(f"A1 using tape {TAG}")


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
log(f"A2 header Q={H[1]} nops={H[4]} staticT={H[5]} | parsed Q={Q} n={n} "
    f"staticT={int(i3.sum())}")

TGT = np.zeros(128, bool)
TOF = np.zeros(128, bool)
RST = np.zeros(128, bool)
SWP = np.zeros(128, bool)
HMR = np.zeros(128, bool)
TGT[[0x10, 0x12, 0x21, 0x31, 0x32, 0x50]] = True
TOF[[0x31, 0x32]] = True
RST[[0x12, 0x50]] = True
SWP[0x22] = True
HMR[0x50] = True

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
log(f"B0 touch pairs {NT} (deduped), wires {Q}")
is_tgt = TGT[base[to]] | ((base[to] == 0x22) & (A[to] == tq))
PT = np.zeros(NT + 1, np.int32)
np.cumsum(is_tgt, out=PT[1:])


def n_tgt_between(x, a, b):
    """value-changing touches of wire x in the open interval (a, b)."""
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


def profile(tight):
    """pool-live profile; tight = window ends at the last non-reset touch."""
    d = np.zeros(n + 1, np.int32)
    for w in range(840, Q):
        g = windows_of(w)
        if g is None:
            continue
        tp, bt, tg, rstd, bounds = g
        los, his = [], []
        for k in range(len(bounds) - 1):
            a_, b_ = int(bounds[k]) + 1, int(bounds[k + 1])
            if b_ < a_:
                continue
            last = (b_ - 1) if (tight and rstd[b_]) else b_
            if last < a_:
                continue
            los.append(int(tp[a_])); his.append(int(tp[last]) + 1)
        if los:
            np.add.at(d, np.array(los, np.int32), 1)
            np.add.at(d, np.array(his, np.int32), -1)
    return np.cumsum(d)[:n]


LIVE_T = profile(True)
LIVE_L = profile(False)
for nm, lv in (("tight(last-use)", LIVE_T), ("loose(through reset)", LIVE_L)):
    mx = int(lv.max())
    mk = lv == mx
    dd = np.diff(np.r_[0, mk.view(np.int8), 0])
    s, e = np.flatnonzero(dd == 1), np.flatnonzero(dd == -1)
    log(f"C0 {nm}: pool-live peak {mx} -> Q {840 + mx}, ops at peak {int(mk.sum())}, "
        f"episodes {len(s)} span {int(s.min())}..{int(e.max())}")
LIVE = LIVE_T
mx = int(LIVE.max())
mxops = LIVE == mx
NPK = int(mxops.sum())
peak_ops = np.flatnonzero(mxops).astype(np.int32)
log(f"C1 PRIMARY peak set: {NPK} ops, {len(np.flatnonzero(np.diff(np.r_[0, mxops.view(np.int8), 0]) == 1))} "
    f"episodes")
del LIVE_L

# total live across all 890 wires (sanity: syndrome wires have no reset -> live throughout)
dall = np.zeros(n + 1, np.int32)
for w in range(Q):
    g = windows_of(w)
    if g is None:
        continue
    tp, bt, tg, rstd, bounds = g
    los, his = [], []
    for k in range(len(bounds) - 1):
        a_, b_ = int(bounds[k]) + 1, int(bounds[k + 1])
        if b_ < a_:
            continue
        last = b_
        if rstd[b_]:
            last = b_ - 1
        if last < a_:
            continue
        los.append(int(tp[a_])); his.append(int(tp[last]) + 1)
    if los:
        np.add.at(dall, np.array(los, np.int32), 1)
        np.add.at(dall, np.array(his, np.int32), -1)
live_all = np.cumsum(dall)[:n]
log(f"C2 TOTAL live peak {int(live_all.max())} -> Q {int(live_all.max())} at "
    f"{int((live_all == live_all.max()).sum())} ops; at the pool-peak ops "
    f"{int(live_all[mxops].min())}..{int(live_all[mxops].max())}")
del live_all, dall

touchcnt = np.zeros(n, np.int16)
sel = (tq >= 840) & (tq < Q)
np.add.at(touchcnt, to[sel], 1)
log(f"C3 pool wires touched at a peak op: max {int(touchcnt[mxops].max())}, "
    f"mean {float(touchcnt[mxops].mean()):.4f} -> k <= {50 - int(touchcnt[mxops].max())}")
del touchcnt, sel

# ------------------------------------------------------------------- gap family
GL, GR, GW, GT, GX, GNW, GOK, GLAST = [], [], [], [], [], [], [], []
for w in range(840, Q):
    g = windows_of(w)
    if g is None:
        continue
    tp, bt, tg, rstd, bounds = g
    isw = tg                     # value-changing touch
    tofw = TOF[bt] & tg
    cxw = (bt == 0x21) & tg
    pf_tof = np.zeros(len(tp) + 1, np.int32); np.cumsum(tofw, out=pf_tof[1:])
    pf_cx = np.zeros(len(tp) + 1, np.int32); np.cumsum(cxw, out=pf_cx[1:])
    pf_w = np.zeros(len(tp) + 1, np.int32); np.cumsum(isw, out=pf_w[1:])
    for k in range(len(bounds) - 1):
        a_, b_ = int(bounds[k]) + 1, int(bounds[k + 1])
        if b_ - a_ < 1:
            continue
        j = np.arange(a_, b_)
        if len(j) == 0:
            continue
        Lg = tp[j] + 1
        Rg = tp[j + 1]
        GL.append(Lg); GR.append(Rg)
        GW.append(np.full(len(j), w, np.int32))
        GT.append(pf_tof[j + 1] - pf_tof[a_])
        GX.append(pf_cx[j + 1] - pf_cx[a_])
        nw = pf_w[j + 1] - pf_w[a_]
        GNW.append(nw)
        # feasibility, only for short chains: every replayed write's operands must be
        # untouched from the original write up to the refill point R.
        ok = np.zeros(len(j), bool)
        for jj in range(len(j)):
            if nw[jj] > CHAIN_CAP:
                continue
            good = True
            for t in range(a_, j[jj] + 1):
                if not isw[t]:
                    continue
                op = int(tp[t])
                bb = int(bt[t])
                if bb == 0x21 or bb == 0x10:
                    ops_ = (int(A[op]),) if bb == 0x10 else (int(A[op]),)
                elif bb == 0x31:
                    ops_ = (int(A[op]), int(B[op]))
                elif bb == 0x22:
                    ops_ = (int(A[op]),) if int(C[op]) == w else (int(C[op]),)
                else:
                    ops_ = ()
                for x in ops_:
                    if x < 0 or x == w:
                        continue
                    if n_tgt_between(x, op, int(Rg[jj])) != 0:
                        good = False
                        break
                if not good:
                    break
            ok[jj] = good
        GOK.append(ok)
GL = np.concatenate(GL).astype(np.int32)
GR = np.concatenate(GR).astype(np.int32)
GW = np.concatenate(GW).astype(np.int32)
GT = np.concatenate(GT).astype(np.int32)
GX = np.concatenate(GX).astype(np.int32)
GNW = np.concatenate(GNW).astype(np.int32)
GOK = np.concatenate(GOK)
log(f"D0 gaps {len(GL)}; chain(p50/p90/p99) {np.percentile(GNW, 50):.0f}/"
    f"{np.percentile(GNW, 90):.0f}/{np.percentile(GNW, 99):.0f}; "
    f"replay T p50 {np.percentile(GT, 50):.0f} p90 {np.percentile(GT, 90):.0f} "
    f"p99 {np.percentile(GT, 99):.0f}; chainCX p50 {np.percentile(GX, 50):.0f} "
    f"p90 {np.percentile(GX, 90):.0f}")
m = GNW <= CHAIN_CAP
log(f"D1 gaps with chain <= {CHAIN_CAP}: {int(m.sum())}; of those restorable "
    f"{int((GOK & m).sum())} ({100.0 * int((GOK & m).sum()) / max(int(m.sum()), 1):.1f}%); "
    f"restorable with chain<=1: {int((GOK & (GNW <= 1)).sum())}, <=2: "
    f"{int((GOK & (GNW <= 2)).sum())}, <=4: {int((GOK & (GNW <= 4)).sum())}, "
    f"<=8: {int((GOK & (GNW <= 8)).sum())}")
LEN = (GR - GL).astype(np.int32)
log(f"D2 gap length p50 {np.percentile(LEN, 50):.0f} p90 {np.percentile(LEN, 90):.0f} "
    f"p99 {np.percentile(LEN, 99):.0f} max {int(LEN.max())}")
cov = np.zeros(n + 1, np.int32)
np.add.at(cov, GL, 1); np.add.at(cov, GR, -1)
covered = np.cumsum(cov)[:n]
log(f"D3 peak ops inside >=1 gap {int((covered[mxops] > 0).sum())}/{NPK}")
del cov, covered

# ---------------------------------------------------------------- cover engine
order = np.argsort(GL, kind="stable")
Ls = GL[order]
KEY0 = (GR[order].astype(np.int64) << 24) | np.arange(len(Ls), dtype=np.int64)
Ts = GT[order].astype(np.int64)
Gs = GX[order].astype(np.int64)
Nw = GNW[order]
Ok = GOK[order]
Ws = GW[order]
MASK = (1 << 24) - 1


def cover(Larr, key, Tarr, Garr=None, NWarr=None, Okarr=None, detail=0):
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
        cnt += 1
        tsum += int(Tarr[p])
        picks.append(p)
        q = int(np.searchsorted(peak_ops, R))
        if q >= len(peak_ops):
            return cnt, tsum, picks, 1
        t = int(peak_ops[q])
    return cnt, tsum, picks, 1


c1, t1, picks1, rc1 = cover(Ls, KEY0, Ts)
log(f"E0 k=1 min cover, ALL gaps: {c1} refills, replayT {t1}, status {rc1} "
    f"(avg {t1 / max(c1, 1):.2f} T/refill)")
for p in picks1:
    log(f"E0   wire q{int(Ws[p])} [{int(Ls[p])},{int(KEY0[p] >> 24)}) len "
        f"{int((KEY0[p] >> 24) - Ls[p])} chain {int(Nw[p])} T {int(Ts[p])} CX {int(Gs[p])} "
        f"restorable {bool(Ok[p])}")

log("E1 min cover restricted to physically restorable gaps:")
for cap in (0, 1, 2, 4, 8, 12):
    m = Ok & (Nw <= cap)
    if not m.any():
        log(f"E1   chain<={cap:2d}: no admissible gap -> FAIL")
        continue
    cc, tt, pk, rc = cover(Ls[m], KEY0[m], Ts[m])
    log(f"E1   chain<={cap:2d}: {int(m.sum())} admissible gaps -> refills {cc} replayT {tt} "
        f"status {rc}")
    del m

log("E2 cheapest single wire (that wire carries the whole plateau):")
best = []
for w in range(840, Q):
    m = Ws == w
    if not m.any():
        continue
    m2 = m & Ok & (Nw <= 4)
    if m2.any():
        cw, tw, _, rcw = cover(Ls[m2], KEY0[m2], Ts[m2])
    else:
        cw, tw, rcw = -1, -1, -9
    cwA, twA, _, rcwA = cover(Ls[m], KEY0[m], Ts[m])
    best.append((tw, cw, w, rcw, twA, cwA, rcwA))
best.sort()
for tw, cw, w, rcw, twA, cwA, rcwA in best[:6]:
    log(f"E2   q{w}: restorable-chain<=4 refills {cw} T {tw} status {rcw} | "
        f"any-gap refills {cwA} T {twA} status {rcwA}")
log(f"E2   worst q{best[-1][2]}: restorable refills {best[-1][1]} T {best[-1][0]}")

log("E3 k-fold cover (all gaps, distinct intervals):")
used = np.zeros(len(Ls), bool)
cum_c = cum_t = 0
out = {}
for j in range(1, 51):
    key = np.where(used, -1, KEY0)
    c, t, pk, rc = cover(Ls, key, Ts)
    if rc != 1:
        log(f"E3 layer {j} FAILED (status {rc})")
        break
    for p in pk:
        used[p] = True
    cum_c += c; cum_t += t
    out[j] = (cum_c, cum_t)
    if j <= 3 or j % 5 == 0:
        log(f"E3   k={j:2d}: refills {cum_c} (+{c}) replayT {cum_t} (+{t}) "
            f"-> {cum_t / j:.1f} T/qubit")
log(f"E3 total layers completed {len(out)}")

log("E4 k-fold cover restricted to restorable gaps with chain<=2:")
used2 = np.zeros(len(Ls), bool)
adm = Ok & (Nw <= 2)
cum_c2 = cum_t2 = 0
out2 = {}
for j in range(1, 51):
    key = np.where(used2 | ~adm, -1, KEY0)
    c, t, pk, rc = cover(Ls, key, Ts)
    if rc != 1:
        log(f"E4 layer {j} FAILED (status {rc})")
        break
    for p in pk:
        used2[p] = True
    cum_c2 += c; cum_t2 += t
    out2[j] = (cum_c2, cum_t2)
    if j <= 3 or j % 5 == 0:
        log(f"E4   k={j:2d}: refills {cum_c2} replayT {cum_t2} -> {cum_t2 / j:.1f} T/qubit")
log(f"E4 total layers completed {len(out2)}")

log("")
log("SUMMARY  k  Q   refills(all)  replayT(all)  T/qubit | restorable refills  replayT  T/qubit")
for k in (1, 3, 5, 10, 25, 50):
    a = out.get(k, (None, None))
    b = out2.get(k, (None, None))
    log(f"SUM {k:2d} {890 - k:4d}   {str(a[0]):>8} {str(a[1]):>10} "
        f"{('%.1f' % (a[1] / k)) if a[1] is not None else '-':>8} | "
        f"{str(b[0]):>8} {str(b[1]):>8} "
        f"{('%.1f' % (b[1] / k)) if b[1] is not None else '-':>8}")

# ---------------------------------------------------- dead-tail trim (diagnostic)
diff3 = np.zeros(n + 1, np.int32)
trimT = 0
for w in range(840, Q):
    g = windows_of(w)
    if g is None:
        continue
    tp, bt, tg, rstd, bounds = g
    los2, his2 = [], []
    for k in range(len(bounds) - 1):
        a_, b_ = int(bounds[k]) + 1, int(bounds[k + 1])
        if b_ < a_:
            continue
        last = b_ - 1 if rstd[b_] else b_
        if last < a_:
            continue
        seg_tg = tg[a_:last + 1]
        seg_sw = SWP[bt[a_:last + 1]]
        seg_hm = HMR[bt[a_:last + 1]]
        consumer = (~seg_tg) | seg_sw | seg_hm
        idx = np.flatnonzero(consumer)
        if len(idx) == 0:
            trimT += int(TOF[bt[a_:last + 1]].sum())
            continue
        lc = a_ + int(idx[-1])
        los2.append(int(tp[a_])); his2.append(int(tp[lc]) + 1)
        trimT += int(TOF[bt[lc + 1:last + 1]].sum())
    if los2:
        np.add.at(diff3, np.array(los2, np.int32), 1)
        np.add.at(diff3, np.array(his2, np.int32), -1)
lv3 = np.cumsum(diff3)[:n]
log(f"F0 dead-tail trim (last consumer incl. HMR): peak {int(lv3.max())} at "
    f"{int((lv3 == lv3.max()).sum())} ops, dead Toffoli {trimT}")

(WORK / "report.txt").write_text("\n".join(REPORT) + "\n")
log("done")
