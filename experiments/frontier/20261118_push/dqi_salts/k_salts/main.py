"""Salt robustness of the shipped DQI tape (575b043f): official verifier at 3 salts.

No splice, no change: this only measures how the public tape behaves on salts other than the
default, i.e. the expected leaderboard risk of the package being submitted at 08:02 Beijing.
CPU only.
"""
import json, lzma, os, pathlib, subprocess, sys, time

WORK = pathlib.Path("/kaggle/working")
COMP = "/kaggle/input/competitions/google-verifiable-quantum-circuit-compilation"
T0 = time.time()


def say(*a):
    print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)


def find(p):
    for x in pathlib.Path("/kaggle/input").rglob(p):
        return x
    raise SystemExit("missing " + p)


xz = find("dqi_575b043f.kmb.xz")
raw = WORK / "dqi.kmb"
with lzma.open(xz, "rb") as fi, open(raw, "wb") as fo:
    while True:
        b = fi.read(1 << 23)
        if not b:
            break
        fo.write(b)
say("decompressed", raw.stat().st_size)
out = {}
env = dict(os.environ, JAX_PLATFORMS="cpu", OMP_NUM_THREADS="4",
           PYTHONPATH=COMP + "/kickmix:" + COMP + "/verifiers")
for salt in ("", "s1", "s2", "s3"):
    cmd = [sys.executable, COMP + "/verifiers/dqi/verify_submission_dqi.py", str(raw)]
    if salt:
        cmd += ["--salt", salt]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=COMP + "/verifiers")
    key = salt or "(default)"
    try:
        d = json.loads(r.stdout)
    except Exception:
        d = {"rc": r.returncode, "tail": r.stdout[-800:] + r.stderr[-800:]}
    out[key] = {k: d.get(k) for k in ("status", "value_errors", "phase_errors", "toffoli_count",
                                      "repetition_factor", "score")} if "score" in d else d
    say(key, out[key])
with open(WORK / "salts.json", "w") as f:
    json.dump(out, f, indent=1)
raw.unlink()
say("done")
