"""Free Lambda lever: orthogonal rotations of each group's copy columns.

For a group, A = [w ; H2_I] is (B+1, C).  Right-multiplying by Q in O(C) keeps
    w w^T          -> error_2 unchanged,
    w H2_I^T       -> h1' (hence error_1, E_gap) unchanged,
    |H2_I|^2       -> E_gap unchanged,
and only changes Lambda's two-body L1 term
    L2 = 1/4 sum_rc ( |H2_I,r_c| + sum_b |w_r_b_c| )^2 .
So this is a zero-error-cost lever on lambda_eff.  Search: pair sweeps with a fine
angle grid, several Haar-random restarts, keep the best per group.
"""
import sys, json, numpy as np
from pathlib import Path

BASE = Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/boristown_out/ext/dfthcsos/submission.npz')
OUT = Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/refit_bdae')
OUT.mkdir(exist_ok=True)
z = np.load(BASE, allow_pickle=False)
d = {k: np.array(z[k]) for k in z.files}
w = np.asarray(d['W'], float)                  # (R, B, C) weights
H2 = np.asarray(d['H2_I'], float)              # (R, C)  = offset + sum_b w
R, B, C = w.shape
print('shape', w.shape, 'H2', H2.shape, flush=True)


def l2(wg, Hg):
    """Lambda's two-body term for one group."""
    m = np.abs(Hg) + np.abs(wg).sum(axis=0)
    return 0.25 * float(np.sum(m ** 2)), m


def sweep(wg, Hg, grid=72, sweeps=6):
    """Greedy pair rotations with a fine angle grid."""
    A = np.vstack([wg, Hg[None, :]])            # (B+1, C)
    best = l2(wg, Hg)[0]
    for _ in range(sweeps):
        improved = False
        for i in range(C):
            for j in range(i + 1, C):
                th = np.linspace(0, np.pi, grid, endpoint=False)
                cs, sn = np.cos(th), np.sin(th)
                # rotate columns i,j:  col_i' = c*col_i - s*col_j ; col_j' = s*col_i + c*col_j
                ai, aj = A[:, i].copy(), A[:, j].copy()
                bestv, bestt = best, None
                for t in range(len(th)):
                    A[:, i] = cs[t] * ai - sn[t] * aj
                    A[:, j] = sn[t] * ai + cs[t] * aj
                    v = 0.25 * float(np.sum((np.abs(A[-1]) + np.abs(A[:-1]).sum(axis=0)) ** 2))
                    if v < bestv - 1e-15:
                        bestv, bestt = v, t
                if bestt is None:
                    A[:, i], A[:, j] = ai, aj
                else:
                    A[:, i] = cs[bestt] * ai - sn[bestt] * aj
                    A[:, j] = sn[bestt] * ai + cs[bestt] * aj
                    best = bestv
                    improved = True
        if not improved:
            break
    return A[:-1].copy(), A[-1].copy(), best


def haar(C, rng):
    q, r = np.linalg.qr(rng.normal(size=(C, C)))
    return q * np.sign(np.diag(r))[None, :]


rng = np.random.default_rng(20261116)
w_new = w.copy(); H2_new = H2.copy()
tot0 = sum(l2(w[r], H2[r])[0] for r in range(R))
tot1 = 0.0
for r in range(R):
    v0 = l2(w[r], H2[r])[0]
    wg, Hg, v = sweep(w[r], H2[r])
    best = (v, wg, Hg)
    for trial in range(6):                       # random restarts
        Q = haar(C, rng)
        wg2, Hg2, v2 = sweep(w[r] @ Q, H2[r] @ Q)
        if v2 < best[0]:
            best = (v2, wg2, Hg2)
    print(f'group {r}: L2 {v0:.5f} -> {best[0]:.5f} ({100*(best[0]/v0-1):+.4f}%)', flush=True)
    w_new[r], H2_new[r] = best[1], best[2]
    tot1 += best[0]
print(f'L2 total {tot0:.5f} -> {tot1:.5f}  (delta {tot1-tot0:+.6f})', flush=True)

# ---- assemble and score with the official metric function
sys.path.insert(0, '/Users/zhaohuaxiang/ccjjllt/quantum/.venv/lib/python3.12/site-packages')
sys.path.insert(0, '/Users/zhaohuaxiang/ccjjllt/quantum/data/competition/verifiers')
import importlib.util
def load(n, p):
    sp = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(sp); sys.modules[n] = m; sp.loader.exec_module(m); return m
V = '/Users/zhaohuaxiang/ccjjllt/quantum/data/competition/verifiers/dfthcsos'
refm = load('dfthcsos.scoreinfra.reference', f'{V}/scoreinfra/reference.py')
dfm = load('dfthcsos.scoreinfra.dfthc_math', f'{V}/scoreinfra/dfthc_math.py')
ref = refm.load_reference(refm.check_fcidump())
S = dfm.symmetric_from_lower(d['Hsym_lower'], 76).astype(float)
b1 = float(d['H1_I']) - 0.5 * float(np.trace(S))
for tag, (ww, HH) in (('base', (w, H2)), ('rotated', (w_new, H2_new))):
    m = dfm.evaluate_dfthc_angle_words(np.asarray(d['angle_words']), ww, HH, S, b1, ref, brot=8,
                                       tree_edges=np.asarray(d['tree_edges']),
                                       energy_upper=refm.UPPER_ENERGY)
    ok = (m['error_1'] <= 0.02 and m['error_2'] <= 0.02 and m['E_gap'] > 3.914898 and m['Lambda'] > 49)
    print(f'{tag:8s} e1 {1e3*m["error_1"]:.6f} e2 {1e3*m["error_2"]:.7f} Lambda {m["Lambda"]:.6f} '
          f'E_gap {m["E_gap"]:.10f} lambda_eff {m["lambda_eff"]:.8f} cost {m["lambda_eff"]*14712*427:.3f} ok={ok}',
          flush=True)
    if tag == 'rotated':
        out = dict(d)
        out['W'] = ww
        out['H2_I'] = HH
        np.savez(OUT / 'submission_rot.npz', **out)
