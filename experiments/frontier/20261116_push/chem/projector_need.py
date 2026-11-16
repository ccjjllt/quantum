"""Is the 143-projector group span saturated?  Prune-and-refit curve on the shipped table.

For each shipped group take its 143 shipped unit vectors u_b (which reproduce the
group's 44 matrices exactly), order them by total absolute weight, keep the top k,
refit the weights by least squares, and report the residual.  A residual that stays
tiny down to small k means the group has spare projector directions (so extra copies
are cheap); a residual that only reaches zero near k = 143 means the span is tight.
"""
import sys, importlib.util, numpy as np

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
PA = np.array(pairs); NS = len(pairs)
wgt = np.array([1.0 if p == q else 2.0 for p, q in pairs]); sqw = np.sqrt(wgt)
flat = np.array([p * N + q for p, q in pairs]); isdiag = np.array([p == q for p, q in pairs])
tei2 = tei.reshape(N * N, N * N)
G = np.empty((NS, NS))
for a, (p, q) in enumerate(pairs):
    G[a] = tei2[p * N + q, flat] + 0.5 * S[p, q] * isdiag + 0.5 * S.ravel()[flat] * (1.0 if p == q else 0.0)
G = 0.5 * (G + G.T)
H = sqw[:, None] * G * sqw[None, :]
del G, tei2
def vec_of(X):
    return X[PA[:, 0], PA[:, 1]] * sqw

z = np.load('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/marculera_ds/submission.npz')
U = z['U'].astype(np.float64); wr = z['W'].astype(np.float64)
R, B, _ = U.shape; C = wr.shape[2]
u = U / np.linalg.norm(U, axis=2, keepdims=True)
X = np.zeros((R, C, N, N))
for r in range(R):
    P = np.einsum('bp,bq->bpq', u[r], u[r])
    X[r] = np.einsum('bc,bpq->cpq', wr[r], P)
X = 0.5 * (X + np.swapaxes(X, -1, -2))
Ys = np.stack([vec_of(X[r, c]) for r in range(R) for c in range(C)], axis=1)
base = 1e3 * np.linalg.norm(Ys @ Ys.T - H)
print(f'shipped error_2 check: {base:.5f} mHa (verifier 19.99997)', flush=True)

print(f'{"group":>5} {"k=20":>9} {"k=40":>9} {"k=60":>9} {"k=80":>9} {"k=100":>9} {"k=120":>9} {"k=143":>9}   (residual mHa, weights refit)')
for r in range(R):
    mats = X[r]
    gn = np.sqrt(sum(np.sum(M * M) for M in mats))
    imp = np.abs(wr[r]).sum(axis=1)              # total absolute weight of projector b
    order = np.argsort(imp)[::-1]
    out = []
    for k in (20, 40, 60, 80, 100, 120, 143):
        Uu = u[r][order[:k]]
        UtU = Uu @ Uu.T
        Gg = UtU * UtU
        Hh = np.stack([np.sum((Uu @ M) * Uu, axis=1) for M in mats], axis=1)
        W = np.linalg.lstsq(Gg, Hh, rcond=1e-12)[0].T
        Xx = np.einsum('cb,bp,bq->cpq', W, Uu, Uu, optimize=True)
        Xx = 0.5 * (Xx + np.swapaxes(Xx, -1, -2))
        res = np.sqrt(sum(np.sum((Xx[c] - mats[c]) ** 2) for c in range(C)))
        out.append(1e3 * res)
    print(f'{r:5d} ' + ' '.join(f'{v:9.3f}' for v in out) +
          f'   |bundle| {1e3*gn:.0f} mHa', flush=True)
