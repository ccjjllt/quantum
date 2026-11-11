"""Kaggle GPU: R3/B129/C114 + C120 L-BFGS, then C150 fallback if needed.

Input dataset: qingyu1232/qcc-r3-train-bundle
  (prob_r5.npz, seed_3x129x114.npz, seed_3x129x120.npz,
   seed_3x129x150.npz, slim_train.py, fastfit.py)
Output: /kaggle/working/train_3x129x*.npz + summary.json.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

import numpy as np

OUT = "/kaggle/working"


def find_bundle():
    for root, _, files in os.walk("/kaggle/input"):
        if "prob_r5.npz" in files and "slim_train.py" in files:
            return root
    raise SystemExit("bundle not found under /kaggle/input")


IN = find_bundle()
sys.path.insert(0, IN)


def run(job, seed, out, iters, chunk):
    cmd = [sys.executable, f"{IN}/slim_train.py", f"{IN}/prob_r5.npz",
           f"{IN}/{seed}" if not seed.startswith("/") else seed,
           f"{OUT}/{out}", "--iters", str(iters), "--chunk", str(chunk)]
    print(f"[{job}] launch: {' '.join(cmd)}", flush=True)
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=False)
    dt = time.time() - t0
    print(f"[{job}] exit={r.returncode} seconds={dt:.1f}", flush=True)
    if r.returncode != 0:
        raise SystemExit(f"[{job}] FAILED")
    return dt


def e2(path):
    import jax.numpy as jnp
    import fastfit
    z = np.load(f"{IN}/prob_r5.npz")
    prob = (jnp.asarray(z["T"]), jnp.asarray(z["M"]),
            jnp.asarray(z["i"]), jnp.asarray(z["j"]))
    s = np.load(path)
    return float(fastfit.error2(jnp.asarray(s["U"]), jnp.asarray(s["W"]), prob)) * 1e3


if __name__ == "__main__":
    import jax
    print("bundle dir:", IN, sorted(os.listdir(IN)), flush=True)
    print("jax devices:", jax.devices(), flush=True)
    summary = {"jobs": [], "budget_seconds": 15000}
    t_all = time.time()
    for c, seed, out in [
        (114, "seed_3x129x114.npz", "train_3x129x114_50000.npz"),
        (120, "seed_3x129x120.npz", "train_3x129x120_50000.npz"),
    ]:
        dt = run(f"R3-C{c}-50k", seed, out, 50000, 500)
        m = e2(f"{OUT}/{out}")
        print(f"[R3-C{c}-50k] continuous e2 = {m:.3f} mHa", flush=True)
        summary["jobs"].append({"shape": [3, 129, c], "iters": 50000,
                                "seconds": round(dt, 1), "e2_mHa": m,
                                "file": out})
    best = min(summary["jobs"], key=lambda j: j["e2_mHa"])
    print("best 50k:", best, flush=True)
    if best["e2_mHa"] < 30.0:
        c = best["shape"][2]
        src = f"{OUT}/{best['file']}"
        out = f"train_3x129x{c}_200000.npz"
        dt = run(f"R3-C{c}-ext150k", src, out, 150000, 1000)
        m = e2(f"{OUT}/{out}")
        print(f"[R3-C{c}-200k] continuous e2 = {m:.3f} mHa", flush=True)
        summary["jobs"].append({"shape": [3, 129, c], "iters": 200000,
                                "seconds": round(dt, 1), "e2_mHa": m,
                                "file": out})
    else:
        dt = run("R3-C150-50k", "seed_3x129x150.npz",
                 "train_3x129x150_50000.npz", 50000, 500)
        m = e2(f"{OUT}/train_3x129x150_50000.npz")
        print(f"[R3-C150-50k] continuous e2 = {m:.3f} mHa", flush=True)
        summary["jobs"].append({"shape": [3, 129, 150], "iters": 50000,
                                "seconds": round(dt, 1), "e2_mHa": m,
                                "file": "train_3x129x150_50000.npz"})
    summary["total_seconds"] = round(time.time() - t_all, 1)
    with open(f"{OUT}/summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2), flush=True)
    print("ALL DONE", flush=True)
