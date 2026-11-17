"""Fit DF-THC shapes on the exact error_2 objective, including the group structure.

error_2^2 = ||Y Y^T - H||_F^2 with Y[:,k] = weighted vech(X_k), X_k = sum_b w_kb u_b u_b^T.
Work in the top-r eigenspace of H (r = 800, tail floor 0.2 mHa) so one objective
evaluation is ~0.1 s; the final number is re-evaluated in the full 2926-dim space.
Protocol: spectral init -> alternate L-BFGS on w (fixed u) and on u (fixed w).
Calibration: the same protocol is run on the known-good (8,143,44).
"""
import os, sys, importlib.util, json, time, argparse
import numpy as np
from scipy.optimize import minimize

# Kernel path resolution: the competition package mounts under /kaggle/input.
COMP = 'google-verifiable-quantum-circuit-compilation'
_cands = [os.path.join(p, 'verifiers', 'dfthcsos') for p in
          ('/kaggle/input/competitions/' + COMP, '/kaggle/input/' + COMP,
           'data/competition')]
V = next(p for p in _cands if os.path.isdir(p))
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


# ---------------------------------------------------------------------------
# Driver: exact-objective shape fits on the B/C axis (Kaggle CPU only).
#
# rows = 76 + R*B and rows-76 = K*(B/C) exactly, so cutting the ANGLE row count
# at fixed K *is* cutting B/C.  Two protocols, both on the objective/gradients
# above (unchanged):
#   A  the historical spectral init (calibrates to 360 mHa on the shipped shape,
#      i.e. 25x off -> non-competitive, kept only as a reference)
#   B  warm start from the shipped (8,143,44) table, projected per group onto
#      the B best eigenvectors of sum_c X_rc X_rc, then the same L-BFGS rounds.
# Nothing is submitted; every number is classical algebra on the reference
# integrals, no circuit simulation.
# ---------------------------------------------------------------------------
import glob
import json
import os
import sys
import time
import traceback
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

WORK = Path('/kaggle/working')
T0 = time.time()
WALL = float(os.environ.get('WALL_HOURS', '3.4')) * 3600.0


def el():
    return time.time() - T0


def log(*a):
    print(f'[{el()/60:6.1f} min]', *a, flush=True)


sys.path.insert(0, str(Path(V).parent))
from dfthcsos.scoreinfra.costs_prepare import SpinFreeData_V1  # noqa: E402

SPECTRUM = ev                      # descending spectrum from the eigh above
NEG2 = float(np.sum(np.minimum(SPECTRUM, 0) ** 2))


def floorK(K):
    return 1e3 * float(np.sqrt(np.sum(np.maximum(SPECTRUM[K:], 0) ** 2) + NEG2))


def gate_c(rows, p_1220=13.8):
    p = p_1220 * np.sqrt(rows / 1220.0)
    return float(np.sqrt(max(0.0, 400.0 - p * p)))


def price(R, B, Cn, brot=8, J=5):
    m = SpinFreeData_V1(R=R, B=B, C=Cn, N=N, chi=10, beta=brot)
    oq, iq = m.outer_state_prep_qubit_cost(), m.inner_state_prep_qubit_cost()
    Q = J * brot + oq['persistent'] + iq['persistent'] + max(
        oq['temporary'], iq['temporary'], 77)
    Th = m.outer_state_prep() + m.inner_state_prep() + m.givens_rotations()
    return Th, Q, iq['temporary']


def loader(rows, model):
    import math
    if model == 'lin':
        return 4025.0 * rows / 1220.0
    hmax = math.ceil(rows / 16)
    top = hmax - 1
    high = top - len([h for h in range(1, top + 1) if h & (h - 1) == 0])
    if model == 'cons':
        return 15.0 * (6 + high + 193)
    cuts = min(5 * (105 - top), 525)
    return 15.0 * (6 + high + (525 - cuts) / 2)


def full_eval(x, R, B, Cn):
    nw = R * B * Cn
    Wf = x[:nw].reshape(R, B, Cn)
    Uf = x[nw:].reshape(R, B, N)
    Uf = Uf / np.linalg.norm(Uf, axis=1, keepdims=True)
    Y = np.zeros((NS, R * Cn))
    for r in range(R):
        Y[:, r * Cn:(r + 1) * Cn] = proj_of(Uf[r]) @ Wf[r]
    return 1e3 * float(np.linalg.norm(Y @ Y.T - H))


def alt_min(x, R, B, Cn, rounds, itw, itu, tag):
    nw = R * B * Cn
    for rd in range(rounds):
        t0 = time.time()
        m = np.zeros_like(x, bool)
        m[:nw] = True
        r1 = minimize(lambda z: fg(merge(z, x, m), R, B, Cn)[0], x[m],
                      jac=lambda z: fg(merge(z, x, m), R, B, Cn)[1][m],
                      method='L-BFGS-B',
                      options=dict(maxiter=itw, maxcor=20, ftol=1e-20, gtol=1e-16))
        x = merge(r1.x, x, m)
        m = ~m
        r2 = minimize(lambda z: fg(merge(z, x, m), R, B, Cn)[0], x[m],
                      jac=lambda z: fg(merge(z, x, m), R, B, Cn)[1][m],
                      method='L-BFGS-B',
                      options=dict(maxiter=itu, maxcor=20, ftol=1e-20, gtol=1e-16))
        x = merge(r2.x, x, m)
        f, _ = fg(x, R, B, Cn)
        log(f'    {tag} round {rd}: {1e3*np.sqrt(f):.3f} mHa '
            f'(w {r1.nit} u {r2.nit}) [{time.time()-t0:.0f}s]')
        if el() > WALL:
            log(f'    {tag}: wall reached inside the loop')
            break
    return x


def init_ship(Ut, Wt, R, B, Cn, seed=0):
    rng = np.random.default_rng(seed)
    U = np.zeros((R, B, N))
    W = np.zeros((R, B, Cn))
    for r in range(R):
        X = np.einsum('bp,bq,bc->cpq', Ut[r], Ut[r], Wt[r], optimize=True)
        agg = np.einsum('cpq,crq->pr', X, X, optimize=True)
        _, vec = np.linalg.eigh(agg)
        base = vec[:, ::-1].T[:min(B, N)].copy()
        if B > N:
            extra = rng.standard_normal((B - N, N))
            extra -= extra @ base.T @ base
            base = np.vstack([base, extra])
        U[r] = base / np.linalg.norm(base, axis=1, keepdims=True)
        Hh = np.einsum('bp,bq,cpq->bc', U[r], U[r], X, optimize=True)
        UtU = U[r] @ U[r].T
        W[r] = np.linalg.lstsq(UtU * UtU, Hh, rcond=1e-12)[0]
    return np.concatenate([W.ravel(), U.ravel()])


SHAPES = [(8, 143, 44), (8, 96, 44), (8, 76, 44), (8, 64, 44), (8, 64, 64),
          (8, 64, 80), (14, 32, 44), (6, 96, 59), (6, 64, 59), (4, 128, 88)]

hits = [p for p in glob.glob('/kaggle/input/**/submission.npz', recursive=True)
        if Path(p).parent.name != 'dfthcsos']
log(f'shipped table candidates: {hits}')
USH = WSH = None
if hits:
    z = np.load(sorted(hits)[0])
    USH, WSH = np.asarray(z['U'], float), np.asarray(z['W'], float)
    log(f'  using {sorted(hits)[0]} U {USH.shape} W {WSH.shape}')
    if USH.shape[0] != 8 or WSH.shape[2] != 44:
        USH = WSH = None

res = {}
for (R, B, Cn) in SHAPES:
    K = R * Cn
    rows = N + R * B
    Th, Q, itemp = price(R, B, Cn)
    rec = dict(R=R, B=B, C=Cn, K=K, rows=rows, floor=floorK(K),
               gate=gate_c(rows), T_h=Th, Q=Q, inner_temp=itemp, b_over_c=B / Cn,
               L={m: loader(rows, m) for m in ('lin', 'cons', 'cut')})
    res[f'{R},{B},{Cn}'] = rec
    log(f'== shape ({R},{B},{Cn}) rows {rows} K {K} B/C {B/Cn:.2f} '
        f'floor {rec["floor"]:.2f} gate {rec["gate"]:.2f} T_h {Th} Q {Q} '
        f'itemp {itemp} | L lin {rec["L"]["lin"]:.0f} cons {rec["L"]["cons"]:.0f} '
        f'cut {rec["L"]["cut"]:.0f}')
    if el() > WALL:
        log('wall reached before this shape; stopping')
        break

    try:
        t0 = time.time()
        eA = fit(R, B, Cn, rounds=2, itw=100, itu=50)
        rec['e2_A'], rec['rho_A'] = eA, eA / rec['floor']
        log(f'    A final: {eA:.3f} mHa ({eA/rec["floor"]:.2f}x floor) '
            f'[{time.time()-t0:.0f}s]')
    except Exception:
        log('protocol A failed:\n' + traceback.format_exc())

    if R == 8 and USH is not None:
        try:
            x = init_ship(USH, WSH, R, B, Cn)
            f0 = full_eval(x, R, B, Cn)
            log(f'    B init: {f0:.2f} mHa')
            x = alt_min(x, R, B, Cn, rounds=2, itw=100, itu=50, tag='B')
            f1 = full_eval(x, R, B, Cn)
            rec.update(e2_B=f1, e2_B_init=f0, rho_B=f1 / rec['floor'])
            log(f'    B final: {f1:.3f} mHa (floor {rec["floor"]:.2f}, '
                f'{f1/rec["floor"]:.2f}x) gate {rec["gate"]:.2f}')
            np.savez_compressed(WORK / f'fit_{R}_{B}_{Cn}.npz', x=x, R=R, B=B, C=Cn)
        except Exception:
            log('protocol B failed:\n' + traceback.format_exc())
    (WORK / 'shape_fits.json').write_text(json.dumps(res, indent=1, default=float))

(WORK / 'shape_fits.json').write_text(json.dumps(res, indent=1, default=float))
log('DONE')
print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != 'L'}
                  for k, v in res.items()}, indent=1, default=float))
