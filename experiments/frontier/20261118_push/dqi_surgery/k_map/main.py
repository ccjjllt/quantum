"""Interface survey for a surgical EEA replacement on the DQI tape 575b043f.

Static IR only. CPU only. Nothing is simulated, nothing is verified, nothing is written back.

The question this kernel answers is *not* "how expensive is the EEA" (that is known: 321,772 T
in two passes) but "what exact quantum state does the forward EEA hand to the Chien block, and
what does the Chien block hand back to the reverse EEA". A replacement that does not reproduce
that state bit for bit cannot be spliced between them.

Concretely it produces, from the .kmb itself:

  A. the resolved op listing of six 300-400 op windows, one at each side of the three cuts;
  B. the full Chien trace: for every one of the 4,025 positions, the E-register index j, the
     word that is X-complemented for the root test, the words that are SWAPped, the CCZ words --
     which gives the sigma *array rotation* per position and proves it, instead of guessing;
  C. per-cut liveness: which words/qubits are touched before vs after the cut, i.e. exactly the
     interface that must be preserved;
  D. the tail of the forward EEA and the head of the reverse EEA at word granularity, so the
     final sigma write and the first sigma read can be compared;
  E. region opcode censuses (conditioned vs not) which decide whether the EEA is a fixed schedule
     (as claimed) or carries data-dependent control;
  F. every multiplication block of the forward EEA: (wa, wb, wt, n) so the operand map of the
     division chain is visible at word level.

Outputs go to /kaggle/working/out; the 479 MB tape is deleted before the kernel exits.
"""
import importlib.util
import json
import lzma
import math
import pathlib
import sys
import time

import numpy as np

WORK = pathlib.Path("/kaggle/working")
OUT = WORK / "out"
OUT.mkdir(parents=True, exist_ok=True)
T0 = time.time()


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

# ---- known anchors (from dqi_align, measured on this exact sha) -------------------------------
FWD = (17_576_206, 30_335_416)     # forward EEA   [a, b)
CHI = (30_335_416, 35_627_261)     # Chien/Forney  (last anchor sits at 35,627,261 = CHI[1])
REV = (35_627_262, 57_520_821)     # reverse EEA
N_WORD = 70                        # S0..S69
POOL_WORDS = (70, 71, 72, 73)
POOL_Q = (888, 889)

# ---- decompress ------------------------------------------------------------------------------
xz = find("dqi_575b043f.kmb.xz")
RAW = WORK / "dqi.kmb"
say("decompress", xz)
with lzma.open(xz, "rb") as fi, open(RAW, "wb") as fo:
    while True:
        blk = fi.read(1 << 23)
        if not blk:
            break
        fo.write(blk)
say("decompressed", RAW.stat().st_size, "bytes")

c = ir.Circuit.read(str(RAW))
sha = c.sha256()
say("read", c.num_ops, "ops", c.num_qubits, "qubits", c.num_bits, "bits sha", sha[:16])

REPORT = {
    "kmb_sha256": sha,
    "num_ops": c.num_ops,
    "num_qubits": c.num_qubits,
    "num_bits": c.num_bits,
    "regions": {"fwd": FWD, "chien": CHI, "rev": REV},
    "depth": {"fwd_a": c.depth(FWD[0]), "fwd_b": c.depth(FWD[1]), "chi_b": c.depth(CHI[1]),
              "rev_a": c.depth(REV[0]), "rev_b": c.depth(REV[1]), "end": c.depth(c.num_ops)},
}


# ---- naming ----------------------------------------------------------------------------------
def qn(q: int) -> str:
    return f"S{q // 12}[{q % 12}]" if q < 12 * N_WORD else f"Q{q}"


def bn(b: int) -> str:
    return f"E{b // 12}[{b % 12}]" if b < 12 * 4095 else f"B{b}"


# ---- payload slicing -------------------------------------------------------------------------
PACKETS = ("qqq0", "qqq1", "qqq2", "qq0", "qq1", "q0", "b0", "bc", "angles")


def packets(a, b):
    ca, cb = c._before(a), c._before(b)
    return {nm: getattr(c, nm)[ca[nm]:cb[nm]] for nm in PACKETS}


def payload_index(t):
    """For an opcode slice, the payload slot of each op for every packet class."""
    l3 = ir.L3Q[t]
    l2 = ir.L2Q[t]
    l1 = ir.L1Q[t]
    lb = ir.L1B[t]
    lc = ir.LCOND[t]
    return {
        "3": np.cumsum(l3, dtype=np.int64) - 1,
        "2": np.cumsum(l2, dtype=np.int64) - 1,
        "1": np.cumsum(l1, dtype=np.int64) - 1,
        "b": np.cumsum(lb, dtype=np.int64) - 1,
        "c": np.cumsum(lc, dtype=np.int64) - 1,
    }


def window(a, b):
    """Resolved listing of ops [a,b): (idx, name, qubits, target bit, cond bit) with names."""
    rows = c.decode(a, b)
    out = []
    for i, nm, qs, tb, cb in rows:
        qsn = ",".join(qn(q) for q in qs)
        tbn = "" if tb is None else bn(tb)
        cbn = "" if cb is None else bn(cb)
        out.append(f"{i}\t{nm}\t{qsn}\t{tbn}\t{cbn}")
    return out


WINDOWS = {
    "fwd_head": (FWD[0], FWD[0] + 300),
    "fwd_tail": (FWD[1] - 400, FWD[1]),
    "chien_head": (CHI[0], CHI[0] + 300),
    "chien_tail": (CHI[1] - 300, CHI[1] + 140),
    "rev_head": (REV[0], REV[0] + 400),
    "rev_tail": (REV[1] - 400, REV[1]),
}
for nm, (a, b) in WINDOWS.items():
    (OUT / f"win_{nm}.txt").write_text("\n".join(window(a, b)) + "\n")
    say("wrote", f"win_{nm}.txt", b - a, "ops")
REPORT["windows"] = {nm: list(r) for nm, r in WINDOWS.items()}

# ---- E. region opcode census, split by "carries a classical condition" ------------------------
NAMES = [ir.name(x) if ir.VALID[x] else "?" for x in range(256)]
base = lambda t: (t & 0x7F)


def census(a, b):
    t = c.types[a:b]
    bs = base(t)
    cond = ir.LCOND[t]
    out = {}
    for k in np.unique(bs):
        m = bs == k
        out[NAMES[int(k)]] = {"n": int(m.sum()), "with_cond": int((m & cond).sum())}
    # _IF variants, keyed by the base name
    out_if = {}
    for k in np.unique(bs[cond]):
        m = (bs == k) & cond
        out_if[NAMES[int(k)]] = int(m.sum())
    return {"base": out, "if_variant": out_if}


for nm, (a, b) in (("fwd", FWD), ("chien", CHI), ("rev", REV)):
    REPORT[f"census_{nm}"] = census(a, b)
    say("census", nm, "done")

# ---- B. Chien trace -------------------------------------------------------------------------
a, b = CHI
t = c.types[a:b]
p = packets(a, b)
pi = payload_index(t)
bs = base(t)
isx = bs == 0x11
isw = bs == 0x22
isc = bs == 0x30
isccx = bs == 0x31
isbs1 = (bs == 0x41) & ir.LCOND[t]

# per-op first operand for 1-qubit ops (X, HMR, BIT_*) and 2-qubit ops
q1 = np.full(b - a, -1, dtype=np.int64)
q1[ir.L1Q[t]] = p["q0"][pi["1"][ir.L1Q[t]]]
qq = np.full((b - a, 2), -1, dtype=np.int64)
l2m = ir.L2Q[t]
qq[l2m, 0] = p["qq0"][pi["2"][l2m]]
qq[l2m, 1] = p["qq1"][pi["2"][l2m]]
qq3 = np.full((b - a, 3), -1, dtype=np.int64)
l3m = ir.L3Q[t]
qq3[l3m, 0] = p["qqq0"][pi["3"][l3m]]
qq3[l3m, 1] = p["qqq1"][pi["3"][l3m]]
qq3[l3m, 2] = p["qqq2"][pi["3"][l3m]]
tbit = np.full(b - a, -1, dtype=np.int64)
tbit[ir.L1B[t]] = p["b0"][pi["b"][ir.L1B[t]]]
cbit = np.full(b - a, -1, dtype=np.int64)
cbit[ir.LCOND[t]] = p["bc"][pi["c"][ir.LCOND[t]]]

# anchors: start of a run of >=12 consecutive BIT_STORE1_IF on one E register
anchor_idx = []
prev = -10
for i in np.flatnonzero(isbs1):
    if i != prev + 1:
        anchor_idx.append(i)
    prev = i
anchor_idx = np.array(anchor_idx, dtype=np.int64)
say("anchors", len(anchor_idx))
anch_end = np.append(anchor_idx[1:], b - a)

# X-runs of exactly 12 on one word (the root-test complement)
xidx = np.flatnonzero(isx)
xruns = []
k = 0
while k < len(xidx):
    j = k
    while j + 1 < len(xidx) and xidx[j + 1] == xidx[j] + 1:
        j += 1
    if j - k + 1 >= 12:
        xruns.append((xidx[k], j - k + 1))
    k = j + 1

trace = []
for n, (s, e) in enumerate(zip(anchor_idx, anch_end)):
    seg = slice(s, e)
    # j from the anchor's 12 conditions (same E register, bits 0..11)
    cb = cbit[seg][isbs1[seg]]
    jreg = int(cb.min()) // 12 if len(cb) else -1
    jbits = sorted(int(x) % 12 for x in cb)
    # the 12-X run of this block
    xs = [r for r in xruns if s <= r[0] < e]
    row = {"n": n, "op": int(a + s), "j": jreg, "jbits": jbits,
           "n_ops": int(e - s),
           "ccx": int(isccx[seg].sum()), "ccz": int(isc[seg].sum()),
           "n_x": int(isx[seg].sum()), "n_swap": int(isw[seg].sum()),
           "n_bit_invert_if": int(((bs == 0x42) & ir.LCOND[t])[seg].sum()),
           "n_push": int((t[seg] == 0x81).sum()), "n_pop": int((t[seg] == 0x01).sum())}
    if xs:
        s0, ln = xs[0]
        w = int(q1[s0]) // 12
        row["x_word"] = w
        row["x_words_all"] = sorted({int(q1[i]) // 12 for i in range(s0, s0 + ln)})
        row["x_run_len"] = int(ln)
    if row["ccz"]:
        cs = np.flatnonzero(isc[seg])
        row["ccz_words"] = [[int(x) // 12 for x in qq3[s + cs[0]]]]
    sw = np.flatnonzero(isw[seg])
    if len(sw):
        row["swap_words_head"] = sorted({int(v) // 12 for i in sw[:24] for v in qq[s + i]})
        row["swap_q_head"] = [[int(x) for x in qq[s + i]] for i in sw[:6]]
    trace.append(row)

(OUT / "chien_trace.json").write_text(json.dumps(trace))
say("chien trace rows", len(trace))

xs = [r["x_word"] for r in trace if "x_word" in r]
jjs = [r["j"] for r in trace]
REPORT["chien_trace"] = {
    "n_rows": len(trace),
    "x_word_first20": xs[:20],
    "x_word_last20": xs[-20:],
    "x_word_distinct": sorted(set(xs)),
    "x_word_hist": {int(k): int(v) for k, v in zip(*np.unique(np.array(xs), return_counts=True))},
    "j_first20": jjs[:20],
    "j_last20": jjs[-20:],
    "j_min": min(jjs), "j_max": max(jjs), "j_distinct": len(set(jjs)),
}
# rotation: step of x_word between consecutive positions, mod 70
if len(xs) > 1:
    d = np.diff(np.array(xs)) % N_WORD
    dj = np.diff(np.array(jjs))
    REPORT["chien_trace"]["dword_mod70_hist"] = {int(k): int(v) for k, v in
                                                 zip(*np.unique(d, return_counts=True))}
    REPORT["chien_trace"]["dj_hist_top"] = {int(k): int(v) for k, v in
                                            zip(*np.unique(dj, return_counts=True))}
    # is x_word a function of j alone?
    m = {}
    for r in trace:
        if "x_word" in r:
            m.setdefault(r["j"], set()).add(r["x_word"])
    REPORT["chien_trace"]["j_to_xword_multi"] = {int(k): sorted(v) for k, v in m.items()
                                                 if len(v) > 1}
    REPORT["chien_trace"]["n_j_with_multi_xword"] = sum(1 for v in m.values() if len(v) > 1)
    # linear fits: x_word = (c0 + c1*n) mod 70  (n = position index) and x_word = f(j)
    def best_fit(vals, args, mod):
        v = np.array(vals, dtype=np.int64) % mod
        ar = np.array(args, dtype=np.int64)
        best = None
        for c1 in range(mod):
            r = (v - c1 * ar) % mod
            k, cnt = np.unique(r, return_counts=True)
            if best is None or cnt.max() > best[2]:
                best = (int(c1), int(k[cnt.argmax()]), int(cnt.max()))
        return {"slope": best[0], "intercept": best[1], "hits": best[2], "of": int(len(v))}
    rowsx = [r for r in trace if "x_word" in r]
    REPORT["chien_trace"]["fit_word_vs_index"] = best_fit(
        [r["x_word"] for r in rowsx], list(range(len(rowsx))), N_WORD)
    REPORT["chien_trace"]["fit_word_vs_j"] = best_fit(
        [r["x_word"] for r in rowsx], [r["j"] for r in rowsx], N_WORD)

# ---- C. per-cut liveness --------------------------------------------------------------------
def cut_liveness(cut, half=3000):
    lo, hi = max(0, cut - half), min(c.num_ops, cut + half)
    rows = c.decode(lo, hi)
    first, last = {}, {}
    for i, nm, qs, tb, cb in rows:
        for q in qs:
            if q not in first:
                first[q] = i
            last[q] = i
        for x in (tb, cb):
            if x is not None:
                q = ("b", x)
                if q not in first:
                    first[q] = i
                last[q] = i
    before = {q for q in first if last[q] < cut}
    after = {q for q in first if first[q] >= cut}
    both = {q for q in first if last[q] >= cut > first[q]}
    f = lambda s: sorted(f"{qn(q)}" if isinstance(q, int) else f"{bn(q[1])}" for q in s)
    return {
        "cut": cut, "window": [lo, hi],
        "n_touched": len(first),
        "qubits_before_only": f(before)[:80], "n_before_only": len(before),
        "qubits_after_only": f(after)[:80], "n_after_only": len(after),
        "qubits_live_across": f(both)[:120], "n_live_across": len(both),
        "depth": c.depth(cut),
    }


for nm, cut in (("fwd_start", FWD[0]), ("fwd_end_chien_start", FWD[1]),
                ("chien_end_rev_start", REV[0]), ("tape_end", REV[1])):
    REPORT[f"cut_{nm}"] = cut_liveness(cut)
    say("cut", nm, REPORT[f"cut_{nm}"]["n_live_across"], "live across")

# ---- D/F. word granularity of the two EEA regions --------------------------------------------
def word_hist(a, b, label):
    t = c.types[a:b]
    p = packets(a, b)
    pi = payload_index(t)
    bs = base(t)
    out = {}
    for nm, code in (("CCX", 0x31), ("CCZ", 0x30), ("CX", 0x21), ("SWAP", 0x22)):
        m = bs == code
        if not m.any():
            continue
        l = ir.L3Q[t] if code in (0x31, 0x30) else ir.L2Q[t]
        pa = p["qqq0"] if code in (0x31, 0x30) else p["qq0"]
        pb_ = p["qqq1"] if code in (0x31, 0x30) else p["qq1"]
        pc = p["qqq2"] if code in (0x31, 0x30) else None
        idx = pi["3" if code in (0x31, 0x30) else "2"]
        q0 = pa[idx[m]]
        q1_ = pb_[idx[m]]
        n = m.sum()
        h = {"target": {int(k): int(v) for k, v in
                        zip(*np.unique(q0 // 12, return_counts=True))}}
        if pc is not None:
            h["z"] = {int(k): int(v) for k, v in zip(*np.unique(pc[idx[m]] // 12, return_counts=True))}
        h["n"] = int(n)
        out[nm] = h
    # 2-qubit control-pair histogram (cheap, word level)
    m = bs == 0x21
    if m.any():
        idx = pi["2"]
        w0 = (p["qq0"][idx[m]] // 12)
        w1 = (p["qq1"][idx[m]] // 12)
        key = w0 * 100 + w1
        k, v = np.unique(key, return_counts=True)
        order = np.argsort(-v)[:20]
        out["CX"]["pair_top"] = [[int(k[i] // 100), int(k[i] % 100), int(v[i])] for i in order]
    return out


REPORT["words_fwd"] = word_hist(*FWD, "fwd")
say("word hist fwd")
REPORT["words_rev"] = word_hist(*REV, "rev")
say("word hist rev")

# ---- EEA tail/head: who writes the last words of the forward pass, who reads first in rev ----
def touch_profile(a, b, bins=20):
    """Per-bin (equal op slices) count of ops touching each word, split qubit/bit."""
    step = max(1, (b - a) // bins)
    rows = []
    for k in range(bins):
        lo, hi = a + k * step, min(b, a + (k + 1) * step)
        if lo >= hi:
            break
        ops = c.decode(lo, hi)
        wq, wb = {}, {}
        for i, nm, qs, tb, cb in ops:
            for q in qs:
                wq[q // 12] = wq.get(q // 12, 0) + 1
            for x in (tb, cb):
                if x is not None:
                    wb[x // 12] = wb.get(x // 12, 0) + 1
        rows.append({"lo": lo, "hi": hi,
                     "q_words": {int(k): int(v) for k, v in sorted(wq.items())},
                     "b_words": {int(k): int(v) for k, v in sorted(wb.items())}})
    return rows


REPORT["profile_fwd_tail"] = touch_profile(FWD[1] - 40_000, FWD[1], 8)
REPORT["profile_rev_head"] = touch_profile(REV[0], REV[0] + 40_000, 8)
say("profiles done")

# ---- multiplication blocks of the forward EEA: (wa, wb, wt, n) --------------------------------
def blocks(a, b):
    t = c.types[a:b]
    p = packets(a, b)
    pi = payload_index(t)
    m = base(t) == 0x31
    idx = pi["3"][m]
    q0 = p["qqq0"][idx] // 12
    q1_ = p["qqq1"][idx] // 12
    q2 = p["qqq2"][idx] // 12
    pos = np.flatnonzero(m)
    out = []
    i = 0
    n = len(pos)
    while i < n:
        j = i
        while j + 1 < n and pos[j + 1] == pos[j] + 1 and \
                (q0[j + 1], q1_[j + 1]) == (q0[i], q1_[i]):
            j += 1
        out.append((int(a + pos[i]), int(a + pos[j]), int(q0[i]), int(q1_[i]), int(q2[i]),
                    j - i + 1))
        i = j + 1
    return out


BL = blocks(*FWD)
REPORT["fwd_blocks"] = {
    "n_runs": len(BL),
    "head": [{"op_lo": x[0], "op_hi": x[1], "wa": x[2], "wb": x[3], "wt": x[4], "n": x[5]}
             for x in BL[:40]],
    "tail": [{"op_lo": x[0], "op_hi": x[1], "wa": x[2], "wb": x[3], "wt": x[4], "n": x[5]}
             for x in BL[-60:]],
    "n_with_n42": sum(1 for x in BL if x[5] == 42),
    "sum_n": sum(x[5] for x in BL),
    "pair_hist": {f"{x[2]},{x[3]},{x[4]}": 0 for x in BL[:0]},
}
pc = {}
for x in BL:
    pc[f"{x[2]},{x[3]},{x[4]}"] = pc.get(f"{x[2]},{x[3]},{x[4]}", 0) + 1
REPORT["fwd_blocks"]["pair_hist_top"] = sorted(pc.items(), key=lambda kv: -kv[1])[:30]
say("fwd blocks", len(BL), "runs, sum n =", REPORT["fwd_blocks"]["sum_n"])

BLR = blocks(*REV)
REPORT["rev_blocks"] = {
    "n_runs": len(BLR),
    "head": [{"op_lo": x[0], "op_hi": x[1], "wa": x[2], "wb": x[3], "wt": x[4], "n": x[5]}
             for x in BLR[:40]],
    "tail": [{"op_lo": x[0], "op_hi": x[1], "wa": x[2], "wb": x[3], "wt": x[4], "n": x[5]}
             for x in BLR[-40:]],
    "sum_n": sum(x[5] for x in BLR),
}
say("rev blocks", len(BLR), "runs, sum n =", REPORT["rev_blocks"]["sum_n"])

# ---- bit-id sanity: are the E registers really 12*idx+k? -------------------------------------
probe = []
for r in trace[:3]:
    probe.append({"anchor": r["op"], "j": r["j"], "jbits": r["jbits"]})
REPORT["bit_probe"] = probe

(OUT / "survey.json").write_text(json.dumps(REPORT, indent=1)[:100_000_000])
say("wrote survey.json", (OUT / "survey.json").stat().st_size, "bytes")

# ---- delete the tape before exit (never leave 479 MB in /kaggle/working) ---------------------
RAW.unlink()
say("deleted", RAW, "exists:", RAW.exists())
say("done")
