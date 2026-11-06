"""Build an exact 8->7 group merge of the current V9 factorization, padded to
R7/B286/C90, as a training intermediate for the Lera shrink pipeline.

The merged two-body tensor is unchanged (block-diagonal weights); only the
array shape grows.  This is not a candidate: A=2078 exceeds the 11-bit address
range and the cache would not fit 128 qubits.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data/competition/verifiers"))
from dfthcsos.scoreinfra.reference import load_reference, PACKAGED_FCIDUMP, load_fixed_shifts  # noqa: E402
from dfthcsos.scoreinfra.dfthc_math import symmetric_from_lower  # noqa: E402

N = 76


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("npz", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--pair", default="", help="r1,r2; default: two least important groups")
    ap.add_argument("--B", type=int, default=286)
    ap.add_argument("--C", type=int, default=90)
    a = ap.parse_args()
    z = np.load(a.npz, allow_pickle=False)
    U = np.asarray(z["U"], np.float64)
    W = np.asarray(z["W"], np.float64)
    H = np.asarray(z["H2_I"], np.float64)
    R, B, C = W.shape
    # group importance sum_c ||X_c||_F^2 = sum_{b,d,c} w_bc w_dc (u_b.u_d)^2
    u = U / np.linalg.norm(U, axis=2, keepdims=True)
    gram = np.einsum("rbp,rdp->rbd", u, u) ** 2
    imp = np.einsum("rbc,rbd,rdc->r", W, gram, W)
    if a.pair:
        r1, r2 = (int(x) for x in a.pair.split(","))
    else:
        order = np.argsort(imp)
        r1, r2 = int(order[0]), int(order[1])
    keep = [r for r in range(R) if r not in (r1, r2)]
    rng = np.random.default_rng(0)
    U2 = np.zeros((R - 1, a.B, N))
    W2 = np.zeros((R - 1, a.B, a.C))
    H2 = np.zeros((R - 1, a.C))
    g = 0
    # merged group
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
    a.out.parent.mkdir(parents=True, exist_ok=True)
    shifts = load_fixed_shifts()
    np.savez(a.out, U=U2, W=W2, H2_I=H2, H1_I=np.float32(shifts["H1_I"]),
             Hsym_lower=np.asarray(shifts["Hsym_lower"], np.float32))
    print(json.dumps({"merged_pair": [r1, r2], "importance": imp.tolist(),
                      "shape": [R - 1, a.B, a.C], "out": str(a.out)}, indent=1))


if __name__ == "__main__":
    main()
