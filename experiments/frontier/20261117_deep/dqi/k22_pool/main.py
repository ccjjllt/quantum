"""DQI 61c8348d: definitive 50-wire shed table with true operand roles (v5). Read-only.

Roles: CCX/CSWAP write C, read A,B.  CX writes C, reads A.  SWAP writes A and C.
CCZ is diagonal: reads A,B,C (no write).  X writes A.  R writes A (destructive).
HMR reads+writes A (X-basis measure + reset).  Z reads A.

Per wire w (pool = 840..889):
  reads      control/read-only touches                (demand for w's value)
  writesT    touches where a Toffoli-like writes w    (replay cost lower bound)
  writesX    CX writes (0 T to replay if a source is live)
  windows    R/HMR-delimited value lifetimes
  winCCX     windows that contain >=1 Toffoli write   (honest per-window replay unit)
  T_in_win   static Toffoli inside w's live windows   (whole-window replay upper bound)
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
TMP = pathlib.Path("/tmp/dqipool")
TMP.mkdir(exist_ok=True)


def sha256(path, chunk=1 << 24):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


ROOT = pathlib.Path("/kaggle/input")
KMB = TMP / "dqi.kmb"
for src in [p for p in sorted(ROOT.rglob("dqi.kmb*")) if p.name in ("dqi.kmb", "dqi.kmb.xz")
            and "sample_submission" not in str(p)]:
    with (lzma.open(src, "rb") if src.suffix == ".xz" else open(src, "rb")) as f, \
            open(KMB, "wb") as g:
        while True:
            b = f.read(1 << 24)
            if not b:
                break
            g.write(b)
    if sha256(KMB) == PIN:
        break

raw = KMB.read_bytes()
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

# register names -> wire sets (payload: u32 kind, u32 count, name bytes, u32 ids)
SYN = set()
rn = []
for r in regs:
    kind, cnt = struct.unpack_from("<II", r, 0)
    body = len(r) - 8 - 4 * cnt
    name = r[8:8 + body].decode("latin1")
    ids = np.frombuffer(r[8 + body:], dtype=np.uint32)
    rn.append((name, kind, ids.tolist()))
    if name.startswith("S"):
        SYN |= {int(x) & 0x7FFFFFFF for x in ids}
log(f"A0 registers {len(regs)} first3 {[x[0] for x in rn[:3]]} last1 {rn[-1][0]}")
log(f"A1 syndrome qubits {len(SYN)} min {min(SYN)} max {max(SYN)} "
    f"=0..839 {SYN == set(range(840))}")
log(f"A2 S67 {sorted(x & 0x7FFFFFFF for x in rn[67][2])[:3]}.. S69 "
    f"{sorted(x & 0x7FFFFFFF for x in rn[69][2])[:3]}")
log(f"A3 E0 raw {rn[70][2][:4]} E4094 raw {rn[-1][2][:4]}")

ops = secs[1]
n = len(ops)
base = ops & 127
i3 = np.isin(base, [0x30, 0x31, 0x32])
i2 = np.isin(base, [0x20, 0x21, 0x22])
i1 = np.isin(base, [0x10, 0x11, 0x12, 0x50])
A = np.full(n, -1, np.int64)
B = np.full(n, -1, np.int64)
C = np.full(n, -1, np.int64)
p3, p2, p1 = (np.cumsum(x) for x in (i3, i2, i1))
q3, q2, q1 = (np.flatnonzero(x) for x in (i3, i2, i1))
A[q3] = secs[2][p3[q3] - 1]
B[q3] = secs[3][p3[q3] - 1]
C[q3] = secs[4][p3[q3] - 1]
A[q2] = secs[5][p2[q2] - 1]
C[q2] = secs[6][p2[q2] - 1]
A[q1] = secs[7][p1[q1] - 1]
Q = int(max(A.max(), B.max(), C.max())) + 1
TP = np.zeros(n + 1, np.int64)
TP[1:] = np.cumsum(i3)
log(f"A4 Q {Q} n {n} staticT {int(i3.sum())}")

# role arrays: for each (op,wire) touch, is it a write?  Build 3 explicit role streams.
WRITE = np.zeros(n, bool)      # does this op write its C operand (or A for 1-op)?
CCX_T = np.isin(base, [0x31, 0x32])
CXW = base == 0x21
XW = base == 0x10
RW = base == 0x12
HW = base == 0x50
SWAPB = base == 0x22
CCZ = base == 0x30
ZW = base == 0x11

NW = Q + 1


def acc(mask_ops, wire_arr, out):
    m = mask_ops
    np.add.at(out, wire_arr[m], 1)


TOT = np.zeros(NW, np.int64)
RD = np.zeros(NW, np.int64)
WT = np.zeros(NW, np.int64)
WX = np.zeros(NW, np.int64)
WXX = np.zeros(NW, np.int64)
RES = np.zeros(NW, np.int64)
FIRST = np.full(NW, n, np.int64)
LAST = np.full(NW, -1, np.int64)

# touches
for arr, isw in ((A, None), (B, None), (C, None)):
    m = arr >= 0
    np.add.at(TOT, arr[m], 1)
    np.minimum.at(FIRST, arr[m], np.flatnonzero(m))
    np.maximum.at(LAST, arr[m], np.flatnonzero(m))
# CCX/CSWAP: C written, A,B read
np.add.at(WT, C[CCX_T], 1)
np.add.at(RD, A[CCX_T], 1)
np.add.at(RD, B[CCX_T], 1)
# CX: C written, A read
np.add.at(WX, C[CXW], 1)
np.add.at(RD, A[CXW], 1)
# SWAP: A and C written
np.add.at(WX, A[SWAPB], 1)
np.add.at(WX, C[SWAPB], 1)
# CCZ: all read
for arr in (A, B, C):
    np.add.at(RD, arr[CCZ], 1)
# X: A written ; R: A written (destructive) ; HMR: A written+read ; Z: A read
np.add.at(WXX, A[XW], 1)
np.add.at(RES, A[RW], 1)
np.add.at(RES, A[HW], 1)
np.add.at(RD, A[HW], 1)
np.add.at(RD, A[ZW], 1)
log(f"A5 role totals: writesT {int(WT.sum())} writesCX {int(WX.sum())} writesX {int(WXX.sum())} "
    f"resets {int(RES.sum())} reads {int(RD.sum())} touches {int(TOT.sum())}")

# per-wire windows + per-window CCX count
POOL = [w for w in range(840, Q)]
win = {}
for w in POOL:
    lst = np.flatnonzero((A == w) | (B == w) | (C == w))
    rst = lst[(base[lst] == 0x12) | (base[lst] == 0x50)]
    bounds = np.r_[-1, rst, n]
    los, his, nccx, tccx = [], [], 0, 0
    winccx = 0
    for k in range(len(bounds) - 1):
        a_, b_ = int(bounds[k]) + 1, int(bounds[k + 1])
        if b_ <= a_:
            continue
        seg = lst[(lst >= a_) & (lst < b_)]
        if len(seg) == 0:
            continue
        los.append(int(seg[0]))
        his.append(int(seg[-1]) + 1)
        nw = int(np.isin(base[seg], [0x30, 0x31, 0x32]).sum())
        nccx += nw
        winccx += 0 if nw == 0 else 1
    win[w] = (np.array(los, np.int32), np.array(his, np.int32), winccx, nccx)
log("A6 windows built")

log("")
log("E wire| touches  reads  writeT writeCX writeX resets windows winWithT winTstatic "
    "T_in_win net1@1T netC")
rows = []
for w in POOL:
    lo, hi, winccx, nccx = win[w]
    tmw = int((TP[hi] - TP[lo]).sum()) if len(lo) else 0
    rows.append((w, len(lo), winccx, int(WT[w]), tmw))
    log(f"E {w:4d}|{TOT[w]:8d} {RD[w]:7d} {WT[w]:7d} {WX[w]:8d} {WXX[w]:6d} {RES[w]:6d} "
        f"{len(lo):7d} {winccx:8d} {nccx:9d} {tmw:9d} {len(lo):9d} {WT[w]:6d}")
tot_win = sum(r[1] for r in rows)
tot_winccx = sum(r[2] for r in rows)
tot_wt = sum(r[3] for r in rows)
log(f"E-sub pool windows {tot_win} windowsWithToffoli {tot_winccx} writeT {tot_wt} "
    f"avg {tot_win / len(POOL):.1f} / {tot_winccx / len(POOL):.1f} / {tot_wt / len(POOL):.1f}")

# pool-live width profile
diff = np.zeros(n + 1, np.int32)
for w in POOL:
    lo, hi = win[w][0], win[w][1]
    if len(lo):
        np.add.at(diff, lo, 1)
        np.add.at(diff, hi, -1)
live = np.cumsum(diff)[:n]
mx = int(live.max())
log("")
log(f"F pool-live peak {mx} -> Q {840 + mx}; ops at peak {int((live == mx).sum())}")
mxops = live == mx
d = np.diff(np.r_[0, mxops.view(np.int8), 0])
st = np.flatnonzero(d == 1)
en = np.flatnonzero(d == -1)
log(f"F episodes at peak {len(st)} span {int(st.min())}..{int(en.max())} "
    f"mean len {float((en - st).mean()):.1f}")
PM = np.zeros(n + 1, np.int64)
PM[1:] = np.cumsum(mxops)
log("F leave-one-out peak (should be peak-1 if every wire is live at the peak):")
for w in POOL[:6] + POOL[-4:]:
    lo, hi = win[w][0], win[w][1]
    cov = int((PM[hi] - PM[lo]).sum())
    log(f"F  q{w}: live at {cov}/{int(mxops.sum())} peak ops")

alive = mxops.copy()
alivec = np.zeros(n + 1, np.int64)
alivec[1:] = np.cumsum(alive)
removed = []
live_all = live.copy()
for step in range(len(POOL)):
    best, bg = -1, -1
    for w in POOL:
        if w in removed:
            continue
        lo, hi = win[w][0], win[w][1]
        if not len(lo):
            continue
        g = int((alivec[hi] - alivec[lo]).sum())
        if g > bg:
            best, bg = w, g
    if best < 0 or bg <= 0:
        break
    removed.append(best)
    lo, hi = win[best][0], win[best][1]
    for j in range(len(lo)):
        alive[lo[j]:hi[j]] = False
    alivec = np.zeros(n + 1, np.int64)
    alivec[1:] = np.cumsum(alive)
    np.add.at(live_all, lo, -1)
    np.add.at(live_all, hi, 1)
    if step < 5 or step % 10 == 9:
        log(f"F greedy {step + 1:2d} +q{best} peak {840 + int(live_all.max())} "
            f"cum windows {sum(win[x][2] for x in removed)} "
            f"cum winTstatic {sum(win[x][3] for x in removed)}")
log(f"F greedy removed {len(removed)} wires; all 50: pool-live peak "
    f"{int(live_all.max())}")

(WORK / "report.txt").write_text("\n".join(REPORT) + "\n")
log("done")
