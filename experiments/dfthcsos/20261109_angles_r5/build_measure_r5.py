"""R5/B135/C70 ANGLES: encode signed words from a factorization, build reference +
tensorqrom shared-planner families (J=5, brot=8), measure angles/T/Q.

Metrology only (shots_per_address small, fixed seed): NOT an official verifier PASS.
Compares measured angles_T against current 8304 and reports exact T x Q.

Usage:
  .venv/bin/python experiments/dfthcsos/20261109_angles_r5/build_measure_r5.py \
    <factor_npz> <tree_npz> <outdir> [--trials 6] [--jobs 4] [--shots 2]
"""
from __future__ import annotations

import argparse
import json
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
    register_layout,
)
from dfthcsos.verify import evaluate_words, heuristic_costs, load_inputs  # noqa: E402
from dfthcsos.example_submission.angle_k_reference_circuit import (  # noqa: E402
    batch_deltas,
    build_angle_k_family,
    write_kmx_family,
)

N = 76
BROT = 8
J = 5
BASE_T, BASE_Q = 14966, 427
BASE_TQ = BASE_T * BASE_Q
ANGLES_CURRENT = 8304.0


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
    wf = (lambda v: signed_words(v, edges, brot)) if signed else (lambda v: to_words(tree_angles(v, edges), brot))
    two = wf(U.reshape(-1, n))

    def decode(w):
        v = reconstruct_u_vectors(w / (1 << (brot - 1)), edges)
        return v / np.linalg.norm(v, axis=1, keepdims=True)

    X = reconstruct_x(decode(two).reshape(R, B, n), inputs.w)
    h1p = build_h1_prime(inputs.ref["h1_thc"], inputs.S, inputs.beta_1,
                         inputs.ref["electrons"], inputs.W, X)
    _, vecs = np.linalg.eigh(h1p)
    return np.vstack([wf(vecs.T), two])


def measure(name, family, words, shots, seed):
    t0 = time.time()
    w, lay, tof = recover_words_from_circuits(
        family, num_vectors=len(words), num_angles=N - 1,
        shots_per_address=shots, seed=seed)
    ok = bool(np.array_equal(w, words))
    cc = circuit_costs(family)
    return {
        "family": name,
        "sim_toffoli_fwd_rev": float(tof),
        "sim_per_pass": float(tof) / 2,
        "static_sum_max_magic": int(sum(c["max_magic"] for c in cc)),
        "qubits_max": int(max(c["num_qubits"] for c in cc)),
        "per_circuit": [{"k": c["k"], "max_magic": c["max_magic"], "num_qubits": c["num_qubits"]} for c in cc],
        "selection_bits": len(lay.selection),
        "words_match": ok,
        "shots_per_address": shots,
        "seconds": round(time.time() - t0, 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("factor_npz", type=Path)
    ap.add_argument("tree_npz", type=Path)
    ap.add_argument("outdir", type=Path)
    ap.add_argument("--trials", type=int, default=6)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--shots", type=int, default=2)
    ap.add_argument("--seed", type=int, default=20261109)
    a = ap.parse_args()
    out = a.outdir
    out.mkdir(parents=True, exist_ok=True)
    log = {}

    inputs = load_inputs(a.factor_npz)
    R, B, C = (int(x) for x in inputs.w.shape)
    zt = np.load(a.tree_npz, allow_pickle=False)
    edges = np.array(zt["tree_edges"] if "tree_edges" in zt.files else zt["arr_0"])
    log["shape"] = {"R": R, "B": B, "C": C, "A": inputs.num_vectors,
                    "addr_bits": int((inputs.num_vectors - 1).bit_length())}

    t0 = time.time()
    words = encode_all(inputs, edges, BROT, signed=True)
    log["encode_seconds"] = round(time.time() - t0, 1)
    assert not np.any(((words >> (BROT - 1)) ^ (words >> (BROT - 2))) & 1)
    m = evaluate_words(inputs, words, edges, BROT)
    log["word_metrics"] = {k: (float(m[k]) if isinstance(m[k], (float, np.floating)) else m[k])
                            for k in ("error_1", "error_2", "Lambda", "E_gap", "lambda_eff", "gap_in_domain")}
    np.save(out / "angle_words_r5.npy", words)

    hc = heuristic_costs(N, R, B, C, BROT)
    log["heuristic"] = {"toffoli": int(hc["toffoli"]),
                        "outer": int(hc["outer_state_prep_toffoli"]),
                        "inner": int(hc["inner_state_prep_toffoli"]),
                        "givens": int(hc["givens_rotations_toffoli"]),
                        "persist": int(hc["persistent_qubits"]),
                        "temp_max": int(hc["temporary_qubits"])}

    t0 = time.time()
    ref_family = build_angle_k_family(words, BROT, J)
    log["ref_build_seconds"] = round(time.time() - t0, 1)
    log["ref"] = measure("reference_J5", ref_family, words, a.shots, a.seed)

    import tensorqrom
    t0 = time.time()
    tensor_family = tensorqrom.build_family(words, brot=BROT, j=J, lowbits=4,
                                            trials=a.trials, jobs=a.jobs)
    log["tensor_build_seconds"] = round(time.time() - t0, 1)
    log["tensor_trials"] = a.trials
    log["tensor"] = measure("tensor_shared_J5", tensor_family, words, a.shots, a.seed)
    write_kmx_family(tensor_family, out / "angles_tensor", format="kmb", overwrite=True)

    for key in ("ref", "tensor"):
        ang = log[key]["sim_toffoli_fwd_rev"]
        T = ang + log["heuristic"]["toffoli"]
        lay_q = log[key]["qubits_max"] - log[key]["selection_bits"] - J * BROT
        Q = log["heuristic"]["persist"] + J * BROT + max(log["heuristic"]["temp_max"], lay_q)
        log[key]["T_total"] = float(T)
        log[key]["Q_total"] = int(Q)
        log[key]["TQ"] = float(T) * int(Q)
        log[key]["dTQ_vs_base_pct"] = 100.0 * (float(T) * int(Q) - BASE_TQ) / BASE_TQ
        log[key]["dAngles_vs_8304"] = float(ang) - ANGLES_CURRENT

    log["base"] = {"T": BASE_T, "Q": BASE_Q, "TQ": BASE_TQ, "angles": ANGLES_CURRENT}
    (out / "angles_r5_costs.json").write_text(json.dumps(log, indent=2) + "\n")
    print(json.dumps({k: log[k] for k in ("shape", "word_metrics", "heuristic")}, indent=2))
    for key in ("ref", "tensor"):
        r = log[key]
        print(f"{key}: angles={r['sim_toffoli_fwd_rev']:.2f} (static {r['static_sum_max_magic']}, "
              f"d={r['dAngles_vs_8304']:+.1f} vs 8304) qubits_max={r['qubits_max']} "
              f"T={r['T_total']:.2f} Q={r['Q_total']} TQ={r['TQ']:.1f} ({r['dTQ_vs_base_pct']:+.2f}%) "
              f"match={r['words_match']}")


if __name__ == "__main__":
    main()
