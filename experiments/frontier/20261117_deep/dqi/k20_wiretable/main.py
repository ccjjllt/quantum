"""DQI 61c8348d: full 50-wire shedding table, plateau episode matrix, hitting set.

Read-only tape analysis. No simulation, no verifier run in this kernel.

Question: for each of the 50 working ancillas (q840..q889) of the shipped 890-qubit
DQI tape, what does it cost to shed that wire, and what does the cheapest k-wire
ablation do to the peak?

Model (this tape is classical-reversible: gate set X,Z,R,CZ,CX,SWAP,CCZ,CCX,CSWAP,
BIT_*, HMR, no H, input is a computational basis state, so every wire holds a
definite bit and every reset (R/HMR) is the only point at which a wire becomes
reusable):
  * a wire's value lives inside a reset-delimited window;
  * model A (tight, def-use): live range [first touch, last touch] in the window;
  * model B (HMR-delimited): [reset op, last touch].
Shedding a wire removes its value; every later read needs recomputation. The
cheapest recomputation of one superposed-free value is one fresh AND = 1 Toffoli,
so the optimistic shed cost of w = (#windows) x 1 T and the realistic cost =
(#Toffoli writes into w) T. CX-only cells would recompute for 0 T but need a live
source, which at the plateau does not exist (that is exactly what the width says).
"""
import hashlib
import lzma
import pathlib
import struct
import time

import numpy as np

t00 = time.time()
REPORT = []


def log(*a):
    s = " ".join(str(x) for x in a)
    REPORT.append(s)
    print(s, flush=True)


MAGIC = bytes.fromhex("d750c7d5c329d326e3cc9f6834f2b8bf")
PIN = "61c8348d6e85bb0259c4b89f14be9a2834c77bf8a680cf79959bf5e1089cf5de"
WORK = pathlib.Path("/kaggle/working")
TMP = pathlib.Path("/tmp/dqitab")
TMP.mkdir(exist_ok=True)


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
            secs[idx] = (np.frombuffer(pay, dtype=np.uint8 if idx == 1 else np.uint32).copy()
                         if idx <= 9 else pay)
        pos += 16 + size
    return h, regs, secs


ROOT = pathlib.Path("/kaggle/input")
srcs = [p for p in sorted(ROOT.rglob("dqi.kmb*"))
        if p.name in ("dqi.kmb", "dqi.kmb.xz") and "sample_submission" not in str(p)]
KMB = TMP / "dqi.kmb"
found = False
for src in srcs:
    with (lzma.open(src, "rb") if src.suffix == ".xz" else open(src, "rb")) as f, \
            open(KMB, "wb") as g:
        while True:
            b = f.read(1 << 24)
            if not b:
                break
            g.write(b)
    sh = sha256(KMB)
    log(f"A0 {src} bytes {KMB.stat().st_size} sha {sh[:16]} pin={sh == PIN}")
    if sh == PIN:
        found = True
        break
log(f"A1 match {found}")
if not found:
    (WORK / "report.txt").write_text("\n".join(REPORT) + "\n")
    raise SystemExit("tape not found")

H, REGS, S = unpack(KMB.read_bytes())
ops = S[1]
n = int(len(ops))
base = (ops & 127)
cond = (ops & 128) != 0
i3 = np.isin(base, [0x30, 0x31, 0x32])
i2 = np.isin(base, [0x20, 0x21, 0x22])
i1 = np.isin(base, [0x10, 0x11, 0x12, 0x50])
ib = np.isin(base, [0x40, 0x41, 0x42])
ip = base == 0x01
A = np.full(n, -1, np.int32)
B = np.full(n, -1, np.int32)
C = np.full(n, -1, np.int32)
BIT = np.full(n, -1, np.int32)
COND = np.full(n, -1, np.int32)
p3, p2, p1, pb, pc = (np.cumsum(x) for x in (i3, i2, i1, ib, cond))
q3, q2, q1, qb = (np.flatnonzero(x) for x in (i3, i2, i1, ib))
A[q3] = S[2][p3[q3] - 1]
B[q3] = S[3][p3[q3] - 1]
C[q3] = S[4][p3[q3] - 1]
A[q2] = S[5][p2[q2] - 1]
C[q2] = S[6][p2[q2] - 1]
A[q1] = S[7][p1[q1] - 1]
BIT[qb] = S[8][pb[qb] - 1]
COND[cond] = S[9][pc[cond] - 1]
del S
Q = int(max(A.max(), B.max(), C.max())) + 1
nbits = int(max(BIT.max(), COND.max())) + 1
log(f"A2 header Q={H[1]} nregs={H[3]} nops={H[4]} staticT={H[5]} | parsed Q={Q} n={n} "
    f"staticT={int(i3.sum())} nbits={nbits}")

names = {0x10: "X", 0x11: "Z", 0x12: "R", 0x20: "CZ", 0x21: "CX", 0x22: "SWAP",
         0x30: "CCZ", 0x31: "CCX", 0x32: "CSWAP", 0x40: "BIT_INVERT", 0x41: "BIT_STORE0",
         0x42: "BIT_STORE1", 0x50: "HMR", 0x01: "PUSH/POP"}
cen = {names.get(int(k), hex(int(k))): int(v) for k, v in zip(*np.unique(base, return_counts=True))}
log(f"A3 opcodes {cen}")
log(f"A4 conditional ops {int(cond.sum())} (of which Toffoli-like {int((cond & i3).sum())})")

# registers
synd = set()
for r in REGS[:70]:
    for x in np.frombuffer(r, dtype=np.uint32):
        synd.add(int(x))
anc = np.array(sorted(set(range(Q)) - synd), np.int32)
log(f"B0 syndrome qubits {len(synd)} ancillas {len(anc)} "
    f"contiguous840..889={bool(len(anc) == 50 and anc.min() == 840 and anc.max() == 889)}")

# touch index
tq = np.concatenate([A[A >= 0], B[B >= 0], C[C >= 0]])
to = np.concatenate([np.flatnonzero(A >= 0), np.flatnonzero(B >= 0), np.flatnonzero(C >= 0)])
o = np.lexsort((to, tq))
tq = tq[o]
to = to[o]
del o
same = np.r_[False, (tq[1:] == tq[:-1]) & (to[1:] == to[:-1])]
tq = tq[~same]
to = to[~same]
del same
tlo = np.searchsorted(tq, np.arange(Q + 2), "left")
log(f"C0 touch pairs {len(tq)}")

TP = np.zeros(n + 1, np.int32)
TP[1:] = np.cumsum(i3)
IS_TGT = np.isin(base, [0x21, 0x31, 0x32, 0x10, 0x12, 0x50])   # CCZ is diagonal: read only
IS_RST = np.isin(base, [0x12, 0x50])
IS_CCXT = np.isin(base, [0x31, 0x32])

LOS = []
HIS = []
LBS = []
NTOUCH = np.zeros(Q, np.int64)
NRESET = np.zeros(Q, np.int64)
NWIN = np.zeros(Q, np.int64)
NCCXT = np.zeros(Q, np.int64)
NCXW = np.zeros(Q, np.int64)
NXW = np.zeros(Q, np.int64)
NREAD = np.zeros(Q, np.int64)
for w in range(Q):
    lo_i, hi_i = int(tlo[w]), int(tlo[w + 1])
    tp = to[lo_i:hi_i]
    if len(tp) == 0:
        LOS.append(np.zeros(0, np.int32))
        HIS.append(np.zeros(0, np.int32))
        LBS.append(np.zeros(0, np.int32))
        continue
    NTOUCH[w] = len(tp)
    bb = base[tp]
    tg = IS_TGT[bb].copy()
    tg |= (bb == 0x22) & (A[tp] == w)
    rstd = IS_RST[bb] & tg
    NRESET[w] = int(rstd.sum())
    NCCXT[w] = int((IS_CCXT[bb] & tg).sum())
    NCXW[w] = int(((bb == 0x21) & tg).sum())
    NXW[w] = int(((bb == 0x10) & tg).sum())
    NREAD[w] = int(len(tp) - int(tg.sum()))
    bounds = np.r_[-1, np.flatnonzero(rstd), len(tp) - 1]
    los, his, lbs = [], [], []
    for k in range(len(bounds) - 1):
        a_, b_ = int(bounds[k]) + 1, int(bounds[k + 1])
        if b_ < a_:
            continue
        seg = tp[a_:b_ + 1]
        if len(seg) == 0:
            continue
        los.append(int(seg[0]))
        his.append(int(seg[-1]) + 1)
        lbs.append(int(tp[bounds[k]]) if bounds[k] >= 0 else int(seg[0]))
        NWIN[w] += 1
    LOS.append(np.array(los, np.int32))
    HIS.append(np.array(his, np.int32))
    LBS.append(np.array(lbs, np.int32))
log("C1 per-wire windows counted")
log(f"C2 nwindows ancilla total {int(NWIN[840:Q].sum())} "
    f"ccxWrites ancilla total {int(NCCXT[840:Q].sum())} "
    f"cxWrites {int(NCXW[840:Q].sum())} xWrites {int(NXW[840:Q].sum())}")


def profile(lo_list, hi_list, label):
    diff = np.zeros(n + 1, np.int32)
    for w in range(840, Q):
        lo, hi = lo_list[w], hi_list[w]
        if len(lo):
            np.add.at(diff, lo, 1)
            np.add.at(diff, hi, -1)
    live = np.cumsum(diff)[:n]
    mx = int(live.max())
    log(f"D0 {label} max ancilla-live {mx} -> Q {840 + mx}; ops at max {int((live == mx).sum())}")
    return live, mx


LA, MXA = profile(LOS, HIS, "modelA(tight def-use)")
LB, MXB = profile(LBS, HIS, "modelB(HMR-delimited)")
live, mx = LA, MXA
mxops = live == mx
d = np.diff(np.r_[0, mxops.view(np.int8), 0])
starts = np.flatnonzero(d == 1)
ends = np.flatnonzero(d == -1)
log(f"D1 modelA episodes {len(starts)} span {int(starts.min())}..{int(ends.max())} "
    f"mean len {float((ends - starts).mean()):.1f}")
epid = np.full(n, -1, np.int32)
for k in range(len(starts)):
    epid[starts[k]:ends[k]] = k

PM = np.zeros(n + 1, np.int32)
PM[1:] = np.cumsum(mxops)
EPL = np.zeros(Q, np.int64)
EPT = np.zeros(Q, np.int64)
CRIT = np.zeros(Q, np.int64)
TMW = np.zeros(Q, np.int64)
for w in range(Q):
    lo, hi = LOS[w], HIS[w]
    if not len(lo):
        continue
    CRIT[w] = int((PM[hi] - PM[lo]).sum())
    TMW[w] = int((TP[hi] - TP[lo]).sum())
    li, hi_i = int(tlo[w]), int(tlo[w + 1])
    e = epid[to[li:hi_i]]
    EPT[w] = len(np.unique(e[e >= 0]))
    if w < 840:
        continue
    # episodes in which the wire is live at a max-width op
    mask = np.zeros(n, bool)
    for j in range(len(lo)):
        mask[lo[j]:hi[j]] = True
    e2 = epid[mask & mxops]
    EPL[w] = len(np.unique(e2))
    del mask
log("D2 per-wire episode/live/T census done")

log("")
log("E wire|touches reads resets windows epTouch epLive crit T_in_win ccxW cxW xW net1 netC")
rows = []
for w in range(840, Q):
    net1 = int(NWIN[w])
    netc = int(NCCXT[w])
    rows.append((w, net1, netc, int(EPL[w])))
    log(f"E {w:4d}|{int(NTOUCH[w]):8d} {int(NREAD[w]):5d} {int(NRESET[w]):6d} "
        f"{int(NWIN[w]):7d} {int(EPT[w]):7d} {int(EPL[w]):6d} {int(CRIT[w]):8d} "
        f"{int(TMW[w]):9d} {int(NCCXT[w]):5d} {int(NCXW[w]):5d} {int(NXW[w]):4d} "
        f"{net1:5d} {netc:5d}")
tot1 = int(NWIN[840:Q].sum())
totc = int(NCCXT[840:Q].sum())
log(f"E-sub sum windows(=net1@1T) {tot1}  sum ccxW(=netC) {totc}")

log("")
log("F greedy hitting set on the max-width ops")
alive = mxops.copy()


def alivec_of(m):
    c = np.zeros(n + 1, np.int64)
    c[1:] = np.cumsum(m)
    return c


alivec = alivec_of(alive)
live_all = live.copy()
diff2 = np.zeros(n + 1, np.int32)
for w in range(840, Q):
    lo, hi = LOS[w], HIS[w]
    if len(lo):
        np.add.at(diff2, lo, 1)
        np.add.at(diff2, hi, -1)
live_all = np.cumsum(diff2)[:n].copy()
removed = []
for step in range(50):
    best, bestg = -1, -1
    for w in range(840, Q):
        if w in removed:
            continue
        lo, hi = LOS[w], HIS[w]
        if not len(lo):
            continue
        g = int((alivec[hi] - alivec[lo]).sum())
        if g > bestg:
            best, bestg = w, g
    if best < 0 or bestg <= 0:
        log(f"F stop at {len(removed)} removals: no wire reduces the peak further")
        break
    removed.append(best)
    lo, hi = LOS[best], HIS[best]
    for j in range(len(lo)):
        alive[lo[j]:hi[j]] = False
    alivec = alivec_of(alive)
    for w2 in removed:
        lo2, hi2 = LOS[w2], HIS[w2]
        np.add.at(live_all, lo2, -1)
        np.add.at(live_all, hi2, 1)
    pk = int(live_all.max())
    cost = sum(r[1] for r in rows if r[0] in removed)
    log(f"F {step + 1:2d} +q{best} epLive {int(EPL[best])} -> peak {840 + pk} "
        f"cum net1 {cost} T")
    if pk == 0:
        break
log(f"F final removed {sorted(removed)}")

log("")
log("G 4x12-bit word structure on the plateau")
for bw in (840, 852, 864, 876):
    ws = list(range(bw, bw + 12))
    if ws[-1] >= Q:
        continue
    ind = np.zeros(n, bool)
    for w in ws:
        lo, hi = LOS[w], HIS[w]
        for j in range(len(lo)):
            ind[lo[j]:hi[j]] = True
    full = int((ind & mxops).sum())
    tot = int(mxops.sum())
    log(f"G q{bw}..q{ws[-1]} all-12-live plateau ops {full}/{tot} "
        f"({100.0 * full / max(tot, 1):.2f}%)")
    del ind

log("")
log("H mean-T accounting: condition depth of every Toffoli-like")
push = ip & (BIT >= 0)
pop = ip & (BIT < 0)
depth = np.cumsum(push.astype(np.int32) - pop.astype(np.int32))
log(f"H0 push {int(push.sum())} pop {int(pop.sum())} final {int(depth[-1])} "
    f"max {int(depth.max())} neg {int((depth < 0).sum())}")
condT = i3 & cond
dd = depth[condT]
if len(dd):
    for k in np.unique(dd):
        m = dd == k
        cnt = int(m.sum())
        log(f"H1 depth {int(k):2d}: conditional Toffoli {cnt:7d} expected mean "
            f"{cnt / (2.0 ** max(int(k), 1)):10.2f} T")
log(f"H2 staticT {int(i3.sum())} conditionalToffoli {int(condT.sum())} "
    f"unconditional {int((i3 & ~cond).sum())}")
log("H3 a NEW gated block would have to be a phase block whose predicate is a mask of "
    "HMR outcomes; no Z-basis measurement exists, so no data predicate is available")

(WORK / "report.txt").write_text("\n".join(REPORT) + "\n")
log("done")
