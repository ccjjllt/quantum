"""Pareto check at C=44 (frozen word-U): is the shipped point on the
(error_2, lambda_eff) frontier?  Scale the weights, re-choose W so E_gap sits on
its floor, and report error_2 / lambda_eff / cost.

Both gates are inclusive (error_2 <= 20 mHa, error_1 <= 20 mHa); E_gap must stay
strictly above 3.914898 and Lambda > 49.
"""
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

sys.path.insert(0, str(Path(__file__).parent))
import infra as I
import wsolve as WS

N = 76
z = np.load(I.ROOT / 'experiments/frontier/20261117_deep/chem/data/dfthcsos/submission.npz')
U = z['U'].astype(np.float64)
w0 = z['W'].astype(np.float64)
wB0 = z['H2_I'].astype(np.float64)
R, B, _ = U.shape
C = w0.shape[2]
ref, S, beta1 = I.reference()
dfm, refm = I.dfm, I.refm
E_UP = I.E_UPPER
eta = int(ref['electrons'])
ecore = float(ref['ecore'])
words = z['angle_words']
tree = z['tree_edges']
full = dfm.reconstruct_u_vectors(words / (1 << 7), tree)
Vrow = full[:N]
h1_thc = np.asarray(ref['oei'], float) - 0.5 * np.einsum('prrq->pq', ref['tei'])
A_h1 = h1_thc - 0.5 * eta * S + beta1 * np.eye(N)
rows_t, cols_t = np.tril_indices(N)
E_FLOOR = 3.914898

u = U / np.linalg.norm(U, axis=2, keepdims=True)


def X_of(w):
    return np.einsum('tjp,tjq,tjl->tlpq', u, u, w, optimize=True)


def design(X):
    Rr, Cc = X.shape[:2]
    return np.stack([X[k // Cc, k % Cc][rows_t, cols_t] for k in range(Rr * Cc)])


def matched(X, Wm):
    h1p = A_h1 - np.einsum('rc,rcpq->pq', Wm, X, optimize=True)
    evs, Ue = np.linalg.eigh(h1p)
    qi, ei = linear_sum_assignment(-np.abs(Vrow @ Ue))
    lam = np.empty(N)
    lam[qi] = evs[ei]
    return lam, h1p, evs


def full_metrics(X, w, Wm):
    lam, h1p, evs = matched(X, Wm)
    lam_h1 = float(np.abs(evs).sum())
    tr = float(np.trace(h1p))
    eg = E_UP - (ecore - eta * beta1 - (lam_h1 - tr) - 0.5 * float(np.sum(Wm ** 2)))
    a = np.abs(w).sum(axis=1)
    wB = Wm + w.sum(axis=1)
    lam_h2 = float(0.25 * np.sum((a + np.abs(wB)) ** 2))
    Lam = lam_h1 + lam_h2
    e1 = float(dfm.h1_thc_reconstruction_error(Vrow, h1_thc, S, beta1, eta, Wm, X))
    le = float(np.sqrt(eg * (2 * Lam - eg))) if 0 < eg < 2 * Lam else float('nan')
    return dict(eg=eg, Lam=Lam, lam_h2=lam_h2, err1=e1, le=le)


def best_W(X, w, lam_init):
    Bm = design(X)
    G = Bm @ Bm.T
    Gi = np.linalg.inv(G + 1e-13 * np.eye(G.shape[0]))
    lam_use = lam_init
    out = None
    for rd in range(2):
        b0 = (A_h1 - (Vrow.T @ (lam_use[:, None] * Vrow)))[rows_t, cols_t]
        W0 = (Gi @ (Bm @ b0)).reshape(X.shape[0], X.shape[1])
        cand = None
        for s in np.linspace(0.9, 1.1, 401):
            Wm = W0 * s
            sc = full_metrics(X, w, Wm)
            if sc['err1'] <= 0.02 and sc['eg'] > E_FLOOR and sc['le'] == sc['le']:
                if cand is None or sc['le'] < cand[0]:
                    cand = (sc['le'], s, sc, Wm)
        if cand is None:
            return out
        out = cand
        lam_use = matched(X, cand[3])[0]
    return out


X0 = X_of(w0)
lam0 = matched(X0, wB0 - w0.sum(axis=1))[0]
Y0 = np.concatenate([WS.frame(u[r], np.array([[p, q] for p in range(N) for q in range(p, N)]),
                              np.sqrt(np.array([1.0 if p == q else 2.0
                                                for p in range(N) for q in range(p, N)]))) @ w0[r]
                     for r in range(R)], axis=1)
ps = I.cached_pair_space()
H = ps['H']
T44 = 14706
print('scale  error_2   error_1   E_gap      Lambda    lambda_eff   cost(M)    GM')
for sc in (0.96, 0.98, 0.99, 1.0, 1.005, 1.01, 1.02, 1.05):
    w = w0 * sc
    X = X_of(w)
    Y = np.concatenate([WS.frame(u[r], ps['PA'], ps['sqw']) @ w[r] for r in range(R)], axis=1)
    e2 = I.e2_pair(Y, H)
    bw = best_W(X, w, lam0)
    if bw is None:
        print(f'{sc:5.3f}  {e2:8.4f}   no feasible W')
        continue
    le, s, m, Wm = bw
    cost = le * T44 * 427
    gm = (2076774.233715 / 74797.36535717871
          * 24439463583672.93 / 346409762292.7187
          * 3355599588.3155375 / cost) ** (1 / 3)
    print(f'{sc:5.3f}  {e2:8.4f}  {1e3*m["err1"]:8.4f}  {m["eg"]:9.6f}  {m["Lam"]:9.4f}'
          f'  {le:9.5f}  {cost/1e6:9.2f}  {gm:8.5f}')
