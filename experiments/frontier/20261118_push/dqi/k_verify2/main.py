"""Verify a DQI candidate .kmb produced by another kernel, with the unmodified official verifier.

Mounts the producing kernel as a kernel source, finds every *.kmb under /kaggle/input, and runs
verifiers/dqi/verify_submission_dqi.py at the default salt plus two fresh ones.
"""
import json
import os
import pathlib
import subprocess
import sys
import time

COMP = None
for p in pathlib.Path("/kaggle/input").rglob("FeMoCo76o113e.fcidump"):
    for up in (p.parents[1], p.parents[2], p.parents[3]):
        if (up / "kickmix").is_dir():
            COMP = up
            break
    if COMP:
        break
print(json.dumps({"competition_root": str(COMP)}), flush=True)

WORK = pathlib.Path("/kaggle/working")
SALTS = ["<default>", "dqi-push-18x", "dqi-push-18y"]
env = dict(os.environ, PYTHONPATH=f"{COMP/'kickmix'}:{COMP/'verifiers'}")
VER = COMP / "verifiers/dqi/verify_submission_dqi.py"

cands = sorted(p for p in pathlib.Path("/kaggle/input").rglob("*.kmb"))
print(json.dumps({"candidates": [str(p) for p in cands]}), flush=True)
out = {"salts": SALTS, "runs": []}
for src in cands:
    for salt in SALTS:
        args = [sys.executable, str(VER), str(src)]
        if salt != "<default>":
            args += ["--salt", salt]
        t0 = time.time()
        r = subprocess.run(args, env=env, cwd=str(COMP / "verifiers"), capture_output=True, text=True)
        rec = {"file": str(src), "salt": salt, "rc": r.returncode, "secs": round(time.time() - t0, 1)}
        try:
            s = r.stdout
            rec["json"] = json.loads(s[s.index("{"):s.rindex("}") + 1])
        except Exception as e:
            rec["parse_error"] = repr(e)
            rec["stdout_tail"] = (r.stdout[-2500:] + "\n--stderr--\n" + r.stderr[-1200:])
        j = rec.get("json") or {}
        print(json.dumps({k: j.get(k) for k in ("status", "score", "toffoli_count", "max_toffoli_count",
                                                "num_qubits", "num_bits", "value_errors", "phase_errors",
                                                "repetition_factor")} | {"salt": salt, "rc": rec["rc"],
                                                                          "secs": rec["secs"]}), flush=True)
        out["runs"].append(rec)
(WORK / "verify_candidate.json").write_text(json.dumps(out, indent=1))
print("DONE", flush=True)
