"""DQI 575b043f: the full-tape liveness test (all 890 wires), the width check that
was run on invsqrt but never on DQI.

Three liveness models, all as a sweep line over the 57.5 M ops:
  M0  per-wire first-use/last-use, one interval per wire (no reset awareness).
  M1  reset-delimited windows: a wire's value lives from its first touch after a reset
      to its last touch before the next reset.  This is the model every earlier DQI
      width note used, and the only one that is sound for this tape: the gate set has
      no H, the input is a basis state, so every touch except R/HMR consumes the
      previous value and an R/HMR reset is the only point where a wire becomes
      reusable.
  M2  M1 with the dead tail trimmed: if a window ends in writes whose result is never
      consumed before the reset, the value is dead at the last consumer and the wire is
      free from there.  M2 is what a pure wire *renumbering* (identical gate multiset,
      no gate changed) can exploit.

Reported for each model: peak simultaneous liveness (sweep line), the number of ops at
the peak, the occupancy histogram, the wires with no touch, and whether the 840
syndrome wires are simultaneously live throughout.  If any model peaks below 890, a
renumbering of that model's intervals buys (peak/890)^2 cost for 0 T.

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
TMP = pathlib.Path("/tmp/dqilive")
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

TOFOP = np.zeros(128, bool); TOFOP[[0x31, 0x32]] = True
CXOP = np.zeros(128, bool); CXOP[0x21] = True
SWOP = np.zeros(128, bool); SWOP[0x22] = True
CSWOP = np.zeros(128, bool); CSWOP[0x32] = True
RSTOP = np.zeros(128, bool); RSTOP[[0x12, 0x50]] = True
W1OP = np.zeros(128, bool); W1OP[[0x10, 0x12, 0x50]] = True

tq = np.concatenate([A[A >= 0], B[B >= 0], C[C >= 0]])
to = np.concatenate([np.flatnonzero(A >= 0), np.flatnonzero(B >= 0), np.flatnonzero(C >= 0)])
o = np.lexsort((to, tq))
tq, to = tq[o], to[o]
del o
same = np.r_[False, (tq[1:] == tq[:-1]) & (to[1:] == to[:-1])]
tq, to = tq[~same], to[~same]
del same
tlo = np.searchsorted(tq, np.arange(Q + 2), "left")
ntouch = np.diff(tlo)
log(f"B0 wires {Q}; wires with 0 touches {int((ntouch == 0).sum())}; "
    f"min touches {int(ntouch.min())} at q{int(np.argmin(ntouch))}")
first = np.array([int(to[tlo[w]]) for w in range(Q)], np.int64)
last = np.array([int(to[tlo[w + 1] - 1]) for w in range(Q)], np.int64)
log(f"B1 first-use span {int(first.min())}..{int(first.max())}; "
    f"last-use span {int(last.min())}..{int(last.max())}")
d0 = np.zeros(n + 2, np.int64)
np.add.at(d0, first, 1)
np.add.at(d0, last + 1, -1)
m0 = np.cumsum(d0)[:n]
log(f"B2 M0 (one interval per wire, [first,last]): peak simultaneous {int(m0.max())} at "
    f"{int((m0 == m0.max()).sum())} ops")
del d0, m0


def profile(trim):
    d = np.zeros(n + 1, np.int32)
    nwin = 0
    ntrim = 0
    for w in range(Q):
        lo_i, hi_i = int(tlo[w]), int(tlo[w + 1])
        tp = to[lo_i:hi_i]
        if len(tp) == 0:
            continue
        bt = base[tp]
        ww = (TOFOP[bt] & (C[tp] == w)) | (CXOP[bt] & (C[tp] == w))
        ww |= (CSWOP[bt] & ((B[tp] == w) | (C[tp] == w)))
        ww |= (SWOP[bt] & ((A[tp] == w) | (C[tp] == w)))
        ww |= (W1OP[bt] & (A[tp] == w))
        rs = RSTOP[bt] & ww
        bounds = np.r_[-1, np.flatnonzero(rs), len(tp) - 1]
        for k in range(len(bounds) - 1):
            a_, b_ = int(bounds[k]) + 1, int(bounds[k + 1])
            if b_ < a_:
                continue
            lastx = (b_ - 1) if rs[b_] else b_
            if lastx < a_:
                continue
            if trim:
                seg_w = ww[a_:lastx + 1]
                idx = np.flatnonzero((~seg_w) | SWOP[bt[a_:lastx + 1]]
                                     | (bt[a_:lastx + 1] == 0x50))
                if len(idx) == 0:
                    ntrim += lastx - a_ + 1
                    continue
                lastx = a_ + int(idx[-1])
            d[int(tp[a_])] += 1
            d[int(tp[lastx]) + 1] -= 1
            nwin += 1
    live = np.cumsum(d)[:n]
    return live, nwin, ntrim


for nm, trim in (("M1 window", False), ("M2 window+dead-tail", True)):
    live, nwin, ntrim = profile(trim)
    mx = int(live.max())
    mk = live == mx
    log(f"C0 {nm}: windows {nwin}, trimmed windows {ntrim}, PEAK live {mx} -> Q {mx}, "
        f"ops at peak {int(mk.sum())}, span {int(np.flatnonzero(mk)[0])}.."
        f"{int(np.flatnonzero(mk)[-1])}")
    h = np.bincount(live.astype(np.int64), minlength=mx + 1)
    log(f"C1 {nm} occupancy histogram (top of the distribution): " +
        ", ".join(f"{k}:{int(h[k])}" for k in range(mx, max(mx - 12, -1), -1)))
    if nm.startswith("M1"):
        peak_ops = np.flatnonzero(mk)
        # pool contribution at the peak ops, via a second sweep restricted to 840..Q
        d2 = np.zeros(n + 1, np.int32)
        for w in range(840, Q):
            lo_i, hi_i = int(tlo[w]), int(tlo[w + 1])
            tp = to[lo_i:hi_i]
            if len(tp) == 0:
                continue
            bt = base[tp]
            ww = (TOFOP[bt] & (C[tp] == w)) | (CXOP[bt] & (C[tp] == w))
            ww |= (CSWOP[bt] & ((B[tp] == w) | (C[tp] == w)))
            ww |= (SWOP[bt] & ((A[tp] == w) | (C[tp] == w)))
            ww |= (W1OP[bt] & (A[tp] == w))
            rs = RSTOP[bt] & ww
            bounds = np.r_[-1, np.flatnonzero(rs), len(tp) - 1]
            for k in range(len(bounds) - 1):
                a_, b_ = int(bounds[k]) + 1, int(bounds[k + 1])
                if b_ < a_:
                    continue
                lastx = (b_ - 1) if rs[b_] else b_
                if lastx < a_:
                    continue
                d2[int(tp[a_])] += 1
                d2[int(tp[lastx]) + 1] -= 1
        pl = np.cumsum(d2)[:n]
        synd = live - pl
        log(f"C2 at the M1 peak ops: pool live {int(pl[peak_ops].min())}..{int(pl[peak_ops].max())}, "
            f"syndrome live {int(synd[peak_ops].min())}..{int(synd[peak_ops].max())}, "
            f"total {int(live[peak_ops].min())}..{int(live[peak_ops].max())}")
        del d2, pl, synd
    del live

(WORK / "report.txt").write_text("\n".join(REPORT) + "\n")
log("done")
