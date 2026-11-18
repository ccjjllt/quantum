"""The W stage, corrected: error_1 = || Omega(W) - Omega_target(lam) ||_F.

    Omega(W) = sum_rc W_rc X_rc            (linear in W)
    Omega_target(lam) = A - V^T diag(lam) V,  A = h1_thc - eta/2 S + beta1 I
    lam = the matched spectrum of h1p (verifier's linear_sum_assignment)

so min_W error_1 is a linear least squares whose residual is the distance from
Omega_target to span{X_rc}.  The shipped X attains residual 0.02 by construction;
a refit w must keep that span close enough.  E_gap pins 0.5*sum W^2, so the norm
is swept with a ridge multiplier and E_gap re-checked exactly.
"""
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

sys.path.insert(0, str(Path(__file__).parent))
import infra as I

N = 76
z = np.load(I.ROOT / 'experiments/frontier/20261117_deep/chem/data/dfthcsos/submission.npz')
U = z['U'].astype(np.float64)
w0 = z['W'].astype(np.float64)
wB0 = z['H2_I'].astype(np.float64)
R, B, _ = U.shape
C0 = w0.shape[2]
ref, S, beta1 = I.reference()
E_UPPER = I.E_UPPER
oei = np.asarray(ref['oei'], float)
tei = np.asarray(ref['tei'], float)
h1_thc = oei - 0.5 * np.einsum('prrq->pq', tei)
eta = int(ref['electrons'])
A = h1_thc - 0.5 * eta * S + beta1 * np.eye(N)
ecore = float(ref['ecore'])
words = z['angle_words']
Vt = I.dfm.reconstruct_u_vectors(words / (1 << 7), z['tree_edges'])
V = Vt[:N]
rows, cols = np.tril_indices(N)


def X_of(w):
    u = U / np.linalg.norm(U, axis=2, keepdims=True)
    return np.einsum('tjp,tjq,tjl->tlpq', u, u, w, optimize=True)


def design(X):
    Rr, Cc = X.shape[:2]
    return np.stack([X[k // Cc, k % Cc][rows, cols] for k in range(Rr * Cc)])


def matched_spectrum(Wm, X):
    h1p = A - np.einsum('rc,rcpq->pq', Wm, X, optimize=True)
    ev, Ue = np.linalg.eigh(h1p)
    ov = np.abs(V @ Ue)
    qi, ei = linear_sum_assignment(-ov)
    lam = np.empty(N)
    lam[qi] = ev[ei]
    return lam, h1p, ev


def egap(Wm, X):
    lam, h1p, ev = matched_spectrum(Wm, X)
    lam_h1 = float(np.abs(ev).sum())
    tr = float(np.trace(h1p))
    return E_UPPER - (ecore - eta * beta1 - (lam_h1 - tr) - 0.5 * float(np.sum(Wm ** 2)))


def ls_w(X, Om_target, mu=0.0):
    Bm = design(X)                     # (RC, 2926), Omega_vech = Bm^T W_flat
    b = Om_target[rows, cols]
    G = Bm @ Bm.T
    return np.linalg.solve(G + mu * np.eye(G.shape[0]), Bm @ b).reshape(X.shape[0], X.shape[1])


def error1(Wm, X):
    return I.dfm.h1_thc_reconstruction_error(V, h1_thc, S, beta1, eta, Wm, X)


X0 = X_of(w0)
W_sh = wB0 - w0.sum(axis=1)
lam_sh, h1p_sh, ev_sh = matched_spectrum(W_sh, X0)
Om_t = A - (V.T @ (lam_sh[:, None] * V))
print('shipped error_1 %.6f mHa   E_gap %.9f   ｜Omega_target - Omega_shipped｜ %.6f'
      % (1e3 * error1(W_sh, X0), egap(W_sh, X0),
         np.linalg.norm(Om_t - np.einsum('rc,rcpq->pq', W_sh, X0, optimize=True))))

print('\n--- shipped X: LS recovers W, and the norm sweep (target = shipped Omega)')
W_ls = ls_w(X0, Om_t)
print('  LS(mu=0): |W| %.4f (shipped %.4f)  error_1 %.6f  E_gap %.9f'
      % (np.linalg.norm(W_ls), np.linalg.norm(W_sh), 1e3 * error1(W_ls, X0), egap(W_ls, X0)))
for mu in (1.0, 30.0, 300.0, 3000.0):
    Wm = ls_w(X0, Om_t, mu)
    print('  LS(mu=%6.1f): |W| %.4f  error_1 %9.4f mHa  E_gap %9.5f'
          % (mu, np.linalg.norm(Wm), 1e3 * error1(Wm, X0), egap(Wm, X0)))

print('\n--- norm-constrained LS with a scaled Omega target (E_gap is pinned near 3.9149)')
for sc in (0.98, 1.0, 1.02):
    Wm = ls_w(X0, Om_t * sc)
    print('  target x%.2f: |W| %.4f  error_1 %9.4f mHa  E_gap %9.5f'
          % (sc, np.linalg.norm(Wm), 1e3 * error1(Wm, X0), egap(Wm, X0)))

# ---- now the refit w at C=44 (frozen U)
f = I.CACHE / 'y_C44_ship.npz'
if f.exists():
    import wsolve as WS
    ps = I.cached_pair_space()
    fu = WS.FixedU(U, ps['H'], ps['PA'], ps['sqw'])
    yy = np.load(f)['y']
    w_new = fu.w_from_y([a for a in yy])
    Xn = X_of(w_new)
    print('\n--- refit C=44 w (same U):')
    print('  ||X_new - X_sh||/||X_sh|| %.4f   sum|w| %.3f (shipped %.3f)'
          % (np.linalg.norm(Xn - X0) / np.linalg.norm(X0), np.abs(w_new).sum(), np.abs(w0).sum()))
    # target from the *new* h1p needs a fixed point; start from the shipped spectrum
    for it in range(3):
        if it == 0:
            lam_use = lam_sh
        else:
            lam_use, _, _ = matched_spectrum(Wm, Xn)
        Om_tn = A - (V.T @ (lam_use[:, None] * V))
        Wm = ls_w(Xn, Om_tn)
        print('  iter %d: |W| %.4f  error_1 %9.4f mHa  E_gap %9.5f'
              % (it, np.linalg.norm(Wm), 1e3 * error1(Wm, Xn), egap(Wm, Xn)))
