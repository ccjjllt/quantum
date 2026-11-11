"""Quantize an (8,B,44) trained factorization into 8-bit ANGLE words and evaluate.

Encoding follows the recovered 20261109_angles_r5 pipeline: signed Givens angles
on the fixed baseline tree, then the one-body rows are the eigenvectors of the
h1_prime built from the decoded two-body rows.  ``evaluate_words`` is the
official metric; no circuit is built.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "data/competition/verifiers"))

from dfthcsos.scoreinfra.dfthc_math import (  # noqa: E402
    build_h1_prime,
    reconstruct_u_vectors,
    reconstruct_x,
)
from dfthcsos.verify import evaluate_words, load_inputs  # noqa: E402

BASE = WT.parents[1] / "artifacts/20261111_grimoire33/candidate/dfthcsos/submission.npz"
BROT = 8


def tree_angles(vectors, edges):
    u = np.array(vectors, dtype=np.float64, ndmin=2)
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    theta = np.zeros((len(u), len(edges)))
    for t in range(len(edges) - 1, -1, -1):
        p, q = edges[t]
        theta[:, t] = np.arctan2(u[:, q], u[:, p])
    return np.mod(theta / np.pi, 2.0)


def signed_angles(vectors, edges):
    a = np.array(vectors, dtype=np.float64)
    a /= np.linalg.norm(a, axis=1, keepdims=True)
    theta = np.zeros((len(a), len(edges)))
    for t in range(len(edges) - 1, -1, -1):
        p, q = edges[t]
        s = np.where(a[:, p] > 0, 1.0, np.where(a[:, p] < 0, -1.0,
                    np.where(a[:, q] > 0, -1.0, 1.0)))
        theta[:, t] = np.arctan2(s * a[:, q], s * a[:, p])
        a[:, p] = s * np.hypot(a[:, p], a[:, q])
        a[:, q] = 0.0
    return theta / np.pi


def to_words(theta_over_pi, brot):
    scaled = np.mod(theta_over_pi, 2.0) * (1 << (brot - 1))
    return np.floor(scaled + 0.5).astype(np.int64) % (1 << brot)


def signed_words(vectors, edges, brot):
    s = 1 << (brot - 1)
    k = np.clip(np.round(signed_angles(vectors, edges) * s), -s // 2, s // 2 - 1)
    return k.astype(np.int64) % (1 << brot)


def encode_all(inputs, edges, brot):
    U = np.asarray(inputs.params["U"], dtype=np.float64)
    R, B, n = U.shape
    wf = lambda v: signed_words(v, edges, brot)  # noqa: E731
    two = wf(U.reshape(-1, n))

    def decode(w):
        v = reconstruct_u_vectors(w / (1 << (brot - 1)), edges)
        return v / np.linalg.norm(v, axis=1, keepdims=True)

    X = reconstruct_x(decode(two).reshape(R, B, n), inputs.w)
    h1p = build_h1_prime(inputs.ref["h1_thc"], inputs.S, inputs.beta_1,
                         inputs.ref["electrons"], inputs.W, X)
    _, vecs = np.linalg.eigh(h1p)
    return np.vstack([wf(vecs.T), two])


def main() -> None:
    train = Path(sys.argv[1])
    out = Path(sys.argv[2])
    base = np.load(BASE)
    H1_I = np.float32(base["H1_I"])
    Hsym_lower = np.asarray(base["Hsym_lower"], np.float32)
    tree = np.asarray(base["tree_edges"], np.int64)
    W_upper = np.asarray(base["H2_I"], np.float64) - np.asarray(base["W"], np.float64).sum(axis=1)
    z = np.load(train)
    U = np.asarray(z["U"], np.float64)
    W = np.asarray(z["W"], np.float64)
    print("train U", U.shape, "W", W.shape)
    params = {
        "U": U, "W": W, "H2_I": W_upper + W.sum(axis=1),
        "H1_I": H1_I, "Hsym_lower": Hsym_lower,
    }
    inputs = load_inputs(params)
    words = encode_all(inputs, tree, BROT)
    m = evaluate_words(inputs, words, tree, BROT)
    print(f"e1={m['error_1']:.9f} Ha ({1000 * m['error_1']:.6f} mHa) "
          f"e2={m['error_2']:.9f} Ha ({1000 * m['error_2']:.6f} mHa)")
    print(f"Lambda={m['Lambda']:.12f} E_gap={m['E_gap']:.12f} "
          f"lambda_eff={m['lambda_eff']:.12f} gap_in_domain={m['gap_in_domain']}")
    np.savez(
        out, U=U, W=W, H2_I=params["H2_I"], H1_I=H1_I, Hsym_lower=Hsym_lower,
        angle_words=words, tree_edges=tree,
    )
    print("wrote", out, "words", words.shape)


if __name__ == "__main__":
    main()
