"""DQI tape 575b043f: exact attribution of the residual Toffoli budget, plus a search for
removable redundancy that previous lines did not test.

Remit (facts handed in, not re-derived):
  * static T = 367,989 (362,012 CCX + 5,977 CCZ); official mean executed T = 367,116.057.
  * NOT this line's: [19,508,954, 21,385,877) 29,543 T and [46,230,185, 52,842,219)
    65,774 T (dqi_align).  Everything else (~272,672 static T) is this line's, including
    the 3,068 42-CCX Toom-4 multiply blocks and the 44,264 T Chien/Forney region.
  * closed elsewhere, not re-derived: plain CCX cancels (0), void/zero/held CCX (0),
    retention pairs (4,184 found / 3 servable), truncation (FAIL 102400/102400),
    Q < 890 (product pool).

What this kernel adds (static IR reads + one classical-trajectory sample; no quantum
simulation, no verifier, no candidate):
  A region / opcode census, cross-checked against the dqi_algo split.
  B word-triple run census (gap 80), cross-checked against the dqi_algo block table.
  C idiom census of all 362,012 CCX: a feature key per CCX (word-run size, CX sandwich
    in/out, R-init, HMR-uncompute, CZ correction, target-as-next-control, word roles,
    condition depth), histogrammed over +-24-op windows, with a decoded example window
    for every reported class.  (A literal +-40-op opcode-string signature was not used
    as the primary key: every multiply block differs in its carrier pattern, so a raw
    string fragments into ~10k singleton classes and the result is not nameable.  The
    feature key is what makes the partition nameable; the raw window is dumped for the
    top classes so each name can be checked against real instructions.)
  D AND/uncompute net accounting per region, plus the plain-cancel confirmation.
  E four untested removable classes:
      E1 degenerate operands (CCX a==b / a==t / b==t, CCZ repeated operand)
      E2 dead target: CCX whose target is unconditionally reset before any read
      E3 duplicated token segments on the same qubit set (>= 200 tokens)
      E4 duplicated multiply blocks (same ordered (a,b,t) triple list)
  F per-round cluster table: where the residual T sits, by T-composition.
  G per-idiom mean executed T (per-gate firing counts on 32,768 classical shots).
  H word-level activity for all 75 words.

Output residual.json (small); the decompressed tape is deleted before the kernel ends.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import lzma
import os
import pathlib
import shutil
import sys
import time
import traceback

import numpy as np

T0 = time.time()
OUT: dict = {}
WORK = pathlib.Path(os.environ.get("DQI_OUT") or "/kaggle/working")
WORK.mkdir(parents=True, exist_ok=True)
TMP = pathlib.Path("/tmp/dqi_residual")
TMP.mkdir(parents=True, exist_ok=True)


def say(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


def save(tag):
    OUT["_stage"] = tag
    with open(WORK / "residual.json", "w") as f:
        json.dump(OUT, f, indent=1, default=str)
    say("saved", tag, (WORK / "residual.json").stat().st_size, "bytes")


def stage(name):
    def deco(fn):
        try:
            fn()
        except Exception:
            OUT.setdefault("errors", {})[name] = traceback.format_exc()[-3000:]
            say("STAGE FAILED", name)
            print(traceback.format_exc()[-3000:], flush=True)
        save(name)
    return deco


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for ch in iter(lambda: f.read(1 << 22), b""):
            h.update(ch)
    return h.hexdigest()


# ---------------------------------------------------------------- inputs
TAPE_OVERRIDE = os.environ.get("DQI_TAPE")
IR_OVERRIDE = os.environ.get("DQI_IR")
XZ = IRPY = None
if not (TAPE_OVERRIDE and IR_OVERRIDE):
    for p in pathlib.Path("/kaggle/input").rglob("dqi_575b043f.kmb.xz"):
        XZ = p
        break
    for p in pathlib.Path("/kaggle/input").rglob("vqcc_ir.py"):
        IRPY = p
        break
    if not (XZ and IRPY):
        raise SystemExit("inputs not found")
    say("xz", XZ)

spec = importlib.util.spec_from_file_location("vqcc_ir",
                                              IR_OVERRIDE or str(IRPY))
ir = importlib.util.module_from_spec(spec)
sys.modules["vqcc_ir"] = ir
spec.loader.exec_module(ir)

if TAPE_OVERRIDE:
    RAW = pathlib.Path(TAPE_OVERRIDE)
    OUT["kmb_sha256"] = sha256(RAW)
    OUT["kmb_bytes"] = RAW.stat().st_size
else:
    RAW = TMP / "dqi.kmb"
    if not RAW.exists():
        with lzma.open(XZ, "rb") as fi, open(RAW, "wb") as fo:
            shutil.copyfileobj(fi, fo, 1 << 23)
    OUT["kmb_sha256"] = sha256(RAW)
    OUT["kmb_bytes"] = RAW.stat().st_size
say("tape", OUT["kmb_bytes"], OUT["kmb_sha256"][:16])

c = ir.Circuit.read(str(RAW))
t = c.types
N = c.num_ops
NQ = c.num_qubits
OUT["num_ops"] = N
OUT["num_qubits"] = NQ
OUT["num_bits"] = c.num_bits
OUT["static_toffoli"] = int(c.toffoli_like())
say("ops", N, "Q", NQ, "T", OUT["static_toffoli"])

NP = 1 << 27
assert N < NP
COND = (t & 0x80) != 0

# ---------------------------------------------------------------- per-op arrays
is_push = (t == 0x81)
base = np.where(is_push, 0x81, (t & 0x7F)).astype(np.uint8)
del is_push

i3 = np.flatnonzero(ir.L3Q[t]).astype(np.int32)
i2 = np.flatnonzero(ir.L2Q[t]).astype(np.int32)
i1 = np.flatnonzero(ir.L1Q[t]).astype(np.int32)
c3 = np.zeros(N + 1, dtype=np.int32)
np.cumsum(ir.L3Q[t], dtype=np.int32, out=c3[1:])
p0 = np.full(N, -1, np.int16)
p1 = np.full(N, -1, np.int16)
p2 = np.full(N, -1, np.int16)
p0[i3] = c.qqq0.astype(np.int16)
p1[i3] = c.qqq1.astype(np.int16)
p2[i3] = c.qqq2.astype(np.int16)
p0[i2] = c.qq0.astype(np.int16)
p1[i2] = c.qq1.astype(np.int16)
p0[i1] = c.q0.astype(np.int16)
say("qubit operands built", len(i3), len(i2), len(i1))

iB = np.flatnonzero(ir.L1B[t]).astype(np.int32)
b0 = np.full(N, -1, np.int32)
b0[iB] = c.b0.astype(np.int32)
iC = np.flatnonzero(ir.LCOND[t]).astype(np.int32)
bc = np.full(N, -1, np.int32)
bc[iC] = c.bc.astype(np.int32)
del iB, iC
say("bit operands built")

ev, dep_after = ir._depth_events(t)
ev = ev.astype(np.int32)


def depth_before(ops):
    k = np.searchsorted(ev, ops, side="left")
    return np.where(k > 0, dep_after[np.maximum(k - 1, 0)], 0).astype(np.int16)


POS = {}
for code, nm in ((0x21, "CX"), (0x20, "CZ"), (0x22, "SWAP"), (0x50, "HMR"),
                 (0x12, "R"), (0x11, "X"), (0x10, "Z"), (0x31, "CCX"), (0x30, "CCZ"),
                 (0x81, "PUSH"), (0x01, "POP")):
    POS[nm] = np.flatnonzero(base == code).astype(np.int32)

tof = np.flatnonzero(ir.LTOF[t]).astype(np.int32)
ccx = tof[base[tof] == 0x31]
ccz = tof[base[tof] == 0x30]
say("toffoli", len(tof), "ccx", len(ccx), "ccz", len(ccz))

BOUND = np.array([17_576_206, 30_335_416, 35_627_262, 52_910_631], np.int64)
if N < BOUND[-1]:            # synthetic / smoke tapes: keep the same region fractions
    BOUND = np.round(BOUND / 52_910_631 * N).astype(np.int64)
REGN = np.array(["pre", "fwd", "chien", "rev", "epi"])
ALIGN = [(19_508_954, 21_385_877), (46_230_185, 52_842_219)]


def region_of(ops):
    return REGN[np.searchsorted(BOUND, ops, side="right")]


def in_align(ops):
    m = np.zeros(len(ops), bool)
    for lo, hi in ALIGN:
        m |= (ops >= lo) & (ops < hi)
    return m


q3i = c3[ccx].astype(np.int64)
A = c.qqq0[q3i].astype(np.int32)
Bv = c.qqq1[q3i].astype(np.int32)
Tt = c.qqq2[q3i].astype(np.int32)
del q3i
wA, wB, wT = A // 12, Bv // 12, Tt // 12
REG = region_of(ccx)
MINE = ~in_align(ccx)
say("ccx mine", int(MINE.sum()), "align", int((~MINE).sum()))


# ---------------------------------------------------------------- runs
def runs_of(keys, gap=80):
    n = len(ccx)
    same = np.zeros(n, bool)
    if n > 1:
        same[1:] = (keys[1:] == keys[:-1]).all(axis=1) & (np.diff(ccx) <= gap)
    run = np.concatenate([[0], np.cumsum(~same[1:])]).astype(np.int64)
    size = np.bincount(run)[run]
    return run, size


runW, sizeW = runs_of(np.stack([wA, wB, wT], 1))
runE, sizeE = runs_of(((A.astype(np.int64) * 890 + Bv) * 890 + Tt).reshape(-1, 1))
say("runs word", int(runW.max()) + 1, "exact", int(runE.max()) + 1,
    "exact>=2", int((sizeE >= 2).sum()))


def bucket(sz):
    b = np.zeros(len(sz), np.int8)
    b[sz >= 2] = 1
    b[sz >= 3] = 2
    b[sz >= 4] = 3
    b[sz >= 12] = 4
    b[sz >= 13] = 5
    b[sz >= 24] = 6
    b[sz >= 42] = 7
    b[sz > 42] = 8
    return b


bsz = bucket(sizeW)
BRUN = {"0": "1", "1": "2", "2": "3", "3": "4-11", "4": "12", "5": "13-23",
        "6": "24-41", "7": "42", "8": ">42"}
BSZNAME = np.array([BRUN[str(k)] for k in range(9)])

# ---------------------------------------------------------------- local atoms
OFF = np.arange(-24, 25, dtype=np.int32)
IDX = np.clip(ccx[:, None] + OFF[None, :], 0, N - 1)
bw = base[IDX]
pw0 = p0[IDX]
pw1 = p1[IDX]
del IDX
TT = Tt[:, None]


def any_off(lo, hi, mask):
    return mask[:, lo + 24:hi + 25].any(axis=1)


isCX = bw == 0x21
isHMR = bw == 0x50
isR = bw == 0x12
isCZ = bw == 0x20
isCCX = bw == 0x31
cx_out = any_off(1, 8, isCX & (pw0 == TT))
cx_in = any_off(-8, -1, isCX & (pw1 == TT))
hmr_t = any_off(1, 16, isHMR & (pw0 == TT))
r_t = any_off(-4, -1, isR & (pw0 == TT))
czy = any_off(1, 24, isCZ & ((pw0 == TT) | (pw1 == TT)))
nfan = (isCX & (pw0 == TT))[:, 25:].sum(axis=1).astype(np.int16)   # CX(T->o), next 24
fan_b = np.zeros(len(ccx), np.int8)
fan_b[nfan >= 1] = 1
fan_b[nfan >= 4] = 2
fan_b[nfan >= 8] = 3
fan_b[nfan >= 12] = 4
nA = np.concatenate([A[1:], [-1]]).astype(np.int32)
nB = np.concatenate([Bv[1:], [-1]]).astype(np.int32)
chain_t = (nA == Tt) | (nB == Tt)
del bw, pw0, pw1, isCX, isHMR, isR, isCZ, isCCX
say("atoms built")

SAND = cx_out.astype(np.int64) + 2 * cx_in.astype(np.int64)
ROLES = ((wA < 70).astype(np.int64) + 2 * (wB < 70).astype(np.int64)
         + 4 * (wT < 70).astype(np.int64))
DEPTH = (depth_before(ccx) > 0).astype(np.int64)
KEY = (((((((bsz.astype(np.int64) * 4 + SAND) * 2 + r_t.astype(np.int64)) * 2
           + hmr_t.astype(np.int64)) * 2 + czy.astype(np.int64)) * 2
         + chain_t.astype(np.int64)) * 8 + ROLES) * 2 + DEPTH)
NKEY = int(KEY.max()) + 1


def key_fields(k):
    dep = k % 2
    k //= 2
    roles = k % 8
    k //= 8
    chain = k % 2
    k //= 2
    czyb = k % 2
    k //= 2
    hmrb = k % 2
    k //= 2
    rtb = k % 2
    k //= 2
    sand = k % 4
    return {"wrun": BRUN[str(k // 4)], "sand": int(sand), "r_init": int(rtb),
            "hmr_out": int(hmrb), "cz_after": int(czyb), "next_ctrl": int(chain),
            "roles": int(roles), "depth_gt0": int(dep)}


NAMES = {0x00: "NEG", 0x01: "POP", 0x10: "Z", 0x11: "X", 0x12: "R", 0x13: "ZP",
         0x20: "CZ", 0x21: "CX", 0x22: "SWAP", 0x30: "CCZ", 0x31: "CCX",
         0x32: "CSWAP", 0x40: "BS0", 0x41: "BS1", 0x42: "BINV", 0x50: "HMR",
         0x81: "PUSH"}


def window_str(i, aa, bb, tt, w=20):
    lab = lambda q: ("A" if q == aa else "B" if q == bb else "T" if q == tt
                     else ("a" + str(q - 12 * (aa // 12)) if q // 12 == aa // 12
                           else "b" + str(q - 12 * (bb // 12)) if q // 12 == bb // 12
                           else "t" + str(q - 12 * (tt // 12)) if q // 12 == tt // 12
                           else "x" + str(q)))
    out = []
    for k in range(max(0, i - w), min(N, i + w + 1)):
        b_ = int(base[k])
        nm = NAMES.get(b_, "?") + ("_IF" if t[k] & 0x80 else "")
        qs = [int(p0[k])] if b_ & 0x10 and not (b_ & 0x30 == 0x30) else []
        if b_ & 0x30 == 0x30:
            qs = [int(p0[k]), int(p1[k]), int(p2[k])]
        elif b_ & 0x30 == 0x20:
            qs = [int(p0[k]), int(p1[k])]
        elif b_ & 0x30 == 0x10:
            qs = [int(p0[k])]
        s = nm + "(" + ",".join(lab(q) for q in qs) + ")" if qs else nm
        if b_ in (0x40, 0x41, 0x42, 0x50):
            s += "->b" + str(int(b0[k]))
        out.append((">>" if k == i else "") + s)
    return " ".join(out)


def stage_A():
    cnt = {}
    for code, nm in ((0x21, "CX"), (0x20, "CZ"), (0x22, "SWAP"), (0x50, "HMR"),
                     (0x12, "R"), (0x11, "X"), (0x10, "Z"), (0x31, "CCX"),
                     (0x30, "CCZ"), (0x81, "PUSH"), (0x01, "POP"), (0x42, "BINV"),
                     (0x40, "BS0"), (0x41, "BS1")):
        cnt[nm] = int((base == code).sum())
    OUT["opcode_census"] = cnt
    r = {}
    for k, nm in enumerate(["pre", "fwd", "chien", "rev", "epi"]):
        lo = 0 if k == 0 else int(BOUND[k - 1])
        hi = N if k == 4 else int(BOUND[k])
        r[nm] = {"ops": hi - lo, "T": int(((tof >= lo) & (tof < hi)).sum()),
                 "ccx": int(((ccx >= lo) & (ccx < hi)).sum()),
                 "ccz": int(((ccz >= lo) & (ccz < hi)).sum())}
    OUT["regions"] = r
    OUT["align_spans"] = [[lo, hi, int(((tof >= lo) & (tof < hi)).sum())]
                          for lo, hi in ALIGN]
    OUT["mine_static_T"] = int(MINE.sum()) + int((~in_align(ccz)).sum())
    say("regions", json.dumps(r))


stage("A_regions")(stage_A)


def stage_B():
    nrun = int(runW.max()) + 1
    run_size = np.bincount(runW, minlength=nrun)          # T (= CCX) inside each run
    per = {}
    for nm in ("fwd", "chien", "rev"):
        sel = REG == nm
        keep = np.zeros(nrun, bool)
        keep[runW[sel]] = True
        sz = run_size[np.flatnonzero(keep)]
        per[nm] = {"blocks": int(keep.sum()),
                   "CCX": int(sz.sum()),
                   "size_hist": {str(int(k)): int(v) for k, v in
                                 zip(*np.unique(sz, return_counts=True))}}
    OUT["word_runs"] = {"n_runs": nrun, "per_region": per,
                        "T_blocks_ge24": int(run_size[run_size >= 24].sum()),
                        "n_blocks_ge24": int((run_size >= 24).sum()),
                        "T_blocks_12": int(run_size[run_size == 12].sum()),
                        "n_blocks_12": int((run_size == 12).sum())}
    OUT["exact_runs"] = {"n_runs": int(runE.max()) + 1,
                         "size_hist_ge2": {str(int(k)): int(v) for k, v in
                                           zip(*np.unique(sizeE[sizeE >= 2],
                                                          return_counts=True))},
                         "n_ccx_in_runs_ge2": int(sizeE[sizeE >= 2].sum())}
    # exact static attribution: region x bucket x (in an align span or not)
    regi = np.searchsorted(BOUND, ccx, side="right")
    al = in_align(ccx)
    tab = {}
    for k in range(5):
        if k >= len(REGN):
            break
        for b in range(9):
            for a in (0, 1):
                s_ = (regi == k) & (bsz == b) & (al == a)
                if s_.sum():
                    tab[f"{REGN[k]}|{BRUN[str(b)]}|{'align' if a else 'mine'}"] = \
                        int(s_.sum())
    OUT["T_exact"] = tab
    ccx_by_bw = {}
    for b in range(9):
        d_ = {}
        for ro in range(8):
            v = int(((bsz == b) & (ROLES == ro)).sum())
            if v:
                d_["".join("S" if (ro >> x) & 1 else "P" for x in (0, 1, 2))] = v
        if d_:
            ccx_by_bw[BRUN[str(b)]] = d_
    OUT["T_by_bucket_wordrel"] = ccx_by_bw
    say("word runs", json.dumps(OUT["word_runs"]["per_region"])[:400])


stage("B_runs")(stage_B)


def stage_C():
    cnt = np.bincount(KEY, minlength=NKEY)
    rows = []
    for k in np.argsort(-cnt)[:70]:
        kk = int(k)
        if cnt[kk] == 0:
            continue
        f = key_fields(kk)
        sel = KEY == kk
        ro = f["roles"]     # bit0 = word(A) is a syndrome word, bit1 = word(B), bit2 = word(T)
        f["word_rel"] = "".join("S" if (ro >> b) & 1 else "P" for b in (0, 1, 2))
        r = {"key": kk, "n": int(cnt[kk]), **f,
             "regions": {nm: int(sel[REG == nm].sum())
                         for nm in ("fwd", "chien", "rev")},
             "example_op": int(ccx[sel][0])}
        rows.append(r)
    for r in rows[:14]:
        e = r["example_op"]
        j = int(np.searchsorted(ccx, e))
        r["example_window"] = window_str(e, int(A[j]), int(Bv[j]), int(Tt[j]))
    OUT["idioms"] = {"n_keys": NKEY, "rows": rows,
                     "covered": int(sum(r["n"] for r in rows)),
                     "total": int(len(ccx)),
                     "uncovered": int(len(ccx) - sum(r["n"] for r in rows))}
    # broadcast check: do single-CCX ANDs share their control pair?
    sing = (bsz == 0)
    if sing.any():
        cp = (A[sing].astype(np.int64) * 890 + Bv[sing])
        uq, uc = np.unique(cp, return_counts=True)
        o = np.argsort(-uc)[:20]
        OUT["single_ccx_control_pairs"] = [
            [int(uq[k] // 890), int(uq[k] % 890), int(uc[k])] for k in o]
        OUT["single_ccx_n"] = int(sing.sum())
    fan = {}
    for b in range(9):
        for f in range(5):
            v = int(((bsz == b) & (fan_b == f)).sum())
            if v:
                fan[f"{BRUN[str(b)]}|fan{[0, 1, 4, 8, 12][f]}"] = v
    OUT["fanout"] = fan
    say("idiom top", [(r["n"], r["wrun"], r["sand"], r["r_init"], r["regions"])
                      for r in rows[:6]])


stage("C_idioms")(stage_C)


def stage_D():
    d = {"R_before_target": int(r_t.sum()), "HMR_after_target": int(hmr_t.sum()),
         "CZ_after_target": int(czy.sum()), "CX_out_of_target": int(cx_out.sum()),
         "CX_into_target": int(cx_in.sum()), "next_ctrl": int(chain_t.sum())}
    for nm in ("fwd", "chien", "rev"):
        s = REG == nm
        d[nm] = {"ccx": int(s.sum()), "R_init": int(r_t[s].sum()),
                 "HMR_uncompute": int(hmr_t[s].sum()), "CZ_correction": int(czy[s].sum()),
                 "net": int(r_t[s].sum() - hmr_t[s].sum())}
    # plain cancels: exact-duplicate runs, no touch of a, b or t in between
    cand = exact = 0
    idx = np.flatnonzero(sizeE >= 2)
    done = set()
    for j in idx[:60000]:
        rj = int(runE[j])
        if rj in done:
            continue
        done.add(rj)
        # run ids are non-decreasing, so a run is a contiguous slice of the CCX order
        lo_r = int(np.searchsorted(runE, rj, "left"))
        hi_r = int(np.searchsorted(runE, rj, "right"))
        for k in range(lo_r, hi_r - 1):
            i0, i1 = int(ccx[k]), int(ccx[k + 1])
            cand += 1
            lo, hi = i0 + 1, i1
            if hi <= lo:
                exact += 1
                continue
            a_, b_, t_ = int(A[k]), int(Bv[k]), int(Tt[k])
            hit = ((p0[lo:hi] == a_) | (p1[lo:hi] == a_) | (p2[lo:hi] == a_)
                   | (p0[lo:hi] == b_) | (p1[lo:hi] == b_) | (p2[lo:hi] == b_)
                   | (p0[lo:hi] == t_) | (p1[lo:hi] == t_) | (p2[lo:hi] == t_))
            if not hit.any():
                exact += 1
    d["dup_gate_candidates"] = int(cand)
    d["dup_gate_plain_cancels"] = int(exact)
    OUT["and_uncompute"] = d
    say("and/uncompute", json.dumps({k: v for k, v in d.items() if not isinstance(v, dict)}))


stage("D_and")(stage_D)


def stage_E1():
    out = {"ccx_n": int(len(ccx))}
    out["ccx_repeated_operand"] = int(((A == Bv) | (A == Tt) | (Bv == Tt)).sum())
    out["ccx_a_eq_b"] = int((A == Bv).sum())
    out["ccx_a_eq_t"] = int((A == Tt).sum())
    out["ccx_b_eq_t"] = int((Bv == Tt).sum())
    q3c = c3[ccz].astype(np.int64)
    cA = c.qqq0[q3c].astype(np.int32)
    cB = c.qqq1[q3c].astype(np.int32)
    cC = c.qqq2[q3c].astype(np.int32)
    del q3c
    out["ccz_n"] = int(len(ccz))
    out["ccz_repeated_operand"] = int(((cA == cB) | (cA == cC) | (cB == cC)).sum())
    uq, uc = np.unique(np.stack([cA // 12, cB // 12, cC // 12], 1), axis=0,
                       return_counts=True)
    order = np.argsort(-uc)[:16]
    out["ccz_word_triples"] = [[int(uq[k][0]), int(uq[k][1]), int(uq[k][2]), int(uc[k])]
                               for k in order]
    out["ccz_regions"] = {nm: int(((ccz >= (0 if k == 0 else BOUND[k - 1]))
                                  & (ccz < (N if k == 4 else BOUND[k]))).sum())
                          for k, nm in enumerate(["pre", "fwd", "chien", "rev", "epi"])
                          if nm in ("fwd", "chien", "rev")}
    OUT["degeneracy"] = out
    del cA, cB, cC


stage("E1_degen")(stage_E1)


def stage_E3():
    th = base.astype(np.uint64)
    th *= np.uint64(0x9E3779B97F4A7C15)
    tmp = np.empty(N, np.int64)
    for arr, mul in ((p0, 2), (p1, 4), (p2, 8), (b0, 16), (bc, 32)):
        np.add(arr, 1, out=tmp)
        tmp *= np.int64(0x2545F4914F6CDD1D + mul)
        th ^= tmp.view(np.uint64)
    del tmp
    say("token hash built")
    res = {}
    for L in (64, 512):
        NB = N // L
        blk = th[:NB * L].reshape(NB, L).sum(axis=1, dtype=np.uint64)
        order = np.argsort(blk, kind="stable")
        sb = blk[order]
        cut = np.flatnonzero(np.diff(sb) != 0) + 1
        starts = np.concatenate([[0], cut])
        ends = np.concatenate([cut, [NB]])
        grp = [(int(starts[k]), int(ends[k])) for k in range(len(starts))
               if ends[k] - starts[k] >= 2]
        tof_in = np.diff(np.searchsorted(tof, np.arange(NB + 1) * L))
        gg = sorted(((int(tof_in[order[a:b]].sum()), a, b) for a, b in grp), reverse=True)
        r = {"n_blocks": int(NB), "n_dup_groups": len(grp), "n_verified": 0,
             "top": []}
        for tsum, a, b in gg[:100]:
            mem = order[a:b].tolist()
            bi = mem[0]
            for other in mem[1:4]:
                i, j = bi * L, other * L
                if not np.array_equal(th[i:i + L], th[j:j + L]):
                    continue
                r["n_verified"] += 1
                l = i
                m = j
                while l > 0 and m > 0 and th[l - 1] == th[m - 1] and (i - l) < 30000:
                    l -= 1
                    m -= 1
                e = i + L
                f = j + L
                while e < N and f < N and th[e] == th[f] and (e - i) < 30000:
                    e += 1
                    f += 1
                r["top"].append({"a": int(l), "b": int(e), "tokens": int(e - l),
                                 "copy2": int(m), "T_each": int(((tof >= l) & (tof < e)).sum()),
                                 "gap_ops": int(m - e)})
                break
            if len(r["top"]) >= 40:
                break
        seen = set()
        ded = []
        for t in sorted(r["top"], key=lambda x: -x["T_each"]):
            kk = (t["a"], t["b"], t["copy2"])
            if kk in seen:
                continue
            seen.add(kk)
            ded.append(t)
        r["top"] = ded[:15]
        res[f"L{L}"] = r
        say("dup L", L, "groups", len(grp), "verified", r["n_verified"])
    OUT["dup_segments"] = res
    del th


stage("E3_dups")(stage_E3)


def stage_E4():
    """Duplicated multiply blocks: hash every 42-CCX and every 24-CCX window over the CCX
    sequence.  Windows are used (rather than only maximal word-runs) because the tape
    really does contain merged runs of 82/99 CCX, and a duplicate pair can be hidden
    inside one such run."""
    rows = []
    for W in (42, 24):
        nb = len(ccx) - W + 1
        if nb <= 0:
            continue
        key = ((A.astype(np.int64) * 890 + Bv) * 890 + Tt)
        # rolling 64-bit hash over each W-window of ordered (a,b,t) triples
        h = np.zeros(nb, np.uint64)
        for k in range(W):
            h += (key[k:k + nb].astype(np.uint64) + np.uint64(1)) \
                * np.uint64(0x2545F4914F6CDD1D + (k * 1315423911) % 1000003)
        order = np.argsort(h, kind="stable")
        sh = h[order]
        cut = np.flatnonzero(np.diff(sh) != 0) + 1
        starts = np.concatenate([[0], cut])
        ends = np.concatenate([cut, [nb]])
        grp = [(int(starts[k]), int(ends[k])) for k in range(len(starts))
               if ends[k] - starts[k] >= 2]
        n_rep = 0
        for a, b in grp:
            mem = order[a:b]
            first = int(mem[0])
            for other in mem[1:4].tolist():
                if abs(other - first) < W:
                    continue
                if not np.array_equal(key[first:first + W], key[other:other + W]):
                    continue
                n_rep += 1
                i0 = int(ccx[first])
                i1 = int(ccx[other])
                # a block's own carrier scaffolding reaches ~600 ops past its last
                # CCX, so the "semantic gap" excludes a 600-op margin on each side
                lo = int(ccx[first + W - 1]) + 1 + 600
                hi = i1 - 600
                touchA = touchB = touchC = -1
                if 0 < hi - lo <= 5_000_000:
                    wa, wb, wt = int(wA[first]), int(wB[first]), int(wT[first])
                    seg = slice(lo, hi)
                    touchA = int(((p0[seg] // 12) == wa).sum()
                                 + ((p1[seg] // 12) == wa).sum()
                                 + ((p2[seg] // 12) == wa).sum())
                    touchB = int(((p0[seg] // 12) == wb).sum()
                                 + ((p1[seg] // 12) == wb).sum()
                                 + ((p2[seg] // 12) == wb).sum())
                    touchC = int(((p0[seg] // 12) == wt).sum()
                                 + ((p1[seg] // 12) == wt).sum()
                                 + ((p2[seg] // 12) == wt).sum())
                rows.append({"W": W, "triple": [int(wA[first]), int(wB[first]),
                                                int(wT[first])],
                             "ops": [i0, i1], "gap_ops": int(i1 - i0),
                             "gap_ops_net": int(hi - lo),
                             "touch_A": touchA, "touch_B": touchB,
                             "touch_C": touchC})
    n_ab = sum(1 for r in rows if r["touch_A"] == 0 and r["touch_B"] == 0)
    n_abc = sum(1 for r in rows if r["touch_A"] == 0 and r["touch_B"] == 0
                and r["touch_C"] == 0)
    best = [r for r in rows if r["touch_A"] == 0 and r["touch_B"] == 0]
    best = best[:40]
    rows.sort(key=lambda r: (-r["W"], r["gap_ops"]))
    OUT["mult_dups"] = {"n_rows": len(rows), "rows": rows[:40],
                        "n_ab_untouched": int(n_ab), "n_abc_untouched": int(n_abc),
                        "disjoint_rows": best,
                        "n_W42_rows": int(sum(1 for r in rows if r["W"] == 42))}
    say("mult window dups", len(rows), "AB", n_ab, "ABC", n_abc)


stage("E4_mult")(stage_E4)


def stage_E2():
    # --- bit liveness: an HMR whose outcome bit is next overwritten by an unconditional
    #     BIT_STORE0/1 is a measurement whose result is discarded -> the HMR is a pure reset
    vb = np.concatenate([np.flatnonzero(b0 >= 0), np.flatnonzero(bc >= 0)]).astype(np.int32)
    bq = np.concatenate([b0[b0 >= 0], bc[bc >= 0]]).astype(np.int32)
    key = bq.astype(np.int64) * NP + vb
    del bq, vb
    key.sort()
    say("bit keys", len(key))
    hq = b0[POS["HMR"]]
    qk = hq.astype(np.int64) * NP + POS["HMR"]
    j = np.searchsorted(key, qk, side="right")
    ok = j < len(key)
    nxt = key[np.minimum(j, len(key) - 1)]
    same = ok & ((nxt // NP) == hq)
    nop = np.where(same, nxt % NP, -1)
    nb = np.where(same, base[np.maximum(nop, 0)], 0)
    ncond = np.where(same, COND[np.maximum(nop, 0)], True)
    pure = same & ((nb == 0x40) | (nb == 0x41)) & (~ncond) & \
        (b0[np.maximum(nop, 0)] == hq)
    hmr_dead = np.zeros(N, bool)
    hmr_dead[POS["HMR"][pure]] = True
    OUT["dead_bits"] = {"n_hmr": int(len(POS["HMR"])), "n_dead": int(pure.sum()),
                        "n_no_next": int((~ok).sum())}
    del key, qk, j, ok, nxt, same, nop, nb, ncond, pure, hq
    say("dead HMR bits", OUT["dead_bits"])

    # --- qubit touches, sorted
    q = np.concatenate([c.qqq0.astype(np.int16), c.qqq1.astype(np.int16),
                        c.qqq2.astype(np.int16), c.qq0.astype(np.int16),
                        c.qq1.astype(np.int16), c.q0.astype(np.int16)])
    o = np.concatenate([i3, i3, i3, i2, i2, i1])
    key = q.astype(np.int64) * NP + o
    del q, o
    key.sort()
    say("qubit keys", len(key))
    qk = Tt.astype(np.int64) * NP + ccx
    j = np.searchsorted(key, qk, side="right")
    ok = j < len(key)
    nxt = key[np.minimum(j, len(key) - 1)]
    same = ok & ((nxt // NP) == Tt)
    nop = np.where(same, nxt % NP, -1).astype(np.int64)
    ncls = np.where(same, base[np.maximum(nop, 0)], 0)
    ncond = np.where(same, COND[np.maximum(nop, 0)], True)
    discA = same & (ncls == 0x12) & (~ncond)
    discB = discA | (same & (ncls == 0x50) & hmr_dead[np.maximum(nop, 0)])
    d = {"n_ccx": int(len(ccx)), "dead_R_A": int(discA.sum()),
         "dead_R_B": int(discB.sum()), "no_next_touch": int((~ok).sum())}
    vals, cnts = np.unique(ncls[same], return_counts=True)
    d["next_touch_hist"] = {NAMES.get(int(v), "?"): int(n) for v, n in zip(vals, cnts)}
    for nm in ("fwd", "chien", "rev"):
        s = REG == nm
        d[nm] = {"ccx": int(s.sum()), "deadA": int(discA[s].sum()),
                 "deadB": int(discB[s].sum())}
    for k in range(9):
        s = MINE & (bsz == k)
        d[f"mine_run_{BRUN[str(k)]}"] = [int(s.sum()), int(discA[s].sum()),
                                         int(discB[s].sum())]
    OUT["dce"] = d
    say("dce", json.dumps({k: v for k, v in d.items() if not isinstance(v, dict)}))
    del key, qk, j, ok, nxt, same, nop, ncls, ncond, discA, discB


stage("E2_dce")(stage_E2)


def stage_F():
    reg_i = np.searchsorted(BOUND, ccx, side="right")
    al_i = in_align(ccx).astype(np.int8)
    cut = np.flatnonzero((np.diff(ccx) > 6000) | (np.diff(reg_i) != 0)
                         | (np.diff(al_i) != 0)) + 1
    rows = []
    for mem in np.split(np.arange(len(ccx)), cut):
        a0, a1 = int(ccx[mem[0]]), int(ccx[mem[-1]])
        T = int(((tof >= a0) & (tof <= a1)).sum())
        comp = {}
        for k in range(9):
            v = int((bsz[mem] == k).sum())
            if v:
                comp[BRUN[str(k)]] = v
        rows.append({"ops": [a0, a1], "T": T, "ccx": int(len(mem)),
                     "mult": int((sizeW[mem] >= 24).sum()),
                     "mine": bool(not in_align(np.array([a0]))[0]), "comp": comp})
    rows.sort(key=lambda r: -r["T"])
    OUT["clusters"] = {"n": len(rows), "rows": rows[:150],
                       "mine_T": int(sum(r["T"] for r in rows if r["mine"])),
                       "align_T": int(sum(r["T"] for r in rows if not r["mine"]))}
    say("clusters", len(rows), OUT["clusters"]["mine_T"], OUT["clusters"]["align_T"])


stage("F_clusters")(stage_F)


def stage_G():
    nw = (NQ + 11) // 12
    rows = []
    ccxw = np.bincount(np.concatenate([A, Bv, Tt]) // 12, minlength=nw + 1)
    q3c = c3[ccz].astype(np.int64)
    cA = c.qqq0[q3c] // 12
    cB = c.qqq1[q3c] // 12
    cC = c.qqq2[q3c] // 12
    del q3c
    cczw = np.bincount(np.concatenate([cA, cB, cC]), minlength=nw + 1)
    cxp0 = np.bincount(p0[POS["CX"]] // 12, minlength=nw + 1)
    cxp1 = np.bincount(p1[POS["CX"]] // 12, minlength=nw + 1)
    cnts = {}
    lasts = {}
    for nm in ("HMR", "R", "X", "Z"):
        arr = POS[nm]
        wq = p0[arr] // 12
        cnts[nm] = np.bincount(wq, minlength=nw + 1)
        last = np.full(nw + 1, -1, np.int64)
        np.maximum.at(last, wq, arr)
        lasts[nm] = last
    for w in range(nw):
        lo, hi = 12 * w, min(12 * w + 12, NQ)
        rows.append({"w": w, "q": f"{lo}-{hi - 1}",
                     "CCX": int(ccxw[w]), "CCZ": int(cczw[w]),
                     "CX": int(cxp0[w] + cxp1[w]),
                     "HMR": int(cnts["HMR"][w]), "R": int(cnts["R"][w]),
                     "X": int(cnts["X"][w]), "Z": int(cnts["Z"][w]),
                     "HMR_last": int(lasts["HMR"][w]), "R_last": int(lasts["R"][w])})
    OUT["words"] = rows
    OUT["words_linear_only"] = [r["w"] for r in rows if r["CCX"] == 0 and r["CCZ"] == 0
                                and r["CX"] > 0 and r["HMR"] == 0]
    OUT["words_never_touched"] = [r["w"] for r in rows if r["CX"] == 0 and r["CCX"] == 0]
    say("words", OUT["words_linear_only"], OUT["words_never_touched"])


stage("G_words")(stage_G)


def stage_H():
    probs = None
    m = se = None
    info = {}
    try:
        m, se, info = c.sample_toffolis(shots=32768, seed=7, per_gate=True)
        probs = info.pop("probs")
    except Exception:
        traceback.print_exc()
    OUT["mean_sampling"] = {"shots": info.get("shots"),
                            "mean": None if probs is None else float(m),
                            "se": None if probs is None else float(se)}
    if probs is None:
        return
    assert len(probs) == len(tof), (len(probs), len(tof))
    C = probs[np.searchsorted(tof, ccx)]
    Z = probs[np.searchsorted(tof, ccz)]
    OUT["mean_sampling"].update({"total": float(probs.sum()), "ccx": float(C.sum()),
                                 "ccz": float(Z.sum())})
    OUT["mean_sampling"]["by_region"] = {
        nm: {"ccx": float(C[REG == nm].sum())} for nm in ("fwd", "chien", "rev")}
    OUT["mean_sampling"]["ccz_by_region"] = {
        nm: float(Z[(ccz >= (0 if k == 0 else BOUND[k - 1]))
                    & (ccz < (N if k == 4 else BOUND[k]))].sum())
        for k, nm in enumerate(["pre", "fwd", "chien", "rev", "epi"])
        if nm in ("fwd", "chien", "rev")}
    tab = {}
    for nm in ("fwd", "chien", "rev"):
        s = REG == nm
        row = {}
        for k in range(9):
            ss = s & (bsz == k)
            if ss.sum():
                row[BRUN[str(k)]] = [int(ss.sum()), round(float(C[ss].sum()), 2)]
        tab[nm] = row
    OUT["mean_sampling"]["by_run_bucket"] = tab
    # exact mean attribution: region x bucket x align
    regi = np.searchsorted(BOUND, ccx, side="right")
    al = in_align(ccx)
    mt = {}
    for k in range(len(REGN)):
        for b in range(9):
            for a in (0, 1):
                s_ = (regi == k) & (bsz == b) & (al == a)
                if s_.sum():
                    mt[f"{REGN[k]}|{BRUN[str(b)]}|{'align' if a else 'mine'}"] = \
                        [int(s_.sum()), round(float(C[s_].sum()), 3)]
    OUT["mean_sampling"]["T_exact"] = mt
    OUT["mean_sampling"]["mine_mean"] = round(
        float(C[~al].sum() + Z[~in_align(ccz)].sum()), 3)
    OUT["mean_sampling"]["align_mean"] = round(
        float(C[al].sum() + Z[in_align(ccz)].sum()), 3)
    rows = []
    for k in np.argsort(-np.bincount(KEY, minlength=NKEY))[:40]:
        sel = KEY == k
        if sel.sum() == 0:
            continue
        rows.append([int(k), int(sel.sum()), round(float(C[sel].sum()), 2),
                     key_fields(int(k))["wrun"]])
    OUT["mean_sampling"]["by_key"] = rows
    say("mean", OUT["mean_sampling"]["total"], "static", OUT["static_toffoli"])


stage("H_mean")(stage_H)

save("done")
say("TOTAL", round(time.time() - T0, 1))
try:
    os.remove(RAW)
    say("removed", RAW)
except OSError:
    pass
say("tmp", [str(x) for x in TMP.iterdir()])
