"""Shared loading / encoding / measurement helpers for the tree-real experiment.

Everything runs against the *official* verifier modules (read-only, ``data/competition/verifiers``)
and copies of the ``dfthc_refit`` pipeline and of ``tensorqrom8.py``.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
WT = ROOT / '.worktree/dfthcsos'
HERE = WT / 'artifacts/20261112_tree_real'
PIPE = HERE / 'pipeline'
GEN = HERE / 'generator'

os.environ.setdefault('DFTHC_DATA', str(ROOT / 'data/competition'))
for _p in (str(ROOT / 'data/competition/verifiers'), str(PIPE), str(GEN), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import encode  # noqa: E402
import tensorqrom8 as tq  # noqa: E402
from dfthcsos.verify import (  # noqa: E402
    QUBIT_CAP,
    evaluate_words,
    heuristic_costs,
    load_inputs,
    resource_costs,
)

BASE = ROOT / 'artifacts/20261112_frontier/chem14840'      # current best: (8,143,44), 4,089/pass
BASE_COST = 297_237_044.95
KEYS = ('U', 'W', 'H2_I', 'H1_I', 'Hsym_lower')


def load_base():
    """The current best submission: params, words, edges and the official inputs."""
    with np.load(BASE / 'submission.npz', allow_pickle=False) as z:
        params = {k: np.array(z[k]) for k in KEYS}
        words = np.asarray(z['angle_words'], np.int64)
        edges = np.asarray(z['tree_edges'], np.int64)
    return params, words, edges, load_inputs(BASE / 'submission.npz')


def encode_tree(inputs, edges: np.ndarray, brot: int = 8) -> np.ndarray:
    """The (N + R*B, N - 1) unsigned word table of the tree (encode.encode, signed=False)."""
    return encode.encode(inputs, np.asarray(edges, np.int64), brot, signed=False)


def metrics(inputs, words, edges, brot: int = 8) -> dict:
    return evaluate_words(inputs, words, edges, brot)


def build_family(words, j: int = 5, lowbits: int = 4, trials: int = 6, jobs: int = 8, full: bool = True):
    return tq.build_family(words, brot=8, j=j, lowbits=lowbits, trials=trials, jobs=jobs, full=full)


def static_toffoli(family) -> tuple[int, list[int], int]:
    """(Toffolis per pass, per-circuit list, max qubits) from the static operation counts."""
    per, total, qmax = [], 0, 0
    for c in family:
        s = c.operation_statistics()
        per.append(int(s.num_toffoli_like))
        total += int(s.num_toffoli_like)
        qmax = max(qmax, int(c.num_qubits))
    return total, per, qmax


def full_cost(inputs, family, m: dict, brot: int = 8) -> dict:
    """The official score of a built family: resource_costs(evaluate_words) with T = 2 * static."""
    T, per, qmax = static_toffoli(family)
    res = resource_costs(inputs, family, brot, 2 * T)
    return {
        'lambda_eff': float(m['lambda_eff']),
        'error_1': float(m['error_1']),
        'error_2': float(m['error_2']),
        'Lambda': float(m['Lambda']),
        'E_gap': float(m['E_gap']),
        'angles_T_pass': T,
        'angles_per_circuit': per,
        'circuit_qmax': qmax,
        'T_total': float(res['toffoli']),
        'Q_total': int(res['qubits']),
        'angles_qubits': int(res['angles_qubits']),
        'angles_persistent': int(res['angles_persistent_qubits']),
        'angles_temporary': int(res['angles_temporary_qubits']),
        'heuristic_toffoli': int(res['heuristic_toffoli']),
        'heuristic_qubits': int(res['heuristic_qubits']),
        'within_cap': bool(res['angles_within_cap']),
        'cost': float(m['lambda_eff']) * float(res['toffoli']) * int(res['qubits']),
    }


def heuristic_only(inputs, brot: int = 8) -> dict:
    R, B, C = inputs.w.shape
    return heuristic_costs(inputs.num_orbitals, R, B, C, brot)


def save_candidate(out: Path, params: dict, words: np.ndarray, edges: np.ndarray, family, brot: int = 8) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for k, c in enumerate(family):
        c.to_file(str(out / f'angle_k_{k}.kmb'), format='kmb')
    np.savez(out / 'submission.npz', **params, tree_edges=np.asarray(edges, np.int64),
             angle_words=np.asarray(words, np.int64), brot=np.int64(brot))


def dump(row: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as f:
        f.write(json.dumps(row) + '\n')


def onebody_words(h1p, edges: np.ndarray, brot: int = 8, start=None, kicks: int = 10, seed: int = 0):
    """`onebody.refresh` without its jax-based progressive-rounding candidate (jax is not installed).

    Candidates: signed rounding of the eigenvectors and ``start``, polished; then random kicks kept
    when they lower error_1. The jax `onebody_quant.quantize_coded` stage is dropped; on the current
    tree the polish alone already lands under the 20 mHa gate.
    """
    import onebody
    _, vecs = np.linalg.eigh(h1p)
    cands = [encode.signed_words(vecs.T, edges, brot)] + ([np.asarray(start, np.int64)] if start is not None else [])
    k = min((onebody.polish(c, h1p, edges, brot, steps=(-2, -1, 1, 2)) for c in cands),
            key=lambda c: onebody.error(c, h1p, edges, brot))
    k = onebody.polish(k, h1p, edges, brot, steps=(-4, -2, -1, 1, 2, 4))
    best = onebody.error(k, h1p, edges, brot)
    rng = np.random.default_rng(seed)
    n = len(k)
    hi = (1 << (brot - 2)) - 1
    for _ in range(kicks):
        trial = k.copy()
        for r in rng.choice(n, 4, replace=False):
            cols = rng.choice(trial.shape[1], 6, replace=False)
            moved = trial[r, cols] + rng.choice([-1, 1], 6)
            signed = np.where(moved > hi, moved - (1 << brot), moved)
            trial[r, cols] = np.where(signed >= -hi - 1, moved, trial[r, cols])
        trial = onebody.polish(trial % (1 << brot), h1p, edges, brot)
        e = onebody.error(trial, h1p, edges, brot)
        if e < best:
            best, k = e, trial
    return onebody.signed_gauge(k, edges, brot)


def build_selected(words, ksel, j: int = 5, lowbits: int = 4, trials: int = 6, full: bool = True):
    """Build only circuits ``ksel`` of the family (same task construction as tensorqrom8.build_family)."""
    from concurrent.futures import ProcessPoolExecutor
    from fourqrom import batch_deltas
    from tensorqrom8 import SIZES, _one, coded_layout, pad_affine
    words = np.asarray(words, np.int64)
    n_sel = max(1, (len(words) - 1).bit_length())
    deltas = list(batch_deltas(words, j))
    tasks = []
    for k in ksel:
        d = deltas[k]
        if full:
            O = d.shape[1] * 8
            perm, sz = None, [6] * (O // 6) + ([O % 6] if O % 6 else [])
        else:
            perm, sz = coded_layout([], d.shape[1], 8)
        tasks.append((d, n_sel, 8, lowbits, sz, trials, k, perm, full))
    with ProcessPoolExecutor(len(tasks)) as ex:
        return list(ex.map(_one, tasks))


def load_inputs_from(params: dict):
    """Official inputs from an in-memory factorization mapping (fixed shifts applied)."""
    return load_inputs({k: np.asarray(params[k]) for k in KEYS})
