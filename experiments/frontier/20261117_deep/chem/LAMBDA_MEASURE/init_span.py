"""In-span matching-pursuit init for an arbitrary (R,B,C).

Each column must lie in its group's span, so build it there: pick the basis by
scoring the orbital pool on the assigned targets, then fill the C columns by
greedy matched filtering on the residual *inside that span* (rank-1 updates keep
P^T R P cheap). This is the only init that produced a competitive number at
B/C < 2 so far: (8,143,88) starts at 19.9 mHa this way.
"""
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import fitlib as F
import infra as I

log = F.log


def kmeans_assign(lead, R, C, n_iter=30):
    K = len(lead)
    cent = [lead[int(np.argmax(np.linalg.norm(lead, axis=1)))]]
    while len(cent) < R:
        d = np.min([np.sum((lead - c) ** 2, axis=1) for c in cent], axis=0)
        cent.append(lead[int(np.argmax(d))])
    cent = np.array(cent)
    for _ in range(n_iter):
        d = np.stack([np.sum((lead - c) ** 2, axis=1) for c in cent], axis=1)
        lab = np.argmin(d, axis=1)
        for r in range(R):
            if np.any(lab == r):
                cent[r] = lead[lab == r].mean(axis=0)
    d = np.stack([np.sum((lead - c) ** 2, axis=1) for c in cent], axis=1)
    pref = np.argsort(d, axis=1)
    cnt = np.zeros(R, int)
    assign = -np.ones(K, int)
    for k in range(K):
        for r in pref[k]:
            if cnt[r] < C:
                assign[k] = r
                cnt[r] += 1
                break
    for k in np.flatnonzero(assign < 0):
        r = int(np.argmin(cnt))
        assign[k] = r
        cnt[r] += 1
    return assign


def init_span(pb, Xs, R, B, C, pool, verbose=True):
    K = len(Xs)
    assert K == R * C, (K, R * C)
    lead = np.zeros((K, F.N))
    for k, X in enumerate(Xs):
        ev, evec = np.linalg.eigh(X)
        v = evec[:, -1]
        if v[int(np.argmax(np.abs(v)))] < 0:
            v = -v
        lead[k] = v
    assign = kmeans_assign(lead, R, C)
    pool = pool / np.linalg.norm(pool, axis=1, keepdims=True)
    U = np.zeros((R, B, F.N))
    w = np.zeros((R, B, C))
    Y = np.zeros((pb.NS, R * C))
    for r in range(R):
        idx = np.flatnonzero(assign == r)
        T = np.stack([Xs[k] for k in idx], axis=0)
        S_ = np.einsum('pn,knm,pm->pk', pool, T, pool, optimize=True)
        score = np.abs(S_).sum(axis=1)
        pick = np.argsort(-score)[:B]
        U[r] = pool[pick]
        P = pb.proj(U[r])
        RP = pb.H @ P                       # (NS,B)
        for c in range(C):
            M = P.T @ RP                    # (B,B) = P^T (H - done) P
            M = 0.5 * (M + M.T)
            lam, vec = np.linalg.eigh(M)
            lam = lam[::-1]
            vec = vec[:, ::-1]
            if lam[0] <= 1e-12:
                break
            v = vec[:, 0]
            Pv = P @ v
            nrm = np.linalg.norm(Pv)
            s = np.sqrt(lam[0])
            w[r, :, c] = s * v / (nrm * nrm)
            y = s * Pv / nrm
            Y[:, r * C + c] = y
            RP = RP - np.outer(y, P.T @ y)
        if verbose:
            Yr = Y[:, r * C:(r + 1) * C]
            log(f'   group {r}: assigned {len(idx)} targets, basis {B}, '
                f'e2 so far {1e3*np.linalg.norm(Y @ Y.T - pb.H):.2f} mHa')
    return np.concatenate([w.ravel(), U.ravel()])


if __name__ == '__main__':
    R, B, C = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    rounds = int(sys.argv[4]) if len(sys.argv) > 4 else 6
    K = R * C
    pb = F.Problem()
    z = np.load(I.ROOT / 'experiments/frontier/20261117_deep/chem/data/dfthcsos/submission.npz')
    Xs0 = F.shipped_Xs(z)
    pool = z['U'].reshape(-1, F.N)
    # targets: shipped columns + the top residual directions up to K
    if K <= len(Xs0):
        # take the K largest shipped columns (by Frobenius norm)
        order = np.argsort([-np.linalg.norm(X) for X in Xs0])[:K]
        tg = [Xs0[i] for i in order]
    else:
        tg = F.targets_from_shipped_plus_residual(pb, Xs0, K)
    log(f'shape ({R},{B},{C}) K {K} rows {F.N+R*B} floor {pb.floor(K):.3f}; '
        f'{len(tg)} targets')
    x = init_span(pb, tg, R, B, C, pool)
    log(f'init e2 {pb.e2_reduced(x, R, B, C):.3f} mHa')
    x = F.alt_min(pb, x, R, B, C, rounds=rounds, itw=250, itu=120, tag=f'span{R}_{B}_{C}')
    e = pb.e2_reduced(x, R, B, C)
    log(f'FINAL ({R},{B},{C}): {e:.3f} mHa = {e/pb.floor(K):.2f}x floor')
    np.savez_compressed(I.CACHE / f'fit_{R}_{B}_{C}.npz', x=x, R=R, B=B, C=C)
