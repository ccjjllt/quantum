"""Which polynomial arrays does the DQI tape's EEA multiply, and is any of them dead?

Tape 575b043f.  Static IR only, CPU only, nothing simulated, nothing written back.

Dumps, for local analysis:

  ccx.npz      every CCX: (op, qa, qb, qc)                   362,012 rows
  ccz.npz      every CCZ: (op, qa, qb, qc)
  touch.npz    whole tape, 2000-op bins, per word 0..73: touch count, write-slot count
  fine.npz     forward EEA region, 200-op bins, per word: touch count
  firstlast.json  per word: first/last touch op over the whole tape and per region
  win1.txt.gz  resolved listing of [17,576,206, 17,830,000)  (~1 EEA iteration of raw ops)

Word w = qubits 12w..12w+11; w<70 is S_w, 70..73 is pool.  The tape is deleted before exit.
"""
import gzip
import importlib.util
import json
import lzma
import pathlib
import sys
import time

import numpy as np

WORK = pathlib.Path("/kaggle/working")
T0 = time.time()
FWD = (17_576_206, 30_151_421)     # forward EEA, real Toffoli boundary
CHI = (30_151_421, 35_627_262)
REV = (35_627_262, 57_520_821)
NW = 74                            # words present as qubits
BIN = 2000
FB = 200


def say(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def find(pattern):
    for p in pathlib.Path("/kaggle/input").rglob(pattern):
        return p
    raise SystemExit(f"missing {pattern}")


ir = load("vqcc_ir", str(find("vqcc_ir.py")))
xz = find("dqi_575b043f.kmb.xz")
RAW = WORK / "dqi.kmb"
say("decompress", xz)
with lzma.open(xz, "rb") as fi, open(RAW, "wb") as fo:
    while True:
        blk = fi.read(1 << 23)
        if not blk:
            break
        fo.write(blk)
say("decompressed", RAW.stat().st_size)

c = ir.Circuit.read(str(RAW))
sha = c.sha256()
t = c.types
N = c.num_ops
say("read", N, "ops", c.num_qubits, "qubits sha", sha[:16])

# ---------------- CCX / CCZ tables ------------------------------------------------------------
slot3 = np.cumsum(ir.L3Q[t], dtype=np.int64) - 1
m3 = ir.L3Q[t]
ops3 = np.flatnonzero(m3)
p3 = slot3[ops3]
base = t & 0x7F
q3a = c.qqq0[p3].astype(np.int32)
q3b = c.qqq1[p3].astype(np.int32)
q3c = c.qqq2[p3].astype(np.int32)
is_ccx = base[ops3] == 0x31
is_ccz = base[ops3] == 0x30
is_csw = base[ops3] == 0x32
say("3q ops", len(ops3), "ccx", int(is_ccx.sum()), "ccz", int(is_ccz.sum()),
    "cswap", int(is_csw.sum()))
np.savez_compressed(WORK / "ccx.npz", op=ops3[is_ccx].astype(np.int32),
                    qa=q3a[is_ccx], qb=q3b[is_ccx], qc=q3c[is_ccx])
np.savez_compressed(WORK / "ccz.npz", op=ops3[is_ccz].astype(np.int32),
                    qa=q3a[is_ccz], qb=q3b[is_ccz], qc=q3c[is_ccz])
np.savez_compressed(WORK / "cswap.npz", op=ops3[is_csw].astype(np.int32),
                    qa=q3a[is_csw], qb=q3b[is_csw], qc=q3c[is_csw])

# ---------------- per-word touch / write histograms -------------------------------------------
NB = (N + BIN - 1) // BIN
touch = np.zeros(NW * NB, dtype=np.int64)
wslot = np.zeros(NW * NB, dtype=np.int64)
CH = 1 << 22
for pkt, lut in (("q0", ir.L1Q), ("qq0", ir.L2Q), ("qq1", ir.L2Q),
                 ("qqq0", ir.L3Q), ("qqq1", ir.L3Q), ("qqq2", ir.L3Q)):
    idx = np.flatnonzero(lut[t]).astype(np.int64)
    arr = getattr(c, pkt)
    acc = np.zeros(NW * NB, dtype=np.int64)
    for i in range(0, len(arr), CH):
        q = arr[i:i + CH].astype(np.int64)
        ix = idx[i:i + CH]
        w = np.minimum(q // 12, NW - 1)
        acc += np.bincount(w * NB + (ix // BIN), minlength=NW * NB)
    if pkt in ("qq1", "qqq2"):
        wslot += acc
    touch += acc
    say("touch", pkt, len(arr))
touch = touch.reshape(NW, NB).astype(np.uint16)
wslot = wslot.reshape(NW, NB).astype(np.uint16)
np.savez_compressed(WORK / "touch.npz", touch=touch, wslot=wslot, bin=BIN, nw=NW)

first = np.full(NW, -1, dtype=np.int64)
last = np.full(NW, -1, dtype=np.int64)
for w in range(NW):
    nz = np.flatnonzero(touch[w])
    if len(nz):
        first[w] = nz[0] * BIN
        last[w] = min(N, (nz[-1] + 1) * BIN)
per_region = {}
for rn, (lo, hi) in (("fwd", FWD), ("chien", CHI), ("rev", REV)):
    b0, b1 = lo // BIN, min(NB, (hi + BIN - 1) // BIN)
    sub = touch[:, b0:b1]
    per_region[rn] = {
        "touch_total": sub.astype(np.int64).sum(1).tolist(),
        "words_touched": np.flatnonzero(sub.any(1)).tolist(),
    }
json.dump({"sha": sha, "num_ops": N, "bin": BIN, "first": first.tolist(), "last": last.tolist(),
           "FWD": FWD, "CHI": CHI, "REV": REV, "regions": per_region},
          open(WORK / "firstlast.json", "w"), indent=1)
say("first/last", first.tolist(), last.tolist())

# fine histogram inside the forward EEA region
a0, a1 = FWD
NF = (a1 - a0 + FB - 1) // FB
fine = np.zeros(NW * NF, dtype=np.int64)
for pkt, lut in (("q0", ir.L1Q), ("qq0", ir.L2Q), ("qq1", ir.L2Q),
                 ("qqq0", ir.L3Q), ("qqq1", ir.L3Q), ("qqq2", ir.L3Q)):
    idx = np.flatnonzero(lut[t]).astype(np.int64)
    arr = getattr(c, pkt)
    for i in range(0, len(arr), CH):
        ix = idx[i:i + CH]
        k = (ix >= a0) & (ix < a1)
        if not k.any():
            continue
        q = arr[i:i + CH][k].astype(np.int64)
        w = np.minimum(q // 12, NW - 1)
        fine += np.bincount(w * NF + ((ix[k] - a0) // FB), minlength=NW * NF)
fine = fine.reshape(NW, NF).astype(np.uint8)
np.savez_compressed(WORK / "fine.npz", fine=fine, fb=FB, a0=a0, a1=a1)
say("fine", fine.shape)

# ---------------- raw text of one EEA iteration ----------------------------------------------
W0, W1 = FWD[0], FWD[0] + 253_794
with gzip.open(WORK / "win1.txt.gz", "wt") as fo:
    for i, nm, qs, tb, cb in c.decode(W0, W1):
        fo.write(f"{i}\t{nm}\t{','.join(str(q) for q in qs)}\t"
                 f"{'' if tb is None else tb}\t{'' if cb is None else cb}\n")
say("window written", W1 - W0)

RAW.unlink()
json.dump({"sha": sha, "ok": True}, open(WORK / "done.json", "w"))
say("done")
