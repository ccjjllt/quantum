"""Fast exact-ish candidate evaluator with full-domain cutting planes.

The baseline phase is precomputed once.  A candidate changes one mask; the LP
angle deltas are usually sparse, so each cutting-plane iteration only touches
a handful of full-domain mask arrays.  This keeps one candidate at a few
tenths of a second while still validating on all 3,133,452 x.
"""
from __future__ import annotations

import numpy as np

import model as M


class Evaluator:
    def __init__(self, m, *, add=400, max_iter=8, seed=20261107):
        self.m = m
        self.masks = m["masks"]
        self.theta0 = m["thetas"].astype(np.int64)
        self.T = m["T"]
        self.tol = m["tol"]
        self.base_phase = M.phase_of(self.masks, self.theta0)
        self.base_err = M.err_of(self.base_phase, self.T)
        self.base_margin = self.tol - np.abs(self.base_err)
        self.add = add
        self.max_iter = max_iter
        self.rng = np.random.default_rng(seed)
        # baseline active set
        self.tight0 = np.argsort(self.base_margin)[:300]
        # sample of sparse mask supports
        rng = np.random.default_rng(seed + 1)
        sp = []
        for i in (34, 35, 36, 37, 38, 39, 40):
            sup = np.flatnonzero(self.masks[i])
            if len(sup):
                sp.append(rng.choice(sup, min(len(sup), 150), replace=False))
        self.sparse = np.concatenate(sp) if sp else np.array([], dtype=np.int64)

    def eval(self, i, g, *, verbose=False):
        masks, theta0, T, tol = self.masks, self.theta0, self.T, self.tol
        n = len(theta0)
        E = (T - self.base_phase.view(np.int64)).astype(np.float64) / 2**M.SHIFT
        Ts = tol.astype(np.float64) / 2**M.SHIFT
        old_all = masks[i].astype(np.float64) * (theta0[i] / 2**M.SHIFT)
        new_all = g.astype(np.float64) * (theta0[i] / 2**M.SHIFT)
        # raw perturbation margin: phase + theta_i*(g-f_i)
        gi = g.astype(np.int64) - masks[i].astype(np.int64)
        raw_phase = self.base_phase + (np.uint64(theta0[i]) * gi.view(np.uint64))
        raw_err = raw_phase.view(np.int64) - T
        raw_viol = np.abs(raw_err) - tol
        # initial working set
        cand = np.concatenate([
            self.tight0,
            np.argsort(-raw_viol)[:300],
            self.sparse,
            self.rng.integers(0, M.MAXX, 200),
        ])
        S = np.unique(cand)
        delta = np.zeros(n, dtype=np.int64)      # units 2^-64
        phase = raw_phase
        lp_m = None
        hist = []
        base_m = int(self.base_margin.min())
        for it in range(self.max_iter):
            A = np.empty((len(S), n), dtype=np.float64)
            for j in range(n):
                A[:, j] = (g if j == i else masks[j])[S]
            Es = E[S] + old_all[S] - new_all[S]
            bnds = [(-2_000_000.0, 2_000_000.0)] * n
            bnds[i] = (-float(1 << 39), float(1 << 39))
            d, lp_m = M.solve_lp(A, Es, Ts[S], bnds)
            # Fewer constraints than the full domain => LP margin is an upper
            # bound on the achievable full-domain margin: reject soundly.
            if lp_m * 2**M.SHIFT < base_m - 4:
                return {"theta": None, "delta": None, "margin": None,
                        "rejected": True, "lp_margin": lp_m * 2**M.SHIFT,
                        "history": hist, "iter": it}
            nd = np.round(d * 2**M.SHIFT).astype(np.int64)
            ch = np.flatnonzero(nd != delta)
            for j in ch:
                if j == i:
                    phase += np.uint64(nd[j] - delta[j]) * g.astype(np.uint64)
                else:
                    phase += np.uint64(nd[j] - delta[j]) * masks[j].astype(np.uint64)
            delta = nd
            st = M.margins(phase, T, tol)
            hist.append({"iter": it, "ncon": int(len(S)),
                         "lp_margin_units": lp_m * 2**M.SHIFT,
                         "full_margin_units": st["margin_units"],
                         "margin_x": st["margin_x"], "n_moved": int(len(ch))})
            if verbose:
                print(hist[-1], flush=True)
            if lp_m * 2**M.SHIFT - st["margin_units"] < 4:
                break
            margin = tol - np.abs(M.err_of(phase, T))
            S = np.unique(np.r_[S, np.argpartition(margin, self.add)[: self.add]])
        theta = theta0 + delta
        return {"theta": theta, "delta": delta, "margin": st["margin_units"],
                "stats": st, "history": hist, "lp_margin": lp_m * 2**M.SHIFT,
                "rejected": False, "iter": it}
