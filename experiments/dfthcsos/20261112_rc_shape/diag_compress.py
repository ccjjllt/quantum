"""Diagnose the compression: exact merge, then B truncation, then C truncation."""
from __future__ import annotations

import numpy as np

import common as C
import seed_rc as S

prob, ref = C.get_target()
d = C.load(C.CURRENT)
U, w = np.asarray(d['U']), np.asarray(d['W'])
i, j = (np.asarray(t) for t in ref['tril'])
mult = np.where(i == j, 1.0, 2.0)
dvec = np.sqrt(mult)              # the metric's per-pair weight

A_all = S.atoms_of(np.concatenate([U[2], U[4]])[None])[0]     # (286, P)
wc = np.concatenate([w[2], w[4]], axis=0)                     # (286, 44)
X = wc.T @ A_all                                              # (44, P) exact term vectors
print('cluster exact: residual of X vs itself 0; ||X||_F %.4f' % np.linalg.norm(X))
# Frobenius residual of the cluster rewrite sum_c x_c x_c^T vs the compressed group
def table_error(groups, new_group):
    """replace groups in `groups` by new_group (U (B,N), W (B,Cnew)) and score error_2."""
    Us, Ws = [], []
    Cn = new_group[1].shape[1]
    for r in range(8):
        if r in groups:
            continue
        Us.append(U[r])
        Wp = np.zeros((w.shape[1], Cn))
        Wp[:, :w.shape[2]] = w[r]
        Ws.append(Wp)
    Us.append(new_group[0])
    Ws.append(new_group[1])
    return C.e2(np.stack(Us), np.stack(Ws), prob)

print('baseline', 1e3 * C.e2(U, w, prob))
for B, Cn in ((286, 88), (286, 44), (143, 88), (143, 64)):
    Un, Wn, sel = S.compress_cluster(np.concatenate([U[2], U[4]]), wc, B, Cn)
    e = table_error((2, 4), (Un, Wn))
    print('B=%d C=%d -> table e2 %.4f mHa' % (B, Cn, 1e3 * e))

# metric check: residual in the weighted norm of the cluster alone
for B, Cn in ((286, 88), (143, 88), (143, 64)):
    Un, Wn, sel = S.compress_cluster(np.concatenate([U[2], U[4]]), wc, B, Cn)
    An = S.atoms_of(Un[None])[0]
    Y = (Wn.T @ An)                       # (Cn, P) rebuilt term vectors
    # best possible: projection of X onto Y's span
    print('B=%d C=%d: ||Y|| %.4f vs ||X|| %.4f' % (B, Cn, np.linalg.norm(Y), np.linalg.norm(X)))
