"""R5/B135/C70装配扫描:固定U/W字表,枚举 J x brot,实测 T/Q/TxQ(零训练).

方法沿用 20261109_angles_r5/build_measure_r5.py(快照 165d6e7):
signed规范编码 + 朴素QROM对照 + tensorqrom共享planner,
kickmix recover_words小shots成本计量 + SpinFreeData_V1精确heuristic。
不是官方verify.py验证,不跑78k-shot PASS。只换装配,不训练。

Usage:
  .venv/bin/python experiments/dfthcsos/20261110_shapes/scan_j_brot.py \
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
    build_angle_k_family,
)

N = 76
J_LIST = (4, 5, 6)
BROT_LIST = (6, 8)
BASE_T, BASE_Q = 14966, 427
BASE_TQ = BASE_T * BASE_Q
ANGLES_CURRENT = 8304.0


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


def signed_words(vectors, edges, brot):
    s = 1 << (brot - 1)
    k = np.clip(np.round(signed_angles(vectors, edges) * s), -s // 2, s // 2 - 1)
    return k.astype(np.int64) % (1 << brot)


def encode_all(inputs, edges, brot):
    U = np.asarray(inputs.params["U"], dtype=np.float64)
    R, B, n = U.shape
    two = signed_words(U.reshape(-1, n), edges, brot)

    def decode(w):
        v = reconstruct_u_vectors(w / (1 << (brot - 1)), edges)
        return v / np.linalg.norm(v, axis=1, keepdims=True)

    X = reconstruct_x(decode(two).reshape(R, B, n), inputs.w)
    h1p = build_h1_prime(inputs.ref["h1_thc"], inputs.S, inputs.beta_1,
                         inputs.ref["electrons"], inputs.W, X)
    _, vecs = np.linalg.eigh(h1p)
    return np.vstack([signed_words(vecs.T, edges, brot), two])


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
        "num_circuits": len(cc),
        "per_circuit": [{"k": c["k"], "max_magic": c["max_magic"], "num_qubits": c["num_qubits"]} for c in cc],
        "selection_bits": len(lay.selection),
        "J": int(lay.batch_size),
        "brot": int(lay.brot),
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
    ap.add_argument("--seed", type=int, default=20261110)
    a = ap.parse_args()
    out = a.outdir
    out.mkdir(parents=True, exist_ok=True)
    log: dict = {"combos": []}

    inputs = load_inputs(a.factor_npz)
    R, B, C = (int(x) for x in inputs.w.shape)
    zt = np.load(a.tree_npz, allow_pickle=False)
    edges = np.array(zt["tree_edges"] if "tree_edges" in zt.files else zt["arr_0"])
    log["shape"] = {"R": R, "B": B, "C": C, "A": inputs.num_vectors,
                    "addr_bits": int((inputs.num_vectors - 1).bit_length())}
    log["factor"] = str(a.factor_npz)
    log["note"] = ("fixed U/W seed, signed words re-encoded per brot; "
                   "no training; metrology only, not a verifier PASS")

    import tensorqrom

    for brot in BROT_LIST:
        t0 = time.time()
        words = encode_all(inputs, edges, brot)
        enc_s = round(time.time() - t0, 1)
        assert not np.any(((words >> (brot - 1)) ^ (words >> (brot - 2))) & 1), "signed gauge violated"
        m = evaluate_words(inputs, words, edges, brot)
        wmet = {k: (float(m[k]) if isinstance(m[k], (float, np.floating)) else m[k])
                for k in ("error_1", "error_2", "Lambda", "E_gap", "lambda_eff", "gap_in_domain")}
        hc = heuristic_costs(N, R, B, C, brot)
        heur = {"toffoli": int(hc["toffoli"]),
                "outer": int(hc["outer_state_prep_toffoli"]),
                "inner": int(hc["inner_state_prep_toffoli"]),
                "givens": int(hc["givens_rotations_toffoli"]),
                "persist": int(hc["persistent_qubits"]),
                "temp_max": int(hc["temporary_qubits"])}
        for J in J_LIST:
            row: dict = {"J": J, "brot": brot, "encode_seconds": enc_s,
                         "word_metrics": wmet, "heuristic": heur}
            t0 = time.time()
            ref_family = build_angle_k_family(words, brot, J)
            row["ref_build_seconds"] = round(time.time() - t0, 1)
            row["ref"] = measure(f"reference_J{J}_b{brot}", ref_family, words, a.shots, a.seed)
            t0 = time.time()
            tensor_family = tensorqrom.build_family(words, brot=brot, j=J, lowbits=4,
                                                    trials=a.trials, jobs=a.jobs)
            row["tensor_build_seconds"] = round(time.time() - t0, 1)
            row["tensor_trials"] = a.trials
            row["tensor"] = measure(f"tensor_shared_J{J}_b{brot}", tensor_family, words, a.shots, a.seed)
            for key in ("ref", "tensor"):
                ang = row[key]["sim_toffoli_fwd_rev"]
                T = ang + heur["toffoli"]
                lay_q = row[key]["qubits_max"] - row[key]["selection_bits"] - J * brot
                Q = heur["persist"] + J * brot + max(heur["temp_max"], lay_q)
                row[key]["T_total"] = float(T)
                row[key]["Q_total"] = int(Q)
                row[key]["TQ"] = float(T) * int(Q)
                row[key]["dTQ_vs_base_pct"] = 100.0 * (float(T) * int(Q) - BASE_TQ) / BASE_TQ
                row[key]["dAngles_vs_8304"] = float(ang) - ANGLES_CURRENT
            log["combos"].append(row)
            for key in ("ref", "tensor"):
                r = row[key]
                print(f"J={J} brot={brot} {key}: angles={r['sim_toffoli_fwd_rev']:.1f} "
                      f"(static {r['static_sum_max_magic']}, qmax {r['qubits_max']}) "
                      f"T={r['T_total']:.1f} Q={r['Q_total']} TQ={r['TQ']:.1f} "
                      f"({r['dTQ_vs_base_pct']:+.2f}%) match={r['words_match']}", flush=True)

    log["base"] = {"T": BASE_T, "Q": BASE_Q, "TQ": BASE_TQ, "angles": ANGLES_CURRENT}
    (out / "j_brot_scan.json").write_text(json.dumps(log, indent=2) + "\n")
    print("wrote " + str(out / "j_brot_scan.json"))


if __name__ == "__main__":
    main()
