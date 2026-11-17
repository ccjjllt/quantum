"""DQI 61c8348d structural audit (v4): header/section alignment, per-wire census, peak models.

Read-only. No simulation, no verifier run.
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
TMP = pathlib.Path("/tmp/dqiaudit")
TMP.mkdir(exist_ok=True)


def sha256(path, chunk=1 << 24):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


ROOT = pathlib.Path("/kaggle/input")
srcs = [p for p in sorted(ROOT.rglob("dqi.kmb*"))
        if p.name in ("dqi.kmb", "dqi.kmb.xz") and "sample_submission" not in str(p)]
KMB = TMP / "dqi.kmb"
for src in srcs:
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
log(f"A0 header {h}")
pos, regs, secs, reglens = 104, [], {}, []
while pos < len(raw):
    idx, size = struct.unpack_from("<QQ", raw, pos)
    pay = raw[pos + 16: pos + 16 + size]
    if idx == 0:
        regs.append(pay)
        reglens.append(size)
    else:
        secs[idx] = np.frombuffer(pay, dtype=np.uint8 if idx == 1 else np.uint32).copy()
    pos += 16 + size
log(f"A1 sections {{k: len(v) for k in secs}} = { {k: len(v) for k, v in secs.items()} }")
log(f"A2 register payload lengths: n {len(reglens)} min {min(reglens)} max {max(reglens)}")
log(f"A3 reg0 hex {regs[0][:64].hex()}")
log(f"A4 reg1 hex {regs[1][:64].hex()}")
log(f"A5 reg69 hex {regs[69][:64].hex()}")
log(f"A6 reg70 hex {regs[70][:64].hex()}")

ops = secs[1]
n = len(ops)
base = ops & 127
cb = (ops & 128) != 0
i3 = np.isin(base, [0x30, 0x31, 0x32])
i2 = np.isin(base, [0x20, 0x21, 0x22])
i1 = np.isin(base, [0x10, 0x11, 0x12, 0x50])
ib = np.isin(base, [0x40, 0x41, 0x42])
cnt = {hex(int(k)): int(v) for k, v in zip(*np.unique(base, return_counts=True))}
log(f"B0 opcode counts {cnt}")
log(f"B1 section sizes: s2..s4 {len(secs[2])},{len(secs[3])},{len(secs[4])} (3-op {int(i3.sum())})")
log(f"B2 s5,s6 {len(secs[5])},{len(secs[6])} (2-op {int(i2.sum())})")
log(f"B3 s7 {len(secs[7])} (1-op {int(i1.sum())})  s8 {len(secs[8])} (bit-ops {int(ib.sum())}, "
    f"HMR {int((base == 0x50).sum())})")
log(f"B4 s9 {len(secs[9])} (bit7-set {int(cb.sum())})  s10 {len(secs.get(10, []))} "
    f"s11 {len(secs.get(11, []))}")
log(f"B5 header h6..h9 {h[6:10]}")

A = np.full(n, -1, np.int32)
B = np.full(n, -1, np.int32)
C = np.full(n, -1, np.int32)
BIT = np.full(n, -1, np.int64)
COND = np.full(n, -1, np.int64)
p3, p2, p1, pb, pc = (np.cumsum(x) for x in (i3, i2, i1, ib, cb))
q3, q2, q1, qb, qc = (np.flatnonzero(x) for x in (i3, i2, i1, ib, cb))
A[q3] = secs[2][p3[q3] - 1]
B[q3] = secs[3][p3[q3] - 1]
C[q3] = secs[4][p3[q3] - 1]
A[q2] = secs[5][p2[q2] - 1]
C[q2] = secs[6][p2[q2] - 1]
A[q1] = secs[7][p1[q1] - 1]
BIT[qb] = secs[8][pb[qb] - 1]
COND[cb] = secs[9][pc[cb] - 1]
Q = int(max(A.max(), B.max(), C.max())) + 1
log(f"B6 parsed Q {Q} n {n}")
log(f"B7 A range {int(A[A >= 0].min())}..{int(A.max())} B {int(B[B >= 0].min())}..{int(B.max())} "
    f"C {int(C[C >= 0].min())}..{int(C.max())}")
log(f"B8 BIT range {int(BIT[BIT >= 0].min())}..{int(BIT.max())} "
    f"COND range {int(COND[COND >= 0].min())}..{int(COND.max())}")

# per-wire census with opcode split
NW = Q + 1
TOT = np.zeros(NW, np.int64)
NX = np.zeros(NW, np.int64)
NZ = np.zeros(NW, np.int64)
NR = np.zeros(NW, np.int64)
NH = np.zeros(NW, np.int64)
NCXT = np.zeros(NW, np.int64)
NCCXT = np.zeros(NW, np.int64)
NCSW = np.zeros(NW, np.int64)
FIRST = np.full(NW, n, np.int64)
LAST = np.full(NW, -1, np.int64)

idx = np.concatenate([np.flatnonzero(A >= 0), np.flatnonzero(B >= 0), np.flatnonzero(C >= 0)])
wid = np.concatenate([A[A >= 0], B[B >= 0], C[C >= 0]]).astype(np.int64)
o = np.lexsort((idx, wid))
idx = idx[o]
wid = wid[o]
same = np.r_[False, (wid[1:] == wid[:-1]) & (idx[1:] == idx[:-1])]
idx = idx[~same]
wid = wid[~same]
logic = np.isin(base[idx], [0x21, 0x31, 0x32, 0x10, 0x12, 0x50]) | (
    (base[idx] == 0x22) & (A[idx] == wid))
for name, arr in (("TOT", TOT), ("NX", NX), ("NZ", NZ), ("NR", NR), ("NH", NH),
                  ("NCXT", NCXT), ("NCCXT", NCCXT), ("NCSW", NCSW)):
    pass
np.add.at(TOT, wid, 1)
np.add.at(NX, wid[logic & (base[idx] == 0x10)], 1)
np.add.at(NZ, wid[base[idx] == 0x11], 1)
np.add.at(NR, wid[logic & (base[idx] == 0x12)], 1)
np.add.at(NH, wid[logic & (base[idx] == 0x50)], 1)
np.add.at(NCXT, wid[logic & (base[idx] == 0x21)], 1)
np.add.at(NCCXT, wid[logic & np.isin(base[idx], [0x31, 0x32])], 1)
np.add.at(NCSW, wid[(base[idx] == 0x22) & (A[idx] == wid)], 1)
lo = np.full(NW, n, np.int64)
hi = np.full(NW, -1, np.int64)
np.minimum.at(lo, wid, idx)
np.maximum.at(hi, wid, idx)

log("")
log("C wire| tot   X      Z      R     HMR   CXt   CCXt  SWAPt | first     last")
for w in range(Q):
    if TOT[w] == 0:
        log(f"C {w:4d}| EMPTY")
        continue
    log(f"C {w:4d}|{TOT[w]:8d} {NX[w]:6d} {NZ[w]:7d} {NR[w]:6d} {NH[w]:6d} {NCXT[w]:6d} "
        f"{NCCXT[w]:6d} {NCSW[w]:6d} |{lo[w]:9d}{hi[w]:10d}")

log("")
log("D reset kinds on the 86 wires that have any")
for w in np.flatnonzero((NR + NH) > 0):
    log(f"D {w:4d} R {NR[w]:5d} HMR {NH[w]:5d} X {NX[w]:5d} tot {TOT[w]:8d}")

(WORK / "report.txt").write_text("\n".join(REPORT) + "\n")
log("done")
