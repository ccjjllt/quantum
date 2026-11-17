"""Merge the (8,136,96) solution into the (5,136,96) family and refit.

Source: fit_8_136_96.npz (17.46 mHa). Its 768 columns are rank-truncated to 480,
assigned to 5 balanced groups of 96, each group's 136 basis vectors are selected
from the source's 8*136 orbitals by |u^T X u| scoring, the weights are a least
squares, and the alternating refit follows.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import fitlib as F
import infra as I
from init_span import kmeans_assign

log = F.log
src = np.load(I.CACHE / 'fit_8_136_96.npz')
Rs, Bs, Cs = int(src['R']), int(src['B']), int(src['C'])
ws = src['x'][:Rs * Bs * Cs].reshape(Rs, Bs, Cs)
Us = src['x'][Rs * Bs * Cs:].reshape(Rs, Bs, F.N)
Us = Us / np.linalg.norm(Us, axis=2, keepdims=True)
pb = F.Problem()
Y = pb.Y_of(Us, ws)
log(f'source ({Rs},{Bs},{Cs}) e2 {1e3*np.linalg.norm(Y @ Y.T - pb.H):.3f} mHa, Y {Y.shape}')
U_, S_, _ = np.linalg.svd(Y, full_matrices=False)
R, B, C = 5, 136, 96
K = R * C
Y480 = U_[:, :K] * S_[:K]
log(f'rank-{K} truncation of the source columns: '
    f'{1e3*np.linalg.norm(Y480 @ Y480.T - pb.H):.3f} mHa')
Xs = []
for k in range(K):
    v = Y480[:, k]
    M = np.zeros((F.N, F.N))
    M[pb.PA[:, 0], pb.PA[:, 1]] = v / pb.sqw
    Xs.append(np.triu(M) + np.triu(M, 1).T)
lead = np.zeros((K, F.N))
for k, X in enumerate(Xs):
    ev, evec = np.linalg.eigh(X)
    v = evec[:, -1]
    if v[int(np.argmax(np.abs(v)))] < 0:
        v = -v
    lead[k] = v
assign = kmeans_assign(lead, R, C)
pool = np.concatenate([Us[r] for r in range(Rs)])
U = np.zeros((R, B, F.N))
w = np.zeros((R, B, C))
for r in range(R):
    idx = np.flatnonzero(assign == r)
    T = np.stack([Xs[k] for k in idx], axis=0)
    S_ = np.einsum('pn,knm,pm->pk', pool, T, pool, optimize=True)
    pick = np.argsort(-np.abs(S_).sum(axis=1))[:B]
    U[r] = pool[pick]
    Hh = np.stack([np.sum((U[r] @ Xs[k]) * U[r], axis=1) for k in idx], axis=1)
    UtU = U[r] @ U[r].T
    w[r] = np.linalg.lstsq(UtU * UtU, Hh, rcond=1e-10)[0]
x = np.concatenate([w.ravel(), U.ravel()])
log(f'merged init ({R},{B},{C}) e2 {pb.e2_reduced(x, R, B, C):.3f} mHa '
    f'(floor {pb.floor(K):.3f})')
x = F.alt_min(pb, x, R, B, C, rounds=int(sys.argv[1]) if len(sys.argv) > 1 else 8,
              itw=250, itu=120, tag='merge5')
e = pb.e2_reduced(x, R, B, C)
log(f'FINAL (5,136,96): {e:.3f} mHa = {e/pb.floor(K):.2f}x floor')
np.savez_compressed(I.CACHE / 'fit_5_136_96.npz', x=x, R=R, B=B, C=C)
