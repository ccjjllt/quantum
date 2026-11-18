"""Validate wsolve: coordinates, f, gradient (vs 4 Q^T R Y), GN operator (vs J^T J dy), e2."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import infra as I
import wsolve as WS

rng = np.random.default_rng(0)
z = np.load(I.ROOT / 'experiments/frontier/20261117_deep/chem/data/dfthcsos/submission.npz')
U = z['U'].astype(np.float64)
w0 = z['W'].astype(np.float64)
wB = z['H2_I'].astype(np.float64)
R, B, N = U.shape
C = w0.shape[2]
ps = I.cached_pair_space()
H, PA, sqw = ps['H'], ps['PA'], ps['sqw']
ref, S, beta1 = I.reference()
W = wB - w0.sum(axis=1)
fu = WS.FixedU(U, H, PA, sqw)
y0 = fu.y_from_w(w0)

print('round-trip |w - w_from_y(y_from_w(w))| = %.2e' % np.abs(fu.w_from_y(y0) - w0).max())
print('e2 from y   %.9f mHa' % fu.e2_mha(y0))
print('e2 official %.9f mHa' % (1e3 * I.metrics_from_words(
    z['angle_words'], w0, W, z['tree_edges'], ref, S, beta1, 8)['error_2']))
f, g = fu.fg(y0)
print('f cheap %.12e   f exact %.12e   e2 from cheap %.9f'
      % (f, (fu.e2_mha(y0) / 1e3) ** 2, 1e3 * np.sqrt(max(f, 0))))

# gradient against the full-space 4 Q^T (YY^T - H) Y
Y = np.concatenate([fu.Qs[r] @ y0[r] for r in range(R)], axis=1)
Res = Y @ Y.T - H
gt = np.concatenate([4.0 * fu.Qs[r].T @ (Res @ Y[:, r * C:(r + 1) * C]) for r in range(R)], axis=1)
gc = np.concatenate(g, axis=1)
print('gradient rel err vs 4Q^T RY: %.3e' % (np.linalg.norm(gt - gc) / np.linalg.norm(gt)))

# GN operator against J^T J dy in the full space
dy = [rng.standard_normal(a.shape) for a in y0]
dY = np.concatenate([fu.Qs[r] @ dy[r] for r in range(R)], axis=1)
L = dY @ Y.T + Y @ dY.T
ana = np.concatenate([fu.Qs[r].T @ (2.0 * L @ Y)[:, r * C:(r + 1) * C] for r in range(R)], axis=1)
num = np.concatenate(fu.A(y0, dy), axis=1)
print('A rel err vs J^T J dy:      %.3e' % (np.linalg.norm(ana - num) / np.linalg.norm(ana)))

# directional derivative with a healthy step
for h in (1e-3, 1e-4):
    fd = (fu.fonly([y0[i] + h * dy[i] for i in range(R)])
          - fu.fonly([y0[i] - h * dy[i] for i in range(R)])) / (2 * h)
    an = float(sum(np.sum(g[i] * dy[i]) for i in range(R)))
    print('directional FD h=%.0e: %.10e  analytic %.10e  rel %.2e'
          % (h, fd, an, abs(fd - an) / max(abs(an), 1e-30)))
