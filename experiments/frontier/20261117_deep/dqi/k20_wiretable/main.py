"""DQI 61c8348d: full 50-wire shedding table, plateau episode matrix, hitting set (v3).

Read-only tape analysis. No simulation, no verifier run in this kernel.

This tape is classical-reversible: the gate set is X,Z,R,CZ,CX,SWAP,CCZ,CCX,CSWAP,
BIT_INVERT,BIT_STORE0/1,HMR,PUSH/POP_CONDITION -- there is no H, the input is a
computational basis state, so every wire holds a definite bit and an R/HMR reset is
the only point at which a wire becomes reusable (|0>).

Model:
  * a wire's value lives inside a reset-delimited window;
  * live range of a window = [first touch, last touch]  (model A, tight def-use)
    or [reset op, last touch]                           (model B, HMR-delimited);
  * the 840 syndrome qubits hold the input and must be restored, so they are live
    for the whole tape: Q(t) = 840 + #(live pool wires);
  * shedding a pool wire removes its value, so every later read needs a
    recomputation. Cheapest recomputation of one value = 1 fresh AND = 1 Toffoli.
    Optimistic shed cost(w) = #windows(w) x 1 T; realistic = #Toffoli writes(w) T.
"""
import hashlib
import lzma
import pathlib
import struct

import numpy as np

REPORT = []


def log(*a):
    s = " ".join(str(x) for x in a)
    REPORT.append(s)
    print(s, flush=True)


MAGIC = bytes.fromhex("d750c7d5c329d326e3cc9f6834f2b8bf")
PIN = "61c8348d6e85bb0259c4b89f14be9a2834c77bf8a680cf79959bf5e1089cf5de"
WORK = pathlib.Path("/kaggle/working")
TMP = pathlib.Path("/tmp/dqitab3")
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
base = ops & 127
condbit = (ops & 128) != 0
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
p3, p2, p1, pb, pc = (np.cumsum(x) for x in (i3, i2, i1, ib, condbit))
q3, q2, q1, qb = (np.flatnonzero(x) for x in (i3, i2, i1, ib))
A[q3] = S[2][p3[q3] - 1]
B[q3] = S[3][p3[q3] - 1]
C[q3] = S[4][p3[q3] - 1]
A[q2] = S[5][p2[q2] - 1]
C[q2] = S[6][p2[q2] - 1]
A[q1] = S[7][p1[q1] - 1]
BIT[qb] = S[8][pb[qb] - 1]
COND[condbit] = S[9][pc[condbit] - 1]
del S
Q = int(max(A.max(), B.max(), C.max())) + 1
nbits = int(max(BIT.max(), COND.max())) + 1
log(f"A2 header Q={H[1]} nregs={H[3]} nops={H[4]} staticT={H[5]} | parsed Q={Q} n={n} "
    f"staticT={int(i3.sum())} nbits={nbits}")

names = {0x00: "OP0", 0x01: "PUSH/POP", 0x02: "OP2", 0x10: "X", 0x11: "Z", 0x12: "R",
         0x20: "CZ", 0x21: "CX", 0x22: "SWAP", 0x30: "CCZ", 0x31: "CCX", 0x32: "CSWAP",
         0x40: "BIT_INVERT", 0x41: "BIT_STORE0", 0x42: "BIT_STORE1", 0x50: "HMR"}
cen = {names.get(int(k), hex(int(k))): int(v) for k, v in zip(*np.unique(base, return_counts=True))}
log(f"A3 opcodes {cen}")
log(f"A4 bit7-set ops {int(condbit.sum())}; Toffoli-like with bit7 {int((condbit & i3).sum())}; "
    f"0x01 with bit7 {int((condbit & ip).sum())} without {int((~condbit & ip).sum())}")

# ---------------------------------------------------------------- touch index
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

TGT_CODE = np.isin(base, [0x21, 0x31, 0x32, 0x10, 0x12, 0x50])   # 1-operand / 2-operand targets
RST_CODE = np.isin(base, [0x12, 0x50])
CCXT_CODE = np.isin(base, [0x31, 0x32])
CXW_CODE = base == 0x21
XW_CODE = base == 0x10
TP = np.zeros(n + 1, np.int32)
TP[1:] = np.cumsum(i3)

NTOUCH = np.zeros(Q, np.int64)
NRESET = np.zeros(Q, np.int64)
NWIN = np.zeros(Q, np.int64)
NCCXT = np.zeros(Q, np.int64)
NCXW = np.zeros(Q, np.int64)
NXW = np.zeros(Q, np.int64)
NREAD = np.zeros(Q, np.int64)
LOS, HIS, LBS = [], [], []
for w in range(Q):
    lo_i, hi_i = int(tlo[w]), int(tlo[w + 1])
    tp = to[lo_i:hi_i]
    if len(tp) == 0:
        LOS.append(np.zeros(0, np.int32)); HIS.append(np.zeros(0, np.int32))
        LBS.append(np.zeros(0, np.int32))
        continue
    NTOUCH[w] = len(tp)
    bb = base[tp]
    tg = TGT_CODE[tp].copy()
    tg |= (bb == 0x22) & (A[tp] == w)
    rstd = RST_CODE[tp] & tg
    NRESET[w] = int(rstd.sum())
    NCCXT[w] = int((CCXT_CODE[tp] & tg).sum())
    NCXW[w] = int((CXW_CODE[tp] & tg).sum())
    NXW[w] = int((XW_CODE[tp] & tg).sum())
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
        los.append(int(seg[0])); his.append(int(seg[-1]) + 1)
        lbs.append(int(tp[bounds[k]]) if bounds[k] >= 0 else int(seg[0]))
        NWIN[w] += 1
    LOS.append(np.array(los, np.int32)); HIS.append(np.array(his, np.int32))
    LBS.append(np.array(lbs, np.int32))
log("C1 windows counted")

reset_wires = np.flatnonzero(NRESET > 0)
log(f"C2 wires with >=1 reset {len(reset_wires)} -> [{reset_wires.min()}..{reset_wires.max()}] "
    f"contiguous={bool(len(reset_wires) == reset_wires.max() - reset_wires.min() + 1)}")
log(f"C3 wires with 0 resets {int((NRESET == 0).sum())} max such wire "
    f"{int(np.flatnonzero(NRESET == 0).max())}")
POOL = reset_wires
log(f"C4 pool size {len(POOL)} total windows {int(NWIN[POOL].sum())} "
    f"toffoli-writes {int(NCCXT[POOL].sum())} cx-writes {int(NCXW[POOL].sum())} "
    f"x-writes {int(NXW[POOL].sum())}")
log(f"C5 top-8 touched wires {list(np.argsort(NTOUCH)[-8:][::-1])}")


def profile(lo_list, hi_list, label):
    diff = np.zeros(n + 1, np.int32)
    for w in POOL:
        lo, hi = lo_list[w], hi_list[w]
        if len(lo):
            np.add.at(diff, lo, 1)
            np.add.at(diff, hi, -1)
    live = np.cumsum(diff)[:n]
    mx = int(live.max())
    log(f"D0 {label} max pool-live {mx} -> Q {840 + mx}; ops at max {int((live == mx).sum())}")
    return live, mx


LA, MXA = profile(LOS, HIS, "modelA(tight def-use)")
LB, MXB = profile(LBS, HIS, "modelB(HMR-delimited)")
live, mx = LA, MXA
mxops = live == mx
d = np.diff(np.r_[0, mxops.view(np.int8), 0])
starts = np.flatnonzero(d == 1)
ends = np.flatnonzero(d == -1)
log(f"D1 modelA plateau episodes {len(starts)} span {int(starts.min())}..{int(ends.max())} "
    f"mean len {float((ends - starts).mean()):.1f}")
epid = np.full(n, -1, np.int32)
for k in range(len(starts)):
    epid[starts[k]:ends[k]] = k

PM = np.zeros(n + 1, np.int32)
PM[1:] = np.cumsum(mxops)
CRIT = np.zeros(Q, np.int64)
TMW = np.zeros(Q, np.int64)
EPT = np.zeros(Q, np.int64)
EPL = np.zeros(Q, np.int64)
for w in POOL:
    lo, hi = LOS[w], HIS[w]
    if not len(lo):
        continue
    CRIT[w] = int((PM[hi] - PM[lo]).sum())
    TMW[w] = int((TP[hi] - TP[lo]).sum())
    li, hi_i = int(tlo[w]), int(tlo[w + 1])
    e = epid[to[li:hi_i]]
    EPT[w] = len(np.unique(e[e >= 0]))
    mask = np.zeros(n, bool)
    for j in range(len(lo)):
        mask[lo[j]:hi[j]] = True
    e2 = epid[mask & mxops]
    EPL[w] = len(np.unique(e2))
    del mask
log("D2 per-wire census done")

log("")
log("E wire|touches reads resets windows epTouch epLive crit T_in_win ccxW cxW xW net1 netC")
for w in POOL:
    log(f"E {w:4d}|{int(NTOUCH[w]):8d} {int(NREAD[w]):5d} {int(NRESET[w]):6d} "
        f"{int(NWIN[w]):7d} {int(EPT[w]):7d} {int(EPL[w]):6d} {int(CRIT[w]):8d} "
        f"{int(TMW[w]):9d} {int(NCCXT[w]):5d} {int(NCXW[w]):5d} {int(NXW[w]):4d} "
        f"{int(NWIN[w]):5d} {int(NCCXT[w]):5d}")
tot1 = int(NWIN[POOL].sum())
totc = int(NCCXT[POOL].sum())
log(f"E-sub sum windows(net1 @1T) {tot1} sum ccxW(netC) {totc} "
    f"avg per qubit {tot1 / len(POOL):.1f} / {totc / len(POOL):.1f}")

log("")
log("F greedy hitting set on the plateau ops (largest live coverage first)")
alive = mxops.copy()


def csum(m):
    c = np.zeros(n + 1, np.int64)
    c[1:] = np.cumsum(m)
    return c


alivec = csum(alive)
live_all = live.copy()
removed = []
for step in range(len(POOL) + 1):
    best, bestg = -1, -1
    for w in POOL:
        if w in removed:
            continue
        lo, hi = LOS[w], HIS[w]
        if not len(lo):
            continue
        g = int((alivec[hi] - alivec[lo]).sum())
        if g > bestg:
            best, bestg = w, g
    if best < 0 or bestg <= 0:
        nrem = len(removed)
        pk = int(live_all.max())
        log(f"F stop after {nrem} removals: no single wire covers a remaining plateau op "
            f"(peak {840 + pk})")
        break
    removed.append(best)
    lo, hi = LOS[best], HIS[best]
    for j in range(len(lo)):
        alive[lo[j]:hi[j]] = False
    alivec = csum(alive)
    np.add.at(live_all, lo, -1)
    np.add.at(live_all, hi, 1)
    pk = int(live_all.max())
    cost = sum(int(NWIN[w]) for w in removed)
    costc = sum(int(NCCXT[w]) for w in removed)
    log(f"F {step + 1:2d} +q{best} epLive {int(EPL[best])} -> peak {840 + pk} "
        f"cum net1 {cost} T netC {costc} T")
    if pk == 0:
        break

log("")
log("G 12-bit word structure on the plateau")
for bw in (840, 852, 864, 876):
    ws = [w for w in range(bw, bw + 12) if w < Q]
    if not ws:
        continue
    ind = np.zeros(n, bool)
    for w in ws:
        lo, hi = LOS[w], HIS[w]
        for j in range(len(lo)):
            ind[lo[j]:hi[j]] = True
    full = int((ind & mxops).sum())
    tot = int(mxops.sum())
    log(f"G q{bw}..q{ws[-1]} all-live plateau ops {full}/{tot} "
        f"({100.0 * full / max(tot, 1):.2f}%)")
    del ind

log("")
log("H PUSH/POP_CONDITION region depth of every Toffoli-like")
push = ip & condbit
pop = ip & ~condbit
depth = np.cumsum(push.astype(np.int32) - pop.astype(np.int32))
log(f"H0 push {int(push.sum())} pop {int(pop.sum())} final depth {int(depth[-1])} "
    f"min {int(depth.min())} max {int(depth.max())}")
dd3 = depth[i3]
u, c = np.unique(dd3, return_counts=True)
pred = 0.0
for k, cnt in zip(u, c):
    pr = 2.0 ** (-max(int(k), 0))
    pred += cnt * pr
    log(f"H1 depth {int(k):2d}: Toffoli-like {int(cnt):7d} expected mean {cnt * pr:10.2f} T")
log(f"H2 staticT {int(i3.sum())} official meanT 367120.004 discount "
    f"{int(i3.sum()) - 367120.004:.3f} model {pred:.3f}")
if len(COND[push]):
    pc_ = COND[push]
    log(f"H3 pushed cond ids: n {len(pc_)} min {int(pc_.min())} max {int(pc_.max())} "
        f"distinct {len(np.unique(pc_))}")
log(f"H4 Toffoli-like inside a push region {int((dd3 > 0).sum())} "
    f"({100.0 * int((dd3 > 0).sum()) / max(int(i3.sum()), 1):.3f}% of static T)")

(WORK / "report.txt").write_text("\n".join(REPORT) + "\n")
log("done")
