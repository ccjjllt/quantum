"""Kaggle GPU: Lera quantize -> refine -> tensorqrom build -> official verify.

Input dataset: qingyu1232/qcc-r3-train-bundle (new version with lera/dfthc_refit,
starter_pkg, struct_8x135x44_20000.npz, base_submission.npz, slim_train.py,
fastfit.py, prob_r5.npz).
Competition source: google-verifiable-quantum-circuit-compilation (FCIDUMP,
kickmix, verifiers).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time


def find(root: str, needle: str) -> str | None:
    for base, _, files in os.walk(root):
        if needle in files:
            return base
    return None


def find_data() -> str:
    for base, _, files in os.walk("/kaggle/input"):
        if "FeMoCo76o113e.fcidump" in files and os.path.basename(base) == "dfthcsos":
            return os.path.dirname(os.path.dirname(base))
    raise SystemExit("competition verifiers not found")


if __name__ == "__main__":
    bundle = find("/kaggle/input", "struct_8x135x44_20000.npz")
    if bundle is None:
        raise SystemExit("train bundle not found")
    data = find_data()
    os.environ["DFTHC_DATA"] = data
    os.environ["DFTHC_STARTER"] = os.path.join(bundle, "starter_pkg")
    print("bundle", bundle, "data", data, flush=True)
    refit = os.path.join(bundle, "lera", "dfthc_refit")
    struct = os.path.join(bundle, "struct_8x135x44_20000.npz")
    out_q = "/kaggle/working/quant_8x135x44.npz"
    out_r = "/kaggle/working/refine_8x135x44.npz"
    out_dir = "/kaggle/working/submission_8x135x44"
    result = "/kaggle/working/result_8x135x44.json"
    t0 = time.time()
    steps = [
        [sys.executable, os.path.join(refit, "quantize.py"), struct, out_q,
         "--brot", "8", "--lbfgs-until", "0.5", "--lbfgs-iters", "12000",
         "--stage-steps", "800", "--final-steps", "1500"],
        [sys.executable, os.path.join(refit, "refine.py"), out_q, out_r,
         "--brot", "8"],
        [sys.executable, os.path.join(refit, "build.py"), out_r, out_dir,
         "--brot", "8", "--qrom", "tensor", "--shots", "64", "--json", result],
    ]
    for cmd in steps:
        print("RUN", " ".join(cmd), flush=True)
        rc = subprocess.call(cmd, cwd=refit)
        print("exit", rc, "seconds", round(time.time() - t0, 1), flush=True)
        if rc != 0:
            raise SystemExit(rc)
    print("RESULT", open(result).read() if os.path.exists(result) else "missing", flush=True)
    print("ALL DONE", flush=True)
