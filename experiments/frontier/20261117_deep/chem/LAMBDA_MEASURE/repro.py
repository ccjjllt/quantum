"""Step 0: reproduce the shipped point from the packaged FCIDUMP, locally.

Checks that (a) the reference integrals load and match the competition checksum,
(b) the official `evaluate_dfthc_angle_words` on the shipped 8-bit words returns
the shipped lambda_eff 46.921716818, error_2 ~14.2 mHa, Lambda 283.14,
(c) the pair-space H used by the shape fits reproduces the official error_2.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import infra as I

T0 = time.time()


def log(*a):
    print(f'[{time.time()-T0:7.1f}s]', *a, flush=True)


SHIP = I.ROOT / 'experiments/frontier/20261117_deep/chem/data/dfthcsos/submission.npz'
z = np.load(SHIP)
U, w, W = z['U'], z['W'], z['H2_I']
words, tree = z['angle_words'], z['tree_edges']
R, B, N = U.shape
C = w.shape[2]
log(f'shipped npz: U {U.shape} w {w.shape} W {W.shape} words {words.shape} '
    f'tree {tree.shape}')

ref, S, beta1 = I.reference()
log(f'ref: N={ref["orbitals"]} eta={ref["electrons"]} ecore={ref["ecore"]:.9f} '
    f'beta1={beta1:.9f} tei {ref["tei"].shape}')
PS = I.pair_space(ref, S)
H = PS['H']
ev = np.linalg.eigvalsh(H)[::-1]
neg2 = float(np.sum(np.minimum(ev, 0) ** 2))
log(f'H: shape {H.shape} ||H||_F {np.linalg.norm(H):.6f}  '
    f'spectral tail floors: ' + '  '.join(f'K={K}:{I.floor_mha(ev, K, neg2):.3f}'
                                          for K in (352, 432, 480, 512, 560)))
np.savez(I.CACHE / 'spectrum.npz', ev=ev, neg2=neg2)

# ---- official path: the shipped 8-bit words
m = I.metrics_from_words(words, w, W, tree, ref, S, beta1, brot=8)
log('official evaluate_dfthc_angle_words (shipped words, brot=8):')
for k, v in m.items():
    log(f'   {k:14s} {v!r}')

d = I.decompose(I.dfm.reconstruct_u_vectors(words / 128.0, tree), w, W, ref, S, beta1)
log('decomposition:')
for k, v in d.items():
    log(f'   {k:14s} {v}')

# ---- pair-space error_2 cross-check (unquantized vectors)
u_all = I.dfm.reconstruct_u_vectors(words / 128.0, tree)
u_b = u_all[N:].reshape(R, B, N)
X = np.einsum('gbp,gbq,gbc->gcpq', u_b / np.linalg.norm(u_b, axis=2, keepdims=True),
              u_b / np.linalg.norm(u_b, axis=2, keepdims=True), w, optimize=True)
X = np.tril(X) + np.swapaxes(np.tril(X, k=-1), -1, -2)
Y = np.zeros((PS['NS'], R * C))
for r in range(R):
    P = np.einsum('bp,bq->bpq', u_b[r] / np.linalg.norm(u_b[r], axis=1, keepdims=True),
                  u_b[r] / np.linalg.norm(u_b[r], axis=1, keepdims=True), optimize=True)
    Pp = (P[:, PS['PA'][:, 0], PS['PA'][:, 1]] * PS['sqw'][None, :]).T
    Y[:, r * C:(r + 1) * C] = Pp @ w[r]
log(f'pair-space error_2 {I.e2_pair(Y, H):.4f} mHa   vs official '
    f'{1e3*m["error_2"]:.4f} mHa')

out = dict(metrics=m, decomp=d, floor_352=I.floor_mha(ev, 352, neg2),
           floor_480=I.floor_mha(ev, 480, neg2), H_fro=float(np.linalg.norm(H)))
(I.CACHE / 'repro.json').write_text(json.dumps(out, indent=1, default=float))
log('DONE')
