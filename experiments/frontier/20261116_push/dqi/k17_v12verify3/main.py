"""Reproduce the v12 889Q DQI source build (sha 7cbe8ecf...) and verify the
UNCHANGED official verifier at the default salt plus two extra salts.

Purpose: 3-salt baseline stability for the v12 line (no candidate is built
or verified in this task: k15/k16 measured zero sound deletions, so there is
nothing to package). Reports per-salt Q / mean-T / score / value+phase
errors, and the salt spread of the published 383,156.29 baseline.
"""
import hashlib, os, pathlib, shutil, subprocess, sys, zipfile, lzma, time

t0 = time.time()
def log(*a):
    print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)

ROOT = pathlib.Path("/kaggle/input")
WORK = pathlib.Path("/kaggle/working")
TMP = pathlib.Path("/tmp/build"); TMP.mkdir(parents=True, exist_ok=True)
PIN = "7cbe8ecf6f6e9743529b574f019504bb1712ce06fbb570c719ce9d9e2c914cd9"

# ---- locate the source tree (dataset may mount unpacked or as a zip)
tree = None
for cand in sorted(ROOT.rglob("build.sh")):
    if "qcc-dqi" in str(cand) or True:
        tree = cand.parent
        break
log("tree", tree)
zip_src = None
if tree is None:
    zs = [p for p in ROOT.rglob("*.zip") if "dqi" in p.name]
    log("zip candidates", zs)
    if zs:
        zip_src = zs[0]

SRC = TMP / "src"
if SRC.exists():
    shutil.rmtree(SRC)
if tree is not None:
    shutil.copytree(tree, SRC)
else:
    SRC.mkdir()
    with zipfile.ZipFile(zip_src) as z:
        z.extractall(SRC)
    b = list(SRC.rglob("build.sh"))
    if b:
        SRC = b[0].parent
log("build dir", SRC, "build.sh", (SRC / "build.sh").exists(),
    "src", (SRC / "src").is_dir())

ENGINE = sorted(ROOT.rglob("kickmix.so"))[0].parent
VERIF = sorted(ROOT.rglob("verify_submission_dqi.py"))[0].parent.parent
log("engine", ENGINE, "verifiers", VERIF)
OUT = TMP / "out"; OUT.mkdir(exist_ok=True)

for rel, srcp in (("pro1_controller_bundle/1_task/official/kickmix.so", ENGINE / "kickmix.so"),
                  ("pro1_controller_bundle/1_task/verifiers/dqi/verify_submission_dqi.py",
                   VERIF / "dqi" / "verify_submission_dqi.py")):
    dst = SRC / "src" / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists():
        shutil.copyfile(srcp, dst)
    log("host file", rel, dst.stat().st_size, hashlib.sha256(dst.read_bytes()).hexdigest()[:16])

env = dict(os.environ)
env["PY"] = "python3.13"
env["WORK"] = str(TMP / "work")
env["KEEP_WORK"] = "1"
t = time.time()
p = subprocess.run(["bash", "build.sh", str(ENGINE), str(VERIF), str(OUT)], cwd=str(SRC),
                   env=env, capture_output=True, text=True, timeout=7200)
log(f"build exited {p.returncode} in {time.time()-t:.0f}s")
print((p.stdout or "")[-5000:], flush=True)
print((p.stderr or "")[-5000:], flush=True)
kmb = OUT / "dqi.kmb"
if kmb.exists():
    h = hashlib.sha256(kmb.read_bytes()).hexdigest()
    log("BUILT", kmb.stat().st_size, h, "MATCH" if h == PIN else "MISMATCH")
else:
    log("NO OUTPUT")

try:
    import importlib.util
    sys.path.insert(0, str(ENGINE))
    if "kickmix" in sys.modules:
        del sys.modules["kickmix"]
    import kickmix as km
    sp = importlib.util.spec_from_file_location("vdqi", str(VERIF / "dqi" / "verify_submission_dqi.py"))
    V = importlib.util.module_from_spec(sp); sys.modules["vdqi"] = V; sp.loader.exec_module(V)
    spec = V.ProblemSpecDQI.benchmark_instance()
    circ = km.Circuit.from_file(str(kmb), format="kmb")
    BASE = 360733280431.94055
    for salt in ("", "dqi-salt-2", "dqi-salt-3"):
        t = time.time()
        res = V.verify(circ, spec, salt=salt)
        log(f"VERIFY salt={salt!r} {time.time()-t:.0f}s")
        log("VERIFY", {k: res[k] for k in ("status", "score", "num_qubits", "toffoli_count",
                                            "value_errors", "phase_errors", "circuit_sha256")})
        log(f"D academic {(res['score']-BASE):+.3f} ({100*(res['score']/BASE-1):+.6f}%) vs 360733280431.941")
except Exception as ex:
    import traceback
    log("VERIFY FAILED", repr(ex)); print(traceback.format_exc()[-2500:], flush=True)
