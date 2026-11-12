"""R=4 B-truncation gate, run entirely on Kaggle-mounted data.

Inputs (mounted, nothing uploaded):
  * competition data       /kaggle/input/google-verifiable-quantum-circuit-compilation
  * public factorization   /kaggle/input/vqcc-apache-public-circuits/factorizations/729cd14c088f.npz

For each B in {180, 200, 220} this keeps the top-B atoms of the public (4, 255, 120)
table by sum_c |w|, re-solves the weights against the full group contribution, encodes
the vectors as 10-bit Givens words, and evaluates the verifier's exact `error_2`.
The full B=255 table is the control.  `error_2` is the gate: it cannot be changed by
the offset solve, because the two-body tensor is fixed by (U, w).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

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
    for p in (IN / 'vqcc-apache-public-circuits' / 'factorizations' / '729cd14c088f.npz',
              IN / 'quantum-rc-kaggle-20261112' / '729cd14c088f.npz'):
        if p.is_file():
            return p
    hits = list(IN.glob('**/factorizations/729cd14c088f.npz'))
    if hits:
        return hits[0]
    raise SystemExit(f'public factorisation not found under {IN}')


DATA = Path(os.environ['DFTHC_DATA']) if os.environ.get('DFTHC_DATA') else find_competition()
SEED = Path(os.environ['DFTHC_SEED']) if os.environ.get('DFTHC_SEED') else find_seed()
sys.path.insert(0, str(DATA / 'verifiers'))
if sys.platform.startswith('linux'):
    sys.path.insert(0, str(DATA / 'kickmix'))  # Linux kickmix build; macOS uses the PyPI wheel
print('competition:', DATA, flush=True)
print('seed:       ', SEED, flush=True)

from dfthcsos.scoreinfra.dfthc_math import evaluate_dfthc_angle_words  # noqa: E402
from dfthcsos.scoreinfra.reference import UPPER_ENERGY, check_fcidump, load_reference  # noqa: E402
from dfthcsos.verify import native_inputs  # noqa: E402

N = 76


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


EDGES = log_depth_tree()
I, J = np.tril_indices(N)
DVEC = np.sqrt(np.where(I == J, 1.0, 2.0))


def tree_angles(vectors: np.ndarray) -> np.ndarray:
    u = np.array(vectors, dtype=np.float64, ndmin=2)
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    theta = np.zeros((len(u), len(EDGES)))
    for t in range(len(EDGES) - 1, -1, -1):
        p, q = EDGES[t]
        theta[:, t] = np.arctan2(u[:, q], u[:, p])
        u[:, p] = np.hypot(u[:, p], u[:, q])
        u[:, q] = 0.0
    return np.mod(theta / np.pi, 2.0)


def to_words(vectors: np.ndarray, brot: int = 10) -> np.ndarray:
    scaled = tree_angles(vectors) * (1 << (brot - 1))
    return np.floor(scaled + 0.5).astype(np.int64) % (1 << brot)


def atoms(u: np.ndarray) -> np.ndarray:
    return (u[..., I] * u[..., J]) * DVEC


def truncate(U: np.ndarray, w: np.ndarray, B: int) -> tuple[np.ndarray, np.ndarray]:
    """Keep the top-B atoms per group and re-solve weights against the full contribution."""
    uu = U / np.linalg.norm(U, axis=2, keepdims=True)
    out_u, out_w = [], []
    for r in range(U.shape[0]):
        A = atoms(uu[r])
        X = w[r].T @ A
        sel = np.argsort(-np.abs(w[r]).sum(axis=1))[:B]
        As = A[sel]
        G = As @ As.T
        coef = np.linalg.solve(G + 1e-10 * np.trace(G) / B * np.eye(B), As @ X.T)
        out_u.append(uu[r][sel])
        out_w.append(coef)
    return np.stack(out_u), np.stack(out_w)


def error2(U: np.ndarray, w: np.ndarray) -> float:
    two = to_words(U.reshape(-1, N))
    words = np.vstack([np.zeros((N, two.shape[1]), dtype=np.int64), two])
    m = evaluate_dfthc_angle_words(
        words, w, np.zeros(w.shape[0:1] + w.shape[2:]), S, beta, ref,
        brot=10, tree_edges=EDGES, energy_upper=UPPER_ENERGY,
    )
    return float(m['error_2'])


with np.load(SEED) as z:
    U0 = np.asarray(z['U'], np.float64)
    w0 = np.asarray(z['W'], np.float64)
    H1_I = np.asarray(z['H1_I'], np.float64)
    Hsym_lower = np.asarray(z['Hsym_lower'], np.float64)

_, _, S, beta = native_inputs({'U': U0, 'W': w0, 'H2_I': w0.sum(axis=1),
                               'H1_I': H1_I, 'Hsym_lower': Hsym_lower})
ref = load_reference(check_fcidump())

results = {'control_b255': {'B': 255, 'error_2': error2(U0, w0)}}
print('control_b255', json.dumps(results['control_b255']), flush=True)

for B in (180, 200, 220):
    UB, wB = truncate(U0, w0, B)
    results[f'b{B}_imp'] = {'B': B, 'error_2': error2(UB, wB)}
    print(f'b{B}_imp', json.dumps(results[f'b{B}_imp']), flush=True)

summary = {
    'seed': str(SEED),
    'threshold_mHa': 20.0,
    'control_mHa': 1e3 * results['control_b255']['error_2'],
    'results': {k: {**v, 'error_2_mHa': 1e3 * v['error_2']} for k, v in results.items()},
}
summary['passing'] = [k for k, v in results.items()
                      if k != 'control_b255' and v['error_2'] <= 0.020]
(OUT / 'diagnostic.json').write_text(json.dumps(summary, indent=2))
print('SUMMARY', json.dumps(summary), flush=True)
print('DONE', flush=True)
