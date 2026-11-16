"""Local shrink probe: merge B10c54 pairs -> (5,240,108), then fade bases/copies to
(5,143,75) with an exact weights-only refit (vectors fixed), all in the 2926-dim
error_2 geometry.  This is a lower bound on what the pipeline's full (u,w) refit can
do, and it says whether the (5,143,75) target is worth a long CPU run.
"""
import sys, importlib.util, numpy as np
from scipy.optimize import minimize

V = '/Users/zhaohuaxiang/ccjjllt/quantum/data/competition/verifiers/dfthcsos'
def load(n, p):
    sp = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(sp); sys.modules[n] = m; sp.loader.exec_module(m); return m
refm = load('dfthcsos.scoreinfra.reference', f'{V}/scoreinfra/reference.py')
dfm = load('dfthcsos.scoreinfra.dfthc_math', f'{V}/scoreinfra/dfthc_math.py')
ref = refm.load_reference(refm.check_fcidump())
tei = np.asarray(ref['tei'], float); N = tei.shape[0]
S = dfm.symmetric_from_lower(refm.load_fixed_shifts()['Hsym_lower'], N).astype(float)
pairs = [(p, q) for p in range(N) for q in range(p, N)]
PA = np.array(pairs); NS = len(pairs)
wgt = np.array([1.0 if p == q else 2.0 for p, q in pairs]); sqw = np.sqrt(wgt)
flat = np.array([p * N + q for p, q in pairs]); isdiag = np.array([p == q for p, q in pairs])
t2 = tei.reshape(N * N, N * N)
Gm = np.empty((NS, NS))
for a, (p, q) in enumerate(pairs):
    Gm[a] = t2[p * N + q, flat] + 0.5 * S[p, q] * isdiag + 0.5 * S.ravel()[flat] * (1.0 if p == q else 0.0)
Gm = 0.5 * (Gm + Gm.T); H = sqw[:, None] * Gm * sqw[None, :]
del t2, Gm
ev = np.linalg.eigvalsh(H)[::-1]; neg2 = float(np.sum(np.minimum(ev, 0) ** 2))
fl = lambda K: 1e3 * np.sqrt((np.maximum(ev, 0) ** 2)[K:].sum() + neg2)


def proj(U):
    P = np.einsum('bp,bq->bpq', U, U, optimize=True)
    return (P[:, PA[:, 0], PA[:, 1]] * sqw[None, :]).T


def e2_and_fit(U, w, fit=True, iters=200):
    """exact error_2 of (U,w); optionally L-BFGS on w at fixed U (unit-normalised)."""
    R, B, _ = U.shape; C = w.shape[2]
    Un = U / np.linalg.norm(U, axis=2, keepdims=True)
    Ps = [proj(Un[r]) for r in range(R)]
    def build(wv):
        ww = wv.reshape(R, B, C)
        return np.concatenate([Ps[r] @ ww[r] for r in range(R)], axis=1)
    def fg(wv):
        Y = build(wv)
        S_ = Y @ Y.T - H
        f = float(np.sum(S_ * S_))
        gY = 4.0 * (S_ @ Y)
        gw = np.stack([Ps[r].T @ gY[:, r * C:(r + 1) * C] for r in range(R)])
        return f, gw.ravel()
    f0 = fg(w.ravel())[0]
    if fit and iters:
        res = minimize(fg, w.ravel(), jac=True, method='L-BFGS-B',
                       options=dict(maxiter=iters, maxcor=30, ftol=1e-18, gtol=1e-14))
        w = res.x.reshape(R, B, C)
        f0 = fg(w.ravel())[0]
    return 1e3 * np.sqrt(max(f0, 0.0)), w


D = '/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/merge_pipe'
z = np.load(f'{D}/B10c54.npz')
U0, w0 = z['U'].astype(float), z['W'].astype(float)
e, _ = e2_and_fit(U0, w0, fit=False)
print(f'seed B10c54 (10,120,54): e2 {e:.3f} mHa (K={10*54}, floor {fl(540):.2f})', flush=True)

# --- exact merge of pairs, as structure.merge does (block-diagonal weights)
R0, B0, C0 = w0.shape
imp = np.sum(w0 ** 2, axis=2).sum(axis=1)
order = np.argsort(-imp)
R1 = R0 // 2
U = np.zeros((R1, 2 * B0, N)); w = np.zeros((R1, 2 * B0, 2 * C0))
for g in range(R1):
    mem = order[g * 2:(g + 1) * 2]
    for j, r in enumerate(mem):
        U[g, j * B0:(j + 1) * B0] = U0[r]
        w[g, j * B0:(j + 1) * B0, j * C0:(j + 1) * C0] = w0[r]
e, w = e2_and_fit(U, w, fit=False)
print(f'merged (5,240,108): e2 {e:.3f} mHa (exact merge check)', flush=True)

# --- fade + remove bases by impact (sum_c w^2), refit w only
R = w.shape[0]
for Bt in (200, 170, 155, 143):
    score = np.sum(w ** 2, axis=2)                      # (R,B)
    keep = np.argsort(-score, axis=1)[:, :Bt]
    Un = np.stack([U[r][keep[r]] for r in range(R)])
    wn = np.stack([w[r][keep[r]] for r in range(R)])
    e, wn = e2_and_fit(Un, wn, fit=True, iters=60)
    print(f'  B={Bt} (vectors fixed, w refit): e2 {e:.3f} mHa', flush=True)
    U, w = Un, wn
# --- fade copies (drop weakest by ||X||) down to 75, refit w only
for Ct in (100, 90, 82, 75):
    sc = np.stack([np.sum(np.einsum('bc,bpq->cpq', w[r],
                                    np.einsum('bp,bq->bpq', U[r], U[r], optimize=True), optimize=True) ** 2,
                          axis=(1, 2)) for r in range(w.shape[0])])   # (R,C)
    keepc = np.argsort(-sc, axis=1)[:, :Ct]
    wn = np.stack([w[r][:, keepc[r]] for r in range(w.shape[0])])
    e, wn = e2_and_fit(U, wn, fit=True, iters=60)
    print(f'  B=143 C={Ct} (w refit only): e2 {e:.3f} mHa  floor {fl(5*Ct):.2f} '
          f'rho {e/fl(5*Ct):.2f}', flush=True)
    w = wn
