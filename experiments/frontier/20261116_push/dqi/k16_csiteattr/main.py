"""CSWAP-by-callsite attribution + large-alloc Q census on the v12 889Q build.

Same exact counting rule as k14 (proved: TOTAL == official 384003 and sha
7cbe8ecf... MATCH), plus two new instruments:

  S1 CSWAP/CCZ/init_and call-site attribution: for every such builder call,
     the outermost `controller_work` Python frame is recorded, so the 12,384
     qubit-controlled CSWAPs are partitioned by source site (route / swap_low
     / exchange / virtual / transpose / tail / lender ...). This shows whether
     the 3.22 % CSWAP block sits at one elidable site or is spread across the
     load-bearing routing of the algorithm.
  S2 large-alloc Q census: every builder.alloc_qubits(count >= 12) records
     (count, Q_before, site). Reports max(Q_before + count), the sites that
     reach it, and how many 24-bit allocs land at Q_before >= 865 (i.e. hit
     the 889 peak). This is the per-site live-set census for the out-of-place
     division question: a dead 24-bit word at any divide site would show up
     here as a 24-bit alloc with Q_before < 865.

No candidate is built and nothing is verified: this kernel only measures.
"""
import hashlib, json, pathlib, shutil, sys, time, collections, traceback, os

t0 = time.time()
def log(*a):
    print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)

ROOT = pathlib.Path("/kaggle/input")
WORK = pathlib.Path("/kaggle/working")
TMP = pathlib.Path("/tmp/k16"); TMP.mkdir(parents=True, exist_ok=True)
REPORT = []
def say(*a):
    s = " ".join(str(x) for x in a)
    REPORT.append(s); print(s, flush=True)

_HERE = os.path.basename(__file__)
def _site():
    """Outermost controller_work Python frame above this file (call-site)."""
    best = "unknown"
    for fr in traceback.extract_stack():
        fn = fr.filename or ""
        if fn.endswith(_HERE):
            continue
        if "controller_work" in fn:
            best = f"{os.path.basename(fn)}:{fr.lineno} {fr.name}"
    return best

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
    """Resolve one argument down to 'const' / 'bit' / 'qubit'."""
    for _ in range(4):
        if isinstance(a, bool) or isinstance(a, int):
            return "const"
        if isinstance(a, km.q):
            return "qubit"
        if isinstance(a, km.b):
            return "bit"
        try:
            a = a[0]
        except Exception:
            return "other"
    return "other"


CLS = collections.Counter()
SITE = collections.Counter()
ALLOC = []   # (count, Q_before, site) for count >= 12
PEAKQ = [0]
Real = km.CircuitBuilder


class Counting(Real):
    def ccx(self, *a, **k):
        if _elem(a[0]) == "qubit" and _elem(a[1]) == "qubit":
            CLS["ccx"] += _n(*a)
        else:
            CLS["ccx_folded"] += _n(*a)
        return super().ccx(*a, **k)
    def ccz(self, *a, **k):
        n = _n(*a)
        if _elem(a[0]) == "qubit" and _elem(a[1]) == "qubit":
            CLS["ccz"] += n
            SITE[("ccz", _site())] += n
        else:
            CLS["ccz_folded"] += n
        return super().ccz(*a, **k)
    def cswap(self, *a, **k):
        n = _n(*a)
        if _elem(a[0]) == "qubit":
            CLS["cswap"] += n
            SITE[("cswap", _site())] += n
        else:
            CLS["cswap_folded"] += n
            SITE[("cswap_folded", _site())] += n
        return super().cswap(*a, **k)
    def init_and(self, *a, **k):
        n = _n(*a)
        if _elem(a[0]) == "qubit" and _elem(a[1]) == "qubit":
            CLS["init_and"] += n
            SITE[("init_and", _site())] += n
        else:
            CLS["init_and_folded"] += n
        return super().init_and(*a, **k)
    def del_and(self, *a, **k):
        CLS["del_and_folded"] += _n(*a)
        return super().del_and(*a, **k)
    def alloc_qubits(self, count):
        try:
            q0 = int(self.num_allocated_qubits)
        except Exception:
            q0 = -1
        out = super().alloc_qubits(count)
        try:
            c = int(count)
        except Exception:
            c = -1
        if c >= 12 and q0 >= 0:
            ALLOC.append((c, q0, _site()))
            if q0 + c > PEAKQ[0]:
                PEAKQ[0] = q0 + c
        return out


km.CircuitBuilder = Counting
say("counter installed")

def total():
    return sum(v for k, v in CLS.items() if not k.endswith("_folded"))

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
say("")
say("CSWAP/CCZ/INIT_AND BY CALL SITE (T units emitted)")
for (op, site), v in SITE.most_common():
    say(f"  {op:12s} {v:8d}  {site}")
say("")
say("cswap_folded total", CLS.get("cswap_folded", 0), "(classical-control swaps, 0 T)")
say("")
say("LARGE-ALLOC Q CENSUS (count >= 12): n =", len(ALLOC))
say("max(Q_before + count) =", PEAKQ[0])
big = [r for r in ALLOC if r[1] + r[0] >= 889]
say("allocs reaching Q >= 889:", len(big))
for c, q0, site in big[:40]:
    say(f"  alloc {c:3d} at Q_before {q0:4d} -> {q0 + c:4d}  {site}")
a24 = [q0 for c, q0, _ in ALLOC if c == 24]
if a24:
    import statistics
    say(f"24-bit allocs: n={len(a24)} min_Qb={min(a24)} max_Qb={max(a24)} "
        f"mean_Qb={statistics.mean(a24):.1f} n_at_Qb>=865={sum(1 for q in a24 if q >= 865)}")
(WORK / "report.txt").write_text("\n".join(REPORT))
(WORK / "rows.json").write_text(json.dumps(rows))
(WORK / "sites.json").write_text(json.dumps(
    {"sites": [[op, site, v] for (op, site), v in SITE.most_common()],
     "alloc": [[c, q0, site] for c, q0, site in ALLOC]}))
say("done")
