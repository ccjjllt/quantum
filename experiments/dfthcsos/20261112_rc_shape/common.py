"""Shared helpers for the (R,C)-shape experiment."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if not (ROOT / 'dfthc_refit').is_dir():   # a record copy under experiments/ points at the artifacts tree
    ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dfthcsos/artifacts/20261112_rc_shape')
PIPE = ROOT / 'dfthc_refit'
DATA = Path('/Users/zhaohuaxiang/ccjjllt/quantum/data/competition')
os.environ.setdefault('DFTHC_DATA', str(DATA))
os.environ.setdefault('DFTHC_STARTER', str(ROOT / 'starter'))
sys.path.insert(0, str(PIPE))
sys.path.insert(0, str(DATA / 'verifiers'))

import numpy as np  # noqa: E402

import encode  # noqa: E402
import fastfit  # noqa: E402

import jax  # noqa: E402

jax.config.update('jax_enable_x64', True)
import jax.numpy as jnp  # noqa: E402
from dfthc import df_thc_sga  # noqa: E402
from dfthc.train_df_thc_sga import Initialize  # noqa: E402

df_thc_sga.dtype = jnp.float64

FCIDUMP = DATA / 'verifiers/dfthcsos/FeMoCo76o113e.fcidump'
SHIFTS = DATA / 'verifiers/dfthcsos/FeMoCo76o113e.fixed_shifts.npz'
CURRENT = Path('/Users/zhaohuaxiang/ccjjllt/quantum/artifacts/20261112_frontier/chem14840/submission.npz')
PUB4 = Path('/Users/zhaohuaxiang/ccjjllt/quantum/artifacts/20261112_rc_seeds/729cd14c088f.npz')
PUB8 = Path('/Users/zhaohuaxiang/ccjjllt/quantum/artifacts/20261112_rc_seeds/9706e2c7ecff.npz')
UPPER = -22140.27335


def load(path) -> dict:
    with np.load(path) as z:
        d = {k: np.asarray(z[k]) for k in ('U', 'W', 'H2_I')}
        for k in ('angle_words', 'tree_edges', 'brot', 'offset_W', 'coded', 'coded2', 'continuous_U'):
            if k in z.files:
                d[k] = np.asarray(z[k])
    return d


def get_target():
    ref = Initialize(str(FCIDUMP), UPPER)
    ref = {k: (jnp.asarray(v, jnp.float64) if hasattr(v, 'dtype') and jnp.issubdtype(v.dtype, jnp.floating)
               else v) for k, v in ref.items()}
    with np.load(SHIFTS) as z:
        frozen = {k: jnp.asarray(z[k], jnp.float64) for k in ('Hsym_lower', 'H1_I')}
    return fastfit.problem(ref, frozen, jnp.float64), ref


def e2(U, w, prob=None) -> float:
    if prob is None:
        prob, _ = get_target()
    return float(fastfit.error2(jnp.asarray(U), jnp.asarray(w), prob))


def official(path, words=None) -> dict:
    inputs = encode.load_inputs(path)
    if words is None:
        d = load(path)
        words, edges, brot = d['angle_words'], d['tree_edges'], int(d['brot'])
    else:
        d = load(path)
        edges, brot = d['tree_edges'], int(d['brot'])
    m = encode.evaluate_words(inputs, words, edges, brot)
    return {'e1': 1e3 * m['error_1'], 'e2': 1e3 * m['error_2'], 'Lambda': m['Lambda'],
            'E_gap': m['E_gap'], 'lambda_eff': m['lambda_eff']}


def terms(U, w, ref) -> np.ndarray:
    """(R*C, P) the matrices X^{rc} in packed pair space."""
    u = U / np.linalg.norm(U, axis=2, keepdims=True)
    i, j = (np.asarray(t) for t in ref['tril'])
    P = u[:, :, i] * u[:, :, j]
    return np.einsum('rbc,rbp->rcp', w, P).reshape(-1, P.shape[-1])
