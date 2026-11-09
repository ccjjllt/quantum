"""Perturbed-restart init for the R5/B135/C70 500-step probe variant.

Adds seeded Gaussian noise (scale 0.01 relative) to U rows (renormalized) and W,
to test whether the 182 mHa stall is a basin artifact of the exact seed point.
Only U/W are read by fit_probe.py; H2_I/H1_I/Hsym_lower are placeholders
(refreshed by fit_probe from the shifts file on save).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]


def main():
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    scale = float(sys.argv[3]) if len(sys.argv) > 3 else 0.01
    sseed = int(sys.argv[4]) if len(sys.argv) > 4 else 7
    z = np.load(src, allow_pickle=False)
    U = np.asarray(z["U"], dtype=np.float64)
    W = np.asarray(z["W"], dtype=np.float64)
    rng = np.random.default_rng(sseed)
    Un = U + scale * rng.standard_normal(U.shape)
    Un /= np.linalg.norm(Un, axis=-1, keepdims=True)
    Wn = W + scale * float(np.abs(W).mean()) * rng.standard_normal(W.shape)
    np.savez(dst, U=Un, W=Wn, H2_I=np.asarray(z["H2_I"]),
             H1_I=np.asarray(z["H1_I"]), Hsym_lower=np.asarray(z["Hsym_lower"]))
    print(f"wrote {dst} U_perturb={scale} rng={sseed} "
          f"|dU|_F={float(np.linalg.norm(Un-U)):.4f} |dW|_F={float(np.linalg.norm(Wn-W)):.4f}")


if __name__ == "__main__":
    main()
