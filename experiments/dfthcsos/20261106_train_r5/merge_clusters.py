"""Exact merge of arbitrary clusters of source groups into a padded seed.

Each cluster concatenates its members' U blocks; W is block-diagonal and
H2_I is concatenated.  Zero padding fills the target (B,C).  The two-body
tensor is unchanged; this is a shrink intermediate.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data/competition/verifiers"))
from dfthcsos.scoreinfra.reference import load_fixed_shifts  # noqa: E402

N = 76


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("npz", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--clusters", required=True, help="e.g. 0-4;5-9;10-14;15-19;20-24;25-26")
    ap.add_argument("--B", type=int, required=True)
    ap.add_argument("--C", type=int, required=True)
    a = ap.parse_args()
    z = np.load(a.npz, allow_pickle=False)
    U = np.asarray(z["U"], np.float64)
    W = np.asarray(z["W"], np.float64)
    H = np.asarray(z["H2_I"], np.float64)
    R, B, C = W.shape
    clusters = []
    for part in a.clusters.split(";"):
        if "-" in part:
            lo, hi = (int(x) for x in part.split("-"))
            clusters.append(list(range(lo, hi + 1)))
        else:
            clusters.append([int(part)])
    flat = [r for c in clusters for r in c]
    if sorted(flat) != list(range(R)):
        raise SystemExit(f"clusters must partition 0..{R-1}, got {flat}")
    used_b = [len(c) * B for c in clusters]
    used_c = [len(c) * C for c in clusters]
    if max(used_b) > a.B or max(used_c) > a.C:
        raise SystemExit(f"target {a.B}x{a.C} too small for {max(used_b)}x{max(used_c)}")
    R2 = len(clusters)
    U2 = np.zeros((R2, a.B, N))
    W2 = np.zeros((R2, a.B, a.C))
    H2 = np.zeros((R2, a.C))
    rng = np.random.default_rng(0)
    for g, cl in enumerate(clusters):
        U2[g, :len(cl) * B] = np.concatenate([U[r] for r in cl], axis=0)
        if len(cl) * B < a.B:
            pad = U2[g, len(cl) * B:]
            pad[:] = rng.normal(size=pad.shape)
            pad /= np.linalg.norm(pad, axis=1, keepdims=True)
        for j, r in enumerate(cl):
            W2[g, j * B:(j + 1) * B, j * C:(j + 1) * C] = W[r]
            H2[g, j * C:(j + 1) * C] = H[r]
    shifts = load_fixed_shifts()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(a.out, U=U2, W=W2, H2_I=H2,
             H1_I=np.float32(shifts["H1_I"]),
             Hsym_lower=np.asarray(shifts["Hsym_lower"], np.float32))
    print(json.dumps({"clusters": clusters, "shape": [R2, a.B, a.C], "out": str(a.out)}, indent=1))


if __name__ == "__main__":
    main()
