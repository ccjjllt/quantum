"""Joint (U,w) C-truncation of the public R=4/B=255/C=120 table, on Kaggle-mounted data.

Stage 1  fixed-atom exact rank-C PSD block-coordinate descent (w-only optimum).
Stage 2  joint L-BFGS on (U, w) minimising the verifier's error_2 directly.
Stage 3  10-bit Givens re-encoding of the optimised U + another w-only polish, then
         the official `evaluate_dfthc_angle_words` metrics and `heuristic_costs`.

Inputs (mounted):
  * competition data      /kaggle/input/.../google-verifiable-quantum-circuit-compilation
  * public factorisation  .../vqcc-apache-public-circuits/factorizations/729cd14c088f.npz
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
from scipy.linalg import eigh
from scipy.optimize import minimize

IN = Path('/kaggle/input')
OUT = Path(os.environ['DFTHC_OUT']) if os.environ.get('DFTHC_OUT') else Path('/kaggle/working')
OUT.mkdir(parents=True, exist_ok=True)


def find_competition() -> Path:
    for p in (IN / 'google-verifiable-quantum-circuit-compilation',
              IN / 'competitions' / 'google-verifiable-quantum-circuit-compilation'):
        if (p / 'verifiers' / 'dfthcsos').is_dir():
            return p
    raise SystemExit(f'competition data not found under {IN}')


def find_seed() -> Path:
    hits = list(IN.glob('**/factorizations/729cd14c088f.npz'))
    if hits:
        return hits[0]
    raise SystemExit(f'public factorisation not found under {IN}')


DATA = Path(os.environ['DFTHC_DATA']) if os.environ.get('DFTHC_DATA') else find_competition()
SEED = Path(os.environ['DFTHC_SEED']) if os.environ.get('DFTHC_SEED') else find_seed()
sys.path.insert(0, str(DATA / 'verifiers'))
if sys.platform.startswith('linux'):
    sys.path.insert(0, str(DATA / 'kickmix'))
print('competition:', DATA, flush=True)
print('seed:       ', SEED, flush=True)

from dfthcsos.scoreinfra.dfthc_math import (  # noqa: E402
    evaluate_dfthc_angle_words, reconstruct_u_vectors, symmetric_from_lower,
)
from dfthcsos.scoreinfra.reference import (  # noqa: E402
    UPPER_ENERGY, check_fcidump, load_fixed_shifts, load_reference,
)
from dfthcsos.verify import heuristic_costs  # noqa: E402

N = 76
CS = [int(x) for x in os.environ.get('DFTHC_CS', '110,105').split(',')]
MAXIT = int(os.environ.get('DFTHC_MAXIT', '1500'))

z = np.load(SEED)
U0 = z['U'].astype(np.float64)
w0 = z['W'].astype(np.float64)
R, B, C0 = w0.shape
brot = int(z['brot'])
I, J = np.tril_indices(N)
PQ = len(I)
DIAG = I == J
WTS = np.where(DIAG, 1.0, np.sqrt(2.0))

S = np.asarray(symmetric_from_lower(load_fixed_shifts()['Hsym_lower'], N), np.float64)
ref = load_reference(check_fcidump())
tei = np.asarray(ref['tei'], np.float64)

T = np.empty((PQ, PQ), np.float64)
for a in range(0, PQ, 256):
    b = min(a + 256, PQ)
    T[a:b] = tei[I[a:b, None], J[a:b, None], I[None, :], J[None, :]]
T *= WTS[:, None] * WTS[None, :]
Ssym = S[I, J]
T += 0.5 * (WTS[:, None] * WTS[None, :]) * (DIAG[None, :] * Ssym[:, None] + DIAG[:, None] * Ssym[None, :])
del tei
print('T fro', np.linalg.norm(T), flush=True)

A0 = (np.einsum('rbp,rbq->rbpq', U0, U0)[:, :, I, J]) * WTS
Q = [np.linalg.qr(A0[r].T)[0].T.copy() for r in range(R)]


# --------------------------------------------------------------------------
# stage 1: exact rank-C PSD block coordinate descent, atoms fixed
# --------------------------------------------------------------------------
def gram(X):
    if np.ndim(X) == 2:
        return np.einsum('cp,cq->pq', X, X, optimize=True)
    return np.einsum('rcp,rcq->pq', X, X, optimize=True)


def als_fixed(U, w_init, Cnew, sweeps=30):
    A = (np.einsum('rbp,rbq->rbpq', U, U)[:, :, I, J]) * WTS
    X = np.einsum('rbc,rbp->rcp', w_init[:, :, :Cnew], A, optimize=True).copy()
    M = gram(X)
    for it in range(sweeps):
        for r in range(R):
            D = T - M + gram(X[r])
            QD = Q[r] @ D
            G = 0.5 * ((QD @ Q[r].T) + (QD @ Q[r].T).T)
            ev, V = np.linalg.eigh(G)
            idx = np.argsort(ev)[::-1][:Cnew]
            lam = np.maximum(ev[idx], 0.0)
            X[r] = (V[:, idx] * np.sqrt(lam)[None, :]).T @ Q[r]
            M = T - D + gram(X[r])
        if abs(float(np.linalg.norm(M - T)) - float(np.linalg.norm(D - T))) < 1e-14:
            break
    W = np.stack([np.linalg.lstsq(A[r].T, X[r].T, rcond=1e-12)[0] for r in range(R)], axis=0)
    return W


# --------------------------------------------------------------------------
# stage 2: joint L-BFGS on (U, w)
# --------------------------------------------------------------------------
def make_fg(Cnew):
    nu = R * B * N

    def unpack(theta):
        return theta[:nu].reshape(R, B, N), theta[nu:].reshape(R, B, Cnew)

    def fg(theta):
        U, W = unpack(theta)
        un = np.linalg.norm(U, axis=2, keepdims=True)
        u = U / un
        A = np.einsum('rbp,rbq->rbpq', u, u)[:, :, I, J] * WTS
        X = np.einsum('rbc,rbp->rcp', W, A, optimize=True)
        M = np.einsum('rcp,rcq->pq', X, X, optimize=True)
        E = M - T
        f = float(np.sum(E * E))
        EX = np.einsum('pq,rcq->rcp', E, X, optimize=True)
        gW = 4.0 * np.einsum('rbp,rcp->rbc', A, EX, optimize=True)
        WEX = np.einsum('rbc,rcp->rbp', W, EX, optimize=True)
        full = np.zeros((R, B, N, N))
        full[:, :, I, J] = 4.0 * WEX * WTS
        full = full + np.swapaxes(full, -1, -2)     # diagonal counted twice, as required
        hu = np.einsum('rbpq,rbq->rbp', full, u, optimize=True)
        gU = (hu - np.sum(hu * u, axis=2, keepdims=True) * u) / un
        return f, np.concatenate([gU.ravel(), gW.ravel()])

    return unpack, fg


def joint(Cnew, Winit, maxit):
    unpack, fg = make_fg(Cnew)
    theta = np.concatenate([U0.ravel(), Winit.ravel()])
    hist = []

    def cb(xk):
        hist.append(float(np.sqrt(fg(xk)[0])))

    res = minimize(fg, theta, jac=True, method='L-BFGS-B', callback=cb,
                   options={'maxiter': maxit, 'maxfun': 4 * maxit, 'maxls': 40,
                            'ftol': 1e-16, 'gtol': 1e-14, 'maxcor': 20})
    U, W = unpack(res.x)
    return U, W, float(np.sqrt(res.fun)), hist


# --------------------------------------------------------------------------
# stage 3: words
# --------------------------------------------------------------------------
def log_depth_tree(n: int = N) -> np.ndarray:
    edges, level, depth = [], [0], 0
    while len(edges) < n - 1:
        nxt = []
        for label in level:
            nxt.append(label)
            right = label + (1 << depth)
            if right < n:
                edges.append((label, right))
                nxt.append(right)
        level, depth = nxt, depth + 1
    return np.asarray(edges, dtype=np.int64)


def tree_angles(vectors: np.ndarray, edges: np.ndarray) -> np.ndarray:
    u = np.array(vectors, dtype=np.float64, ndmin=2)
    u = u / np.linalg.norm(u, axis=1, keepdims=True)
    theta = np.zeros((len(u), len(edges)))
    for t in range(len(edges) - 1, -1, -1):
        p, q = edges[t]
        theta[:, t] = np.arctan2(u[:, q], u[:, p])
        u[:, p] = np.hypot(u[:, p], u[:, q])
        u[:, q] = 0.0
    return np.mod(theta / np.pi, 2.0)


def to_words(vectors, edges, brot=10):
    scaled = tree_angles(vectors, edges) * (1 << (brot - 1))
    return np.floor(scaled + 0.5).astype(np.int64) % (1 << brot)


def metrics(words, ww, edges):
    m = evaluate_dfthc_angle_words(
        words, ww, np.zeros(ww.shape[0:1] + ww.shape[2:]), S, beta1, ref,
        brot=10, tree_edges=edges, energy_upper=UPPER_ENERGY,
    )
    return {k: (float(v) if not isinstance(v, bool) else bool(v)) for k, v in m.items()}


_fixed = load_fixed_shifts()
beta1 = float(_fixed['H1_I']) - 0.5 * float(np.trace(S))
print('beta_1', beta1, flush=True)
edges_npz = np.asarray(z['tree_edges'], np.int64)
edges_log = log_depth_tree()
words_seed = np.asarray(z['angle_words'], np.int64)

# sanity: the npz tree reproduces the npz U exactly
u_dec = reconstruct_u_vectors(words_seed / (1 << (brot - 1)), edges_npz)
print('npz tree decodes to U:', float(np.abs(u_dec[N:] - U0.reshape(-1, N)).max()), flush=True)
print('log tree words == npz words:', bool(np.array_equal(to_words(U0.reshape(-1, N), edges_log), words_seed[N:])), flush=True)
print('log tree decodes to U:', float(np.abs(reconstruct_u_vectors(
    to_words(U0.reshape(-1, N), edges_log) / (1 << (brot - 1)), edges_log)[N:] - U0.reshape(-1, N)).max()), flush=True)


def full_table(U, ww, edges):
    """(N+R*B, N-1) word table: one-body rows from the seed, two-body rows re-encoded."""
    words = words_seed.copy()
    words[N:] = to_words(U.reshape(-1, N), edges)
    u_dec = reconstruct_u_vectors(words / (1 << (brot - 1)), edges)
    return words, u_dec[N:].reshape(R, B, N)


results = {}
for Cnew in CS:
    m0 = metrics(words_seed, w0[:, :, :Cnew], edges_npz)
    print(f'C={Cnew} raw-truncate e2 {1e3*m0["error_2"]:.4f} mHa', flush=True)
    W1 = als_fixed(U0, w0, Cnew)
    _, u_dec0 = full_table(U0, W1, edges_npz)
    W1 = als_fixed(u_dec0, W1, Cnew)          # re-ALS on the exactly-decoded atoms
    m1 = metrics(words_seed, W1, edges_npz)
    print(f'C={Cnew} w-only ALS e2 {1e3*m1["error_2"]:.4f} mHa', flush=True)

    U2, W2, e2c, hist = joint(Cnew, W1, MAXIT)
    print(f'C={Cnew} joint continuous e2 {1e3*e2c:.4f} mHa after {len(hist)} iters', flush=True)

    best = {'C': Cnew, 'w_only_mHa': 1e3 * m1['error_2'], 'joint_cont_mHa': 1e3 * e2c}
    for tag, edges in (('npz', edges_npz), ('log', edges_log)):
        words, u_enc = full_table(U2, W2, edges)
        W3 = als_fixed(u_enc, W2, Cnew, sweeps=40)
        mm = metrics(words, W3, edges)
        u_enc2 = reconstruct_u_vectors(words / (1 << (brot - 1)), edges)[N:].reshape(R, B, N)
        W4 = als_fixed(u_enc2, W3, Cnew, sweeps=40)
        mm2 = metrics(words, W4, edges)
        print(f'C={Cnew} [{tag} tree] encoded e2 {1e3*mm["error_2"]:.4f} mHa, '
              f'polished {1e3*mm2["error_2"]:.4f} mHa', flush=True)
        best[f'encoded_{tag}_mHa'] = 1e3 * mm['error_2']
        best[f'polished_{tag}_mHa'] = 1e3 * mm2['error_2']
        best[f'metrics_{tag}'] = mm2
        if tag == 'npz' and mm2['error_2'] < 0.02:
            np.savez(OUT / f'ctrunc_joint_C{Cnew}.npz', U=u_enc2.reshape(N + R * B, N)[N:],
                     W=W4, H2_I=np.asarray(z['H2_I'])[:, :Cnew].copy(),
                     H1_I=np.asarray(z['H1_I']), Hsym_lower=np.asarray(z['Hsym_lower']),
                     angle_words=words, tree_edges=edges, brot=brot)
    hc = heuristic_costs(N, R, B, Cnew, 10)
    best['heuristic'] = {k: int(v) for k, v in hc.items()}
    for tag, per_pass in (('loader_10bit_infeasible', 2635), ('loader_11bit', 4090)):
        Tt = hc['toffoli'] + 2 * per_pass
        Qh = hc['qubits']
        Q = 429
        lam = 46.907378146123214
        best[f'cost_{tag}'] = {'T_total': int(Tt), 'Q_total': Q, 'lambda_eff_assumed': lam,
                               'cost': lam * Tt * Q}
    results[Cnew] = best
    print(f'C={Cnew} heuristic', json.dumps(best['heuristic']), flush=True)

summary = {'threshold_mHa': 20.0, 'control_mHa': 19.937517696504052, 'results': results}
(OUT / 'ctrunc_joint.json').write_text(json.dumps(summary, indent=2))
print('SUMMARY', json.dumps(summary), flush=True)
print('DONE', flush=True)
