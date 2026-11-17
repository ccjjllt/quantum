"""Shape fits on the exact error_2 objective (local port of the k_bc_axis kernel).

    error_2^2 = ||Y Y^T - H||_F^2,   Y[:, r*C+c] = P_r w_rc,
    P_r[:, b] = sqrt-weight vech(u_b u_b^T)

H is the (2926, 2926) vech target built from the packaged FCIDUMP. The
optimization runs in the top-RANK eigenspace (~0.1 s per objective); final
numbers are re-evaluated in the full space and with the official verifier code.
"""
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).parent))
import infra as I

N = 76
T0 = time.time()


def log(*a):
    print(f'[{time.time()-T0:7.1f}s]', *a, flush=True)


class Problem:
    """Exact full-space error_2 objective: f = ||Y Y^T - H||_F^2, no truncation.

    Uses  f = ||Y^T Y||_F^2 - 2 <Y, H Y> + ||H||_F^2  and
          dF/dY = 4 (Y (Y^T Y) - H Y),
    so one objective+gradient costs two `H @ Y` products and two small (K x K)
    products -- cheaper than the 800-rank eigenspace version and exact.
    """

    def __init__(self):
        ps = I.cached_pair_space()
        self.H, self.PA, self.sqw = ps['H'], ps['PA'], ps['sqw']
        self.NS = ps['NS']
        ev = np.linalg.eigvalsh(self.H)[::-1]
        self.ev = ev
        self.neg2 = float(np.sum(np.minimum(ev, 0) ** 2))
        self.Hfro2 = float(np.sum(self.H * self.H))
        log(f'Problem: NS {self.NS} ||H||_F {np.sqrt(self.Hfro2):.6f} '
            f'floor(K=352) {I.floor_mha(ev, 352, self.neg2):.3f} '
            f'floor(K=480) {I.floor_mha(ev, 480, self.neg2):.3f} mHa')

    def floor(self, K):
        return I.floor_mha(self.ev, K, self.neg2)

    # ---------------------------------------------------------------- objective
    def proj(self, U):
        P = np.einsum('bp,bq->bpq', U, U, optimize=True)
        return np.ascontiguousarray((P[:, self.PA[:, 0], self.PA[:, 1]] * self.sqw[None, :]).T)

    def fg(self, x, R, B, C):
        nw = R * B * C
        w = x[:nw].reshape(R, B, C)
        U = x[nw:].reshape(R, B, N)
        nrm = np.linalg.norm(U, axis=2, keepdims=True)
        Uhat = U / np.maximum(nrm, 1e-12)
        Y = np.zeros((self.NS, R * C))
        Ps, Us = [], []
        for r in range(R):
            P = self.proj(Uhat[r])
            Ps.append(P)
            Us.append(Uhat[r])
            Y[:, r * C:(r + 1) * C] = P @ w[r]
        G = Y.T @ Y                                   # (K,K)
        HY = self.H @ Y                               # (NS,K)
        f = float(np.sum(G * G)) - 2.0 * float(np.sum(Y * HY)) + self.Hfro2
        gY = 4.0 * (Y @ G - HY)                        # 4 (YY^T - H) Y
        gw = np.empty((R, B, C))
        gU = np.empty((R, B, N))
        for r in range(R):
            gw[r] = Ps[r].T @ gY[:, r * C:(r + 1) * C]
        for r in range(R):
            Z = (gY[:, r * C:(r + 1) * C] @ w[r].T) * self.sqw[:, None]   # (NS,B)
            A = np.zeros((B, N, N))
            A[:, self.PA[:, 0], self.PA[:, 1]] = Z.T
            A = np.triu(A) + np.swapaxes(np.triu(A, 1), -1, -2)
            g = np.einsum('bpq,bq->bp', A, Us[r], optimize=True) \
                + A[:, np.arange(N), np.arange(N)] * Us[r]
            # chain rule through uhat = u/||u||
            g = (g - np.sum(g * Us[r], axis=1, keepdims=True) * Us[r]) / np.maximum(nrm[r], 1e-12)
            gU[r] = g
        return f, np.concatenate([gw.ravel(), gU.ravel()])

    def e2_reduced(self, x, R, B, C):
        return 1e3 * np.sqrt(max(self.fg(x, R, B, C)[0], 0.0))

    def e2_full(self, x, R, B, C):
        """Full-space error_2 (mHa) of the fitted (U, w)."""
        nw = R * B * C
        w = x[:nw].reshape(R, B, C)
        U = x[nw:].reshape(R, B, N)
        U = U / np.linalg.norm(U, axis=2, keepdims=True)
        Y = self.Y_of(U, w)
        return I.e2_pair(Y, self.H)

    def Y_of(self, U, w):
        R, B, C = w.shape
        Y = np.zeros((self.NS, R * C))
        for r in range(R):
            Y[:, r * C:(r + 1) * C] = self.proj(U[r]) @ w[r]
        return Y


def merge(z, x, mask):
    y = x.copy()
    y[mask] = z
    return y


def alt_min(pb: Problem, x, R, B, C, rounds, itw, itu, tag='', wall=None):
    nw = R * B * C
    t0 = time.time()
    for rd in range(rounds):
        m = np.zeros_like(x, bool)
        m[:nw] = True
        r1 = minimize(lambda z: pb.fg(merge(z, x, m), R, B, C)[0], x[m],
                      jac=lambda z: pb.fg(merge(z, x, m), R, B, C)[1][m], method='L-BFGS-B',
                      options=dict(maxiter=itw, maxcor=20, ftol=1e-20, gtol=1e-16))
        x = merge(r1.x, x, m)
        m = ~m
        r2 = minimize(lambda z: pb.fg(merge(z, x, m), R, B, C)[0], x[m],
                      jac=lambda z: pb.fg(merge(z, x, m), R, B, C)[1][m], method='L-BFGS-B',
                      options=dict(maxiter=itu, maxcor=20, ftol=1e-20, gtol=1e-16))
        x = merge(r2.x, x, m)
        log(f'  {tag} round {rd}: reduced {pb.e2_reduced(x, R, B, C):.3f} mHa '
            f'(w {r1.nit} it, u {r2.nit} it) [{time.time()-t0:.0f}s]')
        if wall and time.time() - t0 > wall:
            log(f'  {tag}: wall hit')
            break
    return x


# --------------------------------------------------------------------- inits
def init_from_targets(pb, Xs, R, B, C, seed=0, nclust_iter=30):
    """Basis/weights from a list of K target symmetric matrices (K = R*C).

    Cluster the K targets by their leading orbital into R groups (balanced),
    take the B leading eigenvectors of each group's sum X_k X_k^T as the basis,
    then least-squares the weights.
    """
    rng = np.random.default_rng(seed)
    K = len(Xs)
    lead = []
    for X in Xs:
        ev, evec = np.linalg.eigh(X)
        v = evec[:, -1]
        if v[int(np.argmax(np.abs(v)))] < 0:
            v = -v
        lead.append(v)
    lead = np.array(lead)
    cent = [lead[int(np.argmax(np.linalg.norm(lead, axis=1)))]]
    while len(cent) < R:
        d = np.min([np.sum((lead - c) ** 2, axis=1) for c in cent], axis=0)
        cent.append(lead[int(np.argmax(d))])
    cent = np.array(cent)
    for _ in range(nclust_iter):
        d = np.stack([np.sum((lead - c) ** 2, axis=1) for c in cent], axis=1)
        lab = np.argmin(d, axis=1)
        for r in range(R):
            if np.any(lab == r):
                cent[r] = lead[lab == r].mean(axis=0)
    # balanced assignment: each group exactly C
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
    U = np.zeros((R, B, N))
    w = np.zeros((R, B, C))
    for r in range(R):
        idx = np.flatnonzero(assign == r)
        agg = sum(Xs[k] @ Xs[k] for k in idx)
        _, V2 = np.linalg.eigh(agg)
        base = V2[:, ::-1].T[:min(B, N)].copy()
        if B > N:
            extra = rng.standard_normal((B - N, N))
            extra -= extra @ base.T @ base
            base = np.vstack([base, extra])
        if B < N:
            base = V2[:, ::-1].T[:B].copy()
        U[r] = base / np.linalg.norm(base, axis=1, keepdims=True)
        Hh = np.stack([np.sum((U[r] @ Xs[k]) * U[r], axis=1) for k in idx], axis=1)
        UtU = U[r] @ U[r].T
        w[r] = np.linalg.lstsq(UtU * UtU, Hh, rcond=1e-12)[0]
    return np.concatenate([w.ravel(), U.ravel()])


def targets_from_shipped_plus_residual(pb, Xs0, K):
    """K target columns = the shipped X columns + the top residual directions."""
    Y0 = np.zeros((pb.NS, len(Xs0)))
    for k, X in enumerate(Xs0):
        M = np.zeros((N, N))
        M[pb.PA[:, 0], pb.PA[:, 1]] = 1.0
        # vech of X
        Y0[:, k] = X[pb.PA[:, 0], pb.PA[:, 1]] * pb.sqw
    Res = pb.H - Y0 @ Y0.T
    ev, evec = np.linalg.eigh(Res)
    ev, evec = ev[::-1], evec[:, ::-1]
    extra = []
    for j in range(K - len(Xs0)):
        if ev[j] <= 0:
            break
        v = evec[:, j]
        M = np.zeros((N, N))
        M[pb.PA[:, 0], pb.PA[:, 1]] = v / pb.sqw
        M = np.triu(M) + np.triu(M, 1).T
        extra.append(np.sqrt(ev[j]) * M)
    return list(Xs0) + extra


def init_rank1(pb, Xs, R, B, C, seed=0):
    """One projector per column + B-C extra projectors, grouped by leading orbital.

    Each target column is initialised as its own leading rank-1 projector
    (that is the B/C -> 1 limit), and the surplus B - C basis vectors are the
    second orbitals of the largest columns. The weights are then a least
    squares in each group's frame.
    """
    rng = np.random.default_rng(seed)
    K = len(Xs)
    assert K == R * C
    lead = np.zeros((K, N))
    second = np.zeros((K, N))
    top = np.zeros(K)
    for k, X in enumerate(Xs):
        ev, evec = np.linalg.eigh(X)
        v = evec[:, -1]
        if v[int(np.argmax(np.abs(v)))] < 0:
            v = -v
        lead[k] = v
        second[k] = evec[:, -2]
        top[k] = ev[-1]
    # balanced k-means on the leading orbitals
    cent = [lead[int(np.argmax(np.linalg.norm(lead, axis=1)))]]
    while len(cent) < R:
        d = np.min([np.sum((lead - c) ** 2, axis=1) for c in cent], axis=0)
        cent.append(lead[int(np.argmax(d))])
    cent = np.array(cent)
    for _ in range(30):
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
    U = np.zeros((R, B, N))
    w = np.zeros((R, B, C))
    for r in range(R):
        idx = np.flatnonzero(assign == r)
        base = [lead[k] for k in idx]
        extra = B - len(base)
        order = idx[np.argsort(-np.abs(top[idx]))] if extra > 0 else idx[:0]
        pool = [second[k] for k in order] + [lead[k] for k in idx[::-1]]
        cand = []
        for v in pool:
            v = v / np.linalg.norm(v)
            if all(abs(v @ b) < 0.999 for b in base + cand):
                cand.append(v)
            if len(cand) == extra:
                break
        while len(cand) < extra:
            v = rng.standard_normal(N)
            v -= sum((v @ b) * b for b in base + cand)
            v /= np.linalg.norm(v)
            cand.append(v)
        Ub = np.array(base + cand)
        U[r] = Ub / np.linalg.norm(Ub, axis=1, keepdims=True)
        Hh = np.stack([np.sum((U[r] @ Xs[k]) * U[r], axis=1) for k in idx], axis=1)
        UtU = U[r] @ U[r].T
        w[r] = np.linalg.lstsq(UtU * UtU, Hh, rcond=1e-10)[0]
    return np.concatenate([w.ravel(), U.ravel()])


def init_truncate(pb, x_ship, R_old, B_old, C, B_new, seed=0):
    """Keep the B_new most-used basis vectors of each shipped group, re-solve w."""
    w_old = x_ship[:R_old * B_old * C].reshape(R_old, B_old, C)
    U_old = x_ship[R_old * B_old * C:].reshape(R_old, B_old, N)
    U_old = U_old / np.linalg.norm(U_old, axis=2, keepdims=True)
    X = np.einsum('gbp,gbq,gbc->gcpq', U_old, U_old, w_old, optimize=True)
    U = np.zeros((R_old, B_new, N))
    w = np.zeros((R_old, B_new, C))
    for r in range(R_old):
        use = np.abs(w_old[r]).sum(axis=1)
        keep = np.argsort(-use)[:B_new]
        U[r] = U_old[r][keep]
        Hh = np.stack([np.sum((U[r] @ X[r, c]) * U[r], axis=1) for c in range(C)], axis=1)
        UtU = U[r] @ U[r].T
        w[r] = np.linalg.lstsq(UtU * UtU, Hh, rcond=1e-10)[0]
    return np.concatenate([w.ravel(), U.ravel()])


def init_select(pb, Xs, R, B, C, U_pool, seed=0):
    """Group the targets, then pick each group's B basis vectors from a pool.

    The pool is the shipped solution's 1144 unit orbitals -- proven-good
    rank-1 directions -- scored by sum_k |u^T X_k u| over the group's targets.
    """
    rng = np.random.default_rng(seed)
    K = len(Xs)
    assert K == R * C
    lead = np.zeros((K, N))
    for k, X in enumerate(Xs):
        ev, evec = np.linalg.eigh(X)
        v = evec[:, -1]
        if v[int(np.argmax(np.abs(v)))] < 0:
            v = -v
        lead[k] = v
    cent = [lead[int(np.argmax(np.linalg.norm(lead, axis=1)))]]
    while len(cent) < R:
        d = np.min([np.sum((lead - c) ** 2, axis=1) for c in cent], axis=0)
        cent.append(lead[int(np.argmax(d))])
    cent = np.array(cent)
    for _ in range(30):
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
    pool = U_pool / np.linalg.norm(U_pool, axis=1, keepdims=True)
    U = np.zeros((R, B, N))
    w = np.zeros((R, B, C))
    for r in range(R):
        idx = np.flatnonzero(assign == r)
        # score every pool orbital on every target of the group
        T = np.stack([Xs[k] for k in idx], axis=0)             # (C,N,N)
        # (P, C) = u_p^T X_k u_p
        S_ = np.einsum('pn,knm,pm->pk', pool, T, pool, optimize=True)
        score = np.abs(S_).sum(axis=1)
        pick = np.argsort(-score)[:B]
        U[r] = pool[pick]
        Hh = np.stack([np.sum((U[r] @ Xs[k]) * U[r], axis=1) for k in idx], axis=1)
        UtU = U[r] @ U[r].T
        w[r] = np.linalg.lstsq(UtU * UtU, Hh, rcond=1e-10)[0]
    return np.concatenate([w.ravel(), U.ravel()])


def shipped_Xs(z):
    U, w = z['U'], z['W']
    R, B, Nn = U.shape
    X = np.einsum('gbp,gbq,gbc->gcpq', U, U, w, optimize=True)
    out = []
    for r in range(R):
        for c in range(w.shape[2]):
            out.append(X[r, c])
    return out
