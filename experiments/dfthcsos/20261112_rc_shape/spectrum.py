"""How much of ||T||_F^2 sits in the term spectrum tails (decides whether C can shrink)."""
from __future__ import annotations

import numpy as np

import common as C

prob, ref = C.get_target()
T = np.asarray(prob[0])
print('||T||_F^2 %.5f  trace %.5f' % ((T * T).sum(), np.trace(T)))

for name, path, groups in (('current', C.CURRENT, 8), ('pub4', C.PUB4, None), ('pub8', C.PUB8, 8)):
    d = C.load(path)
    U = np.asarray(d['U'], np.float64)
    w = np.asarray(d['W'], np.float64)
    X = C.terms(U, w, ref)
    sv = np.linalg.svd(X, compute_uv=False)
    e = sv ** 2
    tot2 = (e ** 2).sum()
    print(f'\n{name}: terms {len(sv)}, sum s^2 {e.sum():.4f}, sum s^4 {tot2:.4f} (||T||^2 {np.sum(T*T):.4f})')
    for k in (6, 8, 16, 32, 44, 64, 88, 120, 176, 240, 352):
        if k <= len(sv):
            print('  k=%3d: sum s^2 %.4f (%.4f)  sum s^4 %.4f (%.5f)  ||T-T_k||_F %.4f' % (
                k, e[:k].sum(), e[:k].sum() / e.sum(), (e[:k] ** 2).sum(),
                (e[:k] ** 2).sum() / tot2, np.sqrt(max(tot2 - (e[:k] ** 2).sum(), 0))))
    if groups:
        # per-group spectra: energy tails within each group
        print('  per-group: (group: sum s^2, s^4 tail beyond 44)')
        for r in range(groups):
            s2 = np.linalg.svd(w[r], compute_uv=False) ** 2
            print('   g%d: sum %.3f  tail44 %.5f  tail%d %.5f' % (
                r, s2.sum(), (s2[44:] ** 2).sum(), 44, (s2[44:] ** 2).sum()), end='')
        print()
