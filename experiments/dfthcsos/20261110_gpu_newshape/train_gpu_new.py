"""Kaggle GPU script (NEW SHAPE round): R4/B143/C83 + R5-eigrr L-BFGS on precomputed prob.

Input dataset: qingyu1232/qcc-dfthc-train-bundle (v2 = v1 + 2 small seed files)
  reused unchanged: prob_r5.npz (shape-independent packed target T,M,i,j),
                    slim_train.py, fastfit.py
  new (each < 1 MB): seed_4x143x83_cluster_chol.npz, seed_5x135x70_eig_rr.npz
Output: /kaggle/working/train_r4b143_30000.npz, train_r5_eigrr_30000.npz + logs.

Rationale (see experiments/dfthcsos/20261110_gpu_newshape/README.md):
  - R4/B143/C83: conservative T/Q gain -1.54% (heuristic_costs, angles unchanged);
    B 131 -> 143 adds capacity to the R4 line closed at 73.07 mHa (20k, B131).
    NOT falsified: closed table trained only (4,131,83); temp-qubit cliff is at
    B<=128 (Q~697, +45% T x Q), B>=130 is safe (Q=426).
  - R5/B135/C70 eig/roundrobin/omp: canonical Lera init, trained only on R4
    (180.11 mHa @500, best-in-class); R5+eigrr combination untrained.
"""
import subprocess
import sys

OUT = "/kaggle/working"


def find_bundle():
    for root, _, files in __import__("os").walk("/kaggle/input"):
        if "prob_r5.npz" in files and "slim_train.py" in files:
            return root
    raise SystemExit("bundle not found under /kaggle/input")


IN = find_bundle()


def run(job, prob, seed, out, iters, chunk):
    cmd = [sys.executable, f"{IN}/slim_train.py", f"{IN}/{prob}", f"{IN}/{seed}",
           f"{OUT}/{out}", "--iters", str(iters), "--chunk", str(chunk)]
    print(f"[{job}] launch: {' '.join(cmd)}", flush=True)
    r = subprocess.run(cmd, capture_output=False)
    print(f"[{job}] exit={r.returncode}", flush=True)
    if r.returncode != 0:
        raise SystemExit(f"[{job}] FAILED")


if __name__ == "__main__":
    import os
    print("bundle dir:", IN, sorted(__import__("os").listdir(IN)), flush=True)
    import jax
    print("jax devices:", jax.devices(), flush=True)
    # Cut 1 (shape): R4/B143/C83 from cluster_chol seed -> 30000 iters.
    run("R4B143-30k", "prob_r5.npz", "seed_4x143x83_cluster_chol.npz",
        "train_r4b143_30000.npz", 30000, 300)
    # Cut 2 (seed family): R5/B135/C70 from eig/roundrobin/omp seed -> 30000 iters.
    run("R5EIGRR-30k", "prob_r5.npz", "seed_5x135x70_eig_rr.npz",
        "train_r5_eigrr_30000.npz", 30000, 300)
    print("ALL DONE", flush=True)
