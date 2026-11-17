"""Coded-quantizer probe (b3): pure error_2 floor of the merged coded words.

Input: jiyujia/qcc-chem-coded-r9merged-rounded (quantize.py --coded "0-14"
output at (9,180,90): two-body `words` (1620,75), `w` (9,180,90)). refit_weights
cannot run here (its lambda machinery -- rotate_columns/assemble -- NaNs on
the placeholder one-body rows of the shim). Instead this measures the
RESULT4-§2.3-comparable floor directly: pure error_2 L-BFGS over all 145,800
weights at fixed vectors, with the exact gradient from the WeightProblem
docstring (dF/dw_r = 4 K_rs w_s A_rs^T, dL/dw_r = 2 Q_r w_r), finite-difference
checked before optimizing. e2 depends only on (u, w), so this is the true
fixed-words floor of the --coded table. Nothing is submitted.
"""

import glob
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

WORK = Path('/kaggle/working')
SRC = next(Path(h).parents[1] for h in glob.glob('/kaggle/input/**/dfthc_refit/experiments/shrink.py',
                                                recursive=True))
hits = glob.glob('/kaggle/input/**/qcc-chem-coded-r9merged-rounded/**/rounded.npz', recursive=True)
if not hits:
    hits = glob.glob('/kaggle/input/**/rounded.npz')
ROUNDED = Path(hits[0])
PIPE = WORK / 'pipe'
shutil.rmtree(PIPE, ignore_errors=True)
shutil.copytree(SRC, PIPE)

import os
os.environ.setdefault('JAX_PLATFORMS', 'cpu')
T0 = time.time()
S = {'kernel': 'jiyujia/qcc-chem-coded-r9merged-floor2', 'rounded': str(ROUNDED)}


def el() -> float:
    return time.time() - T0


def log(*a):
    print(f'[{el() / 60:7.1f} min]', *a, flush=True)


def save_summary():
    (WORK / 'summary.json').write_text(json.dumps(S, indent=1))


sys.path.insert(0, str(PIPE))
import encode  # noqa: E402
from paths import SHIFTS  # noqa: E402
from dfthcsos.scoreinfra.reference import check_fcidump, load_reference  # noqa: E402
from dfthcsos.verify import native_inputs  # noqa: E402
from refit_weights import error_terms  # noqa: E402 (exact K, Q, T2; no lambda machinery used)

zr = np.load(ROUNDED)
words2 = np.asarray(zr['words'], np.int64)
w0 = np.asarray(zr['w'], np.float64)
R, B, C = w0.shape
N = 76
edges = encode.log_depth_tree(N)
u = encode.decode(words2, edges, 8).reshape(R, B, N)
u /= np.linalg.norm(u, axis=2, keepdims=True)
ref = load_reference(check_fcidump())
with np.load(SHIFTS) as z:
    _, _, Smat, beta = native_inputs({'U': u, 'W': w0, 'H2_I': w0.sum(axis=1),
                                      'H1_I': np.array(z['H1_I']), 'Hsym_lower': np.array(z['Hsym_lower'])})
K, Q, T2 = error_terms(u, np.asarray(ref['tei'], np.float64), Smat)
log(f'K {K.shape} Q {Q.shape} T2 {T2:.6f}')
S.update(K_shape=list(K.shape), Q_shape=list(Q.shape))
save_summary()

T2f = float(T2)


def e2_and_grad(w):
    A = np.einsum('rbc,rbsd,sdk->rcsk', w, K, w, optimize=True)
    F = float(np.sum(A ** 2))
    L = float(np.einsum('rbc,rbd,rdc->', w, Q, w, optimize=True))
    E = F - 2 * L + T2f
    e2 = float(np.sqrt(max(E, 0.0)))
    dF = 4.0 * np.einsum('sdx,rbsd,rcsx->rbc', w, K, A, optimize=True)
    dL = 2.0 * np.einsum('rbd,rdc->rbc', Q, w, optimize=True)
    g = (dF - 2 * dL) / (2 * e2) if e2 > 0 else np.zeros_like(w)
    return e2, g


e2_0, g_0 = e2_and_grad(w0)
log(f'start e2 {1e3 * e2_0:.4f} mHa (|grad| {np.linalg.norm(g_0):.4f})')
# finite-difference check: directional derivative along g (robust to fp noise),
# plus a per-entry spot check at larger h
rng = np.random.default_rng(0)
idx = [(rng.integers(R), rng.integers(B), rng.integers(C)) for _ in range(8)]
gnorm = float(np.linalg.norm(g_0))
gdir = g_0 / gnorm
for h in (3e-6, 1e-6):
    num = (e2_and_grad(w0 + h * gdir)[0] - e2_0) / h
    drel = abs(num - gnorm) / gnorm
    log(f'directional check h={h:g}: num {num:.6e} ana {gnorm:.6e} rel {drel:.2e}')
S['grad_dir_rel_err'] = drel
h = 1e-5
maxrel = 0.0
for r, b, c in idx:
    wp = w0.copy()
    wp[r, b, c] += h
    num = (e2_and_grad(wp)[0] - e2_0) / h
    ana = g_0[r, b, c]
    rel = abs(num - ana) / max(1e-12, abs(num))
    maxrel = max(maxrel, rel)
log(f'grad check: max rel err over 8 entries = {maxrel:.2e}')
S['grad_check_max_rel_err'] = maxrel
S['start_e2_mHa'] = 1e3 * e2_0
save_summary()
assert drel < 5e-2, 'directional gradient mismatch'

n = w0.size


def fun(x):
    e2, g = e2_and_grad(x.reshape(w0.shape))
    return e2, g.ravel()


res = minimize(fun, w0.ravel(), jac=True, method='L-BFGS-B',
               options={'maxiter': 300, 'maxcor': 30, 'ftol': 1e-15, 'gtol': 1e-12})
e2_f = float(res.fun)
log(f'floor e2 {1e3 * e2_f:.4f} mHa after {res.nit} it ({res.nfev} evals): {res.message}')
S['floor_e2_mHa'] = 1e3 * e2_f
S['floor_nit'] = int(res.nit)
S['elapsed_hours'] = round(el() / 3600, 2)
save_summary()
w_opt = res.x.reshape(w0.shape)
np.savez(WORK / 'w_floor.npz', w=w_opt, e2_mHa=np.float64(1e3 * e2_f))
log('done')
