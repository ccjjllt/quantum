"""Encode a DF-THC factorization as brot-bit Givens angle words and score the words.

Mirrors the starter kit's `starter/task2_angles` pipeline, but runs on the competition
verifier's own code (`data/verifiers/dfthcsos`), so it needs only numpy and scipy:

1. Two-body rows: tree angles of each `u_b^(rho)`, rounded to `brot` bits.
2. One-body rows: eigenvectors of `h1_prime` built from the *decoded* two-body vectors,
   so they absorb the two-body rounding error.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import BASELINE  # noqa: E402  (puts the verifiers on sys.path)
from dfthcsos.scoreinfra.dfthc_math import build_h1_prime, reconstruct_u_vectors, reconstruct_x  # noqa: E402
from dfthcsos.verify import evaluate_words, load_inputs  # noqa: E402

N = 76


def path_tree(n: int = N) -> np.ndarray:
    return np.column_stack((np.arange(n - 1), np.arange(1, n))).astype(np.int64)


def log_depth_tree(n: int = N) -> np.ndarray:
    """Breadth-first edges of the log-depth binary tree (the baseline's tree)."""
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
    """theta / pi in [0, 2) such that the tree maps e_0 to each (normalized) row."""
    u = np.array(vectors, dtype=np.float64, ndmin=2)
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    theta = np.zeros((len(u), len(edges)))
    for t in range(len(edges) - 1, -1, -1):
        p, q = edges[t]
        theta[:, t] = np.arctan2(u[:, q], u[:, p])
        u[:, p] = np.hypot(u[:, p], u[:, q])
        u[:, q] = 0.0
    return np.mod(theta / np.pi, 2.0)


def signed_angles(vectors: np.ndarray, edges: np.ndarray) -> np.ndarray:
    """theta/pi in [-1/2, 1/2) such that the tree maps e_0 to each row up to a global sign."""
    a = np.array(vectors, dtype=np.float64)
    a /= np.linalg.norm(a, axis=1, keepdims=True)
    theta = np.zeros((len(a), len(edges)))
    for t in range(len(edges) - 1, -1, -1):
        p, q = edges[t]
        # Keep the parent's sign (cos >= 0); on a zero parent pick theta = -pi/2, not +pi/2.
        s = np.where(a[:, p] > 0, 1.0, np.where(a[:, p] < 0, -1.0, np.where(a[:, q] > 0, -1.0, 1.0)))
        theta[:, t] = np.arctan2(s * a[:, q], s * a[:, p])
        a[:, p] = s * np.hypot(a[:, p], a[:, q])
        a[:, q] = 0.0
    return theta / np.pi


def signed_words(vectors: np.ndarray, edges: np.ndarray, brot: int) -> np.ndarray:
    """Nearest brot-bit words in the signed gauge (bit brot-1 = bit brot-2), as the four-address QROM needs."""
    s = 1 << (brot - 1)
    k = np.clip(np.round(signed_angles(vectors, edges) * s), -s // 2, s // 2 - 1)
    return k.astype(np.int64) % (1 << brot)


def to_words(theta_over_pi: np.ndarray, brot: int) -> np.ndarray:
    scaled = np.mod(theta_over_pi, 2.0) * (1 << (brot - 1))
    return np.floor(scaled + 0.5).astype(np.int64) % (1 << brot)


def decode(words: np.ndarray, edges: np.ndarray, brot: int) -> np.ndarray:
    v = reconstruct_u_vectors(words / (1 << (brot - 1)), edges)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def encode(inputs, edges: np.ndarray, brot: int, signed: bool = False) -> np.ndarray:
    """The `(N + R*B, N - 1)` word table, rounded to nearest: one-body rows first.

    `signed` uses the signed gauge (theta/pi in [-1/2, 1/2)) that the four-address circuits need.
    """
    U = np.asarray(inputs.params['U'], dtype=np.float64)
    R, B, n = U.shape
    words = (lambda v: signed_words(v, edges, brot)) if signed else (lambda v: to_words(tree_angles(v, edges), brot))
    two = words(U.reshape(-1, n))
    X = reconstruct_x(decode(two, edges, brot).reshape(R, B, n), inputs.w)
    h1p = build_h1_prime(inputs.ref['h1_thc'], inputs.S, inputs.beta_1, inputs.ref['electrons'], inputs.W, X)
    _, vecs = np.linalg.eigh(h1p)
    return np.vstack([words(vecs.T), two])


def metrics(factorization, edges: np.ndarray, brot: int, inputs=None, signed: bool = False) -> dict:
    inputs = inputs if inputs is not None else load_inputs(factorization)
    return evaluate_words(inputs, encode(inputs, edges, brot, signed), edges, brot)


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else str(BASELINE)
    inputs = load_inputs(path)
    print(Path(path).name, 'shape', inputs.w.shape)
    for tree_name, edges in (('log_depth', log_depth_tree()), ('path', path_tree())):
        for brot in (10, 11, 12, 13, 14):
            m = metrics(None, edges, brot, inputs)
            print(f"{tree_name:9s} brot {brot}: error_1 {1e3 * m['error_1']:7.2f} mHa  "
                  f"error_2 {1e3 * m['error_2']:6.2f} mHa  Lambda {m['Lambda']:.2f}  "
                  f"E_gap {m['E_gap']:.4f}  lambda_eff {m['lambda_eff']:.3f}")
