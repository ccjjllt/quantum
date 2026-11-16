"""Group-constraint gate for R=5/B=143/C=75 (and R=6/B=143/C=64, R=8/B=143/C=44).

Exact reformulation of the verifier's error_2 (validated below against the shipped table):
    error_2^2 = || Y Y^T - H ||_F^2,   Y[:,k] = sqrt(weight) * vech(X_k)
    X_k = sum_b w_kb u_b u_b^T  (symmetric),   H = W^(1/2) M W^(1/2) (2926 x 2926)
so with K = R*C terms the continuous floor is the eigenvalue tail of H, and the real
DF-THC structure adds the constraint that each group's C terms live in a B-dimensional
span of rank-1 projectors u u^T.  This script measures that group loss by
spectral init -> cluster into R groups of C -> per-group (U, W) fit.
"""
import sys, importlib.util, json, time
import numpy as np
from scipy.optimize import minimize

V = 'data/competition/verifiers/dfthcsos'
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m); return m
refm = load('dfthcsos.scoreinfra.reference', f'{V}/scoreinfra/reference.py')
dfm = load('dfthcsos.scoreinfra.dfthc_math', f'{V}/scoreinfra/dfthc_math.py')

ref = refm.load_reference(refm.check_fcidump())
tei = np.asarray(ref['tei'], dtype=np.float64)
N = tei.shape[0]
S = dfm.symmetric_from_lower(refm.load_fixed_shifts()['Hsym_lower'], N).astype(np.float64)
pairs = [(p, q) for p in range(N) for q in range(p, N)]
PA = np.array(pairs)
NS = len(pairs)
wgt = np.array([1.0 if p == q else 2.0 for p, q in pairs])
sqw = np.sqrt(wgt)
flat = np.array([p * N + q for p, q in pairs])
isdiag = np.array([p == q for p, q in pairs])

tei2 = tei.reshape(N * N, N * N)
G = np.empty((NS, NS))
for a, (p, q) in enumerate(pairs):
    G[a] = tei2[p * N + q, flat] + 0.5 * S[p, q] * isdiag + 0.5 * S.ravel()[flat] * (1.0 if p == q else 0.0)
G = 0.5 * (G + G.T)
H = sqw[:, None] * G * sqw[None, :]
del G, tei2
ev, evec = np.linalg.eigh(H)
ev, evec = ev[::-1].copy(), evec[:, ::-1].copy()
neg2 = float(np.sum(np.minimum(ev, 0) ** 2))
def floor_mha(K):
    return 1e3 * np.sqrt((np.maximum(ev, 0) ** 2)[K:].sum() + neg2)
print('||H||_F %.6f ; floors 352/375/384 = %.3f / %.3f / %.3f mHa'
      % (np.sqrt(np.sum(H * H)), floor_mha(352), floor_mha(375), floor_mha(384)), flush=True)


def vec_of(X):
    return X[PA[:, 0], PA[:, 1]] * sqw


def mat_of(y):
    X = np.zeros((N, N))
    X[PA[:, 0], PA[:, 1]] = y / sqw
    return np.triu(X) + np.triu(X, 1).T


def group_fit(mats, B, iters=80, seed=0, tag=''):
    C, n, _ = mats.shape
    agg = sum(M @ M for M in mats)
    _, V2 = np.linalg.eigh(agg)
    base = V2[:, ::-1].T[:min(B, n)].copy()
    if B > n:                      # B > N: add projectors outside the eigenbasis
        rng = np.random.default_rng(seed + 7)
        extra = rng.standard_normal((B - n, n))
        base = np.vstack([base, extra])
    U0 = base
    U0 /= np.linalg.norm(U0, axis=1, keepdims=True)
    gn = np.sqrt(float(sum(np.sum(M * M) for M in mats)))

    def solve_w(U):
        UtU = U @ U.T          # (B,B): u_b . u_b'
        Gg = UtU * UtU         # <p_b,p_b'> = (u_b.u_b')^2
        Hh = np.stack([np.sum((U @ M) * U, axis=1) for M in mats], axis=1)   # (B, C)
        W = np.linalg.lstsq(Gg, Hh, rcond=1e-10)[0].T                        # (C, B)
        X = np.einsum('cb,bp,bq->cpq', W, U, U, optimize=True)
        X = 0.5 * (X + np.swapaxes(X, -1, -2))
        res = float(sum(np.sum((X[c] - mats[c]) ** 2) for c in range(C)))
        return W, X, res

    def obj(x):
        return solve_w(x.reshape(B, n))[2]

    def grad(x):
        U = x.reshape(B, n)
        W, X, _ = solve_w(U)
        R = X - mats
        return (-4.0 * np.einsum('cb,cpq,bq->bp', W, R, U, optimize=True)).ravel()

    _, _, res0 = solve_w(U0)
    out = minimize(obj, U0.ravel(), jac=grad, method='L-BFGS-B',
                   options=dict(maxiter=iters, maxcor=20, ftol=1e-16, gtol=1e-14))
    W, X, res = solve_w(out.x.reshape(B, n))
    print(f'      {tag}: init {1e3*np.sqrt(res0):8.3f} -> fit {1e3*np.sqrt(res):8.3f} mHa '
          f'({100*np.sqrt(res)/gn:5.1f}% of group norm) | {out.nit} iters', flush=True)
    return X


def run(R, B, C, seed=0):
    K = R * C
    t0 = time.time()
    Y = evec[:, :K] * np.sqrt(np.maximum(ev[:K], 0))[None, :]
    mats = np.stack([mat_of(Y[:, k]) for k in range(K)])
    # cluster by the leading eigenvector with deterministic signs
    lead = []
    for k in range(K):
        w2, v2 = np.linalg.eigh(mats[k])
        v = v2[:, -1]
        if v[int(np.argmax(np.abs(v)))] < 0:
            v = -v
        lead.append(v)
    lead = np.array(lead)
    rng = np.random.default_rng(seed)
    cent = [lead[int(np.argmax(np.linalg.norm(lead, axis=1)))]]
    while len(cent) < R:
        d = np.min([np.sum((lead - c) ** 2, axis=1) for c in cent], axis=0)
        cent.append(lead[int(np.argmax(d))])
    cent = np.array(cent)
    for _ in range(40):
        d = np.stack([np.sum((lead - c) ** 2, axis=1) for c in cent], axis=1)
        lab = np.argmin(d, axis=1)
        for r in range(R):
            if np.any(lab == r):
                cent[r] = lead[lab == r].mean(axis=0)
    d = np.stack([np.sum((lead - c) ** 2, axis=1) for c in cent], axis=1)
    lab = np.argmin(d, axis=1)
    # balance to C per group, using each mode's preference order
    pref = np.argsort(d, axis=1)
    cnt = np.zeros(R, int)
    assign = -np.ones(K, int)
    for k in range(K):
        for r in pref[k]:
            if cnt[r] < C:
                assign[k] = r; cnt[r] += 1; break
    for k in np.flatnonzero(assign < 0):
        r = int(np.argmin(cnt))
        assign[k] = r; cnt[r] += 1
    print(f'shape R={R} B={B} C={C}: K={K}, groups {list(cnt)}', flush=True)
    Xs = np.zeros((K, N, N))
    for r in range(R):
        idx = np.flatnonzero(assign == r)
        Xs[idx] = group_fit(mats[idx], B, seed=seed + r, tag=f'g{r}')
    Yf = np.stack([vec_of(X) for X in Xs], axis=1)
    e2 = float(np.linalg.norm(Yf @ Yf.T - H))
    print(f'  R={R} B={B} C={C}: continuous error_2 = {1e3*e2:.3f} mHa  '
          f'(floor {floor_mha(K):.3f}, {1e3*e2/floor_mha(K):.2f}x)  [{time.time()-t0:.0f}s]', flush=True)
    return e2


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else '5'
    res = {}
    for key in which.split(','):
        R, B, C = {'8': (8, 143, 44), '5': (5, 143, 75), '6': (6, 143, 64),
                   '53': (5, 143, 70), '4': (4, 143, 88)}[key]
        res[f'R{R}B{B}C{C}'] = 1e3 * run(R, B, C)
    print(json.dumps(res, indent=1))
