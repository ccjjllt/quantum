"""Build an (8,129,44) seed by truncating the current (8,143,44) basis and refitting W.

Drops, per rho, the 14 basis vectors with the smallest W-column norm (two
importance variants tried), then solves a linear least squares for W_new so
that sum_b W_new[r,b,c] u_b u_b^T matches the current X[r,c] on the packed
lower triangle.  Evaluates the continuous packed-pair error_2 with the same
objective as slim_train.py.  No training, no circuits.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

WT = Path(__file__).resolve().parents[3]
ART = WT.parents[1] / "artifacts/20261111_grimoire33/candidate/dfthcsos"
PROB = WT / "artifacts/20261110_gputrain/prob_r5.npz"
B_NEW = int(sys.argv[1]) if len(sys.argv) > 1 else 129
OUT = WT / f"artifacts/20261111_r3_probe/seed_8x{B_NEW}x44_truncfit.npz"


def error2(U, W, T, M, i, j):
    u = U / np.linalg.norm(U, axis=2, keepdims=True)
    pairs = u[:, :, i] * u[:, :, j]
    A = np.einsum("rbc,rbp->rcp", W, pairs).reshape(-1, T.shape[0])
    H = A.T @ A - T
    return float(np.sqrt(np.sum(M * H * H)))


def main() -> None:
    sub = np.load(ART / "submission.npz")
    U = np.asarray(sub["U"], np.float64)
    W = np.asarray(sub["W"], np.float64)
    z = np.load(PROB)
    T, M = (np.asarray(z[k], np.float64) for k in ("T", "M"))
    i, j = (np.asarray(z[k], np.int64) for k in ("i", "j"))
    m = np.sqrt(np.diag(M))
    print("current U", U.shape, "W", W.shape, "e2", error2(U, W, T, M, i, j) * 1e3, "mHa")
    best = None
    for name, imp in (
        ("wnorm", np.linalg.norm(W, axis=2)),
        ("wsum", np.abs(W).sum(axis=2)),
    ):
        keep = np.argsort(-imp, axis=1)[:, :B_NEW]
        U_new = np.take_along_axis(U, keep[:, :, None], axis=1)
        W_new = np.zeros((U.shape[0], B_NEW, W.shape[2]))
        for r in range(U.shape[0]):
            u = U_new[r]
            A = (u[:, i] * u[:, j] * m[None, :]).T  # (P, B)
            for c in range(W.shape[2]):
                X = np.sum(
                    W[r, :, c][:, None] * U[r][:, i] * U[r][:, j], axis=0
                )
                W_new[r, :, c] = np.linalg.lstsq(A, X * m, rcond=None)[0]
        e2 = error2(U_new, W_new, T, M, i, j)
        print(f"{name}: seed e2 = {e2 * 1e3:.3f} mHa")
        if best is None or e2 < best[0]:
            best = (e2, U_new, W_new, name)
    e2, U_new, W_new, name = best
    print(f"best {name}: {e2 * 1e3:.3f} mHa")
    np.savez(
        OUT, U=U_new, W=W_new, H2_I=W_new.sum(axis=1),
        H1_I=np.float32(np.load(ART / "submission.npz")["H1_I"]),
        Hsym_lower=np.asarray(np.load(ART / "submission.npz")["Hsym_lower"], np.float32),
    )
    print("wrote", OUT, "sha will be recorded separately")


if __name__ == "__main__":
    main()
