"""Exact static-T budget of the v12 889Q build, per pipeline stage.

Why this exists: k10 (`zhuating/qcc-dqi-tprofile`) counted *calls* to
builder.ccx/ccz/cswap through a Python proxy.  `kickmix.CircuitBuilder.ccx`
BROADCASTS over km.array arguments, so one call can emit up to 24 Toffolis and
one call on three targets emits three.  Call counts are therefore not gate
counts, and the stage shares published from k10 are wrong.

Here the builder class itself is subclassed and every Toffoli-like emission is
counted with its true broadcast multiplicity (ccx, ccz, cswap, init_and,
del_and; verified to reproduce the finished circuit's num_toffoli_like
exactly).  Stage marks are single-counter samples, so consecutive differences
partition the total exactly.
"""
import hashlib, json, os, pathlib, shutil, sys, time

t0 = time.time()
def log(*a):
    print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)

ROOT = pathlib.Path("/kaggle/input")
WORK = pathlib.Path("/kaggle/working")
TMP = pathlib.Path("/tmp/stageT"); TMP.mkdir(parents=True, exist_ok=True)
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

# ---------------------------------------------------------------- exact counter
def _bc(*args):
    n = 1
    for a in args:
        try:
            n = max(n, len(a))
        except TypeError:
            pass
    return n

Real = km.CircuitBuilder
class Counting(Real):
    tof = 0
    def ccx(self, *a, **k):
        Counting.tof += _bc(*a)
        return super().ccx(*a, **k)
    def ccz(self, *a, **k):
        Counting.tof += _bc(*a)
        return super().ccz(*a, **k)
    def cswap(self, *a, **k):
        Counting.tof += _bc(*a)
        return super().cswap(*a, **k)
    def init_and(self, *a, **k):
        Counting.tof += _bc(*a)
        return super().init_and(*a, **k)
    def del_and(self, *a, **k):
        Counting.tof += _bc(*a)
        return super().del_and(*a, **k)
km.CircuitBuilder = Counting
say("counter installed")

# ------------------------------------------------- exact per-call-site totals
SITE = {}
def wrap(mod, attr, label):
    if not hasattr(mod, attr):
        say("MISSING", label); return
    orig = getattr(mod, attr)
    def inner(*a, **k):
        before = Counting.tof
        r = orig(*a, **k)
        row = SITE.setdefault(label, dict(n=0, t=0))
        row["n"] += 1; row["t"] += Counting.tof - before
        return r
    inner.__name__ = getattr(orig, "__name__", attr)
    setattr(mod, attr, inner)

First3 = Pipeline.First3
Retained = First3.Arithmetic          # last_return_retained_norm: the bound provider
Orig = Retained.Original              # direct_carry_arithmetic
First2 = First3.Base                  # direct_carry_first2 (re-exports query_step)
A24 = First3.A                        # gf24_nested_norm
say("modules", First3.__name__, Retained.__name__, Orig.__name__, First2.__name__, A24.__name__)
assert Retained.divide_deferred is Orig.divide_deferred
wrap(First2, "query_step", "query_step")
wrap(Retained, "divide_deferred", "divide_deferred (inclusive)")
wrap(Retained, "restore_with_shared_norm", "restore_with_shared_norm (inclusive)")
wrap(A24, "emit_prefix", "gf24 emit_prefix 24bit (99T)")
wrap(A24, "inverse_deferred", "gf24 inverse_deferred (195T)")

# ---------------------------------------------------------------- build
from v7_events import Events
events = Events()
events.install(Pipeline)

STAGE = []
builder = km.CircuitBuilder()
builder.set_max_qubits(889)
S = [builder.create_quantum_register(12, f"S{i}") for i in range(70)]
E = [builder.create_classical_register(12, f"E{i}") for i in range(4095)]

def stage(message):
    msg = message if isinstance(message, str) else json.dumps(message, sort_keys=True)
    STAGE.append(dict(stage=msg, cum=Counting.tof, Q=builder.num_allocated_qubits))

t = time.time()
contract = Pipeline.emit(builder, S, E, j_min=15, scan_positions=4095, stage=stage)
say(f"emit {time.time()-t:.0f}s")
TOT = Counting.tof
assert builder.num_allocated_qubits == 840, builder.num_allocated_qubits
circuit = builder.finish_circuit()
OFF = int(circuit.operation_statistics().num_toffoli_like)
say("TOTAL counted", TOT, "official", OFF, "MATCH" if TOT == OFF else "MISMATCH")
stats = dict(circuit.operation_statistics())
say("opcodes", json.dumps({k: v for k, v in sorted(stats.items())}, default=str))
assert TOT == OFF == 384003, (TOT, OFF)
say("Q", circuit.num_qubits, "bits", circuit.num_bits)
STAGE.append(dict(stage="TAIL_after_last_stage", cum=Counting.tof, Q=builder.num_allocated_qubits))

out = WORK / "dqi.kmb"
circuit.to_file(out, format="kmb")
sha = hashlib.sha256(out.read_bytes()).hexdigest()
say("SHA", sha, "MATCH" if sha == "7cbe8ecf6f6e9743529b574f019504bb1712ce06fbb570c719ce9d9e2c914cd9" else "MISMATCH")

# ---------------------------------------------------------------- report
say("")
say("STAGE PARTITION (consecutive single-counter differences; exact)")
prev, rows, prevq = 0, [], 844
for r in STAGE:
    rows.append((r["stage"], r["cum"] - prev, r["cum"], r["Q"]))
    prev = r["cum"]
for name, d, cum, q in rows:
    say(f"  {name:52s} {d:8d} {100.0*d/TOT:6.2f}%  cum {cum:8d}  Q {q}")

def group(name):
    for pat in ("raw_query_prefix_", "raw_query_return_"):
        if name.startswith(pat) and name[-2:].isdigit():
            return pat + "NN"
    if name.startswith("synthesis_prefix"):
        return "synthesis_prefix"
    if name.startswith("synthesis_return"):
        return "synthesis_return"
    return name

say("")
say("STAGE GROUPS")
agg = {}
for name, d, cum, q in rows:
    agg[group(name)] = agg.get(group(name), 0) + d
for k, v in sorted(agg.items(), key=lambda kv: -kv[1]):
    if v:
        say(f"  {k:52s} {v:8d} {100.0*v/TOT:6.2f}%")

say("")
say("CALL-SITE TOTALS (inclusive; exact broadcast-aware gate counts)")
for k, v in sorted(SITE.items(), key=lambda kv: -kv[1]["t"]):
    say(f"  {k:48s} n={v['n']:6d} T={v['t']:8d} {100.0*v['t']/TOT:6.2f}%T/call={v['t']/max(1,v['n']):7.1f}")

(WORK / "report.txt").write_text("\n".join(REPORT))
(WORK / "stage_rows.json").write_text(json.dumps(rows))
say("done")
