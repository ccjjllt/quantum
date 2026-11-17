"""lambda_eff at a shape: pick the offset matrix W that just clears the E_gap floor.

For a fitted (U, w) the metric is

    lam_h2 = 0.25 sum_rc ( sum_b|w_rcb| + |wB_rc| )^2 ,  wB = W + sum_b w
    E_gap  = Cg0 + 2*Nneg(W) + 0.5*sum W^2 ,              Cg0 = E_upper-ecore+eta*beta1
    Lambda = lam_h1(W) + lam_h2 ,  lam_eff = sqrt(E_gap (2 Lambda - E_gap))

so W only moves (lam_h1, E_gap). This script profiles wB = -sign(sum_b w) * b with
b >= 0 (the shipped structure: 4*lam_h2 = sum W^2), scales b to the floor by
bisection, and reports the best profile. Exact official formulas throughout.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import fitlib as F
import infra as I

N = 76
log = F.log


class LamProblem:
    def __init__(self, U, w):
        ref, S, b1 = I.reference()
        self.ref, self.S, self.b1 = ref, S, b1
        self.U = U / np.linalg.norm(U, axis=2, keepdims=True)
        self.w = np.asarray(w, float)
        R, B, Nn = U.shape
        self.R, self.B, self.C = R, B, w.shape[2]
        self.X = I.dfm.reconstruct_x(self.U, self.w)
        self.X = np.tril(self.X) + np.swapaxes(np.tril(self.X, k=-1), -1, -2)
        self.h1_thc = np.asarray(ref['oei'], float) - 0.5 * np.einsum('prrq->pq', ref['tei'])
        self.base = (self.h1_thc - 0.5 * ref['electrons'] * S + b1 * np.eye(N))
        self.a = np.abs(self.w).sum(axis=1)
        self.s = self.w.sum(axis=1)
        self.Cg0 = I.E_UPPER - ref['ecore'] + ref['electrons'] * b1

    def stats(self, W):
        h1p = self.base - np.einsum('rc,rcpq->pq', W, self.X, optimize=True)
        ev = np.linalg.eigvalsh(h1p)
        lam_h1 = float(np.abs(ev).sum())
        tr = float(ev.sum())
        wB = W + self.s
        lam_h2 = float(0.25 * np.sum((self.a + np.abs(wB)) ** 2))
        sumW2 = float(np.sum(W ** 2))
        nneg = float(np.abs(ev[ev < 0]).sum())
        gap = self.Cg0 + 2 * nneg + 0.5 * sumW2
        Lam = lam_h1 + lam_h2
        le = float(np.sqrt(gap * (2 * Lam - gap))) if 0 < gap < 2 * Lam else float('nan')
        return dict(lam_h1=lam_h1, lam_h2=lam_h2, Lambda=Lam, E_gap=gap,
                    lambda_eff=le, sumW2=sumW2, tr=tr, nneg=nneg,
                    sum_pos=0.5 * (lam_h1 + tr))

    def solve_scale(self, prof, target_gap=I.E_GAP_FLOOR + 1e-5, lo=0.0, hi=60.0):
        """Scale b = t*prof so that E_gap(t) = target_gap (bisection)."""
        sign = -np.sign(self.s.ravel() + 1e-300)
        f = lambda t: self.stats((sign * (t * prof)).reshape(self.R, self.C) - self.s)['E_gap'] - target_gap
        f0, f1 = f(lo), f(hi)
        if f0 > 0:
            return lo
        if f1 < 0:
            return None
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if f(mid) < 0:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)


def best_W(LP, ts=None, verbose=True):
    """Scan the offset scale; report the feasible point with the smallest lambda_eff.

    E_gap(t) is NOT monotone (the shipped sits at its minimum, which is just
    above the floor), so this scans instead of bisecting.
    """
    K = LP.R * LP.C
    a = LP.a.ravel()
    order = np.argsort(a)
    if ts is None:
        ts = np.linspace(0.0, 2.5, 251)
    out = []
    profiles = {'uniform': a / a.mean()}
    for k in (1, 2, 4, 8, 16, 32, int(K // 4), int(K // 2)):
        if k > K:
            continue
        p = np.zeros(K)
        p[order[:k]] = 1.0
        profiles[f'top{k}'] = p
    sign = -np.sign(LP.s.ravel() + 1e-300)
    for name, prof in profiles.items():
        for t in ts:
            W = (sign * (t * prof)).reshape(LP.R, LP.C) - LP.s
            st = LP.stats(W)
            st.update(profile=name, t=float(t), nnzW=int(np.count_nonzero(np.abs(W) > 1e-9)))
            out.append(st)
    feas = [d for d in out if np.isfinite(d['lambda_eff']) and d['E_gap'] > I.E_GAP_FLOOR
            and d['Lambda'] > I.LAMBDA_FLOOR]
    if verbose:
        log(f'   scanned {len(out)} points, feasible {len(feas)}')
        # the E_gap minimum itself, which is what the trainer sits on
        for name in profiles:
            rows = [d for d in out if d['profile'] == name]
            gmin = min(rows, key=lambda d: d['E_gap'])
            log(f'   {name:8s} min E_gap {gmin["E_gap"]:10.6f} at t {gmin["t"]:.3f} '
                f'-> Lambda {gmin["Lambda"]:.3f}  lambda_eff {gmin["lambda_eff"]:.5f}')
    feas.sort(key=lambda d: d['lambda_eff'])
    return feas


if __name__ == '__main__':
    # validation on the shipped factorization (its own W is the reference)
    z = np.load(I.ROOT / 'experiments/frontier/20261117_deep/chem/data/dfthcsos/submission.npz')
    LP = LamProblem(z['U'], z['W'])
    W_true = z['H2_I'] - z['W'].sum(axis=1)
    st = LP.stats(W_true)
    log(f'SHIPPED with its own W: lambda_eff {st["lambda_eff"]:.9f}  Lambda {st["Lambda"]:.6f} '
        f'E_gap {st["E_gap"]:.12f}  sumW2 {st["sumW2"]:.4f}')
    log("SHIPPED, offset-scale scan:")
    f = best_W(LP)
    for d in f[:5]:
        log(f'   BEST {d["profile"]:8s} t {d["t"]:.3f} lambda_eff {d["lambda_eff"]:.6f} Lambda {d["Lambda"]:.4f} E_gap {d["E_gap"]:.9f} sumW2 {d["sumW2"]:.3f}')
    best_W(LP)
