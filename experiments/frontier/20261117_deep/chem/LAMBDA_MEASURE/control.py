"""Control: can the alternating protocol recover the shipped-shape fit after
damaging the basis? This separates "protocol too weak" from "shape too small".

At (8,143,44) the exact-objective fit reaches 16.55 mHa from the shipped table.
Here the shipped table is damaged (k of the 143 basis vectors per group replaced
by random unit vectors, or the weights perturbed), and the same protocol is run.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import fitlib as F
import infra as I

log = F.log
z = np.load(I.ROOT / 'experiments/frontier/20261117_deep/chem/data/dfthcsos/submission.npz')
U0, w0 = z['U'], z['W']
R, B, N = U0.shape
C = w0.shape[2]
pb = F.Problem()
rng = np.random.default_rng(3)


def damage(x0, k_drop, noise):
    x = x0.copy()
    w = x[:R * B * C].reshape(R, B, C).copy()
    U = x[R * B * C:].reshape(R, B, N).copy()
    if k_drop:
        for r in range(R):
            idx = rng.choice(B, k_drop, replace=False)
            V = rng.standard_normal((k_drop, N))
            V -= V @ U[r].T @ U[r]
            V /= np.linalg.norm(V, axis=1, keepdims=True)
            U[r, idx] = V
            w[r, idx] *= 0.1
    if noise:
        U = U + noise * rng.standard_normal(U.shape)
        w = w * (1 + noise * rng.standard_normal(w.shape))
    return np.concatenate([w.ravel(), U.ravel()])


x0 = np.concatenate([w0.ravel(), U0.ravel()])
for k_drop, noise, tag in ((14, 0.0, 'drop14'), (14, 0.05, 'drop14+noise'),
                           (0, 0.05, 'noise5%')):
    x = damage(x0, k_drop, noise)
    log(f'-- {tag}: init {pb.e2_reduced(x, R, B, C):.1f} mHa')
    x = F.alt_min(pb, x, R, B, C, rounds=8, itw=200, itu=100, tag=tag)
    log(f'-- {tag}: FINAL {pb.e2_reduced(x, R, B, C):.3f} mHa')
