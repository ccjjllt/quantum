"""Two-stage screen of compute/uncompute pair deletions.

Stage 1: all x <= dense-max plus a random sample above it (fast, robust to the
bit-residue aliasing that a fixed stride suffers from).
Stage 2 (run separately): full-domain re-check of survivors.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("circuit", type=Path)
    ap.add_argument("outdir", type=Path)
    ap.add_argument("pairs", type=Path)
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--dense-max", type=int, default=200000)
    ap.add_argument("--sample", type=int, default=300000)
    args = ap.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    pairs = np.load(args.pairs)
    print(f"{len(pairs)} pairs")

    base_npz = args.outdir / "base.npz"
    cmd = [sys.executable, str(HERE / "eval_phase.py"), "--dense-max", str(args.dense_max),
           "--sample", str(args.sample)]
    if not base_npz.exists():
        subprocess.run(cmd + [str(args.circuit), "--out", str(base_npz)], check=True,
                       capture_output=True)
    base = np.load(base_npz)["err"].astype(np.uint64)

    running, results = [], []
    for i, j in pairs:
        i, j = int(i), int(j)
        kmx = args.outdir / f"p_{i}_{j}.kmx"
        npz = kmx.with_suffix(".npz")
        if not npz.exists():
            subprocess.run([sys.executable, str(HERE / "make_variant.py"), str(args.circuit),
                            str(kmx), f"drop={i}:{i+1}", f"drop={j}:{j+1}"],
                           check=True, capture_output=True)
            proc = subprocess.Popen([sys.executable, str(HERE / "eval_phase.py"), str(kmx),
                                     "--out", str(npz)] + cmd[2:],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            running.append((proc, i, j, npz))
            if len(running) >= args.jobs:
                p0 = running.pop(0)
                p0[0].wait()
                results.append(p0)
        else:
            results.append((None, i, j, npz))
    for p0 in running:
        p0[0].wait()
        results.append(p0)

    neutral = []
    for proc, i, j, npz in results:
        z = np.load(npz)
        d = z["err"].astype(np.uint64) - base
        dist = np.minimum(d, np.uint64(0) - d)
        mx = float(dist.astype(np.float64).max() / 2**64)
        if mx < 1e-15 and int(z["dirty"]) == 0:
            neutral.append((i, j, mx))
    print(f"stage-1 neutral pairs: {len(neutral)}")
    for r in neutral:
        print(f"  {r[0]}->{r[1]}")


if __name__ == "__main__":
    main()
