"""Chemistry ANGLE loader: opcode census + Toffoli target/condition structure.

Read-only tape analysis. No simulation, no verifier run.
Checks every shipped `angle_k_*.kmb`, then dissects one in full.
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
WORK = pathlib.Path("/kaggle/working")
TMP = pathlib.Path("/tmp/chemang")
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
allf = [p for p in sorted(ROOT.rglob("*")) if p.is_file()]
log(f"A0 all mounted files {len(allf)}")
for p in allf[:120]:
    log(f"A1 {p} {p.stat().st_size}")
import zipfile
for z in [p for p in allf if p.suffix == ".zip"]:
    out = TMP / ("z_" + z.stem)
    out.mkdir(exist_ok=True)
    with zipfile.ZipFile(z) as zf:
        for m in zf.namelist():
            if m.endswith(".kmb"):
                zf.extract(m, out)
                log(f"A1z {z.name} -> {m} {out.joinpath(m).stat().st_size}")
cands = [p for p in sorted(TMP.rglob("*.kmb*")) if p.suffix in (".kmb", ".xz")]
cands += [p for p in allf if p.suffix in (".kmb", ".xz")
          and "sample_submission" not in str(p)]
log(f"A2 candidate .kmb files {len(cands)}")
ang = [p for p in cands if "angle" in p.name.lower()]
log(f"A3 angle files {len(ang)}")
k0 = [p for p in ang if p.name.startswith("angle_k_")]
log(f"A4 angle_k_* files {len(k0)} -> {[p.name for p in k0][:20]}")
if not ang:
    (WORK / "report.txt").write_text("\n".join(REPORT) + "\n")
    raise SystemExit("no angle loader found")

names = {0x00: "OP0", 0x01: "PUSH/POP", 0x10: "X", 0x11: "Z", 0x12: "R",
         0x20: "CZ", 0x21: "CX", 0x22: "SWAP", 0x30: "CCZ", 0x31: "CCX",
         0x32: "CSWAP", 0x40: "BIT_INVERT", 0x41: "BIT_STORE0", 0x42: "BIT_STORE1",
         0x50: "HMR", 0x60: "T?", 0x61: "RZ?", 0x62: "RY?", 0x63: "RX?",
         0x70: "Z_POW?"}
TAPES = {}
for p in ang:
    q = TMP / (p.name if p.suffix == ".kmb" else p.stem)
    with (lzma.open(p, "rb") if p.suffix == ".xz" else open(p, "rb")) as f, open(q, "wb") as g:
        while True:
            b = f.read(1 << 24)
            if not b:
                break
            g.write(b)
    raw = q.read_bytes()
    h, regs, secs = unpack(raw)
    ops = secs[1]
    base = ops & 127
    i3 = np.isin(base, [0x30, 0x31, 0x32])
    cen = {names.get(int(k), hex(int(k))): int(v)
           for k, v in zip(*np.unique(base, return_counts=True))}
    nr = {names.get(int(k), hex(int(k))): int(v)
          for k, v in zip(*np.unique(base[i3], return_counts=True))}
    log(f"B0 {p.name} sha {sha256(q)[:16]} bytes {len(raw)} Q {h[1]} nregs {h[3]} "
        f"nops {h[4]} staticT {h[5]} nbits {h[2]}")
    log(f"B1   opcodes {cen}")
    log(f"B2   toffoli-like {nr} total {int(i3.sum())}")
    log(f"B3   header {h}")
    if len(TAPES) == 0 or int(i3.sum()) > TAPES["best"][0]:
        TAPES["best"] = (int(i3.sum()), p.name, h, regs, secs)

tn, tname, h, regs, secs = TAPES["best"]
log(f"C0 dissecting {tname} (static T {tn})")
ops = secs[1]
n = len(ops)
base = ops & 127
cb = (ops & 128) != 0
i3 = np.isin(base, [0x30, 0x31, 0x32])
i2 = np.isin(base, [0x20, 0x21, 0x22])
i1 = np.isin(base, [0x10, 0x11, 0x12, 0x50])
ib = np.isin(base, [0x40, 0x41, 0x42])
ip = base == 0x01
A = np.full(n, -1, np.int64)
B = np.full(n, -1, np.int64)
C = np.full(n, -1, np.int64)
BIT = np.full(n, -1, np.int64)
COND = np.full(n, -1, np.int64)
p3, p2, p1, pb, pc = (np.cumsum(x) for x in (i3, i2, i1, ib, cb))
q3, q2, q1, qb, qc = (np.flatnonzero(x) for x in (i3, i2, i1, ib, cb))
if len(secs.get(2, [])) >= len(q3):
    A[q3] = secs[2][p3[q3] - 1]
    B[q3] = secs[3][p3[q3] - 1]
    C[q3] = secs[4][p3[q3] - 1]
A[q2] = secs[5][p2[q2] - 1]
C[q2] = secs[6][p2[q2] - 1]
A[q1] = secs[7][p1[q1] - 1]
BIT[qb] = secs[8][pb[qb] - 1]
COND[cb] = secs[9][pc[cb] - 1]
Q = int(max(A.max(), B.max(), C.max())) + 1
log(f"C1 Q {Q} n {n} nbits {int(max(BIT.max(), COND.max())) + 1}")
log(f"C2 section lens { {k: len(v) for k, v in secs.items() if k <= 9} }")
log(f"C3 3-op {int(i3.sum())} 2-op {int(i2.sum())} 1-op {int(i1.sum())} bitops {int(ib.sum())} "
    f"push/pop {int(ip.sum())} bit7 {int(cb.sum())}")

# registers
SYN = {}
for r in regs:
    if len(r) < 9:
        continue
    kind, cnt = struct.unpack_from("<II", r, 0)
    body = len(r) - 8 - 4 * cnt
    name = r[8:8 + body].decode("latin1") if body > 0 else "?"
    ids = np.frombuffer(r[8 + body:], dtype=np.uint32)
    SYN[name] = ([int(x) & 0x7FFFFFFF for x in ids], kind)
log(f"C4 registers {len(SYN)} first {list(SYN)[:6]}")
log(f"C5 register sizes {sorted({len(v[0]) for v in SYN.values()})}")
for k in list(SYN)[:4] + list(SYN)[-2:]:
    log(f"C6 reg {k}: kind {SYN[k][1]} ids {SYN[k][0][:14]}")

# Toffoli target classification
tt = np.flatnonzero(i3)
log(f"C7 toffoli-like {len(tt)}; target wires distinct "
    f"{len(np.unique(np.r_[C[tt & 0 + np.flatnonzero(i3)], A[tt[base[tt] == 0x30]]]))}")
tgtC = C[tt]
u, c = np.unique(tgtC, return_counts=True)
log(f"C8 CCX/CSWAP target wires {len(u)} histogram(top) "
    f"{sorted(zip(c.tolist(), u.tolist()))[-10:]}")
log(f"C9 target wire range {int(u.min())}..{int(u.max())}")
hi = u >= 64
log(f"C10 targets >=64: {int(hi.sum())} wires, {int(c[hi].sum())} gates; "
    f"targets <64: {int((~hi).sum())} wires, {int(c[~hi].sum())} gates")
# condition depth
push = ip & cb
pop = ip & ~cb
depth = np.cumsum(push.astype(np.int32) - pop.astype(np.int32))
dd = depth[tt]
for k in np.unique(dd)[:8]:
    m = dd == k
    log(f"C11 toffoli at cond depth {int(k):2d}: {int(m.sum())}")
log(f"C12 inline bit7 on toffoli {int(cb[tt].sum())}")
log(f"C13 push {int(push.sum())} pop {int(pop.sum())} max depth {int(depth.max())}")
# per-wire census (Q small)
log("D wire| touches writesT readsX first last")
for w in range(Q):
    m = (A == w) | (B == w) | (C == w)
    idx = np.flatnonzero(m)
    if len(idx) == 0:
        log(f"D {w:4d}| EMPTY")
        continue
    wt = int((i3[idx] & (C[idx] == w)).sum() + ((base[idx] == 0x30) & m[idx]).sum())
    log(f"D {w:4d}|{len(idx):8d} {wt:7d} {int((base[idx] == 0x11).sum()):7d} "
        f"{int(idx[0]):8d} {int(idx[-1]):8d}")

(WORK / "report.txt").write_text("\n".join(REPORT) + "\n")
log("done")
