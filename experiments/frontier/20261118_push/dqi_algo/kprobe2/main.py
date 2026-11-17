"""DQI leg, algorithmic-T line: truncation probe v2, with the base circuit as control.

CPU-only Kaggle kernel.  Runs the UNMODIFIED official verifier as a subprocess on
  (a) the unmodified base 575b043f      -> control: must PASS with T=367,116.06
  (b) the k=1 truncated forward tail    -> the surplus-iteration test
and records the full returncode / stdout / stderr so a harness failure cannot be
mistaken for a circuit failure.
"""
import hashlib
import importlib.util
import json
import lzma
import os
import pathlib
import subprocess
import sys
import time

import numpy as np

WORK = pathlib.Path("/kaggle/working")
T0 = time.time()
OUT = {}


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


if pathlib.Path("/kaggle/input").is_dir():
    XZ = find("dqi_575b043f.kmb.xz")
    IRPY = find("vqcc_ir.py")
    VDIR = None
    for p in pathlib.Path("/kaggle/input").rglob("verify_submission_dqi.py"):
        VDIR = p.parents[2]
        break
    WORK.mkdir(parents=True, exist_ok=True)
    OUT["mode"] = "kaggle"
else:
    XZ = pathlib.Path("/private/tmp/dqid/dqi_575b043f.kmb.xz")
    IRPY = pathlib.Path("artifacts/20261118_push_dqi/ds/vqcc_ir.py").resolve()
    VDIR = pathlib.Path("data/competition").resolve()
    WORK = pathlib.Path("/private/tmp/dqid")
    OUT["mode"] = "local"

OUT["vdir"] = str(VDIR)
OUT["kickmix_dir_exists"] = (pathlib.Path(VDIR) / "kickmix").is_dir()
OUT["verifier_exists"] = (pathlib.Path(VDIR) / "verifiers/dqi/verify_submission_dqi.py").exists()

raw = WORK / "dqi_575b043f.kmb"
if not raw.exists():
    say("decompressing")
    with lzma.open(XZ, "rb") as fi, open(raw, "wb") as fo:
        while True:
            b = fi.read(1 << 23)
            if not b:
                break
            fo.write(b)
OUT["base_sha256"] = sha256(raw)
say("base", OUT["base_sha256"])

spec = importlib.util.spec_from_file_location("vqcc_ir", str(IRPY))
ir = importlib.util.module_from_spec(spec)
sys.modules["vqcc_ir"] = ir
spec.loader.exec_module(ir)

c = ir.Circuit.read(str(raw))
A = 30335416
OUT["num_ops"] = c.num_ops
OUT["static_toffoli"] = c.toffoli_like()

# ---- build the k=1 truncated candidate: drop the last forward multiply cluster + wrap
CUT = (29756473, A)
keep, cuts = [], [CUT[0], CUT[1]]
for a, b, piece in c.pieces(sorted(cuts)):
    if a >= CUT[0] and b <= CUT[1]:
        continue
    keep.append(piece)
tr = ir.Circuit.concat(keep)
p1 = WORK / "dqi_P1.kmb"
OUT["candidate"] = {
    "sha256": tr.write(str(p1)),
    "num_ops": tr.num_ops,
    "num_qubits": tr.num_qubits,
    "static_toffoli": tr.toffoli_like(),
    "deleted": list(CUT),
}
say("candidate", OUT["candidate"]["sha256"], tr.toffoli_like())
del tr, keep

KEYS = ("status", "score", "toffoli_count", "num_qubits", "value_errors", "phase_errors",
        "verified_shots", "effective_error_rate", "repetition_factor", "circuit_sha256",
        "max_toffoli_count", "num_ops", "shot_operation_counts")


def run_verifier(circuit, salt="", workers=2):
    cmd = [sys.executable, str(pathlib.Path(VDIR) / "verifiers/dqi/verify_submission_dqi.py"),
           str(circuit), "--max-workers", str(workers)]
    if salt:
        cmd += ["--salt", salt]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(pathlib.Path(VDIR) / "kickmix") + os.pathsep + env.get("PYTHONPATH", "")
    env["JAX_PLATFORMS"] = "cpu"
    t = time.time()
    proc = subprocess.run(cmd, cwd=str(VDIR), capture_output=True, text=True, env=env)
    payload = None
    for line in reversed((proc.stdout or "").strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                payload = json.loads(line)
                break
            except json.JSONDecodeError:
                pass
    rec = {"returncode": proc.returncode, "seconds": round(time.time() - t, 1),
           "stderr_tail": (proc.stderr or "")[-2500:],
           "stdout_tail": (proc.stdout or "")[-1200:]}
    if payload is not None:
        rec["result"] = {k: payload.get(k) for k in KEYS if k in payload}
    else:
        rec["result"] = None
    return rec


OUT["base_control"] = run_verifier(raw, "", workers=2)
say("base control", json.dumps(OUT["base_control"]["result"] if OUT["base_control"]["result"] else
                              OUT["base_control"]["stderr_tail"][-600:]))

OUT["truncated"] = run_verifier(p1, "", workers=2)
say("truncated", json.dumps(OUT["truncated"]["result"] if OUT["truncated"]["result"] else
                           OUT["truncated"]["stderr_tail"][-600:]))

OUT["seconds"] = round(time.time() - T0, 1)
(WORK / "truncation_probe2.json").write_text(json.dumps(OUT, indent=1))
print("RESULT_JSON_BEGIN")
print(json.dumps(OUT, indent=1))
print("RESULT_JSON_END")
