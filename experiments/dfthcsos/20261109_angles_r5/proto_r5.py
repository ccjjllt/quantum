"""Prototype: encode R5 words (signed gauge) from a factorization NPZ, build ONE
tensorqrom shared-planner circuit + ONE reference circuit for batch 0, measure costs.

Usage: .venv/bin/python experiments/dfthcsos/20261109_angles_r5/proto_r5.py <factor_npz> <tree_npz>
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data" / "competition" / "verifiers"))
sys.path.insert(0, str(ROOT / "artifacts/20261106_high_yield/lera_data/dfthc_refit"))

from dfthcsos.scoreinfra.dfthc_math import (  # noqa: E402
    build_h1_prime,
    reconstruct_u_vectors,
    reconstruct_x,
)
from dfthcsos.scoreinfra.circuits import (  # noqa: E402
    circuit_costs,
    recover_words_from_circuits,
)
from dfthcsos.verify import evaluate_words, heuristic_costs, load_inputs  # noqa: E402
from dfthcsos.example_submission.angle_k_reference_circuit import (  # noqa: E402
    batch_deltas,
    build_angle_k_circuit,
)

N = 76
BROT = 8
J = 5


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
        s = np.where(a[:, p] > 0, 1.0, np.where(a[:, p] < 0, -1.0, np.where(a[:, q] > 0, -1.0, 1.0)))
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


def encode_all(inputs, edges, brot, signed):
    U = np.asarray(inputs.params["U"], dtype=np.float64)
    R, B, n = U.shape
    words = ((lambda v: signed_words(v, edges, brot)) if signed
             else (lambda v: to_words(tree_angles(v, edges), brot)))
    two = words(U.reshape(-1, n))

    def decode(w):
        v = reconstruct_u_vectors(w / (1 << (brot - 1)), edges)
        return v / np.linalg.norm(v, axis=1, keepdims=True)

    X = reconstruct_x(decode(two).reshape(R, B, n), inputs.w)
    h1p = build_h1_prime(inputs.ref["h1_thc"], inputs.S, inputs.beta_1,
                         inputs.ref["electrons"], inputs.W, X)
    _, vecs = np.linalg.eigh(h1p)
    return np.vstack([words(vecs.T), two])


def main():
    fac, tree_npz = Path(sys.argv[1]), Path(sys.argv[2])
    t0 = time.time()
    inputs = load_inputs(fac)
    z = np.load(tree_npz, allow_pickle=False)
    edges = np.array(z["tree_edges"] if "tree_edges" in z.files else z["arr_0"])
    print("shape R,B,C =", inputs.w.shape, "A =", inputs.num_vectors, flush=True)
    words = encode_all(inputs, edges, BROT, signed=True)
    print(f"encode {time.time()-t0:.1f}s words {words.shape} max {words.max()}", flush=True)
    m = evaluate_words(inputs, words, edges, BROT)
    print({k: (round(float(v), 9) if isinstance(v, float) else v)
               for k, v in m.items() if k in ("error_1", "error_2", "Lambda", "E_gap", "lambda_eff", "gap_in_domain")}, flush=True)
    assert not np.any(((words >> (BROT - 1)) ^ (words >> (BROT - 2))) & 1), "not signed gauge"
    print("signed gauge OK", flush=True)

    deltas = batch_deltas(words, J)
    print("batches:", len(deltas), "delta0 shape:", deltas[0].shape, flush=True)

    # reference circuit for batch 0
    ref0 = build_angle_k_circuit(deltas[0], BROT)
    cc = circuit_costs([ref0])[0]
    print("REF batch0:", cc, flush=True)

    # tensorqrom shared-planner circuit for batch 0 (small trials for prototype)
    import tensorqrom
    t1 = time.time()
    terms, grouped = tensorqrom._one((np.asarray(deltas[0]), int((len(words) - 1).bit_length()),
                                      BROT, 4, list(tensorqrom.SIZES), 2, 0, None))
    print(f"_one {time.time()-t1:.1f}s grouped={grouped} nterms={len(terms)}", flush=True)
    from tensorqrom import build_circuit, low_groups
    circ = (build_circuit(np.asarray(deltas[0]), terms, int((len(words) - 1).bit_length()),
                          BROT, 4, groups=low_groups(4), scratch=True) if grouped
            else build_circuit(np.asarray(deltas[0]), terms, int((len(words) - 1).bit_length()), BROT, 4))
    cc2 = circuit_costs([circ])[0]
    print("TENSOR batch0:", cc2, flush=True)

    # functional + cost measurement, 2 shots/address (metrology only, NOT a verifier PASS)
    for name, c in (("ref0", ref0), ("tensor0", circ)):
        w, lay, tof = recover_words_from_circuits([c], num_vectors=len(words),
                                                  num_angles=N - 1, shots_per_address=1, seed=12345)
        print(name, "sim_toffoli_fwd_rev=%.2f" % tof, "qubits:", c.num_qubits,
              "words_match:", bool(np.array_equal(w[:, : J], np.asarray(deltas[0]))), flush=True)

    hc = heuristic_costs(N, *inputs.w.shape, BROT)
    print("heuristic:", {k: hc[k] for k in ("toffoli", "qubits")}, flush=True)


if __name__ == "__main__":
    main()
