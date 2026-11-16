"""Score the public merged factorizations in the exact error_2 geometry.

For each npz: continuous error_2 from (U,W) [the fit], and 8-bit error_2 from the
shipped angle_words (decoded on tree_edges), both as ||Y Y^T - H||, so the pair
gives the pipeline's realised rho = e2_fit / floor(K) at its own B/C.
"""
import sys, importlib.util, numpy as np
V = '/Users/zhaohuaxiang/ccjjllt/quantum/data/competition/verifiers/dfthcsos'
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m); return m
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

def y_of_X(X):
    return X[PA[:, 0], PA[:, 1]] * sqw

def e2_of_uw(U, w):
    R, B, _ = U.shape; C = w.shape[2]
    u = U / np.linalg.norm(U, axis=2, keepdims=True)
    Y = np.zeros((NS, R * C))
    for r in range(R):
        P = np.einsum('bp,bq->bpq', u[r], u[r], optimize=True)
        X = np.einsum('bc,bpq->cpq', w[r], P, optimize=True)
        X = 0.5 * (X + np.swapaxes(X, -1, -2))
        for c in range(C):
            Y[:, r * C + c] = y_of_X(X[c])
    f = 1e3 * np.linalg.norm(Y @ Y.T - H)
    return f, R * C

D = '/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/merge_pipe'
for f in ['B10c54.npz', 'M9x143x46_b8.npz', 'M8x156x60_b8.npz']:
    z = np.load(f'{D}/{f}', allow_pickle=False)
    U, w = z['U'].astype(float), z['W'].astype(float)
    e2, K = e2_of_uw(U, w)
    R, B, C = w.shape
    print(f'{f:18s} ({R},{B},{C}) K={K:4d} B/C={B/C:5.2f} rows={76+R*B:5d} '
          f'continuous e2 {e2:7.3f} mHa  floor {fl(K):6.3f}  rho {e2/fl(K):5.2f}', flush=True)
    if 'angle_words' in z.files:
        words = np.asarray(z['angle_words']); edges = np.asarray(z['tree_edges'])
        brot = int(z['brot']) if 'brot' in z.files else 8
        u_all = dfm.reconstruct_u_vectors(words / (1 << (brot - 1)), edges)
        m = dfm.evaluate_dfthc_angles if False else None
        # rebuild X from decoded vectors: rows 0..N-1 one-body, N.. two-body
        uu = u_all / np.linalg.norm(u_all, axis=1, keepdims=True)
        u_body = uu[N:].reshape(R, B, N)
        X = np.zeros((R, C, N, N))
        for r in range(R):
            P = np.einsum('bp,bq->bpq', u_body[r], u_body[r], optimize=True)
            X[r] = np.einsum('bc,bpq->cpq', w[r], P, optimize=True)
        X = 0.5 * (X + np.swapaxes(X, -1, -2))
        Y = np.stack([y_of_X(X[r, c]) for r in range(R) for c in range(C)], axis=1)
        print(f'{"":18s} 8-bit e2 {1e3*np.linalg.norm(Y @ Y.T - H):7.3f} mHa', flush=True)
