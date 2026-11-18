"""Multi-start at C=44 with the word-U frozen: how low can the *fixed-U* fit go?

Inits:
  ship  : the shipped w
  cont  : the continuous-U 16.55 fit's w (same shape)
  diag  : top-C eigenpairs of each group's own H_rr  (block-diagonal optimum)
  relax : per-group rank-C truncation of the relaxed optimum of H_S (the K-dim
          eigenspace of H_S restricted to each S_r) -- the principled start
  noise : ship + s * N(0,1)
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import infra as I
import wsolve as WS

N = 76
z = np.load(I.ROOT / 'experiments/frontier/20261117_deep/chem/data/dfthcsos/submission.npz')
U = z['U'].astype(np.float64)
w0 = z['W'].astype(np.float64)
ps = I.cached_pair_space()
H, PA, sqw = ps['H'], ps['PA'], ps['sqw']
R, B, N = U.shape
C = int(sys.argv[1]) if len(sys.argv) > 1 else 44
sweeps = int(sys.argv[2]) if len(sys.argv) > 2 else 25
cg = int(sys.argv[3]) if len(sys.argv) > 3 else 120

fu = WS.FixedU(U, H, PA, sqw)
print(f'C={C}  floor(relaxed, K={R*C}) see diag_c2: ', flush=True)

y_ship = fu.y_from_w(w0[:, :, :C])


def y_relax():
    P = np.concatenate(fu.Ps, axis=1)
    G = P.T @ P
    A = P.T @ (H @ P)
    g, Vv = np.linalg.eigh(G)
    g = np.maximum(g, 1e-14)
    Wt = Vv / np.sqrt(g)
    M = Wt.T @ A @ Wt
    mu, Uu = np.linalg.eigh(0.5 * (M + M.T))
    order = np.argsort(mu)[::-1][:R * C]
    Yh = (Uu[:, order] * np.sqrt(np.maximum(mu[order], 0.0)))     # (1144, K) in Q coords
    out = []
    for r in range(R):
        blk = Yh[r * B:(r + 1) * B, :]
        u, s, vt = np.linalg.svd(blk, full_matrices=False)
        out.append((u[:, :C] * s[:C]))
    return out


def y_diag():
    out = []
    for r in range(R):
        lam, Vv = np.linalg.eigh(fu.Hd[r])
        order = np.argsort(lam)[::-1][:C]
        out.append(Vv[:, order] * np.sqrt(np.maximum(lam[order], 0.0)))
    return out


def run(tag, y, iters=sweeps, cgi=cg):
    fu2 = fu
    y1, h = fu2.solve([a.copy() for a in y], iters=iters, cg_iters=cgi, tag=tag,
                      exact_every=5, verbose=True)
    e = fu2.e2_mha(y1)
    w = fu2.w_from_y(y1)
    a = np.abs(w).sum(axis=1)
    s = w.sum(axis=1)
    print(f'== {tag}: e2 {e:.4f} mHa   sum a^2 {np.sum(a**2):.2f}  sum s^2 {np.sum(s**2):.2f}'
          f'  max|w| {np.abs(w).max():.3f}', flush=True)
    np.savez_compressed(I.CACHE / f'y_C{C}_{tag}.npz', y=np.stack(y1), C=C)
    return e, y1


res = {}
res['ship'] = run('ship', y_ship)
f = I.CACHE / 'fit_8_143_44.npz'
if f.exists():
    zz = np.load(f)
    x = zz['x']
    nw = 8 * 143 * 44
    wc = x[:nw].reshape(8, 143, 44)
    res['cont'] = run('cont', fu.y_from_w(wc[:, :, :C]))
res['diag'] = run('diag', y_diag())
res['relax'] = run('relax', y_relax())
rng = np.random.default_rng(7)
for sc in (0.02, 0.1):
    yi = [a + sc * rng.standard_normal(a.shape) * np.sqrt(np.mean(a ** 2)) for a in y_ship]
    res[f'noise{sc}'] = run(f'noise{sc}', yi)
print('\nSUMMARY C=%d' % C)
for k, (e, _) in sorted(res.items(), key=lambda kv: kv[1][0]):
    print(f'  {k:10s} {e:9.4f} mHa')
