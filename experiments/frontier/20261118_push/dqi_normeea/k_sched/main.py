"""DQI normalized-EEA lever, kernel A: reverse-engineer the tape's EEA schedule.

Kaggle CPU, static IR read only (no simulation of the quantum state, no verifier).

Reads `dqi_575b043f.kmb.xz` from the public dataset, decompresses to /tmp, and dumps a
compact block table of the two EEA passes:

  block = maximal run of CCX sharing one (wa, wb, wt) *word* triple
          (wa = q1 // 12, wb = q2 // 12, wt = q3 // 12), inter-CCX gap <= 80

For every block we record (n_ccx, wa, wb, wt, first_op, cx_after) so that the round
structure can be reconstructed offline (each pass is ~2,000 blocks / ~120 KB of JSON).

Plus, per pass: the CCX/T accounting, the block-size histogram, the AND-chain test on
small blocks (is the target of one CCX a control of the next? -> a zero-test chain,
not a product), and the word-role histogram (how many blocks use each word as the
first operand = the quotient word).

The decompressed tape is deleted before exit; only JSON leaves the kernel.
"""
import importlib.util
import json
import lzma
import pathlib
import sys
import time

import numpy as np

T0 = time.time()
OUT = {}


def say(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


def find(pat):
    for p in pathlib.Path("/kaggle/input").rglob(pat):
        return p
    return None


XZ = find("dqi_575b043f.kmb.xz")
IRPY = find("vqcc_ir.py")
say("xz", XZ, "ir", IRPY)
raw = pathlib.Path("/tmp/dqi_575b043f.kmb")
with lzma.open(XZ, "rb") as fi, open(raw, "wb") as fo:
    while True:
        b = fi.read(1 << 23)
        if not b:
            break
        fo.write(b)
say("decompressed", raw.stat().st_size)

spec = importlib.util.spec_from_file_location("vqcc_ir", str(IRPY))
ir = importlib.util.module_from_spec(spec)
sys.modules["vqcc_ir"] = ir
spec.loader.exec_module(ir)

c = ir.Circuit.read(str(raw))
OUT["num_ops"] = int(c.num_ops)
OUT["num_qubits"] = int(c.num_qubits)
OUT["static_toffoli"] = int(c.toffoli_like())
say("read", c.num_ops, c.num_qubits, OUT["static_toffoli"])

t = c.types
tof = np.flatnonzero(ir.LTOF[t])
cczp = np.flatnonzero(ir.L3Q[t] & ((t & 0x7F) == 0x31))            # CCX only
ccz = np.flatnonzero(ir.L3Q[t] & ((t & 0x7F) == 0x30))             # CCZ only
cfun3 = np.cumsum(ir.L3Q[t])
qc = cfun3[cczp + 1] - 1
A = c.qqq0[qc].astype(np.int64)
B = c.qqq1[qc].astype(np.int64)
C = c.qqq2[qc].astype(np.int64)
CRA, CRB, CRT = A // 12, B // 12, C // 12
say("ccx", len(cczp), "ccz", len(ccz))

# CX positions (for the per-block "CX after" traffic and the accumulate-out test)
cxp = np.flatnonzero(ir.L2Q[t] & ((t & 0x7F) == 0x21))             # CX only
say("cx", len(cxp))

FWD = (17576206, 30335416)
REV = (35627262, 52910631)


def blocks(lo, hi, gapmax=80):
    sel = np.flatnonzero((cczp >= lo) & (cczp < hi))
    P = cczp[sel]
    a, b, d = CRA[sel], CRB[sel], CRT[sel]
    out = []
    i = 0
    while i < len(P):
        j = i
        while (j + 1 < len(P) and (P[j + 1] - P[j] <= gapmax)
               and a[j + 1] == a[j] and b[j + 1] == b[j] and d[j + 1] == d[j]):
            j += 1
        out.append((int(P[i]), int(P[j]), j - i + 1, int(a[i]), int(b[i]), int(d[i]),
                    int(sel[i]), int(sel[j])))
        i = j + 1
    return out


def explore(name, lo, hi):
    bl = blocks(lo, hi)
    sizes = np.array([x[2] for x in bl])
    T = int(((tof >= lo) & (tof < hi)).sum())
    nccx = int(((cczp >= lo) & (cczp < hi)).sum())
    nccz = int(((ccz >= lo) & (ccz < hi)).sum())
    hist = {int(s): int(v) for s, v in zip(*np.unique(sizes, return_counts=True))}
    outs = {"ops": hi - lo, "static_T": T, "ccx": nccx, "ccz": nccz,
            "blocks": len(bl), "sizes": hist}

    # --- size classes and the AND-chain test on small blocks -------------------
    # A zero test of a 12-bit word is a chain CCX(t,c0->t) CCX(t,c1->t) ... ; a product
    # uses independent (linear form, linear form) controls.  Test: fraction of the
    # block's CCX whose previous CCX target is one of its controls.
    chain = {}
    for cls, lo_s, hi_s in (("n24plus", 24, 10 ** 9), ("n12_23", 12, 23), ("n2_11", 2, 11), ("n1", 1, 1)):
        num = den = 0
        for x in bl:
            if not (lo_s <= x[2] <= hi_s):
                continue
            prev_t = None
            for k in range(x[6], x[7] + 1):
                if prev_t is not None:
                    den += 1
                    if prev_t == A[k] or prev_t == B[k]:
                        num += 1
                prev_t = C[k]
        chain[cls] = (num, den)
    outs["chain"] = {k: (v[0], v[1], (v[0] / v[1] if v[1] else None)) for k, v in chain.items()}

    # --- word role histograms --------------------------------------------------
    wa_hist = {}
    wb_hist = {}
    wt_hist = {}
    for x in bl:
        if x[2] >= 12:
            wa_hist[x[3]] = wa_hist.get(x[3], 0) + 1
            wb_hist[x[4]] = wb_hist.get(x[4], 0) + 1
            wt_hist[x[5]] = wt_hist.get(x[5], 0) + 1
    outs["wa_hist_ge12"] = dict(sorted(wa_hist.items()))
    outs["wb_hist_ge12"] = dict(sorted(wb_hist.items()))
    outs["wt_hist_ge12"] = dict(sorted(wt_hist.items()))

    # --- block table (compact) -------------------------------------------------
    # [n_ccx, wa, wb, wt, first_op, cx_between]
    cxi = np.searchsorted(cxp, [x[1] for x in bl])
    cxj = np.searchsorted(cxp, [x[0] for x in bl])
    table = []
    for idx, x in enumerate(bl):
        # CX ops strictly after this block's last CCX and before the next block's first
        nxt = bl[idx + 1][0] if idx + 1 < len(bl) else bl[idx][1] + 1
        cxa = int(np.searchsorted(cxp, x[1], side="right"))
        cxb = int(np.searchsorted(cxp, nxt, side="left"))
        table.append([x[2], x[3], x[4], x[5], x[0], max(0, cxb - cxa)])
    outs["table"] = table
    OUT[name] = outs
    say(name, "ops", hi - lo, "T", T, "blocks", len(bl), "ccx", nccx, "ccz", nccz)
    return outs


explore("fwd", *FWD)
explore("rev", *REV)

# ---- whole-tape accounting: what the EEA passes contain, class by class --------
tot = {"all_ccx": int(len(cczp)), "all_ccz": int(len(ccz))}
tot["fwd_plus_rev_ccx"] = OUT["fwd"]["ccx"] + OUT["rev"]["ccx"]
tot["fwd_plus_rev_ccz"] = OUT["fwd"]["ccz"] + OUT["rev"]["ccz"]
tot["fwd_plus_rev_T"] = OUT["fwd"]["static_T"] + OUT["rev"]["static_T"]
for nm in ("fwd", "rev"):
    e = OUT[nm]
    h = e["sizes"]
    e["ccx_by_class"] = {
        "ge24": sum(s * v for s, v in h.items() if s >= 24),
        "n12_23": sum(s * v for s, v in h.items() if 12 <= s <= 23),
        "n2_11": sum(s * v for s, v in h.items() if 2 <= s <= 11),
        "n1": h.get("1", 0),
    }
    e["blocks_by_class"] = {
        "ge24": sum(v for s, v in h.items() if s >= 24),
        "n12_23": sum(v for s, v in h.items() if 12 <= s <= 23),
        "n2_11": sum(v for s, v in h.items() if 2 <= s <= 11),
        "n1": h.get("1", 0),
    }
OUT["totals"] = tot

pathlib.Path("/kaggle/working/sched.json").write_text(json.dumps(OUT))
say("wrote sched.json", pathlib.Path("/kaggle/working/sched.json").stat().st_size)
raw.unlink(missing_ok=True)
say("deleted tape")
