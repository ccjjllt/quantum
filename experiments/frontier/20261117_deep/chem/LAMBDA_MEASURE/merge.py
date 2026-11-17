"""Merge the group axis R -> R-1 at fixed (B,C) and refit.

One merge step:
  1. pick the pair (i,j) whose combined C+C columns lose least under a rank-C
     truncation (exact Gram loss, all pairs scored);
  2. the merged group's columns are that top-C truncation, its basis is the B
     best orbitals out of the union of the two groups' 2B (scored on |u^T X u|);
  3. GN sweeps on the merged group alone, then alternating u-L-BFGS + GN on all
     groups.

Usage: merge.py name  -> chains name's R down to 5, reporting every stage.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).parent))
import fitlib as F
import infra as I
from gn import unpack, pack, gn_w, fval

log = F.log
N = F.N


def gram_error(pb, Ys):
    tot = sum(Y @ Y.T for Y in Ys)
    return 1e3 * float(np.linalg.norm(tot - pb.H))


def best_pair(pb, Ys, C):
    R = len(Ys)
    best = None
    for i in range(R):
        for j in range(i + 1, R):
            M = np.hstack([Ys[i], Ys[j]])
            s = np.linalg.svd(M, compute_uv=False)
            loss = float(np.sum(s[C:] ** 2))
            if best is None or loss < best[0]:
                best = (loss, i, j)
    return best


def unvech(v, sqw):
    M = np.zeros((N, N))
    M[pb.PA[:, 0], pb.PA[:, 1]] = v / sqw
    return np.triu(M) + np.triu(M, 1).T


def merge_once(pb, x, R, B, C, info=None):
    w, U = unpack(x, R, B, C)
    Ys = [pb.proj(U[r]) @ w[r] for r in range(R)]
    e0 = gram_error(pb, Ys)
    loss, i, j = best_pair(pb, Ys, C)
    log(f'  merge pair ({i},{j}): rank-{C} truncation loss {1e3*np.sqrt(loss):.3f} mHa '
        f'(current e2 {e0:.3f})')
    M = np.hstack([Ys[i], Ys[j]])
    Usvd, s, _ = np.linalg.svd(M, full_matrices=False)
    Ynew = Usvd[:, :C] * s[:C]
    # basis: B orbitals out of the union of the two groups
    pool = np.vstack([U[i], U[j]])
    Xs = [unvech(Ynew[:, c], pb.sqw) for c in range(C)]
    T = np.stack(Xs, axis=0)
    S_ = np.einsum('pn,knm,pm->pk', pool, T, pool, optimize=True)
    pick = np.argsort(-np.abs(S_).sum(axis=1))[:B]
    Unew = pool[pick]
    # w for the new group: least squares, then GN on that group alone
    Un = Unew / np.linalg.norm(Unew, axis=1, keepdims=True)
    Hh = np.stack([np.sum((Un @ Xs[k]) * Un, axis=1) for k in range(C)], axis=1)
    UtU = Un @ Un.T
    wnew = np.linalg.lstsq(UtU * UtU, Hh, rcond=1e-10)[0]
    keepU = [U[r] for r in range(R) if r not in (i, j)] + [Unew]
    keepW = [w[r] for r in range(R) if r not in (i, j)] + [wnew]
    Rn = R - 1
    w2 = np.stack(keepW, axis=0)
    U2 = np.stack(keepU, axis=0)
    U2 = U2 / np.linalg.norm(U2, axis=2, keepdims=True)
    x2 = pack(w2, U2)
    Yn = [pb.proj(U2[r]) @ w2[r] for r in range(Rn)]
    log(f'  merged init ({Rn},{B},{C}): e2 {gram_error(pb, Yn):.3f} mHa '
        f'(floor {pb.floor(Rn*C):.3f})')
    # GN on the merged group only
    m = np.zeros(Rn * B * C, bool)
    m[(Rn - 1) * B * C:] = True
    xm = x2.copy()
    for it in range(3):
        xm = gn_w(pb, xm, Rn, B, C, sweeps=1, verbose=False)
        Yn = [pb.proj(unpack(xm, Rn, B, C)[1][r]) @ unpack(xm, Rn, B, C)[0][r] for r in range(Rn)]
        log(f'    after GN({it+1}) on the merged group: {gram_error(pb, Yn):.3f} mHa')
    return xm, Rn


def polish(pb, x, R, B, C, rounds=6, itw=250, itu=120):
    for rd in range(rounds):
        x = gn_w(pb, x, R, B, C, sweeps=1, verbose=False)
        x = F.alt_min(pb, x, R, B, C, rounds=1, itw=itw, itu=itu, tag=f'pol{R}B{B}C{C}')
        log(f'    polish round {rd}: {pb.e2_reduced(x, R, B, C):.3f} mHa')
    return x


if __name__ == '__main__':
    name = sys.argv[1]
    target = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    rounds = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    z = np.load(I.CACHE / f'{name}.npz')
    x, R, B, C = z['x'], int(z['R']), int(z['B']), int(z['C'])
    pb = F.Problem()
    log(f'{name}: ({R},{B},{C}) start {pb.e2_reduced(x, R, B, C):.3f} mHa')
    hist = {R: pb.e2_reduced(x, R, B, C)}
    while R > target:
        x, R = merge_once(pb, x, R, B, C)
        log(f'  == stage ({R},{B},{C}) after merge: {pb.e2_reduced(x, R, B, C):.3f} mHa')
        x = polish(pb, x, R, B, C, rounds=rounds)
        e = pb.e2_reduced(x, R, B, C)
        hist[R] = e
        log(f'  == stage ({R},{B},{C}) FINAL: {e:.3f} mHa = {e/pb.floor(R*C):.2f}x floor '
            f'(rows {N+R*B})')
        np.savez_compressed(I.CACHE / f'merge_{R}_{B}_{C}.npz', x=x, R=R, B=B, C=C)
    (I.CACHE / f'merge_hist_{name}.json').write_text(json.dumps(hist, indent=1))
    log(f'history {hist}')
