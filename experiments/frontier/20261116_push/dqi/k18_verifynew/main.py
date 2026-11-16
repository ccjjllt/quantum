"""Verify byte-new DQI circuits from the 2026-11-16 >=10:00 UTC intel sweep.

Candidates (both Q=890 full-size, both pass the local header gate):
  A. 66b4f18b85273bdc... (balramsrinivasan/vqcc-28-10-norm-preserving-dqi-closings,
     submission/dqi.kmb) — claimed 890Q / 367,877.55 T / 347,128,304,010.81,
     LB 28.10154 (Balram Srinivasan, rank 76, 14:31 UTC).
  B. 00ac37d4ae4ee4ac... (junmiaotiao/qcc-frontier-20261116q, dqi_00ac37d4.kmb.xz)
     — kernel-claimed dqi 347,357,914,646.97 @ salt 'notebook-verification',
     combo GM 28.09535 (tiraJoon LB 28.09535).

Runs the UNCHANGED official DQI verifier at the default salt (102,400 shots,
batch 256, 4 workers via verify()) on each candidate. No patching, no packaging.
"""
import hashlib, lzma, pathlib, sys, time
import importlib.util

t0 = time.time()
def log(*a):
    print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)

ROOT = pathlib.Path("/kaggle/input")

PIN_A = "66b4f18b85273bdc0b325500c43a810aba2772275b977f371731cfc400a315c2"
PIN_B = "00ac37d4ae4ee4ac6a8fe9a2aad241731c20be1c81d6332766f4f4d5a5a853a8"

cands = {}
for p in sorted(ROOT.rglob("dqi.kmb")):
    s = str(p)
    if "balramsrinivasan" in s and "sample_submission" not in s:
        cands.setdefault("A_balram", p)
for p in sorted(ROOT.rglob("dqi_00ac37d4.kmb.xz")):
    cands.setdefault("B_junmiaotiao_xz", p)
log("candidates found", {k: str(v) for k, v in cands.items()})

files = {}
pa = cands.get("A_balram")
if pa is not None:
    files["A"] = pa
pb = cands.get("B_junmiaotiao_xz")
if pb is not None:
    dec = pathlib.Path("/tmp/dqi_00ac37d4.kmb")
    dec.write_bytes(lzma.decompress(pb.read_bytes()))
    files["B"] = dec

for tag, fp in files.items():
    h = hashlib.sha256(fp.read_bytes()).hexdigest()
    exp = PIN_A if tag == "A" else PIN_B
    log(f"{tag} file={fp} bytes={fp.stat().st_size} sha={h[:16]} {'MATCH' if h == exp else 'MISMATCH exp ' + exp[:16]}")

ENGINE = sorted(ROOT.rglob("kickmix.so"))[0].parent
VERIF = sorted(ROOT.rglob("verify_submission_dqi.py"))[0].parent.parent
log("engine", ENGINE, "verifiers", VERIF)

sys.path.insert(0, str(ENGINE))
import kickmix as km
sp = importlib.util.spec_from_file_location("vdqi", str(VERIF / "dqi" / "verify_submission_dqi.py"))
V = importlib.util.module_from_spec(sp); sys.modules["vdqi"] = V; sp.loader.exec_module(V)
spec = V.ProblemSpecDQI.benchmark_instance()

for tag, fp in files.items():
    circ = km.Circuit.from_file(str(fp), format="kmb")
    t = time.time()
    res = V.verify(circ, spec, salt="")
    log(f"VERIFY {tag} {time.time()-t:.0f}s")
    log(f"VERIFY {tag}", {k: res[k] for k in ("status", "score", "num_qubits",
          "toffoli_count", "value_errors", "phase_errors", "circuit_sha256")})
log("DONE")

