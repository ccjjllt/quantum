"""Lambda / lambda_eff minimisation over the 352 offsets W at (8,143,44,brot=8).

Key structural facts (all from the official formulas):
  lam_h2 = 0.25 sum_rc (a_rc + |W_rc|)^2        -> depends on |W| only
  E_SOS  has -0.5 sum W^2                        -> depends on |W| only
  H1_prime = h1_thc - (eta/2) S + beta1 I - sum_rc W_rc X_rc   -> signed!
  E_gap   = const + (lam_h1 - tr h1) + 0.5 sum W^2      (only equality constraint)

So: step 1 pick the |W| profile (concentrate the norm on the smallest-a cells),
step 2 choose the 352 SIGNS to keep E_gap >= floor with as little lam_h1 as
possible, step 3 check that the 76 one-body rows re-encode at 8 bits to <= 20 mHa.
Nothing else changes: w and U are untouched, so error_2 is bit-identical.

Kaggle CPU only; classical numpy; nothing submitted.
"""
import glob
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

WORK = Path('/kaggle/working')
T0 = time.time()


def log(*a):
    print(f'[{time.time()-T0:7.1f}s]', *a, flush=True)


COMP = 'google-verifiable-quantum-circuit-compilation'
DATA = next(p for p in (Path('/kaggle/input/competitions') / COMP, Path('/kaggle/input') / COMP)
            if (p / 'verifiers').is_dir())
for p in (DATA / 'kickmix', DATA / 'verifiers'):
    if p.is_dir():
        sys.path.insert(0, str(p))

from dfthcsos.scoreinfra import reference as refm          # noqa: E402
from dfthcsos.scoreinfra import dfthc_math as dfm         # noqa: E402

ref = refm.load_reference(refm.check_fcidump())
tei = np.asarray(ref['tei'], dtype=np.float64)
oei = np.asarray(ref['oei'], dtype=np.float64)
N = tei.shape[0]
shifts = refm.load_fixed_shifts()
S = dfm.symmetric_from_lower(shifts['Hsym_lower'], N).astype(np.float64)
BETA1 = float(shifts['H1_I']) - 0.5 * float(np.trace(S))
ETA = int(ref['electrons'])
ECORE = float(ref['ecore'])
EUPPER = -22140.27335
FLOOR = 3.914898
LAM0 = 46.921716818
COST0 = 294.64313773
GM0 = 28.15083
log(f'N {N} eta {ETA} ecore {ECORE:.6f} beta1 {BETA1:.6f} H1_I {float(shifts["H1_I"]):.6f}')

hits = [p for p in glob.glob('/kaggle/input/**/submission.npz', recursive=True)
        if Path(p).parent.name != 'dfthcsos']
SHIP = sorted(hits)[0]
z = np.load(SHIP)
U0 = np.asarray(z['U'], dtype=np.float64)
w0 = np.asarray(z['W'], dtype=np.float64)
W0 = np.asarray(z['H2_I'], dtype=np.float64)
AW = np.asarray(z['angle_words'], dtype=np.int64)
TREE = np.asarray(z['tree_edges'], dtype=np.int64)
R, B, N2 = U0.shape
C = w0.shape[2]
brot = 8
log(f'shipped {SHIP}  U {U0.shape} w {w0.shape} W {W0.shape} words {AW.shape}')

h1_thc = oei - 0.5 * np.einsum('prrq->pq', tei, optimize=True)
CONST_M = h1_thc - 0.5 * ETA * S + BETA1 * np.eye(N)
u_all = dfm.reconstruct_u_vectors(AW / (1 << (brot - 1)), TREE)
V1 = u_all[:N].copy()

X0 = np.einsum('gbp,gbq,gbc->gcpq', U0, U0, w0, optimize=True)
assert X0.shape == (R, C, N, N), X0.shape
a = np.abs(w0).sum(axis=1)
S0 = float(np.sum(W0 ** 2))
A2 = float(np.sum(a ** 2))


def h1p(W):
    return CONST_M - np.einsum('rc,rcpq->pq', W, X0, optimize=True)


def stats(W):
    M = h1p(W)
    e = np.linalg.eigvalsh(M)
    lam_h1 = float(np.abs(e).sum())
    trM = float(np.trace(M))
    lam_h2 = 0.25 * float(np.sum((a + np.abs(W)) ** 2))
    eg = EUPPER - (ECORE - ETA * BETA1 - (lam_h1 - trM) - 0.5 * float(np.sum(W ** 2)))
    L = lam_h1 + lam_h2
    le = math.sqrt(eg * (2 * L - eg)) if eg > 0 else float('inf')
    return dict(lam_h1=lam_h1, lam_h2=lam_h2, trM=trM, E_gap=eg, Lambda=L,
                lam_eff=le, sumW2=float(np.sum(W ** 2)),
                sum_absW=float(np.abs(W).sum()), cross=float((a * np.abs(W)).sum()),
                nnz=int(np.count_nonzero(W)))


def e1_of(W, V):
    M = h1p(W)
    e, Vc = np.linalg.eigh(M)
    from scipy.optimize import linear_sum_assignment
    qi, ii = linear_sum_assignment(-np.abs(V @ Vc))
    m = np.empty_like(e)
    m[qi] = e[ii]
    return 1e3 * float(np.linalg.norm(np.einsum('j,jp,jq->pq', m, V, V, optimize=True) - M))


st0 = stats(W0)
st0['e1'] = e1_of(W0, V1)
log('== shipped ==')
for k, v in st0.items():
    log(f'   {k:10s} {v:.9g}' if isinstance(v, float) else f'   {k:10s} {v}')
log(f'   ratio lam_h2/(0.25||H||_F): see RESULT2 (88.7)')

G0 = (st0['lam_h1'] - st0['trM']) + 0.5 * S0
log(f'   g_now = (lam_h1 - tr h1) + 0.5 sumW2 = {G0:.9f}')
RES = dict(ship=st0, g_now=G0, a_min=float(a.min()), S0=S0, A2=A2)


def objective(W):
    """lam_eff with a hard penalty on E_gap < floor and on lam_h1 growth."""
    s = stats(W)
    pen = 1e4 * max(0.0, FLOOR + 1e-9 - s['E_gap']) ** 2
    return s['lam_eff'] + pen, s


order = np.argsort(a.ravel())
log('== step 1+2: |W| profile (k smallest-a cells) x sign search ==')
table = []
for k in (1, 2, 4, 8, 16, 32, 44, 88, 176):
    idx = order[:k]
    for mult in (1.0, 1.05, 1.15, 1.3, 1.6):
        S_use = S0 * mult
        W = np.zeros(R * C)
        W[idx] = math.sqrt(S_use / k)
        W = W.reshape(R, C)
        val, s = objective(W)
        # greedy sign flips (and magnitude sign of the seed) until no improvement
        for _ in range(6):
            improved = False
            for j in idx:
                W2 = W.copy()
                W2.ravel()[j] = -W2.ravel()[j]
                v2, s2 = objective(W2)
                if v2 < val - 1e-10:
                    W, val, s, improved = W2, v2, s2, True
            if not improved:
                break
        table.append(dict(k=k, mult=mult, lam_eff=s['lam_eff'], Lambda=s['Lambda'],
                          lam_h1=s['lam_h1'], lam_h2=s['lam_h2'], E_gap=s['E_gap'],
                          sumW2=s['sumW2'], cross=s['cross'], nnz=s['nnz'],
                          feasible=s['E_gap'] >= FLOOR))
    best = min([t for t in table if t['k'] == k], key=lambda t: t['lam_eff'])
    log(f'  k={k:3d}: best lam_eff {best["lam_eff"]:.4f} Lambda {best["Lambda"]:.3f} '
        f'lam_h1 {best["lam_h1"]:.3f} E_gap {best["E_gap"]:.6f} sumW2 {best["sumW2"]:.2f} '
        f'mult {best["mult"]} feasible {best["feasible"]}')

feas = [t for t in table if t['feasible']]
feas.sort(key=lambda t: t['lam_eff'])
log('  best feasible profiles:' + json.dumps(feas[:5], default=float))
RES['profiles'] = table

log('== step 3: local polish of the best feasible profile (352-dim, numeric) ==')
from scipy.optimize import minimize
if feas:
    bt = feas[0]
    Wb = np.zeros(R * C)
    idx = order[:bt['k']]
    Wb[idx] = math.sqrt(bt['sumW2'] / bt['k'])
    Wb = Wb.reshape(R, C)
    val, s = objective(Wb)
    for _ in range(6):
        for j in idx:
            W2 = Wb.copy()
            W2.ravel()[j] = -W2.ravel()[j]
            v2, s2 = objective(W2)
            if v2 < val - 1e-10:
                Wb, val, s = W2, v2, s2
    r = minimize(lambda z: objective(z.reshape(R, C))[0], Wb.ravel(), method='Powell',
                 options=dict(maxiter=4000, xtol=1e-8, ftol=1e-10))
    Wp = r.x.reshape(R, C)
    v, sp = objective(Wp)
    log(f'  polished: lam_eff {sp["lam_eff"]:.4f} Lambda {sp["Lambda"]:.4f} '
        f'lam_h1 {sp["lam_h1"]:.4f} E_gap {sp["E_gap"]:.9f} sumW2 {sp["sumW2"]:.3f} '
        f'nnz {sp["nnz"]}')
    RES['polished'] = sp
else:
    Wp = None

# step 4: error_1 with the shipped rows (no re-encode) for the best candidates
def u_of_theta(th):
    u = np.zeros(N)
    u[0] = 1.0
    for kk, (p, c) in enumerate(TREE):
        t = math.pi * th[kk]
        co, si = math.cos(t), math.sin(t)
        up, uc = u[p], u[c]
        u[p] = co * up - si * uc
        u[c] = si * up + co * uc
    return u


log('== step 4: error_1 with shipped rows (no re-encode) ==')
for tag, W in (('shipped', W0), ('best_profile', None if not feas else Wp)):
    if W is None:
        continue
    log(f'  {tag}: error_1(shipped rows) {e1_of(W, V1):.3f} mHa')

if feas:
    # 8-bit re-encode of the 76 one-body rows to the new eigenbasis
    from scipy.optimize import least_squares
    M = h1p(Wp)
    e, Vc = np.linalg.eigh(M)
    best = None
    for cand in (Vc.T, Vc[:, ::-1].T):
        th = np.zeros((N, N - 1))
        dv = []
        for j in range(N):
            v = cand[j]
            r = least_squares(lambda t: u_of_theta(t) - v, AW[j] / 128.0,
                              bounds=(0.0, 2.0), xtol=1e-12, ftol=1e-12, gtol=1e-12,
                              max_nfev=200)
            th[j] = np.clip(np.rint(r.x * 128.0), 0, 255) / 128.0
            dv.append(np.linalg.norm(u_of_theta(th[j]) - v))
        Vq = np.array([u_of_theta(t) for t in th])
        e1q = e1_of(Wp, Vq)
        log(f'  8-bit refit: mean|dv| {np.mean(dv):.3e}  error_1 {e1q:.3f} mHa')
        if best is None or e1q < best[0]:
            best = (e1q, th)
    RES['e1_8bit_refit'] = best[0]
    np.savez_compressed(WORK / 'rows8.npz', th=best[1], W=Wp)
    np.savez_compressed(WORK / 'W_best.npz', W=Wp)

(WORK / 'lambda_min.json').write_text(json.dumps(RES, indent=1, default=float))
log('DONE')
print(json.dumps({k: v for k, v in RES.items() if k != 'profiles'}, indent=1, default=float))
