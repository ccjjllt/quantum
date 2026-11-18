"""dqi_refshift: standalone rebuild of the official DQI `_initial_shift_loop`.

Kaggle CPU only (enable_gpu/enable_tpu false).  Static build only: nothing is
simulated, the official verifier is not run.

Question: are the two big Toffoli clusters of tape 575b043f this loop?
    forward span [19,508,954, 21,385,877)  T 29,543  CX 1,826,827  SWAP 8,397
    reverse span [46,230,185, 52,842,219)  T 65,774  CX 4,326,547  SWAP 162,848

Method: copy the official generator out of the competition data (the original is
not modified), import kickmix from the competition mount, and build ONLY
    reg_a = [alloc(12) x 3] + 70 syndrome registers,  n_A = alloc(m.bit_length()+1)
    x(init_ones); gf2_iadd(70, n_A); _initial_shift_loop(..., is_adjoint)
then read the emitted stream back with the competition's `vqcc_ir` and report the
exact opcode census, the first 3000 ops, and the per-`shift_step` breakdown.
`builder.mark()` emits @enter/@exit INFO_TAG instructions, so the step
boundaries are exact (no structural guessing).

The tape's own windows at the head of each cluster are read in the same kernel
(census + CSWAP-idiom test + a short symbolic dump) for a direct comparison.
"""
import hashlib
import importlib.util
import json
import lzma
import pathlib
import shutil
import sys
import time

import numpy as np

WORK = pathlib.Path("/kaggle/working")
T0 = time.time()
OUT = {}
TAG = 0x06


def say(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def find(pat):
    for p in pathlib.Path("/kaggle/input").rglob(pat):
        return p
    return None


def find_comp():
    for p in (pathlib.Path("/kaggle/input/competitions/google-verifiable-quantum-circuit-compilation"),
              pathlib.Path("/kaggle/input/datasets/google-verifiable-quantum-circuit-compilation"),
              pathlib.Path("/kaggle/input/google-verifiable-quantum-circuit-compilation")):
        if (p / "verifiers").is_dir():
            return p
    for p in pathlib.Path("/kaggle/input").rglob("verifiers"):
        if (p / "dqi").is_dir():
            return p.parent
    return None


COMP = find_comp()
OUT["competition_root"] = str(COMP)
say("competition root", COMP)
if COMP is None:
    raise SystemExit("no competition mount")

sys.path.insert(0, str(COMP / "kickmix"))
import kickmix as km  # noqa: E402

OUT["kickmix"] = {"file": str(km.__file__), "version": getattr(km, "__version__", "?")}
say("kickmix", km.__file__, OUT["kickmix"]["version"])

# ---------------------------------------------------------------- reference module
REF_SRC = COMP / "verifiers" / "dqi" / "dqi_reference_circuit.py"
OUT["reference_source"] = {
    "path": str(REF_SRC),
    "sha256": sha256(REF_SRC),
    "bytes": REF_SRC.stat().st_size,
    # `_initial_shift_loop` is lines 140-164 of the official file (1-based).
    "lines_initial_shift_loop": [140, 164],
}
say("reference", OUT["reference_source"]["sha256"])
shutil.copyfile(REF_SRC, WORK / "dqi_reference_circuit.py")   # a copy; the original is untouched
spec = importlib.util.spec_from_file_location("dqi_ref_copy", WORK / "dqi_reference_circuit.py")
ref = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ref)

N_SYN, DEG = 70, 12
M = N_SYN + 3
LOGM = M.bit_length() + 1        # 8; the official build uses m.bit_length() + 1
NBASE = 3 * DEG + N_SYN * DEG    # 876 qubits below n_A
OUT["params"] = {"n_syndromes": N_SYN, "degree": DEG, "m": M, "logm": LOGM,
                 "n_shift_steps": N_SYN - 1, "qubits_reg_a": M * DEG}
dec = ref.ProosAndZalkaDecoder(N_SYN, km.GF2Field(DEG))

# ---------------------------------------------------------------- IR helpers (need ir before builds)
XZ = find("dqi_575b043f.kmb.xz")
IRPY = find("vqcc_ir.py")
say("tape", XZ, "ir", IRPY)
spec = importlib.util.spec_from_file_location("vqcc_ir", str(IRPY))
ir = importlib.util.module_from_spec(spec)
sys.modules["vqcc_ir"] = ir
spec.loader.exec_module(ir)


def phys_mask(t):
    """Real (non tag, non debug-print) instructions."""
    return (t != TAG) & ((t & 0x7F) != 0x07)


def physics_counts(c, lo=0, hi=None):
    hi = c.num_ops if hi is None else hi
    t = np.asarray(c.types[lo:hi])
    keep = phys_mask(t)
    bc = np.bincount(t[keep], minlength=256)
    d = {ir.name(int(x)): int(bc[x]) for x in np.flatnonzero(bc)}
    d["toffoli_like"] = int(bc[[0x30, 0x31, 0x32]].sum())
    d["ops"] = int(keep.sum())
    d["ops_with_tags"] = int(hi - lo)
    return d


def head_symbols(c, n=3000, lo=0, hi=None):
    """First n instructions as [name_index, cond, q0, q1, q2]; q* = raw qubit ids, -1 = absent."""
    hi = c.num_ops if hi is None else hi
    out, names = [], []
    for (i, nm, qs, tb, cb) in c.decode(lo, min(hi, lo + n)):
        if nm not in names:
            names.append(nm)
        q = [int(x) for x in qs] + [-1] * (3 - len(qs))
        out.append([names.index(nm), int(cb) if cb is not None else -1] + q)
    return {"names": names, "ops": out}


def label_map(c, logm):
    reg = {}
    for nm, ids in c.registers:
        for k, q in enumerate(ids):
            v = int(q)
            if v >> 31:                      # quantum register ids carry bit 31
                reg[v & 0x7FFFFFFF] = f"{nm}.{k}"
    lab = {}
    for q in range(c.num_qubits):
        if q in reg:
            lab[q] = reg[q]
        elif NBASE <= q < NBASE + logm:
            lab[q] = f"nA.{q - NBASE}"
        elif q < NBASE:
            lab[q] = f"A{q // DEG}.{q % DEG}"
        else:
            lab[q] = f"anc{q}"
    return lab


# ---------------------------------------------------------------- builders
def build(loop, is_adjoint=False, logm=LOGM):
    """Preamble (+ optional _initial_shift_loop).  Nothing is freed: not needed."""
    b = km.CircuitBuilder()
    synds = [b.create_quantum_register(DEG, name=f"S{i}") for i in range(N_SYN)]
    reg_a = [b.alloc_qubits(DEG) for _ in range(3)] + synds
    n_A = b.alloc_qubits(logm)
    init_ones = km.array([reg_a[0][0], n_A[0]])
    b.x(init_ones)
    b.gf2_iadd(N_SYN, target=n_A)
    if loop:
        with b.mark("initial_shift"):
            dec._initial_shift_loop(b, reg_a, n_A, is_adjoint=is_adjoint)
    circ = b.finish_circuit()
    nm = ("adj" if is_adjoint else "fwd") if loop else "pre"
    p = WORK / f"shift_{nm}{'' if logm == LOGM else f'_logm{logm}'}.kmb"
    circ.to_file(str(p), format="kmb")
    say("built", p.name, "qubits", circ.num_qubits, "stats", dict(circ.operation_statistics()))
    return p


def step_regions(c):
    tags = c.tags()

    def tn(text):
        if text.startswith("@enter:"):
            return "enter", text[7:]
        if text.startswith("@exit:"):
            return "exit", text[6:]
        return None, text

    regs = []
    ent, ext = [], []
    for i, s in tags:
        kind, nm = tn(s)
        if nm != "shift_step":
            continue
        (ent if kind == "enter" else ext if kind == "exit" else []).append(i)
    regs = [(a + 1, b) for a, b in zip(ent, ext)]
    outer = None
    ent_o = [i for i, s in tags if tn(s) == ("enter", "initial_shift")]
    exit_o = [i for i, s in tags if tn(s) == ("exit", "initial_shift")]
    if ent_o and exit_o:
        outer = (ent_o[0] + 1, exit_o[-1])
    return regs, outer, [s for _, s in tags][:6]


def analyse(p, lab=None, is_adjoint=False):
    c = ir.Circuit.read(str(p))
    regs, outer, tag_head = step_regions(c)
    t = np.asarray(c.types)
    b3 = t & 0x7F
    res = {"num_ops_with_tags": int(c.num_ops), "num_qubits": int(c.num_qubits),
           "n_shift_steps": len(regs), "tag_head": tag_head, "is_adjoint": bool(is_adjoint)}
    res.update(physics_counts(c))
    res["CCX"] = int((b3 == 0x31).sum())
    res["CSWAP"] = int((b3 == 0x32).sum())
    res["CX"] = int((b3 == 0x21).sum())
    res["SWAP"] = int((b3 == 0x22).sum())
    res["CCZ"] = int((b3 == 0x30).sum())
    res["HMR"] = int((b3 == 0x50).sum())
    # T if every CSWAP is expanded into CX+CCX+CX, as the tape does
    res["tape_idiom_T"] = int(res["CCX"] + res["CSWAP"] + res["CCZ"])
    res["tape_idiom_CX"] = int(res["CX"] + 2 * res["CSWAP"])
    steps = []
    from collections import Counter
    for k, (a, b) in enumerate(regs):
        d = physics_counts(c, a, b)
        ops = c.decode(a, b)
        first = next((o for o in ops if o[1] != "INFO_TAG"), None)
        first_cs = next((o for o in ops if o[1].startswith("CSWAP")), None)
        # the loop's own `step` value: 0..n-2 forward, n-2..0 adjoint
        s = (N_SYN - 2 - k) if is_adjoint else k
        lane = M - (3 + s)
        fl = lambda o: ([o[1], [lab[int(x)] for x in o[2]]] if (lab is not None)
                        else [o[1], list(map(int, o[2]))])
        steps.append({"index": k, "step": s, "lane_len": lane, "ops": d["ops"],
                      "ops_with_tags": d["ops_with_tags"],
                      "CCX": d.get("CCX", 0), "CSWAP": d.get("CSWAP", 0),
                      "CX": d.get("CX", 0), "SWAP": d.get("SWAP", 0),
                      "HMR": d.get("HMR", 0), "CCZ": d.get("CCZ", 0),
                      "exp_cswap": DEG * (lane - 1),
                      "first_op": fl(first) if first else None,
                      "first_cswap": fl(first_cs) if first_cs else None,
                      "census": {kk: vv for kk, vv in d.items()
                                 if kk not in ("ops", "ops_with_tags", "toffoli_like")}})
        cw = [(int(o[2][1]), int(o[2][2])) for o in ops if o[1].startswith("CSWAP")]
        steps[-1]["cswap_per_bit"] = dict(sorted(Counter(x % DEG for x, _ in cw).items()))
        steps[-1]["cswap_words_span"] = ([min(min(x, y) for x, y in cw) // DEG,
                                          max(max(x, y) for x, y in cw) // DEG] if cw else None)
    for k in (0, 1, len(steps) - 1):
        a, b = regs[k]
        order = [lab[int(x)] for o in c.decode(a, b) if o[1].startswith("CSWAP") for x in o[2]]
        steps[k]["cswap_order_head"] = [order[i:i + 3] for i in range(0, min(len(order), 45), 3)]
    res["steps"] = steps
    loop = physics_counts(c, outer[0], outer[1]) if outer else None
    if loop is not None:
        loop["ops_with_tags"] = int(outer[1] - outer[0])
        loop["CCX"] = int(loop.get("CCX", 0))
        loop["CSWAP"] = int(loop.get("CSWAP", 0))
        loop["CX"] = int(loop.get("CX", 0))
        loop["HMR"] = int(loop.get("HMR", 0))
        loop["tape_idiom_T"] = loop["CCX"] + loop["CSWAP"] + int(loop.get("CCZ", 0))
        # if the loop's CSWAPs were expanded into CX+CCX+CX, as the tape does
        loop["ops_if_cswap_expanded"] = loop["ops"] + 2 * loop["CSWAP"]
    res["loop"] = loop
    res["steps_consistent"] = bool(
        loop is not None
        and sum(s["CSWAP"] for s in steps) == res["CSWAP"]
        and sum(s["CCX"] for s in steps) == loop["CCX"]
        and sum(s["ops"] for s in steps) == loop["ops"]
        # each step's region excludes its own @enter/@exit pair: +2 per step
        and sum(s["ops_with_tags"] for s in steps) + 2 * len(steps) == loop["ops_with_tags"]
        and all(s["CSWAP"] == s["exp_cswap"] for s in steps))
    return c, res


paths = {"pre": build(False), "fwd": build(True, False), "adj": build(True, True),
         "fwd_logm7": build(True, False, logm=7)}
cpre = ir.Circuit.read(str(paths["pre"]))
cfwd_tmp = ir.Circuit.read(str(paths["fwd"]))
lab = label_map(cfwd_tmp, LOGM)
del cfwd_tmp
cfwd, rfwd = analyse(paths["fwd"], lab, is_adjoint=False)
cadj, radj = analyse(paths["adj"], lab, is_adjoint=True)
c7, r7 = analyse(paths["fwd_logm7"], lab, is_adjoint=False)

npre = cpre.num_ops
OUT["preamble"] = physics_counts(cpre)
OUT["preamble"]["num_ops_with_tags"] = npre
OUT["prefix_ok"] = {
    "fwd": bool(np.array_equal(np.asarray(cfwd.types[:npre]), np.asarray(cpre.types))),
    "adj": bool(np.array_equal(np.asarray(cadj.types[:npre]), np.asarray(cpre.types))),
}
OUT["labels"] = {q: lab[q] for q in sorted({int(x) for op in head_symbols(cfwd, 3000)["ops"]
                                            for x in op[2:] if x >= 0})}
OUT["labels_note"] = ("A<w>.<b> = 12-bit scratch word w of reg_a (w<3); S<k>.<b> = syndrome register k; "
                      "nA.<b> = n_A bit; anc* = the per-step ctrl ancilla")

OUT["forward"] = rfwd
OUT["adjoint"] = radj
OUT["forward_logm7"] = {k: v for k, v in r7.items() if k != "steps"}
OUT["forward"]["head_ops_3000"] = head_symbols(cfwd, 3000)
OUT["adjoint"]["head_ops_3000"] = head_symbols(cadj, 3000)
for nm, r in (("fwd", rfwd), ("adj", radj), ("fwd_logm7", r7)):
    say(nm, json.dumps({k: v for k, v in r.items() if k not in ("steps", "loop", "head_ops_3000")}))
    say(nm, "loop", json.dumps(r["loop"]))
say("step0", json.dumps(rfwd["steps"][0]))
say("step1", json.dumps(rfwd["steps"][1]))
say("step68", json.dumps(rfwd["steps"][-1]))
say("adj step0", json.dumps(radj["steps"][0]))
say("adj step68", json.dumps(radj["steps"][-1]))
say("steps_consistent", rfwd["steps_consistent"], radj["steps_consistent"])
print("STEP TABLE fwd: step lane ops ops_tags CSWAP CCX CX HMR first_cswap", flush=True)
for s in rfwd["steps"]:
    print(f"  {s['step']:2d} {s['lane_len']:3d} {s['ops']:5d} {s['ops_with_tags']:5d} "
          f"{s['CSWAP']:5d} {s['CCX']:4d} {s['CX']:3d} {s['HMR']:3d} "
          f"{s['first_cswap'][1] if s['first_cswap'] else None}", flush=True)

# ---------------------------------------------------------------- tape
raw = pathlib.Path("/tmp/dqi_575b043f.kmb")
if raw.exists():
    raw.unlink()
with lzma.open(XZ, "rb") as fi, open(raw, "wb") as fo:
    while True:
        chunk = fi.read(1 << 23)
        if not chunk:
            break
        fo.write(chunk)
say("decompressed", raw.stat().st_size)

tc = ir.Circuit.read(str(raw))
NOW = tc.num_ops
regnames = [nm for nm, _ in tc.registers]
OUT["tape"] = {"num_ops": int(NOW), "num_qubits": int(tc.num_qubits),
               "static_toffoli": int(tc.toffoli_like()), "sha256": tc.sha256(),
               "n_registers": len(regnames),
               "registers_head": regnames[:4], "registers_tail": regnames[-4:],
               "n_syndrome_regs": sum(1 for nm in regnames if nm.startswith("S") and nm[1:].isdigit())}
say("tape read", OUT["tape"]["num_qubits"], NOW, OUT["tape"]["static_toffoli"], OUT["tape"]["n_registers"])

TT = np.asarray(tc.types)
cfun2 = np.zeros(NOW + 1, np.int32)
cfun2[1:] = np.cumsum(ir.L2Q[TT])
cfun3 = np.zeros(NOW + 1, np.int32)
cfun3[1:] = np.cumsum(ir.L3Q[TT])
CCX_ALL = np.flatnonzero(ir.L3Q[TT] & ((TT & 0x7F) == 0x31))
say("tape ccx", len(CCX_ALL))


def cswap_idiom(lo, hi):
    """CCX(c, t1, t2) whose two neighbours are CX on the same pair {t1, t2}: a Fredkin
    expanded as CX+CCX+CX.  Returns the triple count and the shared-control census."""
    ccx = CCX_ALL[(CCX_ALL >= lo) & (CCX_ALL < hi)]
    ccx = ccx[(ccx > lo) & (ccx + 1 < hi)]
    if not len(ccx):
        return {"triples": 0, "sandwich_any": 0}
    k3 = cfun3[ccx + 1] - 1
    c1 = tc.qqq0[k3].astype(np.int64)
    c2 = tc.qqq1[k3].astype(np.int64)
    tg = tc.qqq2[k3].astype(np.int64)
    pc = (TT[ccx - 1] & 0x7F) == 0x21
    nc = (TT[ccx + 1] & 0x7F) == 0x21
    kp = cfun2[ccx] - 1
    kn = cfun2[ccx + 2] - 1
    a1 = tc.qq0[kp].astype(np.int64); b1 = tc.qq1[kp].astype(np.int64)
    a2 = tc.qq0[kn].astype(np.int64); b2 = tc.qq1[kn].astype(np.int64)
    sandwich = pc & nc
    pair_ok = (a1 == a2) & (b1 == b2) & (((a1 == c2) & (b1 == tg)) | ((a1 == tg) & (b1 == c2)))
    ok = sandwich & pair_ok
    d = {"triples": int(ok.sum()), "sandwich_any": int(sandwich.sum()),
         "adjacent_words": int((np.abs(c2[ok] // 12 - tg[ok] // 12) == 1).sum()) if ok.sum() else 0}
    if ok.sum():
        uq, uc = np.unique(c1[ok], return_counts=True)
        d["shared_ctrl"] = {"distinct": int(len(uq)), "max_per_ctrl": int(uc.max()),
                            "median": float(np.median(uc))}
    return d


def tape_window(lo, hi, head, nsym):
    d = {"lo": lo, "hi": hi, "width": hi - lo}
    d.update(physics_counts(tc, lo, hi))
    d["CCX"] = int(d.get("CCX", 0))
    d["idiom"] = cswap_idiom(lo, hi)
    hd = {"lo": lo, "hi": min(hi, lo + head)}
    hd.update(physics_counts(tc, lo, hd["hi"]))
    hd["idiom"] = cswap_idiom(lo, hd["hi"])
    hd["symbols"] = head_symbols(tc, nsym, lo, hd["hi"])
    d["head"] = hd
    return d


OUT["tape"]["forward_cluster"] = tape_window(19_508_954, 21_385_877, 20000, 300)
OUT["tape"]["reverse_cluster"] = tape_window(46_230_185, 52_842_219, 20000, 300)
for k in ("forward_cluster", "reverse_cluster"):
    v = OUT["tape"][k]
    say(k, json.dumps({kk: vv for kk, vv in v.items() if kk != "head"}))
    say(k, "head", json.dumps({kk: vv for kk, vv in v["head"].items() if kk != "symbols"}))

# ---------------------------------------------------------------- comparison + barrel bound
fw = OUT["forward"]
fl = fw["loop"]
FC = OUT["tape"]["forward_cluster"]
RC = OUT["tape"]["reverse_cluster"]
OUT["comparison"] = {
    "ref_loop_T": fl["tape_idiom_T"],
    "ref_loop_CCX": fl["CCX"], "ref_loop_CSWAP": fl["CSWAP"],
    "ref_loop_CX_native": fl["CX"], "ref_loop_CX_if_cswap_expanded": 2 * fl["CSWAP"] + fl["CX"],
    "ref_loop_ops": fl["ops"],
    "ref_loop_ops_if_cswap_expanded": fl["ops_if_cswap_expanded"],
    "ref_loop_ops_with_tags": fl["ops_with_tags"],
    "ref_steps": fw["n_shift_steps"],
    "tape_fwd_CCX": FC.get("CCX", 0), "tape_fwd_toffoli_like": FC.get("toffoli_like", 0),
    "tape_fwd_CX": FC.get("CX", 0), "tape_fwd_SWAP": FC.get("SWAP", 0),
    "tape_fwd_width": FC["width"],
    "dT_ref_minus_29543": int(fl["tape_idiom_T"] - 29543),
    "T_ratio_tape_over_ref": round(29543 / fl["tape_idiom_T"], 3),
    "cswap_cx_needed": 2 * fl["CSWAP"],
    "cx_ratio_tape_over_needed": round(FC.get("CX", 0) / max(1, 2 * fl["CSWAP"]), 2),
    "ops_ratio_tape_over_ref_expanded": round(FC["width"] / max(1, fl["ops_if_cswap_expanded"]), 2),
    "tape_cswap_idiom_triples_fwd": FC["idiom"]["triples"],
    "tape_cswap_idiom_triples_rev": RC["idiom"]["triples"],
}

W, NW = DEG, N_SYN
stages = (NW - 1).bit_length()               # ceil(log2(70)) = 7
zero_test = (W - 1) * NW                     # 70 words x 11 CCX
enc = NW * stages                            # unary -> 7-bit index, upper bound
subc = 2 * (LOGM + stages)                   # n_A -= k, deliberately loose
barrel = {"words": NW, "bits": W, "shift_max": NW - 1, "stages": stages,
          "cswap_per_stage": NW * W, "cswap_total": stages * NW * W,
          "zero_test_ccx": zero_test, "zero_test_uncompute_ccx": zero_test,
          "priority_encoder_ccx": enc, "nA_sub_ccx": subc}
barrel["T_total"] = barrel["cswap_total"] + 2 * zero_test + enc + subc
barrel["ops_total"] = 3 * barrel["cswap_total"] + 2 * zero_test + 2 * enc + 2 * subc
barrel["saving_vs_tape_fwd"] = 29543 - barrel["T_total"]
barrel["saving_pct"] = round(100.0 * barrel["saving_vs_tape_fwd"] / 29543.0, 1)
barrel["saving_vs_ref"] = fl["tape_idiom_T"] - barrel["T_total"]
OUT["barrel_shift_bound"] = barrel
OUT["barrel_note"] = ("upper bound: 7 barrel levels x 70x12 CSWAP (1 CCX each, tape idiom), "
                      "70 12-bit zero-tests computed and uncomputed, 70x7 priority-encoder CCX, "
                      "and a loose 2*(8+7) CCX for n_A -= k")

say("barrel", json.dumps(barrel))
say("comparison", json.dumps(OUT["comparison"]))

OUT["seconds"] = round(time.time() - T0, 1)
(WORK / "reference_shift.json").write_text(json.dumps(OUT, indent=1))
say("wrote reference_shift.json", (WORK / "reference_shift.json").stat().st_size)

# ---------------------------------------------------------------- cleanup
for p in list(paths.values()):
    p.unlink(missing_ok=True)
raw.unlink(missing_ok=True)
(WORK / "dqi_reference_circuit.py").unlink(missing_ok=True)
shutil.rmtree(WORK / "__pycache__", ignore_errors=True)
say("files left", sorted(p.name for p in WORK.iterdir()))
print("RESULT_JSON_BEGIN", flush=True)
print(json.dumps({k: v for k, v in OUT.items() if k not in ("forward", "adjoint", "tape", "labels")},
                 indent=1), flush=True)
print("RESULT_JSON_END", flush=True)
