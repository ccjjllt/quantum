"""DQI leg, algorithmic-T line: staged structure dump of tape 575b043f.

CPU-only Kaggle kernel.  No quantum simulation: only the instruction stream is read,
the Toffoli-like opcode positions are counted, and the *classical* firing probability
of every Toffoli-like instruction is estimated with `vqcc_ir.Circuit.sample_toffolis`
(the estimator the audit tools use).  That is what splits the static 367,989 into a
per-region mean.

Steps
  1. decompress dqi_575b043f.kmb.xz, sha256 it
  2. the tape carries no INFO_TAG, so the Chien/Forney block is located by its only
     unambiguous anchor: `bit_store(is_error, True, control=error_mbuc[j])`, i.e. runs
     of 12 consecutive BIT_STORE1_IF ops whose conditions are the 12 bits of one E
     register (4095 codeword positions -> 4025 such runs)
  3. static Toffoli split: region A (before Chien), B (Chien loop), C (after)
  4. CCX block census per region: maximal runs of CCX sharing the same
     (control-register, control-register, target-register) triple with gaps <= 80
     instructions.  The tape's 12x12 field multiply is one such block.
  5. dynamic split: mean executed Toffoli-like count per region
  6. condition analysis: Toffolis under E-bit (p~1) vs HMR-bit (p~1/2) conditions
"""
import hashlib
import importlib.util
import json
import lzma
import os
import pathlib
import sys
import time

import numpy as np

WORK = pathlib.Path("/kaggle/working")
T0 = time.time()
OUT = {}
STATIC_ONLY = bool(os.environ.get("DQIALGO_STATIC_ONLY"))


def say(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- inputs
def find_inputs():
    cand = irp = root = None
    for p in pathlib.Path("/kaggle/input").rglob("dqi_575b043f.kmb.xz"):
        cand = p
        break
    for p in pathlib.Path("/kaggle/input").rglob("vqcc_ir.py"):
        irp = p
        break
    for p in pathlib.Path("/kaggle/input").rglob("verifiers/dqi/verify_submission_dqi.py"):
        root = p.parents[2]
        break
    if not (cand and irp):
        raise SystemExit("inputs not found")
    return cand, irp, root


if pathlib.Path("/kaggle/input").is_dir():
    XZ, IRPY, COMP = find_inputs()
    WORK.mkdir(parents=True, exist_ok=True)
else:                                    # local dry run
    XZ = pathlib.Path("/private/tmp/dqid/dqi_575b043f.kmb.xz")
    IRPY = pathlib.Path("artifacts/20261118_push_dqi/ds/vqcc_ir.py").resolve()
    COMP = None
    WORK = pathlib.Path("/private/tmp/dqid")
OUT["dataset_xz"] = str(XZ)
OUT["ir_py_sha256"] = sha256(IRPY)

raw = WORK / "dqi_575b043f.kmb"
if not raw.exists():
    say("decompressing", XZ)
    with lzma.open(XZ, "rb") as fi, open(raw, "wb") as fo:
        while True:
            b = fi.read(1 << 23)
            if not b:
                break
            fo.write(b)
OUT["kmb_sha256"] = sha256(raw)
OUT["kmb_bytes"] = raw.stat().st_size
say("kmb", OUT["kmb_sha256"], OUT["kmb_bytes"])

spec = importlib.util.spec_from_file_location("vqcc_ir", str(IRPY))
ir = importlib.util.module_from_spec(spec)
sys.modules["vqcc_ir"] = ir
spec.loader.exec_module(ir)

c = ir.Circuit.read(str(raw))
t = c.types
N = c.num_ops
OUT["num_ops"] = N
OUT["num_qubits"] = c.num_qubits
OUT["num_bits"] = c.num_bits
OUT["num_registers"] = len(c.registers)
OUT["static_counts"] = c.static_counts()
OUT["static_toffoli"] = c.toffoli_like()
say("ops", N, "q", c.num_qubits, "static T", OUT["static_toffoli"])

ebits = set()
for nm, ids in c.registers:
    if nm.startswith("E") and nm[1:].isdigit():
        ebits.update(int(x) for x in ids)
EBIT_MAX = max(ebits)
OUT["n_ebits"] = len(ebits)
OUT["ebit_max"] = EBIT_MAX

# ------------------------------------------------- per-instruction operands
# only the two consumption counters that are actually needed, as int32
cfun3 = np.zeros(N + 1, dtype=np.int32); cfun3[1:] = np.cumsum(ir.L3Q[t])
cfuncc = np.zeros(N + 1, dtype=np.int32); cfuncc[1:] = np.cumsum(ir.LCOND[t])
say("consumption offsets done")

tof = np.flatnonzero(ir.LTOF[t])
is_ccx_op = (t[tof] & 0x7F) == 0x31
is_ccz_op = (t[tof] & 0x7F) == 0x30
ccxp = tof[is_ccx_op]
cczp = tof[is_ccz_op]
q3 = cfun3[ccxp + 1] - 1
CRA = (c.qqq0[q3].astype(np.int64)) // 12
CRB = (c.qqq1[q3].astype(np.int64)) // 12
CRT = (c.qqq2[q3].astype(np.int64)) // 12
del q3
OUT["ccx"] = int(len(ccxp))
OUT["ccz"] = int(len(cczp))
say("ccx", len(ccxp))

# ----------------------------------------------------- Chien loop anchor
pos = np.flatnonzero(t == 0xC1)                       # BIT_STORE1_IF
cond = c.bc[cfuncc[pos + 1] - 1].astype(np.int64)
cn = cond.tolist()
found = []
i, npos = 0, len(cn)
while i + 11 < npos:
    c0 = cn[i]
    if c0 % 12 == 0 and c0 < EBIT_MAX and cn[i + 11] == c0 + 11 and all(cn[i + k] == c0 + k for k in range(12)):
        found.append((int(pos[i]), c0 // 12))
        i += 12
    else:
        i += 1
chien_pos = np.array([f[0] for f in found], dtype=np.int64)
chien_j = np.array([f[1] for f in found], dtype=np.int64)
A = int(chien_pos.min()); B = int(chien_pos.max())
OUT["chien_positions"] = int(len(found))
OUT["chien_region"] = [A, B]
OUT["chien_j_range"] = [int(chien_j.min()), int(chien_j.max())]
OUT["region_bounds"] = {"A": [0, A], "B": [A, B + 1], "C": [B + 1, N]}
say("chien positions", len(found), "region", A, B)

regions = {"A": (0, A), "B": (A, B + 1), "C": (B + 1, N)}
reg_of = np.zeros(N, dtype=np.int8)
reg_of[A:B + 1] = 1
reg_of[B + 1:] = 2
tr = reg_of[tof]
creg = reg_of[ccxp]

split = {}
for k, nm in enumerate("ABC"):
    a, b = regions[nm]
    sel = tr == k
    sub = t[a:b]
    split[nm] = {
        "ops": int(b - a),
        "tof": int(sel.sum()),
        "ccx": int(sel[is_ccx_op].sum()),
        "ccz": int(sel[is_ccz_op].sum()),
        "cx": int((sub == 0x21).sum()),
        "swap": int((sub == 0x22).sum()),
        "hmr": int((sub == 0x50).sum()),
        "push": int((sub == 0x81).sum()),
        "bitinv_if": int((sub == 0xC2).sum()),
        "bitstore0": int((sub == 0x40).sum()),
    }
OUT["static_split"] = split
say("static split", json.dumps(split))

# ---------------------------------------------------- CCX block census
def census(gapmax=80):
    out = {}
    ge12_all = np.zeros(len(ccxp), dtype=bool)
    for k, nm in enumerate("ABC"):
        sel = np.flatnonzero(creg == k)
        P, a, b, d = ccxp[sel], CRA[sel], CRB[sel], CRT[sel]
        sizes, ge = [], np.zeros(len(P), dtype=bool)
        i = 0
        while i < len(P):
            j = i
            while j + 1 < len(P) and (P[j + 1] - P[j] <= gapmax and a[j + 1] == a[j]
                                      and b[j + 1] == b[j] and d[j + 1] == d[j]):
                j += 1
            sizes.append(j - i + 1)
            if j - i + 1 >= 12:
                ge[i:j + 1] = True
            i = j + 1
        ge12_all[sel] = ge
        sizes = np.array(sizes)
        hist = {int(s): int((sizes == s).sum()) for s in sorted(set(sizes.tolist()))}
        out[nm] = {
            "ccx": int(len(P)),
            "blocks": int(len(sizes)),
            "size_hist": dict(sorted(hist.items(), key=lambda kv: -kv[1])[:14]),
            "ccx_in_blocks_ge12": int(sizes[sizes >= 12].sum()),
            "blocks_ge12": int((sizes >= 12).sum()),
            "sizes_ge12": {int(s): int((sizes == s).sum()) for s in sorted(set(sizes[sizes >= 12].tolist()))},
        }
    return out, ge12_all


OUT["ccx_block_census_gap80"], ge12 = census(80)
say("census", json.dumps(OUT["ccx_block_census_gap80"]))

OUT["toffoli_target_family"] = {
    nm: {"syndrome_reg_0_69": int((CRT[creg == k] < 70).sum()),
         "pool_reg_70plus": int((CRT[creg == k] >= 70).sum())}
    for k, nm in enumerate("ABC")
}
if len(cczp):
    qc = cfun3[cczp + 1] - 1
    v, cnt = np.unique(c.qqq0[qc].astype(np.int64) // 12, return_counts=True)
    OUT["ccz_target_regs"] = {int(a): int(b) for a, b in zip(v, cnt)}

# ------------------------------------ condition depth / class of Toffolis
ev_push = np.flatnonzero(t == 0x81)
ev_pop = np.flatnonzero(t == 0x01)
merges = np.concatenate([ev_push, ev_pop])
kinds = np.concatenate([np.ones(len(ev_push), np.int8), -np.ones(len(ev_pop), np.int8)])
order = np.argsort(merges, kind="stable")
merges = merges[order]
kinds = kinds[order]
del order
pushbits = c.bc[cfuncc[ev_push + 1] - 1].astype(np.int64)
tp = tof.tolist()
tpi = 0

def _emit(p, stack, depth_hist, class_hist):
    d = len(stack)
    nm = "ABC"[reg_of[p]]
    key = "0" if d == 0 else ("1-2" if d <= 2 else ("3-6" if d <= 6 else "7+"))
    depth_hist.setdefault(nm, {})
    depth_hist[nm][key] = depth_hist[nm].get(key, 0) + 1
    if d == 0:
        ae = "none"
    elif all(x <= EBIT_MAX for x in stack):
        ae = "E-only"
    elif any(x <= EBIT_MAX for x in stack):
        ae = "mixed"
    else:
        ae = "scratch-only"
    class_hist.setdefault(nm, {})
    class_hist[nm][ae] = class_hist[nm].get(ae, 0) + 1


stack = []
depth_hist, class_hist = {}, {}
missing = 0
ti = 0
nmerges = len(merges)
for i in range(nmerges):
    k = int(kinds[i])
    if k == 1:
        stack.append(int(pushbits[ti])); ti += 1
        continue
    if stack:
        stack.pop()
    else:
        missing += 1
    m = int(merges[i])
    while tpi < len(tp) and tp[tpi] < m:
        _emit(tp[tpi], stack, depth_hist, class_hist)
        tpi += 1
while tpi < len(tp):
    _emit(tp[tpi], stack, depth_hist, class_hist)
    tpi += 1
OUT["toffoli_depth_hist"] = depth_hist
OUT["toffoli_cond_class"] = class_hist
OUT["unmatched_pops"] = missing
say("cond class", json.dumps(class_hist))

# ------------------------------------------------------ dynamic split
OUT["verifier_reference_mean_T"] = 367116.06
if not STATIC_ONLY:
    mean, se, info = c.sample_toffolis(shots=1 << 16, seed=1, per_gate=True)
    probs = info["probs"]
    OUT["dynamic"] = {
        "mean_total": mean,
        "se_total": se,
        "shots": int(info["shots"]),
        "events": int(info["events"]),
        "per_region": {nm: float(probs[tr == k].sum()) for k, nm in enumerate("ABC")},
        "per_region_static": {nm: int((tr == k).sum()) for k, nm in enumerate("ABC")},
        "fired_fraction_min": float(probs.min()),
        "fired_fraction_max": float(probs.max()),
    }
    say("dynamic", json.dumps(OUT["dynamic"]))
    ccx_probs = probs[np.searchsorted(tof, ccxp)]
    OUT["dynamic_ccx"] = {
        nm: {
            "mult_ge12_static": int(ge12[creg == k].sum()),
            "mult_ge12_mean": float(ccx_probs[creg == k][ge12[creg == k]].sum()),
            "small_static": int((~ge12[creg == k]).sum()),
            "small_mean": float(ccx_probs[creg == k][~ge12[creg == k]].sum()),
        }
        for k, nm in enumerate("ABC")
    }
    say("dynamic ccx", json.dumps(OUT["dynamic_ccx"]))

OUT["seconds"] = round(time.time() - T0, 1)
(pathlib.Path(WORK) / "region_split.json").write_text(json.dumps(OUT, indent=1))
print("RESULT_JSON_BEGIN")
print(json.dumps(OUT, indent=1))
print("RESULT_JSON_END")
