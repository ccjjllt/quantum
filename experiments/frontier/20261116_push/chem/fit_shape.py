"""Fit DF-THC shapes on the exact error_2 objective, including the group structure.

error_2^2 = ||Y Y^T - H||_F^2 with Y[:,k] = weighted vech(X_k), X_k = sum_b w_kb u_b u_b^T.
Work in the top-r eigenspace of H (r = 800, tail floor 0.2 mHa) so one objective
evaluation is ~0.1 s; the final number is re-evaluated in the full 2926-dim space.
Protocol: spectral init -> alternate L-BFGS on w (fixed u) and on u (fixed w).
Calibration: the same protocol is run on the known-good (8,143,44).
"""
import sys, importlib.util, json, time, argparse
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
PA = np.array(pairs); NS = len(pairs)
wgt = np.array([1.0 if p == q else 2.0 for p, q in pairs]); sqw = np.sqrt(wgt)
flat = np.array([p * N + q for p, q in pairs]); isdiag = np.array([p == q for p, q in pairs])
tei2 = tei.reshape(N * N, N * N)
Gm = np.empty((NS, NS))
for a, (p, q) in enumerate(pairs):
    Gm[a] = tei2[p * N + q, flat] + 0.5 * S[p, q] * isdiag + 0.5 * S.ravel()[flat] * (1.0 if p == q else 0.0)
Gm = 0.5 * (Gm + Gm.T)
del tei2
H = sqw[:, None] * Gm * sqw[None, :]
ev, evec = np.linalg.eigh(H)
ev, evec = ev[::-1].copy(), evec[:, ::-1].copy()
RANK = 800
Vr = evec[:, :RANK].copy()
lam = ev[:RANK].copy()
neg2_full = float(np.sum(np.minimum(ev, 0) ** 2))
def floor_mha(K):
    return 1e3 * np.sqrt((np.maximum(ev, 0) ** 2)[K:].sum() + neg2_full)
print('floors: ' + '  '.join(f'K={K}:{floor_mha(K):.2f}' for K in (235, 282, 352, 375, 384)), flush=True)


def proj_of(U):
    P = np.einsum('bp,bq->bpq', U, U, optimize=True)
    return (P[:, PA[:, 0], PA[:, 1]] * sqw[None, :]).T          # (NS,B)


def fg(x, R, B, Cn, Ucache=None):
    nw = R * B * Cn
    W = x[:nw].reshape(R, B, Cn)
    U = x[nw:].reshape(R, B, N)
    U = U / np.maximum(np.linalg.norm(U, axis=1, keepdims=True), 1e-12)
    Yp = np.zeros((RANK, R * Cn))
    Ps = []
    for r in range(R):
        P = proj_of(U[r]); Ps.append(P)
        Yp[:, r * Cn:(r + 1) * Cn] = (Vr.T @ P) @ W[r]
    S_ = Yp @ Yp.T - np.diag(lam)
    f = float(np.sum(S_ * S_))
    gYp = 4.0 * (S_ @ Yp)                                        # (RANK, R*Cn)
    gY = Vr @ gYp                                                # (NS, R*Cn)
    gw = np.zeros((R, B, Cn))
    gu = np.zeros((R, B, N))
    for r in range(R):
        gw[r] = Ps[r].T @ gY[:, r * Cn:(r + 1) * Cn]
    for r in range(R):
        Z = (gY[:, r * Cn:(r + 1) * Cn] @ W[r].T) * sqw[:, None]   # (NS,B) = d f / d(u_bp u_bq)
        A = np.zeros((B, N, N))
        A[:, PA[:, 0], PA[:, 1]] = Z.T
        A = np.triu(A) + np.swapaxes(np.triu(A, 1), -1, -2)
        gu[r] = np.einsum('bpq,bq->bp', A, U[r], optimize=True) + A[:, np.arange(N), np.arange(N)] * U[r]
    return f, np.concatenate([gw.ravel(), gu.ravel()])


def merge(z, x, mask):
    y = x.copy(); y[mask] = z; return y


def fit(R, B, Cn, seed=0, rounds=3, itw=80, itu=40, verbose=True):
    K = R * Cn
    t0 = time.time()
    rng = np.random.default_rng(seed)
    Ys = Vr[:, :K] * np.sqrt(np.maximum(lam[:K], 0))[None, :]
    Xs = np.zeros((K, N, N))
    for k in range(K):
        M = np.zeros((N, N)); M[PA[:, 0], PA[:, 1]] = Ys[:, k] / sqw
        Xs[k] = np.triu(M) + np.triu(M, 1).T
    lead = []
    for k in range(K):
        w2, v2 = np.linalg.eigh(Xs[k]); v = v2[:, -1]
        if v[int(np.argmax(np.abs(v)))] < 0: v = -v
        lead.append(v)
    lead = np.array(lead)
    cent = [lead[int(np.argmax(np.linalg.norm(lead, axis=1)))]]
    while len(cent) < R:
        d = np.min([np.sum((lead - c) ** 2, axis=1) for c in cent], axis=0)
        cent.append(lead[int(np.argmax(d))])
    cent = np.array(cent)
    for _ in range(30):
        d = np.stack([np.sum((lead - c) ** 2, axis=1) for c in cent], axis=1)
        lab = np.argmin(d, axis=1)
        for r in range(R):
            if np.any(lab == r): cent[r] = lead[lab == r].mean(axis=0)
    d = np.stack([np.sum((lead - c) ** 2, axis=1) for c in cent], axis=1)
    pref = np.argsort(d, axis=1); cnt = np.zeros(R, int); assign = -np.ones(K, int)
    for k in range(K):
        for r in pref[k]:
            if cnt[r] < Cn: assign[k] = r; cnt[r] += 1; break
    for k in np.flatnonzero(assign < 0):
        r = int(np.argmin(cnt)); assign[k] = r; cnt[r] += 1
    U = np.zeros((R, B, N)); W = np.zeros((R, B, Cn))
    for r in range(R):
        idx = np.flatnonzero(assign == r)
        agg = sum(Xs[k] @ Xs[k] for k in idx)
        _, V2 = np.linalg.eigh(agg)
        base = V2[:, ::-1].T[:min(B, N)].copy()
        if B > N:
            extra = rng.standard_normal((B - N, N))
            extra = extra - extra @ base.T @ base
            base = np.vstack([base, extra])
        U[r] = base / np.linalg.norm(base, axis=1, keepdims=True)
        Hh = np.stack([np.sum((U[r] @ Xs[k]) * U[r], axis=1) for k in idx], axis=1)
        UtU = U[r] @ U[r].T
        W[r] = np.linalg.lstsq(UtU * UtU, Hh, rcond=1e-12)[0]
    x = np.concatenate([W.ravel(), U.ravel()])
    f, _ = fg(x, R, B, Cn)
    print(f'  R={R} B={B} C={Cn} K={K}: spectral init {1e3*np.sqrt(f):.2f} mHa', flush=True)
    nw = R * B * Cn
    for rd in range(rounds):
        m = np.zeros_like(x, bool); m[:nw] = True
        r1 = minimize(lambda z: fg(merge(z, x, m), R, B, Cn)[0], x[m],
                      jac=lambda z: fg(merge(z, x, m), R, B, Cn)[1][m], method='L-BFGS-B',
                      options=dict(maxiter=itw, maxcor=20, ftol=1e-20, gtol=1e-16))
        x = merge(r1.x, x, m)
        m = ~m
        r2 = minimize(lambda z: fg(merge(z, x, m), R, B, Cn)[0], x[m],
                      jac=lambda z: fg(merge(z, x, m), R, B, Cn)[1][m], method='L-BFGS-B',
                      options=dict(maxiter=itu, maxcor=20, ftol=1e-20, gtol=1e-16))
        x = merge(r2.x, x, m)
        f, _ = fg(x, R, B, Cn)
        print(f'    round {rd}: {1e3*np.sqrt(f):.3f} mHa (w {r1.nit} it, u {r2.nit} it) [{time.time()-t0:.0f}s]', flush=True)
    # full-space evaluation
    Wf = x[:nw].reshape(R, B, Cn); Uf = x[nw:].reshape(R, B, N)
    Uf = Uf / np.linalg.norm(Uf, axis=1, keepdims=True)
    Y = np.zeros((NS, R * Cn))
    for r in range(R):
        P = proj_of(Uf[r])
        Y[:, r * Cn:(r + 1) * Cn] = P @ Wf[r]
    e2_full = 1e3 * np.linalg.norm(Y @ Y.T - H)
    print(f'  ==> R={R} B={B} C={Cn}: continuous error_2 {e2_full:.3f} mHa '
          f'(floor {floor_mha(K):.3f}, {e2_full/floor_mha(K):.2f}x)', flush=True)
    return e2_full


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('shapes', nargs='+')
    ap.add_argument('--rounds', type=int, default=3)
    a = ap.parse_args()
    out = {}
    for s in a.shapes:
        R, B, Cn = [int(t) for t in s.split(',')]
        out[s] = fit(R, B, Cn, rounds=a.rounds)
    print(json.dumps(out, indent=1))
