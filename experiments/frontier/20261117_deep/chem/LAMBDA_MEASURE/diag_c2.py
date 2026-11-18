"""Corrected relaxed bound: eigenvalues of H_S = Proj_S H Proj_S via symmetric whitening.

For a fixed dictionary span S = sum_r S_r (S_r = span of the B rank-1 projectors of
group r), the relaxed problem over PSD M = YY^T with range(M) subset S is

    min ||M - H||^2 = ||H||^2 - sum_j max(lam_j(H_S), 0)^2 ,
    lam(H_S) = eig( G^{-1/2} (P^T H P) G^{-1/2} ),   G = P^T P,

since <H_S, H - H_S> = 0 and ||H - H_S||^2 = ||H||^2 - ||H_S||^2.
That is a rigorous lower bound for every C at this U (it ignores the per-group
block structure of Y, so an actual fit can only be worse).
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import infra as I

N = 76
z = np.load(I.ROOT / 'experiments/frontier/20261117_deep/chem/data/dfthcsos/submission.npz')
U = z['U'].astype(np.float64)
R, B, _ = U.shape
ps = I.cached_pair_space()
H, PA, sqw = ps['H'], ps['PA'], ps['sqw']
Hfro2 = float(np.sum(H * H))
ev = np.linalg.eigvalsh(H)[::-1]
neg2 = float(np.sum(np.minimum(ev, 0) ** 2))
print(f'||H||_F {np.sqrt(Hfro2):.6f}  floor 352 {I.floor_mha(ev,352,neg2):.4f} '
      f'336 {I.floor_mha(ev,336,neg2):.4f} 320 {I.floor_mha(ev,320,neg2):.4f} '
      f'304 {I.floor_mha(ev,304,neg2):.4f}')


def frame(Ug):
    P = np.einsum('bp,bq->bpq', Ug, Ug, optimize=True)
    return np.ascontiguousarray((P[:, PA[:, 0], PA[:, 1]] * sqw[None, :]).T)


def span_eigs(Umat):
    Rr = Umat.shape[0]
    P = np.concatenate([frame(Umat[r]) for r in range(Rr)], axis=1)
    G = P.T @ P
    A = P.T @ (H @ P)
    g, V = np.linalg.eigh(G)
    g = np.maximum(g, 1e-14)
    W = V / np.sqrt(g)
    M = W.T @ A @ W
    M = 0.5 * (M + M.T)
    lam = np.linalg.eigvalsh(M)
    return lam, P


def report(tag, Umat):
    lam, P = span_eigs(Umat)
    lam = lam[::-1]
    pos = np.maximum(lam, 0)
    print(f'\n== {tag}: dim S={P.shape[1]}')
    print('   top lam', np.round(pos[:5], 3), 'neg count', int(np.sum(lam < 0)),
          'most neg %.3e' % lam.min())
    print('   ||H_S||^2 %.6f  out-of-span^2 %.6f (%.4f mHa)  sum pos^2 %.4f'
          % (np.sum(lam ** 2), Hfro2 - np.sum(lam ** 2),
             1e3 * np.sqrt(max(Hfro2 - np.sum(lam ** 2), 0)), np.sum(pos ** 2)))
    for K in (352, 344, 336, 328, 320, 304, 288):
        e = 1e3 * np.sqrt(max(Hfro2 - np.sum(pos[:K] ** 2), 0))
        print(f'   relaxed K={K}: lower bound {e:8.4f} mHa   (floor {I.floor_mha(ev,K,neg2):6.3f})')
    return lam


report('shipped word U (8,143)', U)

# reference: continuous U of the 16.55 fit
f = I.CACHE / 'fit_8_143_44.npz'
if f.exists():
    zz = np.load(f)
    x = zz['x']
    nw = 8 * 143 * 44
    Uc = x[nw:].reshape(8, 143, N)
    Uc = Uc / np.linalg.norm(Uc, axis=2, keepdims=True)
    report('continuous U of the (8,143,44) 16.55 fit', Uc)
