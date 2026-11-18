"""Diagnostics for the C axis with U frozen at the shipped (8-bit word) vectors.

1. Official metrics of the shipped npz (stored U == word set) --- reproduces 0.02.
2. The w/W structure that pins Lambda / E_gap (a_rc, s_rc, sum W^2, lam_h2).
3. The exact relaxed optimum for a FIXED dictionary span S = sum_r S_r:
       min_{YY^T funded by S} ||YY^T - H||_F^2 = ||H||^2 - sum_{j<=K} lam_j(H_S)^2
   because  <H_S, H - H_S> = 0  and  ||H - H_S||^2 = ||H||^2 - ||H_S||^2.
   This gives (a) the out-of-span energy, fixed by U, and (b) the in-span tail
   beyond K = R*C, i.e. the true lower bound for every C at this U.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import infra as I

N = 76
np.set_printoptions(precision=6, suppress=False, linewidth=200)

z = np.load(I.ROOT / 'experiments/frontier/20261117_deep/chem/data/dfthcsos/submission.npz')
print('keys', list(z.keys()))
for k in z.keys():
    print(f'  {k}: {z[k].shape} {z[k].dtype}')

ref, S, beta1 = I.reference()
U = z['U'].astype(np.float64)
w = z['W'].astype(np.float64)
wB = z['H2_I'].astype(np.float64)
R, B, Nn = U.shape
C = w.shape[2]
W = wB - w.sum(axis=1)
print(f'\nR={R} B={B} C={C} N={Nn} rows={N + R*B}'
      f'  H1_I={float(z["H1_I"]):.10f}  tree_edges {z["tree_edges"].shape}'
      f'  brot words max {int(z["angle_words"].max())}')

# ---------------------------------------------------------------- 1. official metrics
u_all = np.concatenate([U, np.zeros((0, N))]) if False else z['U'].astype(np.float64)
vec = np.zeros((N + R * B, N))
# one-body rows live in the same U array? check: stored U is (R,B,N) only, so the
# one-body rows must be elsewhere; evaluate_dfthc_vectors needs N + R*B rows.
print('\nstored U is only the two-body block; reconstructing full table from words')
ang = z['angle_words'].astype(np.float64)
tree = z['tree_edges']
full = I.dfm.reconstruct_u_vectors(ang / (1 << 7), tree)
print('  words -> vectors table', full.shape)
e2w = I.metrics_from_words(z['angle_words'], w, W, tree, ref, S, beta1, 8)
print('  official words  ', {k: (round(v, 9) if isinstance(v, float) else v) for k, v in e2w.items()})
e2v = I.metrics_from_vectors(full, w, W, ref, S, beta1)
print('  official vectors', {k: (round(v, 9) if isinstance(v, float) else v) for k, v in e2v.items()})
d = I.decompose(full, w, W, ref, S, beta1)
print('  decompose: Lambda %.9f E_gap %.12f lambda_eff %.9f lam_h2 %.6f sumW2 %.6f'
      % (d['Lambda'], d['E_gap'], d['lambda_eff'], d['lam_h2'], d['sumW2']))
print('  per-row overlap: stored U vs decoded two-body rows:',
      np.abs(np.sum(U * full[N:].reshape(R, B, N), axis=2)).min(),
      np.abs(np.sum(U * full[N:].reshape(R, B, N), axis=2)).max())

a = np.abs(w).sum(axis=1)
s = w.sum(axis=1)
print('\nw structure: a_rc = sum|w|, s_rc = sum w, W_rc = wB - s')
print('  sum a^2 %.4f   sum s^2 %.4f   sum W^2 %.6f (from wB) 0.5sumW2 %.6f'
      % (np.sum(a**2), np.sum(s**2), np.sum(W**2), 0.5*np.sum(W**2)))
print('  |wB| max %.4f  mean %.4f   sum |wB| %.4f' % (np.abs(wB).max(), np.abs(wB).mean(), np.abs(wB).sum()))
print('  per column |s|/a: min %.4f med %.4f max %.4f'
      % (np.min(np.abs(s)/a), np.median(np.abs(s)/a), np.max(np.abs(s)/a)))
print('  sign purity (|sum w|/sum|w|):', np.round(np.abs(s)/a, 3)[0])
print('  a range %.3f..%.3f' % (a.min(), a.max()))
print('  w abs max %.4f  sum w^2 %.3f' % (np.abs(w).max(), np.sum(w**2)))
print('  W (row 0):', np.round(W[0], 3))
print('  s (row 0):', np.round(s[0], 3))

# ---------------------------------------------------------------- 2. pair-space H and span bound
ps = I.cached_pair_space()
H, PA, sqw, NS = ps['H'], ps['PA'], ps['sqw'], ps['NS']
Hfro2 = float(np.sum(H * H))
print(f'\nH: NS {NS} ||H||_F {np.sqrt(Hfro2):.6f}')
ev = np.linalg.eigvalsh(H)[::-1]
neg2 = float(np.sum(np.minimum(ev, 0) ** 2))
print('floor K=352 %.4f mHa   K=336 %.4f   K=320 %.4f   K=304 %.4f'
      % (I.floor_mha(ev, 352, neg2), I.floor_mha(ev, 336, neg2),
         I.floor_mha(ev, 320, neg2), I.floor_mha(ev, 304, neg2)))


def frame(Ug, pb_pa, pb_sqw):
    P = np.einsum('bp,bq->bpq', Ug, Ug, optimize=True)
    return np.ascontiguousarray((P[:, pb_pa[:, 0], pb_pa[:, 1]] * pb_sqw[None, :]).T)


Pb = np.concatenate([frame(U[r], PA, sqw) for r in range(R)], axis=1)   # (NS, R*B)
print('P block shape', Pb.shape)
G = Pb.T @ Pb
A = Pb.T @ (H @ Pb)
Ginv = np.linalg.inv(G)
M = Ginv @ A            # generalised eigenproblem in P coordinates
lam = np.linalg.eigvalsh(0.5 * (M + M.T))
lam = np.sort(lam)[::-1]
print('eigenvalues of H_S: top', np.round(lam[:6], 4), '...')
print('  sum lam^2 %.6f  ||H||^2 %.6f  out-of-span^2 %.6f' % (np.sum(lam**2), Hfro2, Hfro2 - np.sum(lam**2)))
print('  out-of-span ||.||_F = %.4f mHa' % (1e3 * np.sqrt(max(Hfro2 - np.sum(lam**2), 0))))
for K in (352, 344, 336, 328, 320, 304, 288):
    tail2 = float(np.sum(lam[K:] ** 2))
    err = 1e3 * np.sqrt(max(Hfro2 - np.sum(lam[:K] ** 2), 0))
    print(f'  relaxed K={K}: in-span tail {1e3*np.sqrt(tail2):8.4f} mHa  '
          f'total lower bound {err:8.4f} mHa   sum lam^2(<=K)/||H||^2 {np.sum(lam[:K]**2)/Hfro2:.9f}')
