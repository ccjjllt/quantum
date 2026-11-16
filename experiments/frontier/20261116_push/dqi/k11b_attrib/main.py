"""Attribute the Toffoli-like emission count of the v12 build by call site.

k11 counted `max(len(arg))` per builder.ccx/ccz/cswap/init_and/del_and call and
got 946,043 against a finished-circuit num_toffoli_like of 384,003, so the
broadcast multiplicity is not `max(len(arg))` everywhere.  This run records, per
emitting call site (caller file:line), the number of calls, the summed bc, a
histogram of bc, and one sample of the argument shapes, plus the distinct
builder identities.  From that the true emission rule can be read off and the
stage partition fixed.
"""
import hashlib, json, pathlib, shutil, sys, time, collections

t0 = time.time()
def log(*a):
    print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)

ROOT = pathlib.Path("/kaggle/input")
WORK = pathlib.Path("/kaggle/working")
TMP = pathlib.Path("/tmp/attr"); TMP.mkdir(parents=True, exist_ok=True)
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

def _bc(*args):
    n = 1
    for a in args:
        try:
            n = max(n, len(a))
        except TypeError:
            pass
    return n

SITE = collections.defaultdict(lambda: dict(n=0, bc=0, hist=collections.Counter(), sample=""))
BUILDERS = collections.Counter()

def _note(kind, args, bc, fid, line):
    key = f"{pathlib.Path(fid).name}:{line}:{kind}"
    row = SITE[key]
    row["n"] += 1; row["bc"] += bc; row["hist"][bc] += 1
    if not row["sample"]:
        row["sample"] = " ".join(f"{type(a).__name__}[{_len(a)}]" for a in args)

def _len(a):
    try:
        return len(a)
    except TypeError:
        return 1

Real = km.CircuitBuilder
class Counting(Real):
    def _emit(self, kind, args, call):
        f = sys._getframe(2)
        _note(kind, args, _bc(*args), f.f_code.co_filename, f.f_lineno)
        BUILDERS[id(self)] += 1
        return call(*args)
    def ccx(self, *a, **k): return self._emit("ccx", a, super().ccx)
    def ccz(self, *a, **k): return self._emit("ccz", a, super().ccz)
    def cswap(self, *a, **k): return self._emit("cswap", a, super().cswap)
    def init_and(self, *a, **k): return self._emit("init_and", a, super().init_and)
    def del_and(self, *a, **k): return self._emit("del_and", a, super().del_and)
km.CircuitBuilder = Counting
say("counter installed")

STAGE = []
CNT = [0]
builder = km.CircuitBuilder()
builder.set_max_qubits(889)
S = [builder.create_quantum_register(12, f"S{i}") for i in range(70)]
E = [builder.create_classical_register(12, f"E{i}") for i in range(4095)]

def stage(message):
    msg = message if isinstance(message, str) else json.dumps(message, sort_keys=True)
    STAGE.append(dict(stage=msg, cum=sum(r["bc"] for r in SITE.values()), Q=builder.num_allocated_qubits))

t = time.time()
contract = Pipeline.emit(builder, S, E, j_min=15, scan_positions=4095, stage=stage)
say(f"emit {time.time()-t:.0f}s")
builder.finish_circuit().operation_statistics()
say("TOTAL bc", sum(r["bc"] for r in SITE.values()), "builder ids", len(BUILDERS),
    "top builder", BUILDERS.most_common(3))
say("")
say("CALL SITES by summed bc")
for k, v in sorted(SITE.items(), key=lambda kv: -kv[1]["bc"])[:40]:
    h = ",".join(f"{kk}x{vv}" for kk, vv in sorted(v["hist"].items())[:6])
    say(f"  {k:62s} n={v['n']:7d} bc={v['bc']:8d} bc-hist[{h}]  {v['sample'][:70]}")
say("")
say("CALL SITES by call count")
for k, v in sorted(SITE.items(), key=lambda kv: -kv[1]["n"])[:25]:
    say(f"  {k:62s} n={v['n']:8d} bc={v['bc']:9d} bc/call={v['bc']/v['n']:6.2f}")
(WORK / "report.txt").write_text("\n".join(REPORT))
(WORK / "sites.json").write_text(json.dumps({k: dict(n=v["n"], bc=v["bc"], hist=dict(v["hist"]), sample=v["sample"]) for k, v in SITE.items()}, indent=1))
say("done")
