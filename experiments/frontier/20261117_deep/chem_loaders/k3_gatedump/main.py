"""Dump the gate-level structure of one shipped ANGLE loader (read-only)."""
import pathlib
import struct
import zipfile

import numpy as np

REPORT = []


def log(*a):
    s = " ".join(str(x) for x in a)
    REPORT.append(s)
    print(s, flush=True)


MAGIC = bytes.fromhex("d750c7d5c329d326e3cc9f6834f2b8bf")
TMP = pathlib.Path("/tmp/dumpg")
TMP.mkdir(exist_ok=True)
ROOT = pathlib.Path("/kaggle/input")
for z in sorted(ROOT.rglob("*.zip")):
    with zipfile.ZipFile(z) as zf:
        for m in zf.namelist():
            if m.endswith("angle_k_0.kmb") or m.endswith("angle_k_4.kmb"):
                zf.extract(m, TMP)
p = sorted(TMP.rglob("angle_k_*.kmb"))[0]
raw = p.read_bytes()
h = list(struct.unpack_from("<4I9Q", raw, 16))
pos, regs, secs = 104, [], {}
while pos < len(raw):
    idx, size = struct.unpack_from("<QQ", raw, pos)
    if 1 <= idx <= 9:
        secs[idx] = np.frombuffer(raw[pos + 16:pos + 16 + size],
                                  dtype=np.uint8 if idx == 1 else np.uint32).copy()
    pos += 16 + size
ops = secs[1]
n = len(ops)
base = ops & 127
cb = (ops & 128) != 0
log(f"A0 {p.name} Q {h[1]} n {n} staticT {h[5]}")
for op, nm in ((0x10, "X"), (0x11, "Z"), (0x12, "R"), (0x20, "CZ"), (0x21, "CX"),
               (0x22, "SWAP"), (0x30, "CCZ"), (0x31, "CCX"), (0x32, "CSWAP"),
               (0x40, "BI"), (0x41, "BS0"), (0x42, "BS1"), (0x50, "HMR"), (0x01, "PUSH")):
    k = int((base == op).sum())
    if k:
        log(f"A1 {nm} {k}")
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

log("")
log("B every CCX in order:  op  ctrl1 ctrl2 target   (sel=0..10 word=11..50 anc>=51)")
for k in np.flatnonzero(i3).tolist():
    log(f"B {k:6d} {int(A[k]):5d} {int(B[k]):5d} -> {int(C[k]):5d}")

log("")
log("C CX control histogram (how many CX each wire controls)")
cx = np.flatnonzero(base == 0x21)
u, c = np.unique(A[cx], return_counts=True)
o = np.argsort(-c)
log(f"C0 CX total {len(cx)}; controls used {len(u)}")
for j in o[:70].tolist():
    log(f"C1 ctrl {int(u[j]):4d} -> {int(c[j]):6d} CX")

log("")
log("D first 60 ops verbatim")
for k in range(min(60, n)):
    b = int(base[k])
    if b in (0x30, 0x31, 0x32):
        log(f"D {k:4d} op{b:02x} {int(A[k])} {int(B[k])} {int(C[k])}")
    elif b in (0x20, 0x21, 0x22):
        log(f"D {k:4d} op{b:02x} {int(A[k])} -> {int(C[k])}")
    else:
        log(f"D {k:4d} op{b:02x} {int(A[k])}")

pathlib.Path("/kaggle/working/report.txt").write_text("\n".join(REPORT) + "\n")
log("done")
