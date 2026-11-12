"""Cluster-level diagnostic: ||T_cluster - T_approx||_F for B/C truncations (P=2926)."""
from __future__ import annotations

import numpy as np

import common as C
import seed_rc as S

prob, ref = C.get_target()
d = C.load(C.CURRENT)
U, w = np.asarray(d['U']), np.asarray(d['W'])
A_all = S.atoms_of(np.concatenate([U[2], U[4]])[None])[0]
wc = np.concatenate([w[2], w[4]], axis=0)
X = wc.T @ A_all
Tc = X.T @ X
print('cluster T: || ||_F %.4f  trace %.4f' % (np.linalg.norm(Tc), np.trace(Tc)))
print('full T:    || ||_F %.4f' % np.linalg.norm(np.asarray(prob[0])))

def cluster_res(B, Cn):
    Un, Wn, sel = S.compress_cluster(np.concatenate([U[2], U[4]]), wc, B, Cn)
    An = S.atoms_of(Un[None])[0]
    Y = Wn.T @ An
    Ta = Y.T @ Y
    return np.linalg.norm(Tc - Ta), np.linalg.norm(Tc - Y[:len(Y)].T @ Y)

# exact reference (no truncation at all, no OMP)
for B, Cn in ((286, 88), (286, 64), (200, 88), (143, 88), (143, 64), (143, 50)):
    r, _ = cluster_res(B, Cn)
    print('B=%3d C=%2d: ||T_cluster-T_approx||_F %8.4f mHa  (%.5f of full ||T||)' % (
        B, Cn, 1e3 * r, r / 12.10))
