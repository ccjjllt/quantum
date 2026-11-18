"""DQI align line: identify the two large Toffoli clusters of tape 575b043f.

CPU-only Kaggle kernel, **static IR read only, no simulation**.

Targets (from the dqi_bm line's measured attribution):
  forward span [19,508,954, 21,385,877)  -> 29,543 T   (3 multiply blocks, 20,723 small)
  reverse span [46,230,185, 52,842,219)  -> 65,774 T   (66 multiply blocks, 46,966 small)
  plus the 132-block cluster [21,385,877, 21,588,611) for reference (5,896 T)

Dumps per span:
  * base-opcode histogram (confirms CSWAP = 0), CX / CX_IF / SWAP / SWAP_IF counts
  * dense sub-blocks (split at Toffoli gaps > 20k and > 2k) -> is there a repeated step?
  * the ordered list of big CCX blocks (control, control, target) in 12-bit word units
  * how many CCX have all operands inside one word (the 12-bit zero-test signature)
  * top CCX word triples and top CX word pairs
  * how many Toffolis are condition-gated (_IF)

Output: align.json (small).
"""
import hashlib
import importlib.util
import json
import lzma
import pathlib
import sys
import time

import numpy as np

WORK = pathlib.Path("/kaggle/working")
EEA_FWD_START = 17_576_206          # measured: first Toffoli-like op of the tape
T0 = time.time()
OUT = {}


def say(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def find_inputs():
    xz = irp = None
    for p in pathlib.Path("/kaggle/input").rglob("dqi_575b043f.kmb.xz"):
        xz = p
        break
    for p in pathlib.Path("/kaggle/input").rglob("vqcc_ir.py"):
        irp = p
        break
    if not (xz and irp):
        raise SystemExit("inputs not found")
    return xz, irp


XZ, IRPY = find_inputs()
WORK.mkdir(parents=True, exist_ok=True)
raw = WORK / "dqi_575b043f.kmb"
if not raw.exists():
    say("decompress", XZ)
    with lzma.open(XZ, "rb") as fi, open(raw, "wb") as fo:
        while True:
            b = fi.read(1 << 23)
            if not b:
                break
            fo.write(b)
OUT["kmb_sha256"] = sha256(raw)
OUT["kmb_bytes"] = raw.stat().st_size

spec = importlib.util.spec_from_file_location("vqcc_ir", str(IRPY))
ir = importlib.util.module_from_spec(spec)
sys.modules["vqcc_ir"] = ir
spec.loader.exec_module(ir)

c = ir.Circuit.read(str(raw))
t = c.types
N = c.num_ops
OUT["num_ops"] = N
OUT["num_qubits"] = c.num_qubits
OUT["static_toffoli"] = int(c.toffoli_like())
say("ops", N, "Q", c.num_qubits, "T", OUT["static_toffoli"])

base = (t & 0x7F).astype(np.int64)
iscond = (t & 0x80).astype(bool)

names = {0x00: "NEG", 0x01: "POP_CONDITION", 0x10: "Z", 0x11: "X", 0x12: "R",
         0x13: "Z_POW", 0x50: "HMR", 0x20: "CZ", 0x21: "CX", 0x22: "SWAP",
         0x30: "CCZ", 0x31: "CCX", 0x32: "CSWAP", 0x40: "BIT_STORE0",
         0x41: "BIT_STORE1", 0x42: "BIT_INVERT", 0x30 + 0x02: "CSWAP2",
         0x81: "PUSH_CONDITION"}
cnt = {}
for k, nm in names.items():
    v = int((base == k).sum())
    if v:
        cnt[nm] = v
OUT["opcode_census"] = cnt
OUT["cond_variant_census"] = {
    nm: int(((base == k) & iscond).sum()) for k, nm in names.items()
    if int(((base == k) & iscond).sum())}
say("census", json.dumps(cnt))

cfun3 = np.zeros(N + 1, dtype=np.int32); cfun3[1:] = np.cumsum(ir.L3Q[t])
cfun2 = np.zeros(N + 1, dtype=np.int32); cfun2[1:] = np.cumsum(ir.L2Q[t])
cfuncc = np.zeros(N + 1, dtype=np.int32); cfuncc[1:] = np.cumsum(ir.LCOND[t])

tof = np.flatnonzero(ir.LTOF[t])
ccxp = tof[(t[tof] & 0x7F) == 0x31]
cxp = np.flatnonzero(base == 0x21)
swp = np.flatnonzero(base == 0x22)

pos = np.flatnonzero(t == 0xC1)             # BIT_STORE1_IF, the Chien anchor
condbits = c.bc[cfuncc[pos + 1] - 1].astype(np.int64)
cn = condbits.tolist()
found = []
i = 0
while i + 11 < len(cn):
    c0 = cn[i]
    if (c0 % 12 == 0 and cn[i + 11] == c0 + 11
            and all(cn[i + k] == c0 + k for k in range(12))):
        found.append(int(pos[i]))
        i += 12
    else:
        i += 1
A, B = min(found), max(found)
OUT["region_bounds"] = {"eea_fwd": [EEA_FWD_START, A], "chien": [A, B], "eea_rev": [B + 1, N]}
say("regions", A, B, len(found))


def profile(lo, hi, binw=10_000):
    edges = np.arange(lo, hi + binw, binw)
    out = {"lo": lo, "hi": hi, "bin": binw}
    for nm, arr in (("tof", tof), ("ccx", ccxp), ("cx", cxp), ("swap", swp)):
        out[nm] = np.diff(np.searchsorted(arr, edges)).tolist()
    return out


OUT["profile_fwd"] = profile(EEA_FWD_START, A)
OUT["profile_rev"] = profile(B + 1, N)


def segment(sel, gap, cap=200):
    if len(sel) == 0:
        return [], 0
    cut = np.flatnonzero(np.diff(sel) > gap)
    segs = np.split(sel, cut + 1)
    out = []
    for s in segs[:cap]:
        out.append([int(s[0]), int(s[-1]), int(len(s))])
    return out, len(segs)


def span_detail(lo, hi, tag):
    d = {"lo": lo, "hi": hi, "ops": hi - lo}
    sub = tof[(tof >= lo) & (tof < hi)]
    d["T"] = int(len(sub))
    d["opcode_hist"] = {nm: int((base[lo:hi] == k).sum())
                        for k, nm in names.items() if int((base[lo:hi] == k).sum())}
    d["cond_hist"] = {nm: int(((base[lo:hi] == k) & iscond[lo:hi]).sum())
                      for k, nm in names.items()
                      if int(((base[lo:hi] == k) & iscond[lo:hi]).sum())}
    d["cond_toffoli"] = int(iscond[sub].sum())
    d["seg_20k"], d["nseg_20k"] = segment(sub, 20_000)
    d["seg_2k"], d["nseg_2k"] = segment(sub, 2_000)

    sel = ccxp[(ccxp >= lo) & (ccxp < hi)]
    if len(sel):
        q3 = cfun3[sel + 1] - 1
        a = c.qqq0[q3].astype(np.int64) // 12
        b = c.qqq1[q3].astype(np.int64) // 12
        e = c.qqq2[q3].astype(np.int64) // 12
        d["n_ccx_same_word"] = int(((a == b) & (b == e)).sum())
        d["n_ccx_2words"] = int((np.minimum(np.minimum(a, b), e)
                                 == np.maximum(np.maximum(a, b), e)).sum())
        blocks, nblocks = [], 0
        i = 0
        while i < len(sel):
            j = i
            while (j + 1 < len(sel) and sel[j + 1] - sel[j] <= 80
                   and a[j + 1] == a[i] and b[j + 1] == b[i] and e[j + 1] == e[i]):
                j += 1
            if j - i + 1 >= 8:
                nblocks += 1
                if len(blocks) < 260:
                    blocks.append([int(a[i]), int(b[i]), int(e[i]), int(j - i + 1),
                                   int(sel[i])])
            i = j + 1
        d["n_big_blocks"] = nblocks
        d["big_blocks"] = blocks
        trip = np.stack([a, b, e], 1)
        uq, uc = np.unique(trip, axis=0, return_counts=True)
        order = np.argsort(-uc)[:30]
        d["ccx_top"] = [[int(uq[k][0]), int(uq[k][1]), int(uq[k][2]), int(uc[k])]
                        for k in order]
        d["n_distinct_ccx_triples"] = int(len(uq))
    sel2 = cxp[(cxp >= lo) & (cxp < hi)]
    if len(sel2):
        q2 = cfun2[sel2 + 1] - 1
        p0 = c.qq0[q2].astype(np.int64) // 12
        p1 = c.qq1[q2].astype(np.int64) // 12
        uq, uc = np.unique(np.stack([p0, p1], 1), axis=0, return_counts=True)
        order = np.argsort(-uc)[:40]
        d["cx_top"] = [[int(uq[k][0]), int(uq[k][1]), int(uc[k])] for k in order]
        d["n_distinct_cx_pairs"] = int(len(uq))
    sel3 = swp[(swp >= lo) & (swp < hi)]
    if len(sel3):
        q2 = cfun2[sel3 + 1] - 1
        p0 = c.qq0[q2].astype(np.int64) // 12
        p1 = c.qq1[q2].astype(np.int64) // 12
        uq, uc = np.unique(np.stack([p0, p1], 1), axis=0, return_counts=True)
        order = np.argsort(-uc)[:20]
        d["swap_top"] = [[int(uq[k][0]), int(uq[k][1]), int(uc[k])] for k in order]
    return d


for nm, lo, hi in (("span_fwd", 19_508_954, 21_385_877),
                   ("span_rev", 46_230_185, 52_842_219),
                   ("cluster132", 21_385_877, 21_588_611)):
    OUT[nm] = span_detail(lo, hi, nm)
    say(nm, OUT[nm]["T"], OUT[nm]["opcode_hist"])

with open(WORK / "align.json", "w") as f:
    json.dump(OUT, f, indent=1, default=str)
print(json.dumps({k: v for k, v in OUT.items()
                  if k not in ("profile_fwd", "profile_rev", "span_fwd", "span_rev",
                               "cluster132")}, indent=1, default=str))
for k in ("span_fwd", "span_rev", "cluster132"):
    d = OUT[k]
    print(f"\n== {k} ops [{d['lo']:,}, {d['hi']:,})  T {d['T']:,}  "
          f"big blocks {d.get('n_big_blocks')}  same-word CCX {d.get('n_ccx_same_word')}")
    print("  hist", json.dumps(d["opcode_hist"]))
    print("  cond", json.dumps(d["cond_hist"]), "cond_tof", d["cond_toffoli"])
    print("  seg20k", d["nseg_20k"], d["seg_20k"][:24])
    print("  seg2k ", d["nseg_2k"], d["seg_2k"][:12])
    print("  ccx_top", d.get("ccx_top", [])[:12])
    print("  cx_top ", d.get("cx_top", [])[:16])
    print("  big blocks (a,b,t,size,op) first 60:", d.get("big_blocks", [])[:60])
say("done")
