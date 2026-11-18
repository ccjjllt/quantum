"""Driver: C-axis sweep at FROZEN word-U (chemistry leg). Kaggle CPU kernel.

Per C it reports the continuous error_2 (exact full-space ||YY^T-H||_F) of the
best fit, the rank-K floor of H, the relaxed (block-free) span bound of the
frozen dictionary and the excess in quadrature, then the official verifier
metrics with W re-chosen on an Omega-target ray (E_gap scanned onto its floor,
error_1 checked), plus cost and GM for (8,143,C) with the unchanged loader.

Env: CS=44,43,... to shrink the sweep; ITERS/CGI/WALL for the budget.
"""
import base64
import io
import json
import math
import os
import sys
import time

import numpy as np

T0 = time.time()
WALL_TOTAL = float(os.environ.get('WALL_TOTAL', 5.0 * 3600))
OUT = os.environ.get('OUTDIR', '/kaggle/working')


def log(*a):
    print(f'[{time.time()-T0:7.1f}s]', *a, flush=True)


def payload():
    z = np.load(io.BytesIO(base64.b64decode(PAYLOAD_B64)))
    return {k: z[k] for k in z.files}


COMP = 'google-verifiable-quantum-circuit-compilation'
_cands = ([os.environ['DFTHC_DIR']] if os.environ.get('DFTHC_DIR') else []) + [os.path.join(p, 'verifiers', 'dfthcsos') for p in
          ('/kaggle/input/competitions/' + COMP, '/kaggle/input/' + COMP,
           '/kaggle/input/google-verifiable-quantum-circuit-compilation/verifiers/dfthcsos',
           'data/competition/verifiers/dfthcsos')]
V = next((p for p in _cands if os.path.isdir(p)), None)
if V is None:
    for root, dirs, files in os.walk('/kaggle/input'):
        if root.endswith('verifiers' + os.sep + 'dfthcsos'):
            V = root
            break
assert V is not None, 'competition dfthcsos not found'
log(f'competition dfthcsos at {V}')


def load(name, path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


refm = load('dfthcsos.scoreinfra.reference', f'{V}/scoreinfra/reference.py')
dfm = load('dfthcsos.scoreinfra.dfthc_math', f'{V}/scoreinfra/dfthc_math.py')
vmod = load('dfthcsos.verify', f'{V}/verify.py')

# ------------------------------------------------------------------ target H
ref = refm.load_reference(refm.check_fcidump())
N = int(np.asarray(ref['tei']).shape[0])
sh = refm.load_fixed_shifts()
Sshift = dfm.symmetric_from_lower(sh['Hsym_lower'], N).astype(np.float64)
beta1 = float(sh['H1_I']) - 0.5 * float(np.trace(Sshift))
eta = int(ref['electrons'])
ecore = float(ref['ecore'])
E_UP = refm.UPPER_ENERGY
tei = np.asarray(ref['tei'], dtype=np.float64)
pairs = [(p, q) for p in range(N) for q in range(p, N)]
PA = np.array(pairs)
sqw = np.sqrt(np.array([1.0 if p == q else 2.0 for p, q in pairs]))
flat = np.array([p * N + q for p, q in pairs])
isdiag = np.array([p == q for p, q in pairs])
tei2 = tei.reshape(N * N, N * N)
Gm = np.empty((len(pairs), len(pairs)))
for a, (p, q) in enumerate(pairs):
    Gm[a] = (tei2[p * N + q, flat] + 0.5 * Sshift[p, q] * isdiag
             + 0.5 * Sshift.ravel()[flat] * (1.0 if p == q else 0.0))
Gm = 0.5 * (Gm + Gm.T)
H = sqw[:, None] * Gm * sqw[None, :]
del tei2, Gm, tei
h1_thc = np.asarray(ref['oei'], float) - 0.5 * np.einsum('prrq->pq', ref['tei'])
A_h1 = h1_thc - 0.5 * eta * Sshift + beta1 * np.eye(N)
log(f'reference N={N} electrons={eta} beta1={beta1:.10f} ||H||_F {np.linalg.norm(H):.6f}')

# ------------------------------------------------------------------ payload
pl = payload()
words = pl['angle_words'].astype(np.int64)
tree = pl['tree_edges'].astype(np.int64)
w_ship = pl['w_ship'].astype(np.float64)
R, B, Cmax = w_ship.shape
full = dfm.reconstruct_u_vectors(words / (1 << 7), tree)
U = full[N:].reshape(R, B, N).copy()
Vrow = full[:N].copy()
W_ship = pl['wB_ship'].astype(np.float64) - w_ship.sum(axis=1)
_XU = U / np.linalg.norm(U, axis=2, keepdims=True)
X_ship = np.einsum('tjp,tjq,tjl->tlpq', _XU, _XU, w_ship, optimize=True)
m0 = dfm.evaluate_dfthc_angle_words(words, w_ship, W_ship, Sshift, beta1, ref,
                                   brot=8, tree_edges=tree, energy_upper=E_UP)
log('shipped: error_1 %.6f error_2 %.6f Lambda %.6f E_gap %.12f lambda_eff %.9f'
    % (1e3 * m0['error_1'], 1e3 * m0['error_2'], m0['Lambda'], m0['E_gap'], m0['lambda_eff']))
log(f'payload words {words.shape} decoded {full.shape} w {w_ship.shape}')

fu = WS.FixedU(U, H, PA, sqw)
ev = np.linalg.eigvalsh(H)[::-1]
neg2 = float(np.sum(np.minimum(ev, 0) ** 2))


def rank_floor(K):
    return 1e3 * float(np.sqrt(np.sum(np.maximum(ev[K:], 0) ** 2) + neg2))


P_all = np.concatenate(fu.Ps, axis=1)
G_all = P_all.T @ P_all
g_all, V_all = np.linalg.eigh(G_all)
g_all = np.maximum(g_all, 1e-14)
Wt_all = V_all / np.sqrt(g_all)
M_all = Wt_all.T @ (P_all.T @ (H @ P_all)) @ Wt_all
mu_all, UU_all = np.linalg.eigh(0.5 * (M_all + M_all.T))
CSUM = np.cumsum(np.maximum(mu_all, 0)[::-1] ** 2)


def span_bound(K):
    return 1e3 * float(np.sqrt(max(fu.Hfro2 - float(CSUM[K - 1]), 0.0)))


log('rank floors: ' + ' '.join(f'{K}:{rank_floor(K):.3f}' for K in (288, 304, 320, 336, 352)))
log('span bounds: ' + ' '.join(f'{K}:{span_bound(K):.3f}' for K in (288, 304, 320, 336, 352)))

# ------------------------------------------------------------------ W stage
rows_t, cols_t = np.tril_indices(N)
E_GAP_FLOOR = 3.914898


def X_of(w):
    u = U / np.linalg.norm(U, axis=2, keepdims=True)
    return np.einsum('tjp,tjq,tjl->tlpq', u, u, w, optimize=True)


def design(X):
    Rr, Cc = X.shape[:2]
    return np.stack([X[k // Cc, k % Cc][rows_t, cols_t] for k in range(Rr * Cc)])


def matched(X, Wm):
    from scipy.optimize import linear_sum_assignment
    h1p = A_h1 - np.einsum('rc,rcpq->pq', Wm, X, optimize=True)
    evs, Ue = np.linalg.eigh(h1p)
    qi, ei = linear_sum_assignment(-np.abs(Vrow @ Ue))
    lam = np.empty(N)
    lam[qi] = evs[ei]
    return lam, h1p, evs


def scores(X, w, Wm):
    lam, h1p, evs = matched(X, Wm)
    lam_h1 = float(np.abs(evs).sum())
    tr = float(np.trace(h1p))
    e_sos = ecore - eta * beta1 - (lam_h1 - tr) - 0.5 * float(np.sum(Wm ** 2))
    eg = E_UP - e_sos
    a = np.abs(w).sum(axis=1)
    wB = Wm + w.sum(axis=1)
    lam_h2 = float(0.25 * np.sum((a + np.abs(wB)) ** 2))
    Lam = lam_h1 + lam_h2
    e1 = float(dfm.h1_thc_reconstruction_error(Vrow, h1_thc, Sshift, beta1, eta, Wm, X))
    le = float(np.sqrt(eg * (2 * Lam - eg))) if 0 < eg < 2 * Lam else float('nan')
    return dict(eg=eg, lam_h1=lam_h1, lam_h2=lam_h2, Lambda=Lam, err1=e1, le=le)


def choose_W(X, w, nscan=601, lam_init=None):  # noqa: F811
    Bm = design(X)
    G = Bm @ Bm.T
    Gi = np.linalg.inv(G + 1e-13 * np.eye(G.shape[0]))
    lam_use = lam_init if lam_init is not None else matched(X_ship, W_ship)[0]
    best = None
    for rd in range(2):
        b0 = (A_h1 - (Vrow.T @ (lam_use[:, None] * Vrow)))[rows_t, cols_t]
        W0 = (Gi @ (Bm @ b0)).reshape(X.shape[0], X.shape[1])
        for s in np.linspace(0.90, 1.10, nscan):
            Wm = W0 * s
            sc = scores(X, w, Wm)
            if sc['err1'] <= 0.02 and sc['eg'] > E_GAP_FLOOR and sc['le'] == sc['le']:
                if best is None or sc['le'] < best[0]:
                    best = (sc['le'], s, sc.copy(), Wm.copy())
        if best is None:
            log(f'   choose_W rd{rd}: no feasible W on the ray (|W0| {np.linalg.norm(W0):.3f})')
            break
        lam_use = matched(X, best[3])[0]
    return best


def th(C):
    return int(vmod.heuristic_costs(N, R, B, C, 8)['toffoli'])


REF = {'invsqrt': 2076774.233715, 'dqi': 24439463583672.93, 'chem': 3355599588.3155375}
CUR = {'invsqrt': 74797.36535717871, 'dqi': 346409762292.7187, 'chem': 294643137.73}
SHIPPED_GM = math.prod([REF['invsqrt'] / CUR['invsqrt'], REF['dqi'] / CUR['dqi'],
                        REF['chem'] / CUR['chem']]) ** (1 / 3)


def gm(cost):
    return math.prod([REF['invsqrt'] / CUR['invsqrt'], REF['dqi'] / CUR['dqi'],
                      REF['chem'] / cost]) ** (1 / 3)


# ------------------------------------------------------------------ inits
def collective_truncate(y, C):
    st = np.concatenate(y, axis=0)
    Uu, ss, Vt = np.linalg.svd(st, full_matrices=False)
    O = Vt.T
    return [(a @ O)[:, :C].copy() for a in y]


def relax_init(C):
    order = np.argsort(mu_all)[::-1][:R * C]
    Yh = UU_all[:, order] * np.sqrt(np.maximum(mu_all[order], 0.0))
    out = []
    for r in range(R):
        blk = Yh[r * B:(r + 1) * B, :]
        u, s, vt = np.linalg.svd(blk, full_matrices=False)
        out.append(u[:, :C] * s[:C])
    return out


def diag_init(C):
    out = []
    for r in range(R):
        lam, Vv = np.linalg.eigh(fu.Hd[r])
        order = np.argsort(lam)[::-1][:C]
        out.append(Vv[:, order] * np.sqrt(np.maximum(lam[order], 0.0)))
    return out


ITERS = int(os.environ.get('ITERS', 22))
CGI = int(os.environ.get('CGI', 150))
PIT = int(os.environ.get('PIT', 18))
PCG = int(os.environ.get('PCG', 170))
WALL = float(os.environ.get('WALL', 480))


def solve_to(C, y0, iters, cgi, tag, wall=None):
    y, _ = fu.solve([a.copy() for a in y0], iters=iters, cg_iters=cgi, tag=tag,
                    verbose=False, wall=(wall or WALL), exact_every=0)
    return y


# ------------------------------------------------------------------ sweep
CS = [int(x) for x in os.environ.get('CS', '44,43,42,41,40,39,38').split(',')]
y44 = pl['y44'].astype(np.float64)
log('C=44 init e2 %.4f mHa' % fu.e2_mha([a.copy() for a in y44]))
best = {max(CS): [a.copy() for a in y44]}
out = {}
for C in CS:
    if time.time() - T0 > WALL_TOTAL:
        log(f'skipping C={C}: total wall reached')
        continue
    yA = best.get(C)
    if yA is None:
        prev = max(k for k in best if k > C) if any(k > C for k in best) else None
        if prev is not None and best[prev][0].shape[1] != C:
            y0 = collective_truncate(best[prev], C)
        else:
            yA0 = best.get(prev) if prev is not None else None
            y0 = (collective_truncate(yA0, C) if yA0 is not None else relax_init(C))
        yA = solve_to(C, y0, ITERS, CGI, f'lin{C}')
    cands = [('lin', yA)]
    if C < Cmax and C not in best:
        cands.append(('relax', solve_to(C, relax_init(C), max(ITERS - 6, 8), CGI, f'rel{C}')))
        cands.append(('diag', solve_to(C, diag_init(C), max(ITERS - 8, 8), CGI, f'dia{C}')))
    cands.sort(key=lambda kv: fu.e2_mha(kv[1]))
    log(f'  C={C} cands: ' + '  '.join(f'{t}={fu.e2_mha(y):.4f}' for t, y in cands))
    tt, ybest = cands[0]
    ybest = solve_to(C, ybest, PIT, PCG, f'pol{C}')
    e = fu.e2_mha(ybest)
    best[C] = ybest
    w = fu.w_from_y(ybest)
    moff = dfm.evaluate_dfthc_vectors(full, w, np.zeros((R, C)), Sshift, beta1, ref,
                                      energy_upper=E_UP)
    K = R * C
    a1 = np.abs(w).sum(axis=1)
    s1 = w.sum(axis=1)
    row = dict(C=C, K=K, e2=e, e2_official=1e3 * moff['error_2'],
               rank_floor=rank_floor(K), span_bound=span_bound(K),
               excess=float(np.sqrt(max(e ** 2 - span_bound(K) ** 2, 0.0))),
               l1=float(np.abs(w).sum()), sum_a2=float(np.sum(a1 ** 2)),
               sum_s2=float(np.sum(s1 ** 2)), max_abs=float(np.abs(w).max()),
               T=2 * 4022 + th(C), Q=427, init=tt)
    bw = choose_W(X_of(w), w)
    if bw is not None:
        le, s, sc, Wm = bw
        row.update(err1_mHa=1e3 * sc['err1'], E_gap=sc['eg'], Lambda=sc['Lambda'],
                   lam_h2=sc['lam_h2'], lambda_eff=le, sumW2=float(np.sum(Wm ** 2)),
                   Wscale=s)
        row['cost'] = le * row['T'] * row['Q']
        row['gm'] = gm(row['cost'])
    log('== C=%d e2 %.4f (official %.4f) floor %.4f span %.4f excess %.4f | L1 %.2f '
        'sum_a2 %.2f | T %d | %s'
        % (C, e, row['e2_official'], row['rank_floor'], row['span_bound'], row['excess'],
           row['l1'], row['sum_a2'], row['T'],
           ('err1 %.3f E_gap %.9f lambda_eff %.6f cost %.1f GM %.5f'
            % (row['err1_mHa'], row['E_gap'], row['lambda_eff'], row['cost'], row['gm']))
           if 'gm' in row else 'no feasible W'))
    out[str(C)] = row
    np.savez_compressed(os.path.join(OUT, f'y_C{C}.npz'), y=np.stack(ybest).astype(np.float32), C=C)
    np.savez_compressed(os.path.join(OUT, f'w_C{C}.npz'), w=w.astype(np.float32), C=C)
    with open(os.path.join(OUT, 'result.json'), 'w') as f:
        json.dump(out, f, indent=1)
log('SHIPPED GM reference %.6f' % SHIPPED_GM)
log('done')
