"""DQI 575b043f: per-episode spill/refill, v4 - CORRECTED write/target roles.

Fixes the v1-v3 bug: the target mask was taken from the *opcode* only, so a wire used
as a CCX/CX **control** was counted as written.  Every replay count and every operand
test was therefore wrong in the pessimistic direction.  Here the write role comes from
the operand slot:

  C target for CX/CCX/CSWAP(C),  B and C for SWAP,  B and C for CSWAP,
  A for X / R(reset) / HMR,  A and C for SWAP.

Everything else in this kernel is the same measurement as before:
  * the pool-live plateau (window model, exact),
  * every within-window touch gap of the 50 pool wires,
  * replay chain = the value-changing writes into the wire since the window's reset,
  * a refill at gap (L,R) is admissible only if every replayed write's operands still
    hold their values at R (no value-changing touch of the operand in between),
  * min covers of the plateau point set by gap intervals, under a ladder of
    restrictions, and the k-fold covers that buy k qubits,
  * dead-tail trim (trailing writes whose result is never consumed).

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
WORK = pathlib.Path("/kaggle/working")
TMP = pathlib.Path("/tmp/dqik27")
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

# opcode property LUTs (slot-independent)
TOFOP = np.zeros(128, bool); TOFOP[[0x31, 0x32]] = True       # Toffoli-like gate
C3 = np.zeros(128, bool); C3[[0x30, 0x31, 0x32]] = True       # 3-operand
C2 = np.zeros(128, bool); C2[[0x20, 0x21, 0x22]] = True       # 2-operand
CXOP = np.zeros(128, bool); CXOP[0x21] = True
SWOP = np.zeros(128, bool); SWOP[0x22] = True
CSWOP = np.zeros(128, bool); CSWOP[0x32] = True
RSTOP = np.zeros(128, bool); RSTOP[[0x12, 0x50]] = True
W1OP = np.zeros(128, bool); W1OP[[0x10, 0x12, 0x50]] = True   # 1-operand writes A

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
log(f"B0 touch pairs {NT}")

b_to = base[to]
a_to = A[to]
b2_to = B[to]
c_to = C[to]
wr = TOFOP[b_to] & (c_to == tq)                                    # CX/CCX C target
wr |= (CXOP[b_to] & (c_to == tq))
wr |= (CSWOP[b_to] & ((b2_to == tq) | (c_to == tq)))
wr |= (SWOP[b_to] & ((a_to == tq) | (c_to == tq)))
wr |= (W1OP[b_to] & (a_to == tq))
PT = np.zeros(NT + 1, np.int32)
np.cumsum(wr, out=PT[1:])
log(f"B1 value-changing touches {int(wr.sum())} of {NT} "
    f"(opcode-only mask would give {int((TOFOP[b_to] | CXOP[b_to] | W1OP[b_to]).sum())})")
del b_to, a_to, b2_to, c_to, wr

def n_tgt_between(x, a, b):
    lo, hi = int(tlo[x]), int(tlo[x + 1])
    if hi <= lo:
        return 0
    sub = to[lo:hi]
    j0 = int(np.searchsorted(sub, a, "right"))
    j1 = int(np.searchsorted(sub, b, "left"))
    return int(PT[lo + j1] - PT[lo + j0])


def next_tgt_after(x, a):
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


def roles(w):
    """per-touch (op, base, is_write, is_toffoli_write, is_reset) for wire w"""
    lo_i, hi_i = int(tlo[w]), int(tlo[w + 1])
    tp = to[lo_i:hi_i]
    if len(tp) == 0:
        return None
    bt = base[tp]
    ww = (TOFOP[bt] & (C[tp] == w)) | (CXOP[bt] & (C[tp] == w))
    ww |= (CSWOP[bt] & ((B[tp] == w) | (C[tp] == w)))
    ww |= (SWOP[bt] & ((A[tp] == w) | (C[tp] == w)))
    ww |= (W1OP[bt] & (A[tp] == w))
    tf = TOFOP[bt] & (C[tp] == w)
    rs = RSTOP[bt] & ww
    return tp, bt, ww, tf, rs


def windows(tp, bt, ww, rs):
    bounds = np.r_[-1, np.flatnonzero(rs), len(tp) - 1]
    out = []
    for k in range(len(bounds) - 1):
        a_, b_ = int(bounds[k]) + 1, int(bounds[k + 1])
        if b_ < a_:
            continue
        last = (b_ - 1) if rs[b_] else b_
        if last < a_:
            continue
        out.append((a_, last))
    return out


# --------------------------------------------------------------- pool plateau
d = np.zeros(n + 1, np.int32)
WIN = {}
for w in range(840, Q):
    r = roles(w)
    if r is None:
        continue
    tp, bt, ww, tf, rs = r
    WIN[w] = windows(tp, bt, ww, rs)
    if WIN[w]:
        np.add.at(d, np.array([int(tp[a_]) for a_, _ in WIN[w]], np.int32), 1)
        np.add.at(d, np.array([int(tp[b_]) + 1 for _, b_ in WIN[w]], np.int32), -1)
live = np.cumsum(d)[:n]
mx = int(live.max())
mxops = live == mx
NPK = int(mxops.sum())
peak_ops = np.flatnonzero(mxops).astype(np.int32)
dd = np.diff(np.r_[0, mxops.view(np.int8), 0])
log(f"C0 pool-live peak {mx} -> Q {840 + mx}; ops at peak {NPK}; "
    f"episodes {len(np.flatnonzero(dd == 1))} span {int(peak_ops[0])}..{int(peak_ops[-1])}")
del d, live, dd

# ------------------------------------------------------------------ gap family
GL, GR, GW, GT, GX, GNW, GFO = [], [], [], [], [], [], []
for w in range(840, Q):
    r = roles(w)
    if r is None:
        continue
    tp, bt, ww, tf, rs = r
    pf_t = np.zeros(len(tp) + 1, np.int32); np.cumsum(tf, out=pf_t[1:])
    pf_c = np.zeros(len(tp) + 1, np.int32); np.cumsum(CXOP[bt] & ww, out=pf_c[1:])
    pf_w = np.zeros(len(tp) + 1, np.int32); np.cumsum(ww, out=pf_w[1:])
    for a_, last in WIN[w]:
        j = np.arange(a_, last)          # gaps between consecutive touches, incl. the
        if len(j) == 0:                  # gap that ends at the window's last touch
            continue
        j = j[tp[j] < tp[last]]
        if len(j) == 0:
            continue
        Rg = tp[j + 1]
        GL.append(tp[j] + 1); GR.append(Rg)
        GW.append(np.full(len(j), w, np.int32))
        GT.append(pf_t[j + 1] - pf_t[a_])
        GX.append(pf_c[j + 1] - pf_c[a_])
        GNW.append(pf_w[j + 1] - pf_w[a_])
        idx0 = np.flatnonzero(ww[a_:last + 1])
        if len(idx0) == 0:
            allow = np.full(len(j), 1 << 62, np.int64)
        else:
            i0 = a_ + int(idx0[0])
            t0 = int(tp[i0]); b0 = int(bt[i0])
            ops0 = []
            if b0 == 0x31:
                ops0 = [int(A[t0]), int(B[t0])]
            elif b0 == 0x21:
                ops0 = [int(A[t0])]
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
log(f"D0 gaps {len(GL)}; length p50 {np.percentile(LEN, 50):.0f} p90 "
    f"{np.percentile(LEN, 90):.0f} p99 {np.percentile(LEN, 99):.0f} max {int(LEN.max())}")
log(f"D1 replay chain (value-changing writes since the window reset): p50 "
    f"{np.percentile(GNW, 50):.0f} p90 {np.percentile(GNW, 90):.0f} p99 "
    f"{np.percentile(GNW, 99):.0f}; replay Toffoli p50 {np.percentile(GT, 50):.0f} p90 "
    f"{np.percentile(GT, 90):.0f} p99 {np.percentile(GT, 99):.0f} max {int(GT.max())}")
log(f"D2 first-write-operand-kept {int(GFO.sum())}/{len(GFO)} ({100.0 * GFO.mean():.2f}%)")
for thr in (100, 1000, 10000, 100000):
    m = GFO & (LEN >= thr)
    log(f"D2   kept with length >= {thr:6d}: {int(m.sum()):7d} of {int((LEN >= thr).sum()):7d}")

cov = np.zeros(n + 1, np.int32)
np.add.at(cov, GL[GFO], 1); np.add.at(cov, GR[GFO], -1)
cf = np.cumsum(cov)[:n]
log(f"D3 plateau ops inside >=1 first-kept gap {int((cf[mxops] > 0).sum())}/{NPK}")
del cov, cf

order = np.argsort(GL, kind="stable")
Ls = GL[order]
KEY0 = (GR[order].astype(np.int64) << 24) | np.arange(len(Ls), dtype=np.int64)
Ts = GT[order].astype(np.int64)
FOs = GFO[order]
LNs = LEN[order]
Ws = GW[order]
NWs = GNW[order]
MASK = (1 << 24) - 1


def pack(L, R, T):
    o = np.argsort(L, kind="stable")
    return L[o], (R[o].astype(np.int64) << 24) | np.arange(len(o), dtype=np.int64), T[o]


def cover(Larr, key, Tarr):
    runkey = np.maximum.accumulate(key)
    t = int(peak_ops[0]); lastop = int(peak_ops[-1])
    cnt = tsum = 0
    picks = []
    while t <= lastop:
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
log(f"E0 k=1 min cover ALL gaps: {c1} refills replayT {t1} status {rc1}")

# full-chain replay feasibility for a given (wire, L, R)
def chain_check(w, L, R):
    r = roles(w)
    if r is None:
        return 0, 0, 0, 0
    tp, bt, ww, tf, rs = r
    jR = int(np.searchsorted(tp, R, "left"))            # touches strictly before R
    j = np.searchsorted(tp, L - 1, "right") - 1         # the gap's left touch
    rs_i = np.flatnonzero(rs[:j + 1]) if j >= 0 else np.array([], np.int64)
    a_ = int(rs_i[-1]) + 1 if len(rs_i) else 0
    tot = bad = ntof = ncx = 0
    for i in range(a_, jR):
        bb = int(bt[i]); op = int(tp[i])
        if not ww[i] or rs[i]:
            continue
        tot += 1
        if TOFOP[bb]:
            ntof += 1
        elif CXOP[bb]:
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
            if n_tgt_between(x, op, R) != 0:
                bad += 1
                break
    return tot, bad, ntof, ncx


log("E1 full-chain check on the k=1 picks:")
nsucc = 0
for p in picks1[:12]:
    w = int(Ws[p])
    L = int(Ls[p]); R = int(KEY0[p] >> 24)
    tot, bad, ntof, ncx = chain_check(w, L, R)
    ok = (bad == 0)
    nsucc += ok
    log(f"E1   q{w} [{L},{R}) len {R - L} | chain writes {tot} (T {ntof} CX {ncx}) "
        f"stale {bad} -> restorable {ok}")
log(f"E1 restorable picks {nsucc}/{min(12, len(picks1))}")

log("E2 exhaustive full-chain test on a filtered family (len>=1000, chain<=c):")
for c in (2, 4, 8):
    m = (LNs >= 1000) & (NWs <= c)
    idx = np.flatnonzero(m)
    okv = np.zeros(len(idx), bool)
    for kk, p in enumerate(idx):
        w = int(Ws[p]); L = int(Ls[p]); R = int(KEY0[p] >> 24)
        _, bad, _, _ = chain_check(w, L, R)
        okv[kk] = (bad == 0)
    if not okv.any():
        log(f"E2   chain<={c}: {len(idx)} candidates, none restorable")
        continue
    cov2 = np.zeros(n + 1, np.int32)
    np.add.at(cov2, Ls[idx[okv]], 1); np.add.at(cov2, (KEY0[idx[okv]] >> 24).astype(np.int32), -1)
    c2 = np.cumsum(cov2)[:n]
    log(f"E2   chain<={c}: {len(idx)} candidates, {int(okv.sum())} restorable, "
        f"plateau coverage {int((c2[mxops] > 0).sum())}/{NPK}")
    Lc, Kc, Tc = pack(Ls[idx[okv]], (KEY0[idx[okv]] >> 24).astype(np.int32), Ts[idx[okv]])
    cc, tt, _, rc = cover(Lc, Kc, Tc)
    log(f"E2     cover: refills {cc} replayT {tt} status {rc}")
    del cov2, c2, Lc, Kc, Tc

log("E3 k-fold cover, all gaps:")
used = np.zeros(len(Ls), bool)
cum_c = cum_t = 0
out = {}
for j in range(1, 11):
    key = np.where(used, -1, KEY0)
    c, t, pk, rc = cover(Ls, key, Ts)
    if rc != 1:
        log(f"E3 layer {j} FAILED (status {rc})")
        break
    for p in pk:
        used[p] = True
    cum_c += c; cum_t += t
    out[j] = (cum_c, cum_t)
    log(f"E3   k={j:2d}: refills {cum_c} (+{c}) replayT {cum_t} (+{t}) -> {cum_t / j:.1f} T/qubit")

# ------------------------------------------------------- dead-tail trim (fixed)
diff = np.zeros(n + 1, np.int32)
trimT = 0
for w in range(840, Q):
    r = roles(w)
    if r is None:
        continue
    tp, bt, ww, tf, rs = r
    los, his = [], []
    for a_, last in WIN[w]:
        seg_w = ww[a_:last + 1]
        seg_s = SWOP[bt[a_:last + 1]]
        seg_h = (bt[a_:last + 1] == 0x50)
        idx = np.flatnonzero((~seg_w) | seg_s | seg_h)
        if len(idx) == 0:
            trimT += int(tf[a_:last + 1].sum())
            continue
        lc = a_ + int(idx[-1])
        los.append(int(tp[a_])); his.append(int(tp[lc]) + 1)
        trimT += int(tf[lc + 1:last + 1].sum())
    if los:
        np.add.at(diff, np.array(los, np.int32), 1)
        np.add.at(diff, np.array(his, np.int32), -1)
lv = np.cumsum(diff)[:n]
log(f"F0 dead-tail trim: pool peak {int(lv.max())} at {int((lv == lv.max()).sum())} ops, "
    f"dead Toffoli {trimT}")

log("")
log("SUMMARY  k  Q   refills  replayT  T/qubit")
for k in sorted(out):
    cc, tt = out[k]
    log(f"SUM {k:2d} {890 - k:4d} {cc:7d} {tt:8d} {tt / k:9.1f}")

(WORK / "report.txt").write_text("\n".join(REPORT) + "\n")
log("done")
