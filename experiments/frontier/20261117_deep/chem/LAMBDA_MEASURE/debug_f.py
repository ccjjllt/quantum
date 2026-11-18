"""Debug: which term of the small-coordinate f disagrees with the full-space f?"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import infra as I
import wsolve as WS

z = np.load(I.ROOT / 'experiments/frontier/20261117_deep/chem/data/dfthcsos/submission.npz')
U = z['U'].astype(np.float64)
w0 = z['W'].astype(np.float64)
ps = I.cached_pair_space()
H, PA, sqw = ps['H'], ps['PA'], ps['sqw']
fu = WS.FixedU(U, H, PA, sqw)
y = fu.y_from_w(w0)
R = fu.R
Y = np.concatenate([fu.Qs[r] @ y[r] for r in range(R)], axis=1)
YtY = Y.T @ Y
trYY2 = float(np.sum(YtY * YtY))
trH = float(np.sum(Y * (H @ Y)))
print('full: ||YY^T||^2 %.8f   tr(Y^T H Y) %.8f   ||H||^2 %.8f' % (trYY2, trH, fu.Hfro2))
print('full f %.6e   e2 %.6f mHa' % (trYY2 - 2 * trH + fu.Hfro2,
                                     1e3 * np.sqrt(abs(trYY2 - 2 * trH + fu.Hfro2))))
Cy = [[fu.C[r][s] @ y[s] for s in range(R)] for r in range(R)]
P = [[y[r].T @ Cy[r][s] for s in range(R)] for r in range(R)]
print('small: sum||P_rs||^2 %.8f' % sum(np.sum(P[r][s] ** 2) for r in range(R) for s in range(R)))
print('small: sum tr(y_r^T H_rs y_s) %.8f'
      % sum(np.sum(y[r] * (fu.Hs[r][s] @ y[s])) for r in range(R) for s in range(R)))
# block-by-block comparison of P_rs vs Y_r^T Y_s
for r in range(2):
    for s in range(2):
        print(' (r,s)=(%d,%d) |P-YrYs| %.3e  |P| %.4f  |YrYs| %.4f'
              % (r, s, np.linalg.norm(P[r][s] - Y[:, r * 44:(r + 1) * 44].T
                                      @ Y[:, s * 44:(s + 1) * 44]),
                 np.linalg.norm(P[r][s]),
                 np.linalg.norm(Y[:, r * 44:(r + 1) * 44].T @ Y[:, s * 44:(s + 1) * 44])))
gt = [4.0 * fu.Qs[r].T @ ((Y @ Y.T - H) @ Y[:, r * 44:(r + 1) * 44]) for r in range(R)]
gc = fu.fg(y)[1]
print('grad small-vs-true rel %.3e' % (np.linalg.norm(np.concatenate(gt, 1) - np.concatenate(gc, 1))
                                       / np.linalg.norm(np.concatenate(gt, 1))))
