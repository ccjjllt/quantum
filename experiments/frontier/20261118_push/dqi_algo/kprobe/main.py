"""DQI leg, algorithmic-T line: EEA iteration-count / truncation probe on tape 575b043f.

CPU-only Kaggle kernel.  No local simulation: every circuit here is run through the
UNMODIFIED official verifier (verifiers/dqi/verify_submission_dqi.py) as a subprocess.

Region map of the tape (measured, see region_split.json):
    preamble  [        0, 17,576,206)   0 Toffoli
    EEA fwd   [17,576,206, 30,335,416)  153,186
    Chien     [30,335,416, 35,627,262)   44,264
    EEA rev   [35,627,262, 52,910,631)  170,539
    epilogue  [52,910,631, 57,520,821)   0

Candidates: delete the tail of the forward EEA pass (the last multiply cluster, and
last cluster + wrap-up), i.e. the coordinator's "truncate the last k forward
iterations".  A truncation is only legal if the deleted chunk is the identity on the
EEA state, so the test is direct: 0 value/phase errors over 102,400 shots.
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

WORK = pathlib.Path("/kaggle/working")
T0 = time.time()
OUT = {"candidates": {}}


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
else:
    XZ = pathlib.Path("/private/tmp/dqid/dqi_575b043f.kmb.xz")
    IRPY = pathlib.Path("artifacts/20261118_push_dqi/ds/vqcc_ir.py").resolve()
    VDIR = pathlib.Path("data/competition").resolve()
    WORK = pathlib.Path("/private/tmp/dqid")

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
OUT["base_bytes"] = raw.stat().st_size
say("base", OUT["base_sha256"])

spec = importlib.util.spec_from_file_location("vqcc_ir", str(IRPY))
ir = importlib.util.module_from_spec(spec)
sys.modules["vqcc_ir"] = ir
spec.loader.exec_module(ir)

c = ir.Circuit.read(str(raw))
N = c.num_ops
OUT["num_ops"] = N
OUT["num_qubits"] = c.num_qubits
OUT["static_toffoli"] = c.toffoli_like()
t = c.types
tof_pos = ir.LTOF[t]
import numpy as np
tof = np.flatnonzero(tof_pos)
A, B, C = 30335416, 35627262, 52910631

# --- identity round trip: concat(pieces(no cuts)) must reproduce the file sha
rt = ir.Circuit.concat([p for _, _, p in c.pieces([])])
OUT["roundtrip_sha256"] = rt.sha256()
OUT["roundtrip_ok"] = OUT["roundtrip_sha256"] == OUT["base_sha256"]
say("roundtrip", OUT["roundtrip_sha256"], OUT["roundtrip_ok"])

# --- condition-stack depth must be 0 at every cut we use
ev, clamped = ir._depth_events(t)


def depth(a):
    k = int(np.searchsorted(ev, a, side="left"))
    return int(clamped[k - 1]) if k > 0 else 0


CUTS = {
    # name: list of (start, end) instruction ranges to delete
    "P1_lastClusterAndWrap": [(29756473, A)],
    "P2_lastCluster": [(29756473, 29806000)],
    "P3_last3ClustersAndWrap": [(29247514, A)],
}
for nm, del_ in CUTS.items():
    for a, b in del_:
        assert depth(a) == 0 and depth(b) == 0, (nm, a, depth(a), b, depth(b))
OUT["cut_depths"] = {nm: [(a, b, depth(a), depth(b)) for a, b in dl] for nm, dl in CUTS.items()}
OUT["deleted_static_toffoli"] = {
    nm: int(sum(((tof >= a) & (tof < b)).sum() for a, b in dl)) for nm, dl in CUTS.items()
}
say("delete map", json.dumps(OUT["deleted_static_toffoli"]))


def build(del_):
    keep, cuts = [], []
    for a, b in del_:
        cuts.extend([a, b])
    for a, b, piece in c.pieces(sorted(cuts)):
        if any(a >= da and b <= db for da, db in del_):
            continue
        keep.append(piece)
    return ir.Circuit.concat(keep)


paths = {}
for nm, dl in CUTS.items():
    circ = build(dl)
    p = WORK / f"dqi_{nm}.kmb"
    s = circ.write(str(p))
    paths[nm] = p
    OUT["candidates"][nm] = {
        "path": p.name,
        "sha256": s,
        "num_ops": circ.num_ops,
        "num_qubits": circ.num_qubits,
        "static_toffoli": circ.toffoli_like(),
        "deleted_static_toffoli": OUT["deleted_static_toffoli"][nm],
    }
    say(nm, s, circ.num_ops, circ.toffoli_like())


def run_verifier(circuit, salt=""):
    cmd = [sys.executable, str(VDIR / "verifiers/dqi/verify_submission_dqi.py"), str(circuit)]
    if salt:
        cmd += ["--salt", salt]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(VDIR / "kickmix") + os.pathsep + env.get("PYTHONPATH", "")
    env["JAX_PLATFORMS"] = "cpu"
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
    if payload is None:
        payload = {"status": "ERROR", "returncode": proc.returncode,
                   "stderr_tail": (proc.stderr or "")[-1500:], "stdout_tail": (proc.stdout or "")[-1500:]}
    return payload


KEYS = ("status", "score", "toffoli_count", "num_qubits", "value_errors", "phase_errors",
        "verified_shots", "effective_error_rate", "repetition_factor", "circuit_sha256")

for nm, p in paths.items():
    if os.environ.get("DQIALGO_NOVERIFY"):
        OUT["candidates"][nm]["default_salt"] = {"status": "SKIPPED_LOCAL"}
        continue
    r = run_verifier(p, "")
    OUT["candidates"][nm]["default_salt"] = {k: r.get(k) for k in KEYS}
    say(nm, "default salt ->", json.dumps({k: r.get(k) for k in ("status", "toffoli_count",
                                                               "value_errors", "phase_errors")}))
    ok = r.get("status") == "PASS" and r.get("value_errors") == 0 and r.get("phase_errors") == 0
    if ok:
        for salt in ("s1", "s2"):
            r2 = run_verifier(p, salt)
            OUT["candidates"][nm][f"salt_{salt}"] = {k: r2.get(k) for k in KEYS}
            say(nm, salt, "->", json.dumps({k: r2.get(k) for k in ("status", "toffoli_count",
                                                                  "value_errors", "phase_errors")}))

OUT["seconds"] = round(time.time() - T0, 1)
(WORK / "truncation_probe.json").write_text(json.dumps(OUT, indent=1))
print("RESULT_JSON_BEGIN")
print(json.dumps(OUT, indent=1))
print("RESULT_JSON_END")
