"""Baseline probe: current (8,143,44) table metrics, target norm/spectrum, fastfit speed."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PIPE = ROOT / 'dfthc_refit'
os.environ.setdefault('DFTHC_DATA', '/Users/zhaohuaxiang/ccjjllt/quantum/data/competition')
os.environ.setdefault('DFTHC_STARTER', str(ROOT / 'starter'))
sys.path.insert(0, str(PIPE))

import numpy as np  # noqa: E402

import encode  # noqa: E402

CUR = Path('/Users/zhaohuaxiang/ccjjllt/quantum/artifacts/20261112_frontier/chem14840/submission.npz')

with np.load(CUR) as z:
    U = np.asarray(z['U'], np.float64)
    w = np.asarray(z['W'], np.float64)
    off = np.asarray(z['H2_I'], np.float64)
    words = np.asarray(z['angle_words'], np.int64)
    edges = np.asarray(z['tree_edges'], np.int64)
    brot = int(z['brot'])
    print('shape', U.shape, w.shape, off.shape, 'words', words.shape, 'brot', brot)

inputs = encode.load_inputs(CUR)
m = encode.evaluate_words(inputs, words, edges, brot)
print('given words: e1 %.6f mHa e2 %.6f mHa Lambda %.6f E_gap %.9f lambda_eff %.6f' % (
    1e3 * m['error_1'], 1e3 * m['error_2'], m['Lambda'], m['E_gap'], m['lambda_eff']))

# rounded from the float U (no polish): the pure rounding cost of this table
t0 = time.time()
mm = encode.metrics(None, edges, brot, inputs)
print('re-encoded: e1 %.4f e2 %.4f Lambda %.4f E_gap %.6f lambda_eff %.6f (%.1fs)' % (
    1e3 * mm['error_1'], 1e3 * mm['error_2'], mm['Lambda'], mm['E_gap'], mm['lambda_eff'], time.time() - t0))

# target norm and spectrum (fastfit's packed objective)
import jax  # noqa: E402

jax.config.update('jax_enable_x64', True)
import jax.numpy as jnp  # noqa: E402
from dfthc import df_thc_sga  # noqa: E402
from dfthc.train_df_thc_sga import Initialize  # noqa: E402

import fastfit  # noqa: E402

df_thc_sga.dtype = jnp.float64
ref = Initialize(str(PIPE.parents[3] / 'data/competition/verifiers/dfthcsos/FeMoCo76o113e.fcidump')
                 if False else '/Users/zhaohuaxiang/ccjjllt/quantum/data/competition/verifiers/dfthcsos/FeMoCo76o113e.fcidump',
                 encode.UPPER_ENERGY if hasattr(encode, 'UPPER_ENERGY') else -22140.27335)
ref = {k: (jnp.asarray(v, jnp.float64) if hasattr(v, 'dtype') and jnp.issubdtype(v.dtype, jnp.floating) else v)
       for k, v in ref.items()}
with np.load('/Users/zhaohuaxiang/ccjjllt/quantum/data/competition/verifiers/dfthcsos/FeMoCo76o113e.fixed_shifts.npz') as z:
    frozen = {k: jnp.asarray(z[k], jnp.float64) for k in ('Hsym_lower', 'H1_I')}
prob = fastfit.problem(ref, frozen, jnp.float64)
T = np.asarray(prob[0])
print('T shape', T.shape, '||T||_F %.4f' % np.linalg.norm(T), 'trace %.4f' % np.trace(T))
ev = np.linalg.eigvalsh(T)
print('top eigenvalues', np.round(ev[::-1][:8], 4), 'min', ev[0], 'negative count', int((ev < 0).sum()))

# float residual of the current U/w
e2f = float(fastfit.error2(jnp.asarray(U), jnp.asarray(w), prob))
print('float e2 of current U/W: %.6f mHa' % (1e3 * e2f))

# per-group term spectra: how concentrated is sum_c x_c (x) x_c?
u = U / np.linalg.norm(U, axis=2, keepdims=True)
i, j = (np.asarray(t) for t in ref['tril'])
P = u[:, :, i] * u[:, :, j]
X = np.einsum('rbc,rbp->rcp', w, P).reshape(-1, P.shape[-1])   # (R*C, 2926)
print('term matrix X', X.shape, '||X||_F %.4f' % np.linalg.norm(X))
sv = np.linalg.svd(X, compute_uv=False)
print('term singular values: top', np.round(sv[:5], 4), 'sum sq %.3f' % (sv ** 2).sum())
for k in (32, 44, 64, 88, 120, 176, 352):
    print('  rank %3d captures %.5f of sum sq' % (k, (sv[:k] ** 2).sum() / (sv ** 2).sum()))

# float error of an exact merge in pairs (4,286,88)
from structure import merge  # noqa: E402

p = {'U': U, 'W': w, 'H2_I': off}
pm = merge(p, 2, 88)
print('merge pairs ->', pm['W'].shape, 'float e2 %.9f mHa' % (1e3 * float(fastfit.error2(
    jnp.asarray(pm['U']), jnp.asarray(pm['W']), prob))))
