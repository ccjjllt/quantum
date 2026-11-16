"""Exact static-T partition of the v12 889Q build, per pipeline stage.

Corrected emission rule (calibrated in k11b, reproduced exactly here):

  builder.ccx(c1,c2,t)          -> CCX      : always emitted, broadcast length
  builder.ccz(c1,c2,t)          -> CCZ      : only if c1 is a QUBIT; a classical
                                              bit control folds to `CZ ... if b` (0 T)
  builder.init_and(c1,c2,t)     -> R + CCX  : only if both controls are QUBITS;
                                              a constant/classical control folds
                                              to R + CX / R + X (0 T)
  builder.del_and(c1,c2,t)      -> HMR + `CZ if b` (0 T)   <-- measurement-based
  builder.cswap(c1,c2,t)        -> CSWAP    : only if c1 is a QUBIT; a classical
                                              control folds to a plain SWAP (0 T)

The assertion below requires the partition total to equal the finished
circuit's CCX+CCZ+CSWAP exactly, so every stage share is exact.
"""
import hashlib, json, pathlib, shutil, sys, time, collections

t0 = time.time()
def log(*a):
    print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)

ROOT = pathlib.Path("/kaggle/input")
WORK = pathlib.Path("/kaggle/working")
TMP = pathlib.Path("/tmp/k13"); TMP.mkdir(parents=True, exist_ok=True)
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


def _n(*args):
    n = 1
    for a in args:
        try:
            n = max(n, len(a))
        except TypeError:
            pass
    return n


def _elem(a):
    """'const' / 'bit' / 'qubit' for the first element of a (possibly array) arg."""
    if isinstance(a, bool) or isinstance(a, int):
        return "const"
    try:
        a = a[0]
    except TypeError:
        pass
    if isinstance(a, km.b):
        return "bit"
    return "qubit"


CLS = collections.Counter()
Real = km.CircuitBuilder


class Counting(Real):
    def ccx(self, *a, **k):
        CLS["ccx"] += _n(*a)
        return super().ccx(*a, **k)
    def ccz(self, *a, **k):
        if _elem(a[0]) == "qubit":
            CLS["ccz"] += _n(*a)
        return super().ccz(*a, **k)
    def cswap(self, *a, **k):
        if _elem(a[0]) == "qubit":
            CLS["cswap"] += _n(*a)
        return super().cswap(*a, **k)
    def init_and(self, *a, **k):
        if _elem(a[0]) == "qubit" and _elem(a[1]) == "qubit":
            CLS["init_and"] += _n(*a)
        return super().init_and(*a, **k)
    def del_and(self, *a, **k):
        CLS["del_and_folded"] += _n(*a)
        return super().del_and(*a, **k)


km.CircuitBuilder = Counting
say("counter installed")

def total():
    return sum(CLS.values())

STAGE = []
builder = km.CircuitBuilder()
builder.set_max_qubits(889)
S = [builder.create_quantum_register(12, f"S{i}") for i in range(70)]
E = [builder.create_classical_register(12, f"E{i}") for i in range(4095)]

def stage(message):
    msg = message if isinstance(message, str) else json.dumps(message, sort_keys=True)
    STAGE.append(dict(stage=msg, cum=total(), Q=builder.num_allocated_qubits))

t = time.time()
contract = Pipeline.emit(builder, S, E, j_min=15, scan_positions=4095, stage=stage)
say(f"emit {time.time()-t:.0f}s")
TOT = total()
circuit = builder.finish_circuit()
stats = dict(circuit.operation_statistics())
OFF = int(stats.get("CCX", 0)) + int(stats.get("CCZ", 0)) + int(stats.get("CSWAP", 0))
say("TOTAL", TOT, "official", OFF, "MATCH" if TOT == OFF else "MISMATCH")
say("components", json.dumps(dict(CLS)))
say("opcodes", json.dumps({k: v for k, v in sorted(stats.items())}, default=str))
assert TOT == OFF == 384003, (TOT, OFF)
out = WORK / "dqi.kmb"
circuit.to_file(out, format="kmb")
say("SHA", hashlib.sha256(out.read_bytes()).hexdigest(),
    "(expect 7cbe8ecf6f6e9743529b574f019504bb1712ce06fbb570c719ce9d9e2c914cd9)")
STAGE.append(dict(stage="TAIL", cum=total(), Q=builder.num_allocated_qubits))

def group(name):
    for pat in ("raw_query_prefix_", "raw_query_return_"):
        if name.startswith(pat) and name[-2:].isdigit():
            return pat + "NN"
    if name.startswith("synthesis_prefix"):
        return "synthesis_prefix_{33..00}"
    if name.startswith("synthesis_return"):
        return "synthesis_return_{00..33}"
    if name.startswith("adaptive64_scan"):
        return "adaptive64_scan(all)"
    return name

prev, rows = 0, []
for r in STAGE:
    rows.append((r["stage"], r["cum"] - prev, r["cum"], r["Q"]))
    prev = r["cum"]
say("")
say("EXACT STAGE PARTITION")
for name, d, cum, q in rows:
    if d or True:
        say(f"  {name:56s} {d:8d} {100.0*d/TOT:6.2f}% cum {cum:8d} Q {q}")
agg = {}
order = []
for name, d, cum, q in rows:
    g = group(name)
    if g not in agg:
        order.append(g)
    agg[g] = agg.get(g, 0) + d
say("")
say("EXACT STAGE GROUPS (emission order)")
for g in order:
    v = agg[g]
    if v:
        say(f"  {g:56s} {v:8d} {100.0*v/TOT:6.2f}%")
say("")
say("sum of groups", sum(agg.values()), "== total", TOT)
(WORK / "report.txt").write_text("\n".join(REPORT))
(WORK / "rows.json").write_text(json.dumps(rows))
say("done")
