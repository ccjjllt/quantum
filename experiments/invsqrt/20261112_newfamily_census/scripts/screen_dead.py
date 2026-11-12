"""Random-sample screen of single Toffoli-like deletions (dead-gate census).

All x <= dense_max plus N uniform random x above it.  A fixed-stride sample is
NOT safe here: an earlier stride-64 screen missed gates whose effect only shows
for x not congruent to 0 mod 64 (see README).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from kmx_parse import load_ops  # noqa: E402

TOFF = {"CCX", "CCZ", "CSWAP"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("circuit", type=Path)
    ap.add_argument("outdir", type=Path)
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--dense-max", type=int, default=200000)
    ap.add_argument("--sample", type=int, default=300000)
    args = ap.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    ops, _, _ = load_ops(args.circuit)
    idxs = [o.index for o in ops if o.kind in TOFF]
    print(f"{len(idxs)} gates", flush=True)

    base_npz = args.outdir / "base.npz"
    cmd = [sys.executable, str(HERE / "eval_phase.py"), "--dense-max", str(args.dense_max),
           "--sample", str(args.sample)]
    if not base_npz.exists():
        subprocess.run(cmd + [str(args.circuit), "--out", str(base_npz)], check=True,
                       capture_output=True)
    base = np.load(base_npz)["err"].astype(np.uint64)

    running, results = [], []
    for k in idxs:
        kmx = args.outdir / f"s_{k}.kmx"
        npz = kmx.with_suffix(".npz")
        if not npz.exists():
            subprocess.run([sys.executable, str(HERE / "make_variant.py"), str(args.circuit),
                            str(kmx), f"drop={k}:{k+1}"], check=True, capture_output=True)
            proc = subprocess.Popen([sys.executable, str(HERE / "eval_phase.py"), str(kmx),
                                     "--out", str(npz)] + cmd[2:],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            running.append((proc, k, npz))
            if len(running) >= args.jobs:
                p0 = running.pop(0)
                p0[0].wait()
                results.append(p0)
        else:
            results.append((None, k, npz))
        if len(results) % 100 == 0:
            print(f"  {len(results)}/{len(idxs)}", flush=True)
    for p0 in running:
        p0[0].wait()
        results.append(p0)

    neutral = []
    for proc, k, npz in results:
        z = np.load(npz)
        d = z["err"].astype(np.uint64) - base
        dist = np.minimum(d, np.uint64(0) - d)
        mx = float(dist.astype(np.float64).max() / 2**64)
        nchg = int(np.count_nonzero(dist))
        if mx < 1e-15 and int(z["dirty"]) == 0:
            neutral.append((k, mx, nchg))
    print(f"stage-1 dead-gate candidates: {len(neutral)}")
    for r in neutral:
        print(f"  op {r[0]}")


if __name__ == "__main__":
    main()
