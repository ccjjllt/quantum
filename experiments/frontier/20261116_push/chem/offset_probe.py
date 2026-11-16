"""Is there any lambda_eff left in the offsets at fixed words?

Free parameters: the offsets W (R,C) = H2_I - sum_b w.  Invariants under column
rotations are already exhausted (rotate_columns.py).  Here we do a projected
gradient on W with the exact lambda/E_gap gradients (refine.py's formulas) and a
hard rejection of any step that breaks error_1 <= 20 mHa or E_gap > floor, since
the words (and hence the one-body rows) are fixed by the circuits.
"""
import sys, importlib.util, json, numpy as np
V = '/Users/zhaohuaxiang/ccjjllt/quantum/data/competition/verifiers/dfthcsos'
def load(n, p):
    sp = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(sp); sys.modules[n] = m; sp.loader.exec_module(m); return m
refm = load('dfthcsos.scoreinfra.reference', f'{V}/scoreinfra/reference.py')
dfm = load('dfthcsos.scoreinfra.dfthc_math', f'{V}/scoreinfra/dfthc_math.py')
ref = refm.load_reference(refm.check_fcidump())
S = dfm.symmetric_from_lower(refm.load_fixed_shifts()['Hsym_lower'], 76).astype(float)
eta = int(ref['electrons'])
UPPER = refm.UPPER_ENERGY
NPZ = '/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/boristown_out/ext/dfthcsos/submission.npz'
z = np.load(NPZ, allow_pickle=False)
d = {k: np.array(z[k]) for k in z.files}
w = np.asarray(d['W'], float); H2 = np.asarray(d['H2_I'], float)
words = np.asarray(d['angle_words']); edges = np.asarray(d['tree_edges'])
R, B, C = w.shape
beta1 = float(d['H1_I']) - 0.5 * float(np.trace(S))
u_all = dfm.reconstruct_u_vectors(words / 128.0, edges)
u_all = u_all / np.linalg.norm(u_all, axis=1, keepdims=True)
one_body = u_all[:76]
u2 = u_all[76:].reshape(R, B, 76)
X = np.zeros((R, C, 76, 76))
for r in range(R):
    P = np.einsum('bp,bq->bpq', u2[r], u2[r], optimize=True)
    X[r] = np.einsum('bc,bpq->cpq', w[r], P, optimize=True)
X = np.tril(X) + np.swapaxes(np.tril(X, -1), -1, -2)
h1_thc = np.asarray(ref['h1_thc'], float)
h1_base = h1_thc - 0.5 * eta * S + beta1 * np.eye(76)
energy = UPPER - ref['ecore'] + eta * beta1
sum_w = w.sum(axis=1); l1_w = np.abs(w).sum(axis=1)
GAP_FLOOR = 3.914898


def state(Wo):
    k = np.einsum('rc,rbc->rb', Wo, w)
    h1 = h1_base - np.einsum('rb,rbp,rbq->pq', k, u2, u2, optimize=True)
    vals, vecs = np.linalg.eigh(h1)
    sign = (vecs * np.sign(vals)) @ vecs.T
    c = np.einsum('rbp,pq,rbq->rb', u2, sign, u2, optimize=True)
    gap = energy + np.abs(vals).sum() - vals.sum() + 0.5 * np.sum(Wo ** 2)
    wB = Wo + sum_w
    lam = np.abs(vals).sum() + 0.25 * np.sum((l1_w + np.abs(wB)) ** 2)
    d_abs = -np.einsum('rb,rbc->rc', c, w)
    g_gap = d_abs + sum_w + Wo
    g_lam = d_abs + 0.5 * (l1_w + np.abs(wB)) * np.sign(wB)
    e1 = dfm.h1_thc_reconstruction_error(one_body, h1_thc, S, beta1, eta, Wo, X)
    e2 = None
    return gap, lam, e1, g_gap, g_lam


def leff(gap, lam):
    return np.sqrt(gap * (2 * lam - gap))


Wo = H2 - w.sum(axis=1)
gap, lam, e1, g_gap, g_lam = state(Wo)
print(f'base: gap {gap:.10f} Lam {lam:.6f} e1 {1e3*e1:.6f} mHa lambda_eff {leff(gap,lam):.8f} '
      f'cost {leff(gap,lam)*14712*427:.2f}', flush=True)
E1_MAX = 0.0199995
best = (leff(gap, lam), Wo.copy(), gap, lam, e1)
step = 1e-3
for it in range(4000):
    gap, lam, e1, g_gap, g_lam = state(Wo)
    L = leff(gap, lam)
    rad = gap * (2 * lam - gap)
    g = ((lam - gap) * g_gap + gap * g_lam) / rad          # d log L / dW
    d = -g / (np.linalg.norm(g) + 1e-30)
    ok = False
    for _ in range(30):
        Wt = Wo + step * d
        gt, lt, e1t, _, _ = state(Wt)
        if gt > GAP_FLOOR + 1e-9 and e1t <= E1_MAX and leff(gt, lt) < L:
            Wo, step, ok = Wt, step * 1.5, True
            break
        step *= 0.5
    if not ok:
        break
    if it % 200 == 0:
        gt, lt, e1t, _, _ = state(Wo)
        print(f'  it {it}: gap {gt:.10f} Lam {lt:.6f} e1 {1e3*e1t:.6f} lam {leff(gt,lt):.8f} '
              f'cost {leff(gt,lt)*14712*427:.2f}', flush=True)
gap, lam, e1, _, _ = state(Wo)
L = leff(gap, lam)
print(f'FINAL: gap {gap:.10f} Lam {lam:.6f} e1 {1e3*e1:.6f} mHa lambda_eff {L:.8f} '
      f'cost {L*14712*427:.2f}  (base 294762632.08)', flush=True)
if L * 14712 * 427 < 294762632.0:
    out = dict(d); out['H2_I'] = Wo + w.sum(axis=1)
    np.savez('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/refit_bdae/submission_off.npz', **out)
    print('saved offsets candidate', flush=True)
