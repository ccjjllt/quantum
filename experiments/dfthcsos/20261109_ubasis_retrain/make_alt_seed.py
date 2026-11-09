"""Alternate U-basis seeds for R5/B135/C70 (and R4/B131/C83): random-sphere / real-DFT frame.

Keeps the Lera compact_seed leaf construction (pivoted-Cholesky leaves of the
weighted target + balanced k-means groups) but REPLACES the OMP shared bases:
  - mode rand: U[r] = iid Gaussian rows, renormalized (random frame; B>N so
    overcomplete, not strictly orthogonal).
  - mode dft : U[r] = deterministic real Fourier frame (cos/sin cycling),
    delocalized opposite of chol-local OMP bases.
W is then least-squares optimal for that fixed U per copy
(W[r,:,c] = lstsq(Pi.T, leaf*mult)), exactly as compact_seed does after basis
selection. This isolates the U-basis effect: same copies, same grouping, same
W-solve, different U.

Not cluster_chol/OMP: no omp_bases call, no eigenvector candidates.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "artifacts/20261106_high_yield/lera_data/dfthc_refit"))
sys.path.insert(0, str(ROOT / "artifacts/20261106_high_yield/lera_data/dfthc_refit/experiments"))
sys.path.insert(0, str(ROOT / "artifacts/20261106_high_yield/starter_kit/starter_kit"))
import jax  # noqa: E402

jax.config.update("jax_enable_x64", True)
jax.config.update("jax_default_matmul_precision", "highest")
import jax.numpy as jnp  # noqa: E402
import fastfit  # noqa: E402
from dfthc.train_df_thc_sga import Initialize  # noqa: E402

N_ORB = 76


def unpack(a: np.ndarray, i: np.ndarray, j: np.ndarray) -> np.ndarray:
    L = np.zeros((N_ORB, N_ORB))
    L[i, j] = a
    L[j, i] = a
    return L


def balanced_kmeans(X: np.ndarray, R: int, size: int, weight: np.ndarray, iters: int = 60, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = len(X)
    lab = rng.permutation(np.repeat(np.arange(R), size))
    for _ in range(iters):
        cen = np.array([np.average(X[lab == r], axis=0, weights=weight[lab == r] + 1e-12) for r in range(R)])
        cen /= np.linalg.norm(cen, axis=1, keepdims=True)
        sim = X @ cen.T
        srt = np.sort(sim, axis=1)
        order = np.argsort(-(srt[:, -1] - srt[:, -2]))
        left, new = np.full(R, size), np.zeros(n, int)
        for idx in order:
            for r in np.argsort(-sim[idx]):
                if left[r] > 0:
                    new[idx] = r
                    left[r] -= 1
                    break
        if np.all(new == lab):
            break
        lab = new
    return lab


def real_dft_frame(B: int, N: int, rng: np.random.Generator) -> np.ndarray:
    """Deterministic real Fourier frame (B,N), rows unit-normed.

    First N rows: cos/sin pairs at frequencies 1..N/2 (N=76 even).
    Remaining B-N rows: same frequencies with a fixed pseudo-random phase
    shift per row (seeded), so the extension stays delocalized but distinct.
    """
    U = np.zeros((B, N))
    F = N // 2
    for b in range(B):
        f = (b % F) + 1
        n = np.arange(N)
        if b < N:
            if b < F:
                U[b] = np.cos(2 * np.pi * f * n / N)
            else:
                U[b] = np.sin(2 * np.pi * f * n / N)
        else:
            phi = float(rng.uniform(0, 2 * np.pi))
            U[b] = np.cos(2 * np.pi * f * n / N + phi)
    U /= np.linalg.norm(U, axis=1, keepdims=True)
    return U


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("R", type=int)
    ap.add_argument("B", type=int)
    ap.add_argument("C", type=int)
    ap.add_argument("--mode", choices=("rand", "dft"), required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--fcidump", default=str(ROOT / "data/competition/verifiers/dfthcsos/FeMoCo76o113e.fcidump"))
    ap.add_argument("--shifts", default=str(ROOT / "data/competition/verifiers/dfthcsos/FeMoCo76o113e.fixed_shifts.npz"))
    a = ap.parse_args()

    t0 = time.time()
    ref = Initialize(a.fcidump, -22140.27335)
    ref = {k: (jnp.asarray(v, jnp.float64) if hasattr(v, "dtype") and jnp.issubdtype(v.dtype, jnp.floating) else v)
           for k, v in ref.items()}
    with np.load(a.shifts) as z:
        frozen = {k: jnp.asarray(z[k], jnp.float64) for k in ("Hsym_lower", "H1_I")}
        shifts = {k: np.array(z[k]) for k in ("H1_I", "Hsym_lower")}
    prob = fastfit.problem(ref, frozen, jnp.float64)
    T, M, ii, jj = (np.asarray(x) for x in prob)
    mult = np.where(ii == jj, 1.0, 2.0)
    d = np.sqrt(mult)
    Tw = d[:, None] * T * d[None, :]
    K = a.R * a.C
    diag, L = np.diag(Tw).copy(), np.zeros((len(Tw), K))
    for k in range(K):
        q = int(np.argmax(diag))
        L[:, k] = (Tw[:, q] - L[:, :k] @ L[q, :k]) / np.sqrt(diag[q])
        diag = np.maximum(diag - L[:, k] ** 2, 0)
    leaves = [unpack(L[:, k] / d, ii, jj) for k in range(K)]
    profile = np.array([np.sqrt(np.sum(l ** 2, axis=1)) for l in leaves])
    profile /= np.linalg.norm(profile, axis=1, keepdims=True)
    weight = np.array([np.sum(l ** 2) for l in leaves])
    label = balanced_kmeans(profile, a.R, a.C, weight, seed=a.seed)
    N = leaves[0].shape[0]

    rng = np.random.default_rng(a.seed + (0 if a.mode == "rand" else 10_000))
    U = np.zeros((a.R, a.B, N))
    if a.mode == "rand":
        for r in range(a.R):
            Ur = rng.standard_normal((a.B, N))
            Ur /= np.linalg.norm(Ur, axis=1, keepdims=True)
            U[r] = Ur
    else:
        base = real_dft_frame(a.B, N, rng)
        for r in range(a.R):
            # per-group fixed permutation so groups differ but stay Fourier
            perm = rng.permutation(a.B)
            U[r] = base[perm]

    W = np.zeros((a.R, a.B, a.C))
    for r in range(a.R):
        ks = list(np.flatnonzero(label == r))
        pairs = (U[r][:, ii] * U[r][:, jj]) * mult[None, :]
        for c, k in enumerate(ks):
            W[r, :, c] = np.linalg.lstsq(pairs.T, leaves[k][ii, jj] * mult, rcond=None)[0]

    A = np.einsum("rbc,rbp->rcp", W, U[:, :, ii] * U[:, :, jj]).reshape(-1, len(ii)) * d
    e2 = float(np.linalg.norm(A.T @ A - Tw))
    share = np.bincount(label, weights=weight, minlength=a.R) / weight.sum()
    print(f"mode={a.mode} R={a.R} B={a.B} C={a.C} seed={a.seed}: "
          f"start error_2 {1e3*e2:.2f} mHa ({time.time()-t0:.0f}s); "
          f"groups {100*share.min():.1f}-{100*share.max():.1f}% weight")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(a.out, U=U, W=W, H2_I=W.sum(axis=1), **shifts)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
