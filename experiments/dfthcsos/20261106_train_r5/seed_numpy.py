"""NumPy-only DF-THC seed at any (R,B,C), adapted from Lera V7 df_init.py.

Builds the unweighted packed target from the official FCIDUMP and fixed shifts,
then uses pivoted-Cholesky leaves, balanced k-means and simultaneous OMP to
produce U (R,B,N), W (R,B,C).  No starter kit, JAX or torch is needed for the
seed itself; this is a feasibility probe, not a submission.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data/competition/verifiers"))
from dfthcsos.scoreinfra.reference import load_reference, PACKAGED_FCIDUMP, load_fixed_shifts  # noqa: E402
from dfthcsos.scoreinfra.dfthc_math import symmetric_from_lower  # noqa: E402

N = 76
CHOL_TOL = 1e-6


def unpack(a, i, j):
    L = np.zeros((N, N))
    L[i, j] = a
    L[j, i] = a
    return L


def omp_bases(cand, targets, i, j, m, B, power=1.0):
    Pi = (cand[:, i] * cand[:, j]) * m[None, :]
    Pi_n = Pi / np.linalg.norm(Pi, axis=1, keepdims=True)
    Y = targets * m[None, :]
    Y = Y * np.linalg.norm(Y, axis=1, keepdims=True) ** power
    resid = Y.copy()
    chosen = []
    for _ in range(B):
        score = np.sum((Pi_n @ resid.T) ** 2, axis=1)
        score[chosen] = -1.0
        chosen.append(int(np.argmax(score)))
        A = Pi[chosen].T
        resid = Y - (A @ np.linalg.lstsq(A, Y.T, rcond=None)[0]).T
    return cand[chosen]


def balanced_kmeans(X, R, size, weight, iters=60, seed=0):
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


def target():
    ref = load_reference(PACKAGED_FCIDUMP)
    shifts = load_fixed_shifts()
    S = np.asarray(symmetric_from_lower(shifts["Hsym_lower"], N), np.float64)
    t = ref["tei"].copy()
    d = np.arange(N)
    t[:, :, d, d] += 0.5 * S[:, :, None]
    t[d, d, :, :] += 0.5 * S[None, :, :]
    i, j = np.tril_indices(N)
    T = t.reshape(N * N, N * N)[np.ix_(i * N + j, i * N + j)].copy()
    m = np.where(i == j, 1.0, np.sqrt(2.0))
    M = np.outer(m, m)
    return T, M, i, j, ref, S


def seed(R, B, C, prob, assign, leaves_kind, select, seed_id):
    T, M, i, j = prob
    m = np.sqrt(np.diag(M))
    Tw = m[:, None] * T * m[None, :]
    lam, V = np.linalg.eigh(Tw)
    order = np.argsort(-lam)
    pos = int((lam > 0).sum())
    K = R * C
    if K > pos:
        raise SystemExit(f"only {pos} positive eigenvalues for {K} copies")
    info = {"positive": pos, "kept_weight": float(lam[order[:K]].sum() / lam[lam > 0].sum())}
    if leaves_kind == "chol":
        P = len(Tw)
        diag, L, tol = np.diag(Tw).copy(), np.zeros((P, K)), CHOL_TOL * float(np.diag(Tw).max())
        nchol = K
        for k in range(K):
            q = int(np.argmax(diag))
            v = Tw[:, q] - L[:, :k] @ L[q, :k]
            if v[q] <= tol:
                nchol = k
                break
            L[:, k] = v / np.sqrt(v[q])
            diag = np.maximum(diag - L[:, k] ** 2, 0)
        if nchol < K:
            resid = Tw - L[:, :nchol] @ L[:, :nchol].T
            lr, Vr = np.linalg.eigh(resid)
            take = np.argsort(-lr)[:K - nchol]
            L[:, nchol:] = np.sqrt(np.maximum(lr[take], 0)) * Vr[:, take]
        info["chol_leaves"] = nchol
        info["chol_reproduction_mHa"] = 1e3 * float(np.linalg.norm(L @ L.T - Tw))
        leaves = [unpack(L[:, k] / m, i, j) for k in range(K)]
    else:
        leaves = [unpack(np.sqrt(lam[k]) * V[:, k] / m, i, j) for k in order[:K]]
    if assign == "cluster":
        prof = np.array([np.sqrt(np.sum(l**2, axis=1)) for l in leaves])
        prof /= np.linalg.norm(prof, axis=1, keepdims=True)
        wt = np.array([np.sum(l**2) for l in leaves])
        lab = balanced_kmeans(prof, R, C, wt, seed=seed_id)
        groups = [list(np.flatnonzero(lab == r)) for r in range(R)]
        info["group_weight_share"] = [float(wt[g].sum() / wt.sum()) for g in groups]
    else:
        groups = [list(range(r * C, (r + 1) * C)) if assign == "blocks" else list(range(r, K, R)) for r in range(R)]
    U = np.zeros((R, B, N))
    W = np.zeros((R, B, C))
    for r, ks in enumerate(groups):
        t0 = time.time()
        cand, score = [], []
        for k in ks:
            e, Q = np.linalg.eigh(leaves[k])
            cand.append(Q.T)
            score.append(np.abs(e))
        cand, score = np.concatenate(cand), np.concatenate(score)
        if select == "omp":
            U[r] = omp_bases(cand, np.stack([leaves[k][i, j] for k in ks]), i, j, m, B, 1.0)
        else:
            chosen = []
            for idx in np.argsort(-score):
                v = cand[idx]
                if all(abs(v @ c) < 0.98 for c in chosen):
                    chosen.append(v)
                if len(chosen) == B:
                    break
            U[r] = np.stack(chosen)
        u = U[r] / np.linalg.norm(U[r], axis=1, keepdims=True)
        Pi = (u[:, i] * u[:, j]) * m[None, :]
        for c, k in enumerate(ks):
            W[r, :, c] = np.linalg.lstsq(Pi.T, leaves[k][i, j] * m, rcond=None)[0]
        print(f"group {r} done in {time.time()-t0:.1f}s", flush=True)
    A = np.einsum("rbc,rbp->rcp", W, U[:, :, i] * U[:, :, j]).reshape(-1, len(i)) * m
    e2 = float(np.linalg.norm(A.T @ A - Tw))
    return U, W, info, e2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("R", type=int)
    ap.add_argument("B", type=int)
    ap.add_argument("C", type=int)
    ap.add_argument("--assign", choices=("cluster", "blocks", "roundrobin"), default="cluster")
    ap.add_argument("--leaves", choices=("eig", "chol"), default="chol")
    ap.add_argument("--select", choices=("omp", "eig"), default="omp")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    T, M, i, j, ref, S = target()
    t0 = time.time()
    U, W, info, e2 = seed(a.R, a.B, a.C, (T, M, i, j), a.assign, a.leaves, a.select, a.seed)
    info.update(shape=[a.R, a.B, a.C], error_2_mHa=1e3 * e2, seconds=round(time.time() - t0, 1),
                assign=a.assign, leaves=a.leaves, select=a.select)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(a.out, U=U, W=W, H2_I=W.sum(axis=1),
             H1_I=np.float32(load_fixed_shifts()["H1_I"]), Hsym_lower=np.asarray(load_fixed_shifts()["Hsym_lower"], np.float32))
    print(json.dumps(info, indent=1))


if __name__ == "__main__":
    main()
