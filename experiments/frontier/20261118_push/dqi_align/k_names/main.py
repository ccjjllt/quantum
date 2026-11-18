"""DQI align line v2: what are the two big Toffoli clusters of tape 575b043f?

CPU-only Kaggle kernel.  **Static IR read only.  No simulation, no verifier, no
candidate, no submission.**

Delivers four small JSONs (nothing else is left in /kaggle/working; the 479 MB
decompressed tape is deleted before exit so `kernels_output` does not time out):

  windows.json    six 20,000-op symbolic windows
                  [opcode_name, is_cond, q0, q1, q2]   (physical qubit numbers)
                    W1 [19,508,954, 19,528,954)  forward cluster start
                    W2 [20,400,000, 20,420,000)  forward cluster middle
                    W3 [46,230,185, 46,250,185)  reverse cluster start
                    W4 [46,300,000, 46,320,000)  reverse cluster middle
                    W5 [21,900,000, 21,920,000)  the decaying segment
                    W6 [17,576,206, 17,596,206)  forward region start
  units.json      repeated-unit detection: for every CCX anchor, a normalised
                  +-120-op signature (opcode sequence + operand offsets relative
                  to the anchor's target qubit), clustered; top 20 per cluster span
  word_hist.json  CCX target-word / control-word-pair histograms and per-word
                  single-qubit-control counts for both spans
  decay_fit.json  200-segment T / CX / CCX / SWAP / HMR profile and linear fit for
                  [21.6M, 26.3M), span_fwd and span_rev

Decision rule (stated by the coordinator): if the dominant unit is "1 CCX + 2 CX
with the three operands in the same or adjacent word and a single-qubit control"
it is a Fredkin/CSWAP gadget and the cluster is a shift; if the dominant unit is a
42-CCX multiply block, the cluster is EEA arithmetic and the alignment line closes.
"""
import hashlib
import importlib.util
import json
import lzma
import pathlib
import sys
import time

import numpy as np
from hashlib import blake2b

WORK = pathlib.Path("/kaggle/working")
T0 = time.time()


def say(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


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
raw = WORK / "dqi_575b043f.kmb"
if not raw.exists():
    say("decompress", XZ)
    with lzma.open(XZ, "rb") as fi, open(raw, "wb") as fo:
        while True:
            b = fi.read(1 << 23)
            if not b:
                break
            fo.write(b)

spec = importlib.util.spec_from_file_location("vqcc_ir", str(IRPY))
ir = importlib.util.module_from_spec(spec)
sys.modules["vqcc_ir"] = ir
spec.loader.exec_module(ir)

c = ir.Circuit.read(str(raw))
t = c.types
N = c.num_ops
say("ops", N, "Q", c.num_qubits, "T", int(c.toffoli_like()))

base = (t & 0x7F)
iscond = (t & 0x80).astype(bool)

NAMES2 = [(0x00, "NEG"), (0x01, "POP"), (0x10, "Z"), (0x11, "X"), (0x12, "R"),
          (0x13, "ZPOW"), (0x50, "HMR"), (0x20, "CZ"), (0x21, "CX"),
          (0x22, "SWAP"), (0x30, "CCZ"), (0x31, "CCX"), (0x32, "CSWAP"),
          (0x40, "BS0"), (0x41, "BS1"), (0x42, "BINV"), (0x06, "TAG"),
          (0x07, "DBG")]
KOTHER, KPUSH = len(NAMES2), len(NAMES2) + 1
names_out = [n for _, n in NAMES2] + ["OTHER", "PUSH"]
nid = np.full(N, KOTHER, np.int16)
for k, (v, _) in enumerate(NAMES2):
    nid[base == v] = k
nid[t == 0x81] = KPUSH

L1, L2, L3 = ir.L1Q[t], ir.L2Q[t], ir.L3Q[t]
cf1 = np.zeros(N + 1, np.int32); cf1[1:] = np.cumsum(L1)
cf2 = np.zeros(N + 1, np.int32); cf2[1:] = np.cumsum(L2)
cf3 = np.zeros(N + 1, np.int32); cf3[1:] = np.cumsum(L3)
q0 = np.full(N, -1, np.int16)
q1 = np.full(N, -1, np.int16)
q2 = np.full(N, -1, np.int16)
try:
    i1 = np.flatnonzero(L1)
    q0[i1] = c.q0[cf1[i1 + 1] - 1]
except Exception as _ex:            # packet absent from this tape
    say("L1 payload unavailable:", repr(_ex))
    i1 = np.zeros(0, dtype=np.int64)
i2 = np.flatnonzero(L2); k2 = cf2[i2 + 1] - 1
q0[i2] = c.qq0[k2]; q1[i2] = c.qq1[k2]
i3 = np.flatnonzero(L3); k3 = cf3[i3 + 1] - 1
q0[i3] = c.qqq0[k3]; q1[i3] = c.qqq1[k3]; q2[i3] = c.qqq2[k3]
del i1, i2, i3, k2, k3, cf1
say("operand arrays ready")

# ------------------------------------------------------------- windows.json
WINDOWS = {
    "W1_fwd_start": [19_508_954, 19_528_954],
    "W2_fwd_mid": [20_400_000, 20_420_000],
    "W3_rev_start": [46_230_185, 46_250_185],
    "W4_rev_mid": [46_300_000, 46_320_000],
    "W5_decay": [21_900_000, 21_920_000],
    "W6_fwd_region_start": [17_576_206, 17_596_206],
}
win_out = {"opcode_names": names_out, "windows": {}}
for tag, (lo, hi) in WINDOWS.items():
    rows = [[names_out[int(nid[p])], bool(iscond[p]), int(q0[p]), int(q1[p]),
             int(q2[p])] for p in range(lo, hi)]
    win_out["windows"][tag] = {"lo": lo, "hi": hi, "ops": rows}
with open(WORK / "windows.json", "w") as f:
    json.dump(win_out, f, separators=(",", ":"))
say("windows.json written",
    sum(len(v["ops"]) for v in win_out["windows"].values()), "ops")

# --------------------------------------------------------------- units.json
ccxp = np.flatnonzero((t & 0x7F) == 0x31)
cxp = np.flatnonzero((t & 0x7F) == 0x21)
swp = np.flatnonzero((t & 0x7F) == 0x22)


def units(lo, hi, half=120, topk=20, cap_anchor=40000):
    sel = ccxp[(ccxp >= lo + half) & (ccxp < hi - half)]
    if len(sel) > cap_anchor:
        sel = sel[:: max(1, len(sel) // cap_anchor)]
    sig = {}
    for p in sel:
        s = slice(int(p) - half, int(p) + half + 1)
        code = nid[s].astype(np.int16) * 2 + iscond[s]
        tgt = int(q2[p])
        o0 = np.where(q0[s] >= 0, q0[s] - tgt, -1).astype(np.int16)
        o1 = np.where(q1[s] >= 0, q1[s] - tgt, -1).astype(np.int16)
        o2 = np.where(q2[s] >= 0, q2[s] - tgt, -1).astype(np.int16)
        buf = np.stack([code, o0, o1, o2], 1).tobytes()
        h = blake2b(buf, digest_size=8).digest()
        e = sig.get(h)
        if e is None:
            sig[h] = [1, int(p)]
        else:
            e[0] += 1
    tot = sum(v[0] for v in sig.values())
    top = sorted(sig.items(), key=lambda kv: -kv[1][0])[:topk]
    out = {"anchors": int(len(sel)), "distinct_signatures": len(sig),
           "coverage_of_top20": None, "top": []}
    cov = 0
    for h, (cnt, ex) in top:
        cov += cnt
        s = slice(ex - half, ex + half + 1)
        seg = nid[s]
        comp = {"CCX": int((seg == 11).sum()), "CX": int((seg == 8).sum()),
                "SWAP": int((seg == 9).sum()), "HMR": int((seg == 6).sum()),
                "CCZ": int((seg == 10).sum()), "CZ": int((seg == 7).sum()),
                "R": int((seg == 4).sum()), "PUSH": int((seg == KPUSH).sum()),
                "BS": int(((seg == 13) | (seg == 14)).sum()),
                "BINV": int((seg == 15).sum())}
        out["top"].append({"sig": h.hex(), "count": int(cnt),
                           "frac": round(cnt / tot, 4), "example_op": ex,
                           "example_window_counts": comp,
                           "example_window": [
                               [names_out[int(nid[x])], bool(iscond[x]),
                                int(q0[x] - int(q2[ex])), int(q1[x] - int(q2[ex])),
                                int(q2[x] - int(q2[ex]))]
                               for x in range(ex - half, ex + half + 1)]})
    out["coverage_of_top20"] = round(cov / tot, 4) if tot else None
    return out


UNITS = {}
for tag, lo, hi in (("span_fwd", 19_508_954, 21_385_877),
                    ("span_rev", 46_230_185, 52_842_219)):
    UNITS[tag] = units(lo, hi)
    say(tag, "distinct sigs", UNITS[tag]["distinct_signatures"],
        "top frac", UNITS[tag]["top"][0]["frac"] if UNITS[tag]["top"] else None)
with open(WORK / "units.json", "w") as f:
    json.dump(UNITS, f, separators=(",", ":"))
say("units.json written")

# ------------------------------------------------------------ word_hist.json
def word_hist(lo, hi):
    m = (ccxp >= lo) & (ccxp < hi)
    out = {"lo": lo, "hi": hi, "n_ccx": int(m.sum())}
    if not m.sum():
        return out
    sel = ccxp[m]
    qq3 = cf3[sel + 1] - 1
    a = c.qqq0[qq3].astype(np.int64)
    b = c.qqq1[qq3].astype(np.int64)
    e = c.qqq2[qq3].astype(np.int64)
    tw = np.bincount(e // 12)
    out["target_word_hist"] = {int(k): int(v) for k, v in enumerate(tw) if v}
    pw = np.bincount((a // 12) * 100 + (b // 12))
    idx = np.argsort(-pw)[:30]
    out["control_word_pair_top"] = [[int(k // 100), int(k % 100), int(pw[k])]
                                    for k in idx if pw[k]]
    out["n_distinct_control_word_pairs"] = int((pw > 0).sum())
    # single-qubit control: the two controls sit in different words
    cross = (a // 12) != (b // 12)
    out["n_ccx_cross_word_controls"] = int(cross.sum())
    if cross.sum():
        w0 = (a // 12)[cross]
        w1 = (b // 12)[cross]
        cnt = np.bincount(w0, minlength=75) + np.bincount(w1, minlength=75)
        idx = np.argsort(-cnt)[:20]
        out["cross_word_ctrl_word_counts"] = [[int(k), int(cnt[k])] for k in idx
                                              if cnt[k]]
        out["n_cross_word_ctrl_words"] = int((cnt > 0).sum())
    same = ((a // 12) == (b // 12))
    out["n_ccx_same_word_controls"] = int(same.sum())
    return out


WORD = {"span_fwd": word_hist(19_508_954, 21_385_877),
        "span_rev": word_hist(46_230_185, 52_842_219),
        "cluster132": word_hist(21_385_877, 21_588_611)}
with open(WORK / "word_hist.json", "w") as f:
    json.dump(WORD, f, separators=(",", ":"))
say("word_hist.json written")

# ------------------------------------------------------------ decay_fit.json
def seg_profile(lo, hi, nseg=200):
    edges = np.linspace(lo, hi, nseg + 1).astype(np.int64)
    rows = []
    for i in range(nseg):
        a, b = int(edges[i]), int(edges[i + 1])
        rows.append({
            "lo": a, "hi": b,
            "T": int((((t[a:b] & 0x7F) == 0x30).sum()
                      + ((t[a:b] & 0x7F) == 0x31).sum()
                      + ((t[a:b] & 0x7F) == 0x32).sum())),
            "cx": int(((t[a:b] & 0x7F) == 0x21).sum()),
            "ccx": int(((t[a:b] & 0x7F) == 0x31).sum()),
            "swap": int(((t[a:b] & 0x7F) == 0x22).sum()),
            "hmr": int(((t[a:b] & 0x7F) == 0x50).sum()),
        })
    y = np.array([r["T"] for r in rows], dtype=float)
    x = np.arange(nseg, dtype=float)
    A2 = np.stack([np.ones_like(x), x], 1)
    (a0, b0), *_ = np.linalg.lstsq(A2, y, rcond=None)
    resid = y - (a0 + b0 * x)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return {"lo": lo, "hi": hi, "nseg": nseg, "segment_ops": int((hi - lo) / nseg),
            "T": int(y.sum()), "T_head": float(y[:5].mean()), "T_tail": float(y[-5:].mean()),
            "all_T": [int(v) for v in y],
            "fit_intercept": float(a0), "fit_slope_per_segment": float(b0),
            "fit_r2": float(1 - float((resid ** 2).sum()) / ss_tot) if ss_tot else None,
            "rows": rows}


DECAY = {
    "decay_21p6_26p3": seg_profile(21_600_000, 26_300_000),
    "span_fwd": seg_profile(19_508_954, 21_385_877),
    "span_rev": seg_profile(46_230_185, 52_842_219),
}
with open(WORK / "decay_fit.json", "w") as f:
    json.dump(DECAY, f, separators=(",", ":"))
say("decay_fit.json written")

for k, v in DECAY.items():
    print(f"  {k}: T {v['T']:,} head {v['T_head']:.0f} tail {v['T_tail']:.0f} "
          f"slope {v['fit_slope_per_segment']:.2f} r2 {v['fit_r2']}")
for k, v in UNITS.items():
    print(f"  {k}: anchors {v['anchors']} distinct {v['distinct_signatures']} "
          f"top {v['top'][0]['frac']:.3f} counts {v['top'][0]['example_window_counts']}")
for k, v in WORD.items():
    print(f"  {k}: n_ccx {v.get('n_ccx')} cross {v.get('n_ccx_cross_word_controls')} "
          f"same {v.get('n_ccx_same_word_controls')} "
          f"target_hist {json.dumps(v.get('target_word_hist', {}))[:200]}")

raw.unlink()
say("tape removed, done")
