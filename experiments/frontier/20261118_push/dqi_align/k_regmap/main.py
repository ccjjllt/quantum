"""DQI align line v3: is `q // 12` a valid word model, and what are the two big clusters?

CPU-only Kaggle kernel.  **Static IR read only.  No simulation, no verifier.**

The `.kmb` carries its own register table, so the qubit -> (register, bit) map is
exact.  This kernel

  1. dumps `c.registers` (name, width, kind, min/max/first ids, contiguity) -- decides
     whether S0..S69 are 12 contiguous qubits each and whether `q // 12` == register;
  2. recomputes the CCX census of both spans in **(register, bit)** terms;
  3. runs the **Fredkin-neighbourhood test**: for every CCX at op p with operands
     (a, b, e) it checks whether p-1 and p+1 are CX gates on the pair (e, b) -- the
     `CX(e,b); CCX(a,b,e); CX(e,b)` decomposition of a controlled bit swap -- plus the
     three other orderings.  A shift built from controlled swaps must fire this;
     a Toom/Karatsuba AND network cannot;
  4. groups the CCX by their single-qubit control q0 and reports, per control, the
     number of CCX, the number of distinct (register, bit) target pairs, the bit set
     and the op range -- the 69-step signature of an initial alignment is a family of
     69 controls serving 12*(67-step) swaps each;
  5. emits three 20,000-op symbolic windows with **register labels**.

Output: registers.json, regmap.json, windows3.json
"""
import importlib.util
import json
import lzma
import pathlib
import sys
import time

import numpy as np

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
NQ = c.num_qubits
say("ops", N, "Q", NQ, "T", int(c.toffoli_like()))

# ------------------------------------------------------------- 1. registers
MASK = 0x7FFFFFFF          # register ids are tagged with bit 31
regs = [(str(nm), [int(x) for x in ids]) for nm, ids in c.registers]
regs = [(nm, [x & MASK for x in ids]) for nm, ids in regs]
REG = {"n_registers": len(regs), "num_qubits": NQ, "num_bits": c.num_bits, "rows": []}
for nm, ids in regs:
    qs = [q for q in ids if q < NQ]
    bs = [q for q in ids if q >= NQ]          # bit payloads carry the same offset
    lo = min(ids) if ids else None
    hi = max(ids) if ids else None
    contig = bool(qs) and (hi - lo + 1 == len(qs))
    REG["rows"].append({
        "name": nm, "len": len(ids), "is_quantum": bool(qs),
        "min": lo, "max": hi, "n_qubits": len(qs), "n_bits": len(bs),
        "contiguous": contig, "first24": ids[:24],
    })
    if len(REG["rows"]) > 400:
        break
REG["n_rows_dumped"] = len(REG["rows"])
names_all = [nm for nm, _ in regs]
REG["names_head"] = names_all[:6]
REG["names_tail"] = names_all[-6:]
with open(WORK / "registers.json", "w") as f:
    json.dump(REG, f, indent=1)
say("registers.json", len(regs), "registers;", names_all[:4], "...", names_all[-2:])

# qubit -> (register index, bit index) using the quantum half of the table
reg_of_q = np.full(NQ, -1, np.int16)
bit_of_q = np.full(NQ, -1, np.int16)
reg_names = []
for ridx, (nm, ids) in enumerate(regs):
    qs = [q for q in ids if q < NQ]
    if not qs:
        continue
    reg_names.append(nm)
    for k, q in enumerate(ids):
        if q < NQ:
            reg_of_q[q] = ridx
            bit_of_q[q] = k
say("qubit map: registers with quantum wires", len(reg_names))

# consistency checks of the `q // 12` model
q12_ok = int((reg_of_q[::12][: NQ // 12] >= 0).sum())
S_rows = [(nm, ids) for nm, ids in regs if nm.startswith("S") and nm[1:].isdigit()]
REG2 = {"id_tag_high_bit": int(c.registers[0][1][0]) >> 31,
        "n_S_registers": len(S_rows),
        "S_widths": sorted({len(ids) for _, ids in S_rows})[:8],
        "S0_ids": S_rows[0][1] if S_rows else None,
        "S1_ids": S_rows[1][1] if len(S_rows) > 1 else None,
        "S69_ids": S_rows[-1][1] if S_rows else None,
        "S_all_contiguous": bool(all(max(ids) - min(ids) + 1 == len(ids)
                                     for _, ids in S_rows)) if S_rows else None,
        "S_min_ids": [min(ids) for _, ids in S_rows][:8] if S_rows else None,
        "S_starts_step": ([min(ids) for _, ids in S_rows][1]
                          - [min(ids) for _, ids in S_rows][0]) if len(S_rows) > 1 else None,
        "is_word12_equals_register": None}
# is the register == {12k..12k+11} for every syndrome?
ok = True
for nm, ids in S_rows:
    s = sorted(ids)
    if s != list(range(12 * (s[0] // 12), 12 * (s[0] // 12) + 12)):
        ok = False
        break
REG2["is_word12_equals_register"] = bool(ok)
with open(WORK / "registers.json", "w") as f:
    json.dump({"table": REG, "checks": REG2}, f, indent=1)
say("word12==register?", REG2["is_word12_equals_register"],
    "S widths", REG2["S_widths"], "S0", REG2["S0_ids"])

# --------------------------------------------------------------- op arrays
base = (t & 0x7F)
L1, L2, L3 = ir.L1Q[t], ir.L2Q[t], ir.L3Q[t]
cf2 = np.zeros(N + 1, np.int32); cf2[1:] = np.cumsum(L2)
cf3 = np.zeros(N + 1, np.int32); cf3[1:] = np.cumsum(L3)
q0 = np.full(N, -1, np.int16)
q1 = np.full(N, -1, np.int16)
q2 = np.full(N, -1, np.int16)
try:
    cf1 = np.zeros(N + 1, np.int32); cf1[1:] = np.cumsum(L1)
    i1 = np.flatnonzero(L1); q0[i1] = c.q0[cf1[i1 + 1] - 1]
except Exception as ex:
    say("L1 payload unavailable", repr(ex))
i2 = np.flatnonzero(L2); k2 = cf2[i2 + 1] - 1
q0[i2] = c.qq0[k2]; q1[i2] = c.qq1[k2]
i3 = np.flatnonzero(L3); k3 = cf3[i3 + 1] - 1
q0[i3] = c.qqq0[k3]; q1[i3] = c.qqq1[k3]; q2[i3] = c.qqq2[k3]
del i2, i3, k2, k3, cf1, cf2
say("payloads ready")

ccxp = np.flatnonzero(base == 0x31)


def fredkin_test(lo, hi):
    """does each CCX sit inside CX(e,b) / CCX(a,b,e) / CX(e,b) ?"""
    sel = ccxp[(ccxp >= lo + 1) & (ccxp < hi - 1)]
    if len(sel) == 0:
        return {}
    a, b, e = q0[sel], q1[sel], q2[sel]
    pv, nx = sel - 1, sel + 1
    is_cx_pv = base[pv] == 0x21
    is_cx_nx = base[nx] == 0x21
    # variant A: CX(e,b) ; CCX(a,b,e) ; CX(e,b)
    pvA = is_cx_pv & (q0[pv] == e) & (q1[pv] == b)
    nxA = is_cx_nx & (q0[nx] == e) & (q1[nx] == b)
    # variant B: CX(b,e) ; CCX(a,b,e) ; CX(b,e)
    pvB = is_cx_pv & (q0[pv] == b) & (q1[pv] == e)
    nxB = is_cx_nx & (q0[nx] == b) & (q1[nx] == e)
    # variant C: controls swapped: CX(e,a) ; CCX(b,a,e) ; CX(e,a)
    pvC = is_cx_pv & (q0[pv] == e) & (q1[pv] == a)
    nxC = is_cx_nx & (q0[nx] == e) & (q1[nx] == a)
    return {
        "n_ccx": int(len(sel)),
        "both_sides_A": int((pvA & nxA).sum()),
        "both_sides_B": int((pvB & nxB).sum()),
        "both_sides_C": int((pvC & nxC).sum()),
        "either_side_A": int((pvA | nxA).sum()),
        "prev_is_cx": int(is_cx_pv.sum()), "next_is_cx": int(is_cx_nx.sum()),
        "prev_pair_matches_A": int(pvA.sum()), "next_pair_matches_A": int(nxA.sum()),
        # is (q1,q2) the same bit of two registers?  (a controlled word-swap needs it)
        "same_bit_q1_q2": int((bit_of_q[b] == bit_of_q[e]).sum()) if (b >= 0).all() else None,
        "same_bit_q0_q1": int((bit_of_q[a] == bit_of_q[b]).sum()),
        "distinct_q0": int(len(np.unique(a))),
        "distinct_pairs_q1q2": int(len(np.unique(b.astype(np.int32) * 4096 + e))),
    }


def reg_census(lo, hi, topk=25):
    m = (ccxp >= lo) & (ccxp < hi)
    out = {"lo": lo, "hi": hi, "n_ccx": int(m.sum())}
    if not m.sum():
        return out
    sel = ccxp[m]
    a, b, e = q0[sel], q1[sel], q2[sel]
    ra, rb, re = reg_of_q[a], reg_of_q[b], reg_of_q[e]
    # register-level triple (register index only)
    key = (ra.astype(np.int64) * 128 + rb.astype(np.int64)) * 128 + re
    uq, uc = np.unique(key, return_counts=True)
    order = np.argsort(-uc)[:topk]
    def rn(i):
        return reg_names[i] if 0 <= i < len(reg_names) else f"r{i}"
    out["reg_triple_top"] = [[rn(int(uq[k] // 128 // 128)),
                              rn(int((uq[k] // 128) % 128)),
                              rn(int(uq[k] % 128)), int(uc[k])]
                             for k in order]
    out["n_distinct_reg_triples"] = int(len(uq))
    out["ccx_per_reg_triple"] = round(float(len(sel) / len(uq)), 3)
    # per-control-q0 clusters
    uqc, ucc = np.unique(a, return_counts=True)
    order = np.argsort(-ucc)[:topk]
    cl = []
    for k in order:
        q = int(uqc[k])
        selc = sel[a == q]
        bb, ee = q1[selc], q2[selc]
        cl.append({"q0": q,
                   "reg": (reg_names[int(reg_of_q[q])]
                           if 0 <= int(reg_of_q[q]) < len(reg_names) else None),
                   "bit": int(bit_of_q[q]),
                   "n_ccx": int(ucc[k]),
                   "distinct_pairs": int(len(np.unique(bb.astype(np.int32) * 4096 + ee))),
                   "op_lo": int(selc.min()), "op_hi": int(selc.max())})
    out["ctrl_top"] = cl
    out["n_distinct_ctrl"] = int(len(uqc))
    out["fredkin"] = fredkin_test(lo, hi)
    return out


SPANS = {"span_fwd": (19_508_954, 21_385_877),
         "span_rev": (46_230_185, 52_842_219),
         "head_fwd": (17_576_206, 17_700_000),
         "cluster132": (21_385_877, 21_588_611)}
RM = {}
for k, (lo, hi) in SPANS.items():
    RM[k] = reg_census(lo, hi)
    say(k, "ccx", RM[k]["n_ccx"], "sigs", RM[k].get("fredkin"))
with open(WORK / "regmap.json", "w") as f:
    json.dump({"checks": REG2, "spans": RM}, f, indent=1)

# --------------------------------------------------------------- 3 windows
opname = np.full(N, 0, np.int16)
NAMES2 = [(0x00, "NEG"), (0x01, "POP"), (0x10, "Z"), (0x11, "X"), (0x12, "R"),
          (0x13, "ZPOW"), (0x50, "HMR"), (0x20, "CZ"), (0x21, "CX"),
          (0x22, "SWAP"), (0x30, "CCZ"), (0x31, "CCX"), (0x32, "CSWAP"),
          (0x40, "BS0"), (0x41, "BS1"), (0x42, "BINV"), (0x06, "TAG"),
          (0x07, "DBG")]
nmlist = [n for _, n in NAMES2] + ["OTHER", "PUSH"]
for k, (v, _) in enumerate(NAMES2):
    opname[base == v] = k
opname[t == 0x81] = len(NAMES2) + 1
opname[opname == 0] = len(NAMES2)


def lab(q):
    if q < 0:
        return "-"
    r = reg_of_q[q]
    if r < 0:
        return f"q{q}"
    return f"{reg_names[r]}[{int(bit_of_q[q])}]"


WINDOWS = {"W1_fwd_start": [19_508_954, 19_528_954],
           "W3_rev_start": [46_230_185, 46_250_185],
           "W5_decay": [21_900_000, 21_920_000]}
wo = {"names": nmlist, "windows": {}}
for tag, (lo, hi) in WINDOWS.items():
    rows = [[nmlist[int(opname[p])], bool(t[p] & 0x80), lab(int(q0[p])),
             lab(int(q1[p])), lab(int(q2[p]))] for p in range(lo, hi)]
    wo["windows"][tag] = {"lo": lo, "hi": hi, "ops": rows}
with open(WORK / "windows3.json", "w") as f:
    json.dump(wo, f, separators=(",", ":"))

print(json.dumps(REG2, indent=1))
for k, v in RM.items():
    print(f"\n== {k} ccx {v['n_ccx']}  per-reg-triple {v.get('ccx_per_reg_triple')} "
          f"distinct ctrl {v.get('n_distinct_ctrl')}")
    print("  fredkin:", json.dumps(v.get("fredkin")))
    print("  ctrl_top:", json.dumps(v.get("ctrl_top", [])[:8]))
    print("  reg_triple_top:", json.dumps(v.get("reg_triple_top", [])[:8]))
print("\nW1 first 40 register-labelled ops:")
for r in wo["windows"]["W1_fwd_start"]["ops"][:40]:
    print("  ", r)

raw.unlink()
say("tape removed, done")
