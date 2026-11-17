"""Expressiveness gate for DF-THC shapes: exact rank-K floor of error_2.

The verifier's error_2 is
    || sum_{rho,c} X^{rc} (x) X^{rc}  -  tei  -  shifts ||_F ,  X symmetric,
with X^{rc} = sum_b w^{rc}_b u^rho_b u^rho_b^T.  With y = sqrt(weight) * vech(X)
(the Frobenius inner product becomes Euclidean on the 2926 pairs p<=q) this is
    || sum_k y_k y_k^T - H ||_F ,  H = W^1/2 M W^1/2  (2926 x 2926),
so the best possible continuous error_2 for K = R*C terms is the tail of H's
spectrum (negative eigenvalues cannot be represented by y y^T and stay).
This gives a hard floor per K, independent of the optimiser and of the loader.
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
print('N', N, 'fixed S from the packaged baseline shifts')

pairs = [(p, q) for p in range(N) for q in range(p, N)]
NS = len(pairs)
w = np.array([1.0 if p == q else 2.0 for p, q in pairs])
flat = np.array([p * N + q for p, q in pairs])
isdiag = np.array([p == q for p, q in pairs])

G = np.empty((NS, NS))
tei2 = tei.reshape(N * N, N * N)
Sf = S.ravel()
for a, (p, q) in enumerate(pairs):
    row = tei2[p * N + q, flat] + 0.5 * S[p, q] * isdiag + 0.5 * Sf[flat] * (1.0 if p == q else 0.0)
    G[a] = row
G = 0.5 * (G + G.T)
H = np.sqrt(w)[:, None] * G * np.sqrt(w)[None, :]
print('H built', H.shape, 'sym err', np.abs(H - H.T).max())

ev = np.linalg.eigvalsh(H)
ev = ev[::-1]
print('top 6 eigenvalues', np.round(ev[:6], 6))
print('smallest 6 eigenvalues', np.round(ev[-6:], 8))
print('negative mass (sum of squares of negative eigenvalues) %.6e' % np.sum(np.minimum(ev, 0) ** 2))

neg2 = float(np.sum(np.minimum(ev, 0) ** 2))
tail = np.concatenate([np.cumsum((np.maximum(ev, 0) ** 2)[::-1])[::-1][1:], [0.0]])
# tail[k] = sum_{i>k} max(ev_i,0)^2  with k = number of kept terms
def floor_mha(K):
    keep = np.maximum(ev, 0) ** 2
    return 1e3 * np.sqrt(keep[K:].sum() + neg2)

print()
print(' K     floor(error_2) mHa   (K = R*C)')
for K in (200, 300, 320, 328, 336, 340, 344, 348, 352, 356, 360, 375, 384, 400, 450):
    print(f'{K:4d}   {floor_mha(K):9.3f}')
print()
for K in (352, 375, 384):
    import math
    f = floor_mha(K)
    print(f'K={K}: floor {f:.3f} mHa -> quantized upper estimate sqrt(f^2+13.7^2) = '
          f'{math.hypot(f,13.7):.2f} mHa, sqrt(f^2+11^2) = {math.hypot(f,11.0):.2f} mHa')

# ---- calibration: the shipped (8,143,44) table, evaluated in the same space
z = np.load('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/marculera_ds/submission.npz')
U = z['U'].astype(np.float64)                     # (R,B,N)
w_rc = z['W'].astype(np.float64)                  # (R,B,C)
R, B, _ = U.shape
C = w_rc.shape[2]
u = U / np.linalg.norm(U, axis=2, keepdims=True)
X = np.einsum('rb,rbp,rbq->rcpq', w_rc.transpose(0, 2, 1), u, u, optimize=True) if False else None
X = np.zeros((R, C, N, N))
for rho in range(R):
    P = np.einsum('bp,bq->bpq', u[rho], u[rho])      # (B,N,N)
    X[rho] = np.einsum('bc,bpq->cpq', w_rc[rho], P)
X = np.tril(X) + np.swapaxes(np.tril(X, -1), -1, -2)
flatX = X.reshape(R * C, N * N)[:, flat]
flatX = 0.5 * (flatX + X.reshape(R * C, N * N)[:, [q * N + p for p, q in pairs]])  # symmetric already
Y = (np.sqrt(w)[None, :] * X.reshape(R * C, N * N)[:, flat]).T        # (2926, K)
K = Y.shape[1]
res = Y @ Y.T - H
print()
print(f'shipped table R={R} B={B} C={C} K={K}: realised error_2 = {1e3*np.linalg.norm(res):.5f} mHa '
      f'(verifier reported 19.99997)  floor {floor_mha(K):.3f} -> fit is '
      f'{np.linalg.norm(res)/floor_mha(K)*1e3:.2f}x the floor')
np.save('H_spectrum.npy', ev)
