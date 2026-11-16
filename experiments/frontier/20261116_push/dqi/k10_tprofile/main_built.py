"""Exact Toffoli budget of the v12 889Q build, by stage and by call site.

The builder is a C type with no live operation_statistics(), so it is wrapped in a counting
proxy (the same technique the earlier Q=888 probe used for alloc_qubits). Counts are exact.
"""
import hashlib, json, os, pathlib, shutil, sys, time, importlib

t0 = time.time()
def log(*a):
    print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)

ROOT = pathlib.Path("/kaggle/input")
WORK = pathlib.Path("/kaggle/working")
TMP = pathlib.Path("/tmp/prof"); TMP.mkdir(parents=True, exist_ok=True)
REPORT = []
def say(*a):
    s = " ".join(str(x) for x in a)
    REPORT.append(s); print(s, flush=True)

tree = sorted(ROOT.rglob("build.sh"))[0].parent
SRC = TMP / "src"
if SRC.exists():
    shutil.rmtree(SRC)
shutil.copytree(tree, SRC)
ENGINE = sorted(ROOT.rglob("kickmix.so"))[0].parent
VERIF = sorted(ROOT.rglob("verify_submission_dqi.py"))[0].parent.parent
for rel, srcp in (("pro1_controller_bundle/1_task/official/kickmix.so", ENGINE / "kickmix.so"),
                  ("pro1_controller_bundle/1_task/verifiers/dqi/verify_submission_dqi.py",
                   VERIF / "dqi" / "verify_submission_dqi.py")):
    dst = SRC / "src" / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists():
        shutil.copyfile(srcp, dst)
ROOTDIR = TMP / "root"
if ROOTDIR.exists():
    shutil.rmtree(ROOTDIR)
shutil.copytree(SRC / "src", ROOTDIR)
CW = ROOTDIR / "controller_work"
for p in sorted(CW.rglob("*")):
    if p.is_dir():
        sys.path.insert(0, str(p))
sys.path.insert(0, str(ROOTDIR / "pro1_controller_bundle" / "1_task" / "official"))

import kickmix as km
import v7_pipeline as Pipeline
Pipeline.configure()
say("configured")

class Counted:
    """Forwarding proxy that counts Toffoli-like gate emissions."""
    __slots__ = ("_b", "_n")
    def __init__(self, b):
        object.__setattr__(self, "_b", b)
        object.__setattr__(self, "_n", 0)
    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, "_b"), name)
    @property
    def tof(self):
        return object.__getattribute__(self, "_n")
    def ccx(self, *a, **k):
        object.__setattr__(self, "_n", object.__getattribute__(self, "_n") + 1)
        return object.__getattribute__(self, "_b").ccx(*a, **k)
    def ccz(self, *a, **k):
        object.__setattr__(self, "_n", object.__getattribute__(self, "_n") + 1)
        return object.__getattribute__(self, "_b").ccz(*a, **k)
    def cswap(self, *a, **k):
        object.__setattr__(self, "_n", object.__getattribute__(self, "_n") + 1)
        return object.__getattribute__(self, "_b").cswap(*a, **k)

CANDS = {
    "direct_carry_arithmetic": ["divide_deferred", "restore_with_shared_norm", "emit_prefix",
                                "emit_closing", "_adjoint_consume", "_consume_halves", "_inverse_norm",
                                "_quotient_phase_with_norm"],
    "raw_query_extractor": ["query_step"],
    "gf24_arithmetic": ["product", "xor_product", "phase_product"],
    "tower_inverse": ["xor_product", "phase_product", "init_norm", "erase_norm"],
    "fused_crt_synthesis": ["emit_prefix", "emit_closing"],
    "additive_fft_phase_scan": ["emit"],
    "projective_finish": ["emit_prefix", "emit_closing"],
    "gauge_park_outer": ["emit_prefix", "emit_closing"],
    "local_flag_window": ["emit_prefix", "emit_closing"],
    "third_pivot_chart": ["emit_prefix", "emit_closing"],
    "inverse_retained_norm_deferred": ["inverse_prefix_with_bank", "inverse_return_with_bank"],
    "gf24_nested_norm": ["emit_prefix", "emit_closing", "product"],
    "window_tensor_shared": ["xor_product", "product"],
    "window_transpose_shared": ["xor_product"],
    "mask_gauge_blocked": ["open_gauge"],
    "scalar_seed_padded": ["emit_prefix", "close_padded", "finish_after_swap"],
    "direct_carry_extractor": ["emit_prefix", "emit_closing"],
}
STATS = {}
def tof(b):
    return b.tof if isinstance(b, Counted) else 0

def wrap(mod_name, fn_name, fn):
    key = f"{mod_name}.{fn_name}"
    def inner(*a, **k):
        b = a[0] if a else None
        if not isinstance(b, Counted):
            return fn(*a, **k)
        before = b.tof
        r = fn(*a, **k)
        st = STATS.setdefault(key, dict(n=0, t=0))
        st["n"] += 1; st["t"] += b.tof - before
        return r
    inner.__name__ = fn_name
    return inner

patched = []
for mod_name, fns in CANDS.items():
    try:
        m = importlib.import_module(mod_name)
    except Exception:
        continue
    for f in fns:
        if hasattr(m, f) and callable(getattr(m, f)):
            setattr(m, f, wrap(mod_name, f, getattr(m, f)))
            patched.append(f"{mod_name}.{f}")
say("patched", len(patched))

STAGE = []
def stage(message):
    b = CUR[0]
    STAGE.append(dict(stage=str(message)[:80], tof=b.tof, q=b.num_allocated_qubits))

CUR = [None]
real = km.CircuitBuilder()
builder = Counted(real)
CUR[0] = builder
builder.set_max_qubits(889)
S = [builder.create_quantum_register(12, f"S{i}") for i in range(70)]
E = [builder.create_classical_register(12, f"E{i}") for i in range(4095)]
t = time.time()
contract = Pipeline.emit(builder, S, E, j_min=15, scan_positions=4095, stage=stage)
say(f"emit {time.time()-t:.0f}s")
TOT = builder.tof
circ = real.finish_circuit()
say("TOTAL counted", TOT, "official", int(circ.operation_statistics().num_toffoli_like),
    "Q", circ.num_qubits)

rows = []
prev = 0
for r in STAGE:
    rows.append((r["stage"], r["tof"] - prev))
    prev = r["tof"]
rows.append(("TAIL", TOT - prev))
agg = {}
for k, d in rows:
    for pat in ("raw_query_prefix_", "synthesis_prefix", "synthesis_return", "raw_query_return_"):
        if k.startswith(pat):
            k = pat + "*"
    agg[k] = agg.get(k, 0) + d
say("STAGE BUDGET")
for k, v in sorted(agg.items(), key=lambda kv: -kv[1]):
    if v:
        say(f"  {k:40s} {v:8d} {100.0*v/TOT:5.2f}%")

say("CALL SITE BUDGET (inclusive; nesting means children sum can exceed the parent)")
for k, v in sorted(STATS.items(), key=lambda kv: -kv[1]["t"]):
    if v["t"]:
        say(f"  {k:46s} n={v['n']:6d} T={v['t']:8d} {100.0*v['t']/TOT:5.2f}% "
            f"T/call={v['t']/max(1,v['n']):7.1f}")

(WORK / "report.txt").write_text("\n".join(REPORT))
say("done")
