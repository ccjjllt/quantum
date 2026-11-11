"""Lera (8,143,44) build static recompute (no verify.py call).

Source: Kaggle dataset marculera/dfthc-c44-build (kernel
marculera/df-thc-11-2x-codes-on-the-xor-of-five-words), copied byte-identical
to artifacts/20261111_lera11x/. Compares every static term against P0
(experiments/dfthcsos/20261110_p0_gauge, score 299497670.48).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

EXP = Path(__file__).resolve().parent
WORKTREE = EXP.parents[2]
ART = WORKTREE / "artifacts" / "20261111_lera11x"
sys.path.insert(0, str(WORKTREE / "data" / "competition" / "verifiers"))

from dfthcsos.scoreinfra.circuits import (  # noqa: E402
    circuit_costs,
    load_circuits,
    recover_words_from_circuits,
    register_layout,
)
from dfthcsos.verify import evaluate_words, heuristic_costs, load_inputs  # noqa: E402


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def main() -> None:
    files = ["submission.npz"] + [f"angle_k_{k}.kmb" for k in range(15)]
    shas = {f: sha256_file(ART / f) for f in files}
    sub = np.load(ART / "submission.npz")
    print("npz keys:", list(sub.files))
    for k in sub.files:
        a = np.asarray(sub[k])
        print(f"  {k}: shape={a.shape} dtype={a.dtype}")
    words = np.asarray(sub["angle_words"])
    tree = np.asarray(sub["tree_edges"])
    print(f"n_words={len(words)} word_len={words.shape[1]}")

    # 1. Official word metrics (exact, no shots).
    inp = load_inputs(str(ART / "submission.npz"))
    m = evaluate_words(inp, words, tree, 8)
    for k in ("error_1", "error_2", "Lambda", "E_SOS", "E_gap", "lambda_eff", "gap_in_domain"):
        print(f"  {k} = {m[k]!r}")
    print(f"  error_1_mHa = {float(m['error_1']) * 1000:.6f}")
    print(f"  error_2_mHa = {float(m['error_2']) * 1000:.6f}")
    lam = float(m["lambda_eff"])

    # 2. Loader metrology: words_match + angles + static + qubits.
    fam = load_circuits(ART)
    lay = register_layout(fam)
    w, _, tof = recover_words_from_circuits(
        fam, num_vectors=len(words), num_angles=words.shape[1],
        shots_per_address=2, seed=20261111)
    ok = bool(np.array_equal(w, words))
    cc = circuit_costs(fam)
    static = int(sum(c["max_magic"] for c in cc))
    qmax = int(max(c["num_qubits"] for c in cc))
    per_loader_tof = [int(c.get("toffoli", -1)) if "toffoli" in c else None for c in cc]
    print(f"words_match={ok} sim_toffoli_fwd_rev={tof} static_sum={static} qubits_max={qmax}")
    print(f"selection_size={len(lay.selection)}")
    print("circuit_costs keys per loader:", sorted(cc[0].keys()))
    print("per-loader:", [(c.get("toffoli"), c.get("num_qubits"), c.get("max_magic")) for c in cc])

    # 3. Heuristic costs + T/Q/score (same formula as P0 assemble.py).
    hc = heuristic_costs(76, 8, 143, 44, 8)
    print("heuristic_costs:", {k: hc[k] for k in hc})
    heur = int(hc["toffoli"])
    T = float(tof) + heur
    sel = len(lay.selection)
    temp = qmax - sel - 5 * 8
    Q = int(hc["persistent_qubits"]) + 5 * 8 + max(int(hc["temporary_qubits"]), temp)
    pred = lam * T * Q
    print(f"T_angles_fwd_rev={tof} T_heur={heur} T={T} Q={Q} lambda_eff={lam:.10f}")
    print(f"pred_score={pred:.4f} (= {pred:.6e})")
    print(f"vs P0 299497670.4814: delta={pred - 299497670.4814:+.4f}")

    out = {
        "file_sha256": shas,
        "npz_shapes": {k: list(np.asarray(sub[k]).shape) for k in sub.files},
        "metrics": {k: (float(m[k]) if isinstance(m[k], (float, np.floating)) else m[k])
                    for k in ("error_1", "error_2", "Lambda", "E_SOS", "E_gap",
                              "lambda_eff", "gap_in_domain")},
        "words_match_shots2": ok,
        "sim_toffoli_fwd_rev": float(tof),
        "static_sum": static,
        "qubits_max": qmax,
        "selection_size": sel,
        "heuristic": {k: (int(hc[k]) if isinstance(hc[k], (int, np.integer)) else hc[k]) for k in hc},
        "T_total": float(T),
        "Q_total": int(Q),
        "predicted_score": float(pred),
    }
    (ART / "static_metrics.json").write_text(json.dumps(out, indent=2) + "\n")
    print("wrote", ART / "static_metrics.json")


if __name__ == "__main__":
    main()
