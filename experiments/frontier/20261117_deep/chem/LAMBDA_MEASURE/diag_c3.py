"""Cross-checks that the pair-space objective equals the official one, plus the
W / error_1 / E_gap coupling that a C=42..38 refit has to keep legal."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import infra as I

N = 76
z = np.load(I.ROOT / 'experiments/frontier/20261117_deep/chem/data/dfthcsos/submission.npz')
U = z['U'].astype(np.float64)
w = z['W'].astype(np.float64)
wB = z['H2_I'].astype(np.float64)
R, B, _ = U.shape
C = w.shape[2]
W = wB - w.sum(axis=1)
ref, S, beta1 = I.reference()
ps = I.cached_pair_space()
H, PA, sqw = ps['H'], ps['PA'], ps['sqw']


def frame(Ug):
    Pm = np.einsum('bp,bq->bpq', Ug, Ug, optimize=True)
    return np.ascontiguousarray((Pm[:, PA[:, 0], PA[:, 1]] * sqw[None, :]).T)


P = [frame(U[r]) for r in range(R)]
Y = np.concatenate([P[r] @ w[r] for r in range(R)], axis=1)
print('pair-space e2  %.6f mHa' % I.e2_pair(Y, H))
ang = z['angle_words'].astype(np.float64)
full = I.dfm.reconstruct_u_vectors(ang / (1 << 7), z['tree_edges'])
m = I.metrics_from_words(z['angle_words'], w, W, z['tree_edges'], ref, S, beta1, 8)
print('official e2    %.6f mHa  (error_1 %.6f, E_gap %.9f, lambda_eff %.6f)'
      % (1e3 * m['error_2'], 1e3 * m['error_1'], m['E_gap'], m['lambda_eff']))

# ---- W sensitivity: E_gap and error_1 as W is rescaled / perturbed
print('\nW sensitivity on the SHIPPED X, one-body rows fixed:')
for scale in (0.98, 0.99, 1.0, 1.01, 1.02):
    Wt = W * scale
    mm = I.metrics_from_words(z['angle_words'], w, Wt, z['tree_edges'], ref, S, beta1, 8)
    print('  W*%.2f: E_gap %.9f  lambda_eff %9.6f  error_1 %.6f  error_2 %.6f  Lambda %.4f'
          % (scale, mm['E_gap'], mm['lambda_eff'], 1e3 * mm['error_1'], 1e3 * mm['error_2'],
             mm['Lambda']))

# ---- how much does error_1 move when X changes?  Use a rank-truncated X.
print('\nX sensitivity (shipped W, one-body rows fixed), X = shipped and C-truncated:')
for cc in (44, 42, 40, 38):
    ww = np.zeros_like(w)
    ww[:, :, :cc] = w[:, :, :cc]
    mm = I.metrics_from_words(z['angle_words'], ww, W, z['tree_edges'], ref, S, beta1, 8)
    print('  keep %2d cols: error_1 %.6f  error_2 %.6f  E_gap %.9f  lambda_eff %.6f  Lambda %.4f'
          % (cc, 1e3 * mm['error_1'], 1e3 * mm['error_2'], mm['E_gap'], mm['lambda_eff'], mm['Lambda']))

# ---- geometry of the shipped Y blocks
print('\nblock geometry (shipped w, word U):')
for r in (0, 3):
    Yr = P[r] @ w[r]
    sv = np.linalg.svd(Yr, compute_uv=False)
    print('  r%d singular values: %s' % (r, np.round(sv, 3)))
print('  ||Y||_F^2 %.4f' % np.sum(Y * Y))
