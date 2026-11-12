"""Numbers behind the shape question: target norm, term spectra, public-table metrics."""
from __future__ import annotations

import time

import numpy as np

import common as C

prob, ref = C.get_target()
T = np.asarray(prob[0])
print('T P=%d ||T||_F %.4f trace %.4f' % (T.shape[0], np.linalg.norm(T), np.trace(T)))
ev = np.linalg.eigvalsh(T)
print('T top eigenvalues', np.round(ev[::-1][:6], 4), 'min %.4f' % ev[0], 'neg %d' % int((ev < 0).sum()))

for name, path in (('current 8x143x44', C.CURRENT), ('pub 8x143x45', C.PUB8), ('pub 4x255x120', C.PUB4)):
    d = C.load(path)
    U, w = np.asarray(d['U'], np.float64), np.asarray(d['W'], np.float64)
    t0 = time.time()
    o = C.official(path)
    ef = C.e2(U, w, prob)
    print(f'\n{name}: float e2 {1e3*ef:.4f} mHa | words e1 {o["e1"]:.5f} e2 {o["e2"]:.5f} '
          f'Lambda {o["Lambda"]:.3f} E_gap {o["E_gap"]:.9f} lambda_eff {o["lambda_eff"]:.5f} ({time.time()-t0:.1f}s)')
    X = C.terms(U, w, ref)
    sv = np.linalg.svd(X, compute_uv=False)
    tot = (sv ** 2).sum()
    print(f'  terms {X.shape}, ||X||^2 {tot:.4f}, rank-max {min(X.shape)}')
    for k in (32, 44, 64, 80, 96, 120, 176, 255, 352, 480):
        if k <= len(sv):
            print('   keep %3d: %.5f' % (k, (sv[:k] ** 2).sum() / tot), end='')
    print()
    # per-group G spectrum: rank needed per group
    print('  per-group singular values of W_r (rank cap):', end='')
    for r in range(w.shape[0]):
        s = np.linalg.svd(w[r], compute_uv=False)
        e = (s ** 2).sum()
        print(' [%d n>1e-6:%d top3 %.2f/%.2f/%.2f]' % ((s > 1e-9).sum(), (s ** 2 / e)[:3]), end='')
    print()
