"""Fixed-dictionary w-solver for the chemistry leg.

U is FROZEN at the shipped 8-bit word set (so `angle_words` / `tree_edges` never
change); only the (R,B,C) weights w move, and W (the identity offsets, stored as
H2_I = wB = W + sum_b w) is re-chosen afterwards.  Objective is the exact
full-space metric of the verifier, in the (2926,2926) vech form:

    f(w) = || Y Y^T - H ||_F^2 ,   Y[:, r*C+c] = P_r w[r][:, c],
    P_r[:, b] = vech(u_b u_b^T) with off-diagonal weight sqrt(2).

Coordinates.  With G_r = P_r^T P_r and Q_r = P_r G_r^{-1/2} (orthonormal columns),
y_r = G_r^{1/2} w_r gives Y_r = Q_r y_r and ||Y_r||_F = ||y_r||_F.  Everything
reduces to the small blocks

    C_rs = Q_r^T Q_s ,   H_rs = Q_r^T H Q_s      (B x B each),

so one f+grad evaluation costs ~1e8 flops instead of 3e9:

    M_rs = y_r^T y_s                       (C x C)
    f    = sum_rs ||M_rs||_F^2 - 2 sum_rs tr(y_r^T H_rs y_s) + ||H||_F^2
    g_r  = 4 [ (sum_s y_s y_s^T) y_r - sum_s H_rs y_s ]

Gauss-Newton operator (J dY = dY Y^T + Y dY^T, J^T Z = 2 Z Y):

    A(dy)_r = 2 [ sum_s C_rs dy_s M_sr + sum_s C_rs y_s (dy_s^T C_sr y_r) ]

solved by conjugate gradients with Levenberg-Marquardt damping and a backtracking
line search on the true objective.  Joint solve: the whole B x C block per group
moves at once, no per-column coordinate descent.
"""
import sys
import time

import numpy as np

T0 = time.time()


def log(*a):
    print(f'[{time.time()-T0:7.1f}s]', *a, flush=True)


# --------------------------------------------------------------------- pair space
def build_pair_space(V):
    """(2926,2926) vech target H from the packaged FCIDUMP, plus PA/sqw/ref."""
    import importlib.util

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        m = importlib.util.module_from_spec(spec)
        sys.modules[name] = m
        spec.loader.exec_module(m)
        return m

    refm = load('dfthcsos.scoreinfra.reference', f'{V}/scoreinfra/reference.py')
    dfm = load('dfthcsos.scoreinfra.dfthc_math', f'{V}/scoreinfra/dfthc_math.py')
    ref = refm.load_reference(refm.check_fcidump())
    N = int(np.asarray(ref['tei']).shape[0])
    S = dfm.symmetric_from_lower(refm.load_fixed_shifts()['Hsym_lower'], N).astype(np.float64)
    tei = np.asarray(ref['tei'], dtype=np.float64)
    pairs = [(p, q) for p in range(N) for q in range(p, N)]
    PA = np.array(pairs)
    sqw = np.sqrt(np.array([1.0 if p == q else 2.0 for p, q in pairs]))
    flat = np.array([p * N + q for p, q in pairs])
    isdiag = np.array([p == q for p, q in pairs])
    tei2 = tei.reshape(N * N, N * N)
    Gm = np.empty((len(pairs), len(pairs)))
    for a, (p, q) in enumerate(pairs):
        Gm[a] = (tei2[p * N + q, flat] + 0.5 * S[p, q] * isdiag
                 + 0.5 * S.ravel()[flat] * (1.0 if p == q else 0.0))
    Gm = 0.5 * (Gm + Gm.T)
    H = sqw[:, None] * Gm * sqw[None, :]
    del tei2, Gm, tei
    return dict(H=H, PA=PA, sqw=sqw, ref=ref, S=S, dfm=dfm, refm=refm, N=N)


def frame(Ug, PA, sqw):
    Pm = np.einsum('bp,bq->bpq', Ug, Ug, optimize=True)
    return np.ascontiguousarray((Pm[:, PA[:, 0], PA[:, 1]] * sqw[None, :]).T)


# --------------------------------------------------------------------- the solver
class FixedU:
    def __init__(self, U, H, PA, sqw, eig_floor=1e-12):
        self.R, self.B, self.N = U.shape
        self.U = U / np.linalg.norm(U, axis=2, keepdims=True)
        self.H = H
        self.Hfro2 = float(np.sum(H * H))
        R, B = self.R, self.B
        self.Ps, self.Gs, self.Qs, self.ginv = [], [], [], []
        for r in range(R):
            P = frame(self.U[r], PA, sqw)
            G = 0.5 * (P.T @ P + (P.T @ P).T)
            g, Vv = np.linalg.eigh(G)
            g = np.maximum(g, eig_floor * max(g.max(), 1.0))
            self.Ps.append(P)
            self.Gs.append(G)
            self.ginv.append((Vv, 1.0 / np.sqrt(g), Vv.T))
            self.Qs.append(P @ ((Vv / np.sqrt(g)) @ Vv.T))
        HQ = H @ np.concatenate(self.Qs, axis=1)
        self.C = [[self.Qs[r].T @ self.Qs[s] for s in range(R)] for r in range(R)]
        self.Hd = [self.Qs[r].T @ HQ[:, r * B:(r + 1) * B] for r in range(R)]
        self.Hd = [0.5 * (a + a.T) for a in self.Hd]
        del HQ
        cond = max(np.linalg.cond(G) for G in self.Gs)
        log(f'FixedU: R={R} B={B} N={self.N} cond(G) {cond:.3e} ||H||_F {np.sqrt(self.Hfro2):.6f}')

    # ---- coordinates
    def y_from_w(self, w):
        out = []
        for r in range(self.R):
            Vv, si, Vt = self.ginv[r]
            out.append((Vv * np.sqrt(1.0 / si ** 2)) @ (Vt @ w[r]))
        return out

    def w_from_y(self, y):
        out = np.zeros((self.R, self.B, y[0].shape[1]))
        for r in range(self.R):
            Vv, si, Vt = self.ginv[r]
            out[r] = (Vv * si) @ (Vt @ y[r])
        return out

    # ---- objective.  The group spans overlap (C_rs = Q_r^T Q_s != 0), so the Gram
    # blocks of Y are P_rs = y_r^T C_rs y_s, not y_r^T y_s.  The one-body term is
    # tr(Y^T H Y) = sum_r tr(y_r^T H_rr y_r)  (diagonal blocks only).
    def fg(self, y):
        R = self.R
        Cy = [[self.C[r][s] @ y[s] for s in range(R)] for r in range(R)]
        P = [[y[r].T @ Cy[r][s] for s in range(R)] for r in range(R)]
        f = sum(float(np.sum(P[r][s] * P[r][s])) for r in range(R) for s in range(R))
        Hy = [self.Hd[r] @ y[r] for r in range(R)]
        tr = 0.0
        for r in range(R):
            tr += float(np.sum(y[r] * Hy[r]))
        f = f - 2.0 * tr + self.Hfro2
        g = []
        for r in range(R):
            acc = np.zeros_like(y[r])
            for s in range(R):
                acc += self.C[r][s] @ (y[s] @ P[s][r])
            g.append(4.0 * (acc - Hy[r]))
        return f, g

    def fonly(self, y):
        R = self.R
        acc = 0.0
        tr = 0.0
        for r in range(R):
            for s in range(R):
                Pm = y[r].T @ (self.C[r][s] @ y[s])
                acc += float(np.sum(Pm * Pm))
            tr += float(np.sum(y[r] * (self.Hd[r] @ y[r])))
        return acc - 2.0 * tr + self.Hfro2

    def A(self, y, dy):
        R = self.R
        Cy = [[self.C[r][s] @ y[s] for s in range(R)] for r in range(R)]
        Ps = [[y[s].T @ Cy[s][r] for r in range(R)] for s in range(R)]   # Ps[s][r] = P_sr
        CY = [self.C[r] for r in range(R)]
        out = []
        for r in range(R):
            acc = np.zeros_like(dy[r])
            for s in range(R):
                acc += CY[r][s] @ (dy[s] @ Ps[s][r])
            for s in range(R):
                acc += (CY[r][s] @ y[s]) @ (dy[s].T @ CY[s][r] @ y[r])
            out.append(2.0 * acc)
        return out

    # ---- exact full-space error (mHa)
    def e2_mha(self, y):
        Y = np.concatenate([self.Qs[r] @ y[r] for r in range(self.R)], axis=1)
        Res = Y @ Y.T
        Res -= self.H
        return 1e3 * float(np.linalg.norm(Res))

    # ---- LM + CG
    def solve(self, y, iters=40, cg_iters=200, lam0=None, gtol=1e-10, wall=None,
              tag='', verbose=True, exact_every=0):
        y = [a.copy() for a in y]
        f, g = self.fg(y)
        gnorm2 = float(sum(np.sum(a * a) for a in g))
        lam = (lam0 if lam0 is not None else max(f, 1e-12) / max(gnorm2, 1e-300))
        lam = min(max(lam, 1e-12), 1e4)
        hist = []
        t0 = time.time()
        for it in range(iters):
            if verbose:
                ex = f'  exact {self.e2_mha(y):9.4f}' if (exact_every and it % exact_every == 0) else ''
                log(f'  {tag} it{it:03d} e2 {1e3*np.sqrt(max(f,0)):9.4f} mHa{ex}  lam {lam:.2e}'
                    f'  |g| {np.sqrt(gnorm2):.2e}  [{time.time()-t0:.0f}s]')
            hist.append((it, 1e3 * np.sqrt(max(f, 0.0)), lam))
            if gnorm2 < gtol:
                break
            dy = [np.zeros_like(a) for a in y]
            r = [-a.copy() for a in g]
            p = [a.copy() for a in r]
            rs = float(sum(np.sum(a * a) for a in r))
            rs0 = max(rs, 1e-300)
            for k in range(cg_iters):
                Ap = self.A(y, p)
                den = lam * float(sum(np.sum(a * a) for a in p)) \
                    + float(sum(np.sum(p[i] * Ap[i]) for i in range(len(p))))
                if den <= 0 or not np.isfinite(den):
                    break
                alpha = rs / den
                for i in range(len(y)):
                    dy[i] += alpha * p[i]
                    r[i] -= alpha * (Ap[i] + lam * p[i])
                rs_new = float(sum(np.sum(a * a) for a in r))
                if not np.isfinite(rs_new) or rs_new < 1e-12 * rs0:
                    break
                for i in range(len(p)):
                    p[i] = r[i] + (rs_new / rs) * p[i]
                rs = rs_new
            step, accepted = 1.0, False
            for _ in range(30):
                yt = [y[i] + step * dy[i] for i in range(len(y))]
                ft = self.fonly(yt)
                if np.isfinite(ft) and ft < f:
                    y, f, g = yt, ft, None
                    f, g = self.fg(y)
                    accepted = True
                    lam = max(lam * 0.2, 1e-12)
                    break
                step *= 0.5
            if not accepted:
                lam *= 10.0
                if lam > 1e8:
                    log(f'  {tag}: LM stalled')
                    break
            gnorm2 = float(sum(np.sum(a * a) for a in g))
            if wall and time.time() - t0 > wall:
                log(f'  {tag}: wall hit at it{it}')
                break
        e2 = self.e2_mha(y)
        if verbose:
            log(f'  {tag} FINAL cheap {1e3*np.sqrt(max(f,0)):.4f}  exact {e2:.4f} mHa')
        hist.append(('final', e2, lam))
        return y, hist


def rank_truncate(y, C):
    """Drop columns down to C in the *collective* gauge (shape (B,C) result).

    The c index is only defined up to a common rotation across groups, so the
    truncation uses the right singular vectors of the stacked (R*B, C_old)
    matrix; keeping the first C columns then removes the least-energy collective
    directions.  NOTE: an earlier version kept (B, C_old) with rank C -- that is
    a *different* (and invalid for the cost model) family; see RESULT3.md §3.
    """
    st = np.concatenate(y, axis=0)
    Uu, ss, Vt = np.linalg.svd(st, full_matrices=False)
    O = Vt.T
    return [(a @ O)[:, :C].copy() for a in y]
