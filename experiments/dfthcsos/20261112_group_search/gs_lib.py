"""Shared machinery for the dfthcsos group-selection search.

The model:  A = sum_rc x_rc x_rc^T,  x_rc = sum_b w_rbc p_b,  p_b = vec(u_b u_b^T),
so A = P M P^T with M = sum_rc w_rc w_rc^T block diagonal by group (rank <= C per block).
error_2^2 = tr((M G)^2) - 2 tr(M Q0) + ||T||^2,  G = P^T P,  Q0 = P^T T P.

Because the 1144 rows are distinct, the 8 groups of 143 are a *partition* of the rows: regrouping
is free (same directions, same 8-bit words up to row order, same T/Q) and only changes which pairs
can co-occur.  Everything below works in the 1144-dim coordinate space so a partition costs
milliseconds before the refit.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
os.environ.setdefault('DFTHC_DATA', str(ROOT / 'data' / 'competition'))
sys.path.insert(0, str(ROOT / 'data/competition/verifiers'))
sys.path.insert(0, str(ROOT / 'artifacts/20261112_chem_pipeline/dfthc_refit'))

import encode  # noqa: E402
import onebody  # noqa: E402
import refit_weights as rw  # noqa: E402
from dfthcsos.verify import evaluate_words, heuristic_costs, load_inputs  # noqa: E402

SUB = ROOT / 'artifacts/20261112_eae_candidate/dfthcsos/submission.npz'
OUT = Path(__file__).resolve().parent
ART = Path('/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dfthcsos/artifacts/20261112_group_search')
ART.mkdir(parents=True, exist_ok=True)
N = 76
BROT = 8
GAP_FLOOR = 3.914898


def load_current():
    with np.load(SUB, allow_pickle=False) as z:
        return {k: np.array(z[k]) for k in z.files}


def target(inp):
    Nn = inp.num_orbitals
    T = np.asarray(inp.ref['tei'], np.float64).reshape(Nn * Nn, Nn * Nn).copy()
    eye = np.eye(Nn).ravel()
    T += 0.5 * (np.outer(inp.S.ravel(), eye) + np.outer(eye, inp.S.ravel()))
    return T


class Space:
    """Precomputed p-vectors, Gram, block target and low-dim coordinates (one per U)."""

    def __init__(self, U, inp):
        self.inp = inp
        self.R, self.B, _ = U.shape
        self.C = inp.w.shape[2]
        u = np.asarray(U, np.float64)
        u = u / np.linalg.norm(u, axis=2, keepdims=True)
        self.u = u
        self.p = np.einsum('rbp,rbq->rbpq', u, u).reshape(self.R * self.B, N * N)
        T = target(inp)
        self.T = T
        self.normT2 = float(np.linalg.norm(T) ** 2)
        self.p_thc = {}
        self.G = self.p @ self.p.T
        self.Q0 = self.p @ T @ self.p.T
        self.Q0 = 0.5 * (self.Q0 + self.Q0.T)
        # low-dim coordinates: orthonormal basis of span{p_b}
        self.Q, _ = np.linalg.qr(self.p.T)
        self.Cmat = self.Q.T @ self.p.T                    # (D, D) coordinates of each p_b
        self.Ts = self.Q.T @ (T @ self.Q)
        self.Ts = 0.5 * (self.Ts + self.Ts.T)
        self.outside2 = max(self.normT2 - float(np.linalg.norm(self.Ts) ** 2), 0.0)

    # -- objective -------------------------------------------------------
    def error2(self, w, perm=None):
        """||P M P^T - T|| for w (R,B,C), exact and fast via the block form.

        Group r of w owns rows perm[r*B:(r+1)*B] of the original table.
        """
        M = np.zeros_like(self.G)
        for r, b in enumerate(self.blocks_from_w(w, perm)):
            M[np.ix_(b, b)] = w[r] @ w[r].T
        return self.error2_M(M)

    def error2_M(self, M):
        A = M @ self.G
        val = float(np.sum(A * A.T)) - 2 * np.trace(M @ self.Q0) + self.normT2
        return float(np.sqrt(max(val, 0.0)))

    def init_W(self, w, perm, w_ref, W_ref):
        """Offsets W (R,C) reproducing the reference h1' correction with the new w."""
        k_ref = np.einsum('rc,rbc->rb', W_ref, w_ref)
        C_tot = np.einsum('rb,rbp,rbq->pq', k_ref, self.u, self.u, optimize=True)
        pidx = np.arange(self.R * self.B) if perm is None else np.asarray(perm)
        up = self.u.reshape(self.R * self.B, N)[pidx].reshape(self.R, self.B, N)
        D = np.zeros((N * N, self.R * self.C))
        for r in range(self.R):
            for c in range(self.C):
                D[:, r * self.C + c] = np.einsum('b,bp,bq->pq', w[r, :, c], up[r], up[r]).ravel()
        sol = np.linalg.lstsq(D, C_tot.ravel(), rcond=None)[0]
        return sol.reshape(self.R, self.C)

    def blocks_from_w(self, w, perm=None):
        R, B = w.shape[:2]
        perm = np.arange(R * B) if perm is None else np.asarray(perm)
        return [perm[r * B:(r + 1) * B] for r in range(R)]

    # -- initialisation --------------------------------------------------
    def block_init(self, perm, blocks, rank=None):
        """Best rank-`rank` PSD fit of T inside each group's span, as w (R,B,C).

        perm  : list of 1144 row indices, group r owns perm[r*B:(r+1)*B] in table order
        blocks: the same partition as index arrays into perm order
        """
        R, B, C = self.R, self.B, self.C
        rank = C if rank is None else rank
        w = np.zeros((R, B, C))
        Ts = self.Ts
        Cm = self.Cmat
        for r in range(R):
            idx = np.asarray(perm)[np.asarray(blocks[r])]
            coords = Cm[:, idx]                       # (D, B)
            Qr, _ = np.linalg.qr(coords)              # (D, B)
            Bm = Qr.T @ Ts @ Qr
            ev, V = np.linalg.eigh(Bm)
            order = np.argsort(-ev)[:rank]
            lam = np.maximum(ev[order], 0.0)
            Xs = Qr @ (V[:, order] * np.sqrt(lam))    # (D, rank)
            rhs = coords.T @ Xs                       # (B, rank)
            w[r] = np.linalg.solve(self.G[np.ix_(idx, idx)], rhs)
        return w

    def bcd_init(self, perm, sweeps=6, log=None):
        """Joint block-coordinate fit of the block-diagonal rank-C model to Ts.

        The blocks' spans overlap heavily, so fitting each block to T separately double counts
        (sum of the eight block traces >> trace T).  Here each block is fitted to the *residual*
        of the others, compressed to its span, with the top-C positive eigenpairs; the sweep is
        monotone in ||sum_r Xi_r Xi_r^T - Ts||.
        """
        perm = np.asarray(perm)
        R, B, C = self.R, self.B, self.C
        spans, coords, Xis = [], [], []
        for r in range(R):
            idx = perm[r * B:(r + 1) * B]
            c = self.Cmat[:, idx]
            Qr, _ = np.linalg.qr(c)
            spans.append(Qr)
            coords.append(c)
            Xis.append(np.zeros((self.Cmat.shape[0], C)))
        S = np.zeros_like(self.Ts)
        for it in range(sweeps):
            for r in range(R):
                Qr = spans[r]
                Rr = self.Ts - S + Xis[r] @ Xis[r].T
                Bm = Qr.T @ Rr @ Qr
                Bm = 0.5 * (Bm + Bm.T)
                ev, V = np.linalg.eigh(Bm)
                order = np.argsort(-ev)[:C]
                lam = np.maximum(ev[order], 0.0)
                Xi = Qr @ (V[:, order] * np.sqrt(lam))
                S += Xi @ Xi.T - Xis[r] @ Xis[r].T
                Xis[r] = Xi
            err = np.linalg.norm(S - self.Ts)
            if log:
                log('   bcd sweep %d: %.4f mHa' % (it, 1e3 * np.sqrt(err ** 2 + self.outside2)))
        w = np.zeros((R, B, C))
        for r in range(R):
            idx = perm[r * B:(r + 1) * B]
            rhs = coords[r].T @ Xis[r]
            w[r] = np.linalg.lstsq(self.G[np.ix_(idx, idx)], rhs, rcond=1e-10)[0]
        return w

    def fit_error_at_lambda(self, w0, W0, Lam0, kappa=1e-3, kappa_g=1e5, maxiter=600, perm=None,
                            log=None):
        """Minimise error_2 subject to Lambda <= Lam0 and E_gap >= floor (scalarised penalty).

        Pure error-vs-Lambda frontier probe: no log lambda_eff term, so this answers "what is the
        lowest error this structure can reach at this Lambda" independently of the cost objective.
        """
        from scipy.optimize import minimize
        perm = np.arange(self.R * self.B) if perm is None else np.asarray(perm)
        Gp = self.G[np.ix_(perm, perm)]
        Q0p = self.Q0[np.ix_(perm, perm)]
        K = Gp.reshape(self.R, self.B, self.R, self.B)
        Q = np.stack([Q0p[r * self.B:(r + 1) * self.B, r * self.B:(r + 1) * self.B]
                      for r in range(self.R)])
        Q = 0.5 * (Q + Q.swapaxes(1, 2))
        ref = self.inp.ref
        eta = int(ref['electrons'])
        wp = rw.WeightProblem(self.u.reshape(self.R * self.B, N)[perm].reshape(self.R, self.B, N),
                              K, Q, self.normT2,
                              ref['h1_thc'] - 0.5 * eta * self.inp.S + self.inp.beta_1 * np.eye(N),
                              float(rw.UPPER_ENERGY - ref['ecore'] + eta * self.inp.beta_1))
        floor = GAP_FLOOR + 1e-4
        scale = np.concatenate([np.full(w0.size, max(np.std(w0), 1e-12)),
                                np.full(W0.size, max(np.std(W0), 1e-12))])

        def obj(z):
            x = z * scale
            w, W = x[:w0.size].reshape(w0.shape), x[w0.size:].reshape(W0.shape)
            (e2, gap, Lam), (de2, dgap, dLam) = wp.evaluate(w, W)
            f = 1e6 * e2 ** 2
            g = 2e6 * e2 * de2
            ex = max(0.0, (Lam - Lam0))
            if ex > 0:
                f += kappa * ex ** 2
                g = g + 2 * kappa * ex * dLam
            gy = max(0.0, floor - gap)
            if gy > 0:
                f += kappa_g * gy ** 2
                g = g - 2 * kappa_g * gy * dgap
            return f, np.concatenate([g.ravel(), np.zeros(0)]) if False else \
                np.concatenate([g.ravel()]) * scale

        z0 = np.concatenate([w0.ravel(), W0.ravel()]) / scale
        # gradient must span both blocks: build it explicitly
        def obj2(z):
            x = z * scale
            w, W = x[:w0.size].reshape(w0.shape), x[w0.size:].reshape(W0.shape)
            (e2, gap, Lam), (de2, dgap, dLam) = wp.evaluate(w, W)
            f = 1e6 * e2 ** 2
            gw, gW = 2e6 * e2 * de2, np.zeros_like(W)
            ex = max(0.0, (Lam - Lam0))
            if ex > 0:
                f += kappa * ex ** 2
                gw = gw + 2 * kappa * ex * dLam[0]
                gW = gW + 2 * kappa * ex * dLam[1]
            gy = max(0.0, floor - gap)
            if gy > 0:
                f += kappa_g * gy ** 2
                gw = gw - 2 * kappa_g * gy * dgap[0]
                gW = gW - 2 * kappa_g * gy * dgap[1]
            return f, np.concatenate([gw.ravel(), gW.ravel()]) * scale

        res = minimize(obj2, z0, jac=True, method='L-BFGS-B',
                       options={'maxiter': maxiter, 'maxcor': 30, 'ftol': 1e-15, 'gtol': 1e-9, 'maxls': 40})
        x = res.x * scale
        w, W = x[:w0.size].reshape(w0.shape), x[w0.size:].reshape(W0.shape)
        (e2, gap, Lam), _ = wp.evaluate(w, W)
        if log:
            log('   Lam0 %.0f: e2 %.3f mHa  Lambda %.2f  E_gap %.5f  (%d its, %s)'
                % (Lam0, 1e3 * e2, Lam, gap, res.nit, res.message))
        return w, W, e2, gap, Lam

    # -- exact refit -----------------------------------------------------
    def refit(self, w0, W0, perm=None, target_mha=19.999, margin=0.0005, outer=10, inner=200, log=print):
        """Augmented-Lagrangian refit of (w, W) at fixed u and fixed partition (refit_al style)."""
        perm = np.arange(self.R * self.B) if perm is None else np.asarray(perm)
        Gp = self.G[np.ix_(perm, perm)]
        Q0p = self.Q0[np.ix_(perm, perm)]
        K = Gp.reshape(self.R, self.B, self.R, self.B)
        Q = np.stack([Q0p[r * self.B:(r + 1) * self.B, r * self.B:(r + 1) * self.B]
                      for r in range(self.R)])
        Q = 0.5 * (Q + Q.swapaxes(1, 2))
        ref = self.inp.ref
        eta = int(ref['electrons'])
        wp = rw.WeightProblem(self.u.reshape(self.R * self.B, N)[perm].reshape(self.R, self.B, N),
                              K, Q, self.normT2,
                              ref['h1_thc'] - 0.5 * eta * self.inp.S + self.inp.beta_1 * np.eye(N),
                              float(rw.UPPER_ENERGY - ref['ecore'] + eta * self.inp.beta_1))
        tgt, floor = 1e-3 * target_mha, GAP_FLOOR + margin
        scale = np.concatenate([np.full(w0.size, max(np.std(w0), 1e-12)),
                                np.full(W0.size, max(np.std(W0), 1e-12))])
        y_e, y_g, rho = 0.0, 0.0, 1.0

        def lagrangian(z):
            x = z * scale
            w, W = x[:w0.size].reshape(w0.shape), x[w0.size:].reshape(W0.shape)
            (e2, gap, Lam), (de2, dgap, dLam) = wp.evaluate(w, W)
            rad = gap * (2 * Lam - gap)
            if rad <= 0:
                return 1e12, np.zeros_like(z)
            f = 500.0 * np.log(rad)
            gw, gW = [1e3 * ((Lam - gap) * g + gap * l) / rad for g, l in zip(dgap, dLam)]
            ce, cg = 1e3 * (e2 - tgt), 1e3 * (floor - gap)
            pe, pg = max(0.0, y_e + rho * ce), max(0.0, y_g + rho * cg)
            f += (pe ** 2 - y_e ** 2 + pg ** 2 - y_g ** 2) / (2 * rho)
            gw = gw + 1e3 * pe * de2 - 1e3 * pg * dgap[0]
            gW = gW - 1e3 * pg * dgap[1]
            return f, np.concatenate([gw.ravel(), gW.ravel()]) * scale

        from scipy.optimize import minimize
        z = np.concatenate([w0.ravel(), W0.ravel()]) / scale
        best = None
        for k in range(outer):
            res = minimize(lagrangian, z, jac=True, method='L-BFGS-B',
                           options={'maxiter': inner, 'maxcor': 30, 'ftol': 1e-13, 'gtol': 1e-7, 'maxls': 40})
            z = res.x
            x = z * scale
            w, W = x[:w0.size].reshape(w0.shape), x[w0.size:].reshape(W0.shape)
            (e2, gap, Lam), _ = wp.evaluate(w, W)
            lam = float(np.sqrt(max(gap * (2 * Lam - gap), 0.0)))
            ce, cg = 1e3 * (e2 - tgt), 1e3 * (floor - gap)
            best = (w.copy(), W.copy(), e2, gap, Lam, lam)
            log('   outer %d: %d its  e2 %.4f mHa  E_gap %.5f  Lambda %.3f  lambda_eff %.4f'
                % (k, res.nit, 1e3 * e2, gap, Lam, lam))
            y_e, y_g = max(0.0, y_e + rho * ce), max(0.0, y_g + rho * cg)
            if max(ce, cg) > 0.02:
                rho = min(rho * 2.0, 200.0)
        return best


def metrics_of(U, w, W, edges, brot=BROT, one_start=None, coded=(), coded2=()):
    """Official metrics of a factorization with freshly encoded words (nearest 8-bit)."""
    u = np.asarray(U, np.float64)
    u = u / np.linalg.norm(u, axis=2, keepdims=True)
    two = encode.to_words(encode.tree_angles(u.reshape(-1, N)), edges, brot)
    ref = rw.load_reference(rw.check_fcidump())
    with np.load(rw.SHIFTS) as z:
        shifts = {k: np.array(z[k]) for k in ('H1_I', 'Hsym_lower')}
        _, _, S, beta = rw.native_inputs({'U': u, 'W': w, 'H2_I': W + w.sum(axis=1),
                                          'H1_I': z['H1_I'], 'Hsym_lower': z['Hsym_lower']})
    p = rw.Problem(u, w, ref, S, beta)
    one = onebody.refresh(p.h1(W), edges, brot, start=one_start, kicks=10, coded=coded, coded2=coded2,
                          following=two[:16] if len(coded) else None)
    data = {'U': u, 'W': w, 'H2_I': W + w.sum(axis=1), **shifts, 'tree_edges': edges,
            'angle_words': np.vstack([one, two]), 'coded': np.asarray(coded, np.int64),
            'coded2': np.asarray(coded2, np.int64)}
    return data, rw.official(data, brot)
