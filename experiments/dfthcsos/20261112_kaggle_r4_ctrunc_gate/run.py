"""R=4 C-truncation gate on Kaggle-mounted data.

Keep the full public (4, 255, 120) basis, but truncate each group's copy rank C:
SVD the group contribution X (C, P), keep the top-C' directions, refit the 255 atom
weights against those directions, and let the verifier score error_2.  The angle-word
table (76 + 4*255 rows) is unchanged, so the loader cost is unchanged; only the
outer/inner state-preparation rank drops.

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
    sys.path.insert(0, str(DATA / 'kickmix'))
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


def truncate_c(U: np.ndarray, w: np.ndarray, Cnew: int) -> tuple[np.ndarray, list[float]]:
    """SVD-truncate each group's C copies, then refit the full atom set to the kept directions."""
    uu = U / np.linalg.norm(U, axis=2, keepdims=True)
    out_w, tail = [], []
    for r in range(U.shape[0]):
        A = atoms(uu[r])                 # (B, P)
        X = w[r].T @ A                   # (C, P)
        _, s, Vt = np.linalg.svd(X, full_matrices=False)
        Y = s[:Cnew, None] * Vt[:Cnew]   # (Cnew, P)
        G = A @ A.T
        coef = np.linalg.solve(G + 1e-10 * np.trace(G) / A.shape[0] * np.eye(A.shape[0]), A @ Y.T)
        out_w.append(coef)
        tail.append(float(np.sqrt(np.sum(s[Cnew:] ** 2)) / np.sqrt(np.sum(s ** 2))))
    return np.stack(out_w, axis=0), tail


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

results = {'c120_control': {'C': 120, 'error_2': error2(U0, w0), 'tail_rel': [0.0, 0.0, 0.0, 0.0]}}
print('c120_control', json.dumps(results['c120_control']), flush=True)

for Cnew in (115, 110, 105, 100, 95, 90, 80):
    wc, tail = truncate_c(U0, w0, Cnew)
    results[f'c{Cnew}'] = {'C': Cnew, 'error_2': error2(U0, wc), 'tail_rel': tail}
    print(f'c{Cnew}', json.dumps(results[f'c{Cnew}']), flush=True)

summary = {
    'seed': str(SEED),
    'threshold_mHa': 20.0,
    'control_mHa': 1e3 * results['c120_control']['error_2'],
    'results': {k: {**v, 'error_2_mHa': 1e3 * v['error_2']} for k, v in results.items()},
}
summary['passing'] = [k for k, v in results.items()
                      if k != 'c120_control' and v['error_2'] <= 0.020]
(OUT / 'diagnostic_ctrunc.json').write_text(json.dumps(summary, indent=2))
print('SUMMARY', json.dumps(summary), flush=True)
print('DONE', flush=True)
