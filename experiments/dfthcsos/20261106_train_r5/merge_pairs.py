"""Exact merge of several pairs of V9 groups into a padded R-2 or R-3 seed.

Each merged group concatenates two U blocks and uses block-diagonal weights;
the remaining groups are padded with zero-weight vectors/copies.  The two-body
tensor is unchanged.  This is a shrink intermediate, not a candidate.
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
    ap.add_argument("--pairs", required=True, help="e.g. 0,1;2,3")
    ap.add_argument("--B", type=int, default=286)
    ap.add_argument("--C", type=int, default=90)
    a = ap.parse_args()
    z = np.load(a.npz, allow_pickle=False)
    U = np.asarray(z["U"], np.float64)
    W = np.asarray(z["W"], np.float64)
    H = np.asarray(z["H2_I"], np.float64)
    R, B, C = W.shape
    pairs = [tuple(int(x) for x in p.split(",")) for p in a.pairs.split(";")]
    used = {r for p in pairs for r in p}
    if len(used) != 2 * len(pairs):
        raise SystemExit("pairs must be disjoint")
    keep = [r for r in range(R) if r not in used]
    R2 = len(pairs) + len(keep)
    rng = np.random.default_rng(0)
    U2 = np.zeros((R2, a.B, N))
    W2 = np.zeros((R2, a.B, a.C))
    H2 = np.zeros((R2, a.C))
    g = 0
    for r1, r2 in pairs:
        U2[g, :2 * B] = np.concatenate([U[r1], U[r2]], axis=0)
        W2[g, :B, :C] = W[r1]
        W2[g, B:2 * B, C:2 * C] = W[r2]
        H2[g, :C] = H[r1]
        H2[g, C:2 * C] = H[r2]
        g += 1
    for r in keep:
        U2[g, :B] = U[r]
        U2[g, B:] = rng.normal(size=(a.B - B, N))
        U2[g, B:] /= np.linalg.norm(U2[g, B:], axis=1, keepdims=True)
        W2[g, :B, :C] = W[r]
        H2[g, :C] = H[r]
        g += 1
    shifts = load_fixed_shifts()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(a.out, U=U2, W=W2, H2_I=H2,
             H1_I=np.float32(shifts["H1_I"]),
             Hsym_lower=np.asarray(shifts["Hsym_lower"], np.float32))
    print(json.dumps({"pairs": pairs, "kept": keep, "shape": [R2, a.B, a.C], "out": str(a.out)}, indent=1))


if __name__ == "__main__":
    main()
