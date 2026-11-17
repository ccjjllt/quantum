"""Optimise a B-orbital rank-1-projector span for a set of target columns.

For targets Yt (2926 x n) and a frame P (2926 x B), P[:,b] = vech(u_b u_b^T), the
fraction of the targets' energy inside span(P) is

    capture = tr( (P^T P)^{-1} P^T Yt Yt^T P ) / ||Yt||_F^2 ,

maximised with L-BFGS over the B*76 orbital entries (gradient analytic). This is
the "dictionary" subproblem every DF-THC init needs; unlike the |u^T X u| scoring
heuristic it optimises the thing that matters.
"""
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).parent))
import fitlib as F
import infra as I

N = F.N
P = None


def frame(U, pb):
    P = np.einsum('bp,bq->bpq', U, U, optimize=True)
    return np.ascontiguousarray((P[:, pb.PA[:, 0], pb.PA[:, 1]] * pb.sqw[None, :]).T)


def capture_and_grad(Uf, Yt, pb, B):
    U = Uf.reshape(B, N)
    nrm = np.linalg.norm(U, axis=1, keepdims=True)
    U = U / np.maximum(nrm, 1e-12)
    P = frame(U, pb)
    G = P.T @ P
    G = G + 1e-10 * np.eye(B)
    A = Yt.T @ P                      # (n,B)
    M = A.T @ A
    Gi = np.linalg.inv(G)
    cap = float(np.trace(Gi @ M)) / float(np.sum(Yt * Yt))
    GP = 2.0 * (Yt @ (A @ Gi)) - 2.0 * (P @ (Gi @ M @ Gi))     # (NS,B)
    gU = np.empty((B, N))
    for b in range(B):
        Z = GP[:, b]
        Ab = np.zeros((N, N))
        Ab[pb.PA[:, 0], pb.PA[:, 1]] = Z
        Ab = np.triu(Ab) + np.triu(Ab, 1).T
        g = np.einsum('pq,q->p', Ab, U[b]) + np.diag(Ab) * U[b]
        gU[b] = g
    # chain rule through u/||u||
    gU = (gU - np.sum(gU * U, axis=1, keepdims=True) * U) / np.maximum(nrm, 1e-12)
    return cap, gU.ravel()


def opt_span(Yt, B, U0=None, iters=300, seed=0, tag='', pb=None):
    n = Yt.shape[1]
    rng = np.random.default_rng(seed)
    if pb is None:
        pb = P
    if U0 is None:
        # init: leading eigenvector of each of the top-B covariance directions,
        # rounded to its best rank-1 projector
        C = Yt @ Yt.T if False else None
        ev, evec = np.linalg.eigh(Yt @ Yt.T)
        order = np.argsort(ev)[::-1][:B]
        U0 = np.zeros((B, N))
        for j, i in enumerate(order):
            M = np.zeros((N, N))
            M[pb.PA[:, 0], pb.PA[:, 1]] = evec[:, i] / pb.sqw
            M = np.triu(M) + np.triu(M, 1).T
            w, v = np.linalg.eigh(M)
            U0[j] = v[:, -1]
    x0 = U0.ravel().copy()
    f0, _ = capture_and_grad(x0, Yt, pb, B)
    r = minimize(lambda z: -capture_and_grad(z, Yt, pb, B)[0], x0,
                 jac=lambda z: -capture_and_grad(z, Yt, pb, B)[1], method='L-BFGS-B',
                 options=dict(maxiter=iters, maxcor=20, ftol=1e-18, gtol=1e-14))
    U = r.x.reshape(B, N)
    U = U / np.linalg.norm(U, axis=1, keepdims=True)
    cap = capture_and_grad(U.ravel(), Yt, pb, B)[0]
    F.log(f'   span {tag}: B={B} n={n} capture {100*cap:.4f}% '
          f'(init {100*f0:.3f}%, {r.nit} it) residual '
          f'{1e3*np.sqrt(max((1-cap)*np.sum(Yt*Yt),0)):.2f} mHa-equivalent')
    return U, cap


if __name__ == '__main__':
    pb = F.Problem()
    z = np.load(I.ROOT / 'experiments/frontier/20261117_deep/chem/data/dfthcsos/submission.npz')
    Xs0 = F.shipped_Xs(z)
    U0s = z['U']
    # control: the shipped's own 8 groups, B=143 (a good span provably exists)
    Yt = np.array([(X[pb.PA[:, 0], pb.PA[:, 1]] * pb.sqw) for X in Xs0]).T   # (NS,352)
    for r in range(3):
        Yr = Yt[:, r * 44:(r + 1) * 44]
        opt_span(Yr, 143, U0=U0s[r], tag=f'shipped r{r} (own basis init)')
    # target shape: rank-480 ideal factor, 5 groups of 96, B=136
    ev, evec = np.linalg.eigh(pb.H)
    order = np.argsort(ev)[::-1][:480]
    Yideal = evec[:, order] * np.sqrt(np.maximum(ev[order], 0))
    for r in range(2):
        Yr = Yideal[:, r * 96:(r + 1) * 96]
        opt_span(Yr, 136, tag=f'ideal r{r} (B=136)')
