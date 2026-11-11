"""Static recompute of one chemistry family: metrics, words, Toffoli, T/Q/score.

Official functions only (``evaluate_words``, ``recover_words_from_circuits``,
``heuristic_costs``); no ``verify.py`` call.  The directory must contain
``submission.npz`` and ``angle_k_*.kmb`` (for the prefixed Heliosli files use a
directory of symlinks with the standard names).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "data/competition/verifiers"))

from dfthcsos.scoreinfra.circuits import (  # noqa: E402
    circuit_costs,
    load_circuits,
    recover_words_from_circuits,
    register_layout,
)
from dfthcsos.verify import evaluate_words, heuristic_costs, load_inputs  # noqa: E402

SCORE_BASE = 298600061.555139


def main() -> None:
    directory = Path(sys.argv[1])
    sub = np.load(directory / "submission.npz")
    words = np.asarray(sub["angle_words"])
    tree = np.asarray(sub["tree_edges"])
    inputs = load_inputs(directory / "submission.npz")
    m = evaluate_words(inputs, words, tree, 8)
    print(f"e1={m['error_1']:.9f} Ha ({1000 * m['error_1']:.6f} mHa) "
          f"e2={m['error_2']:.9f} Ha ({1000 * m['error_2']:.6f} mHa)")
    print(f"Lambda={m['Lambda']:.12f} E_gap={m['E_gap']:.12f} "
          f"lambda_eff={m['lambda_eff']:.12f}")
    fam = load_circuits(directory)
    layout = register_layout(fam)
    w, _, tof = recover_words_from_circuits(
        fam, num_vectors=len(words), num_angles=words.shape[1],
        shots_per_address=2, seed=20261111,
    )
    cc = circuit_costs(fam)
    qmax = max(c["num_qubits"] for c in cc)
    print(f"words_match={np.array_equal(w, words)} angles_tof={tof} "
          f"static_sum={sum(c['max_magic'] for c in cc)} qubits_max={qmax}")
    print("per-loader static:", [c["max_magic"] for c in cc])
    h = heuristic_costs(76, 8, 143, 44, 8)
    temp = qmax - len(layout.selection) - 40
    Q = h["persistent_qubits"] + 40 + max(h["temporary_qubits"], temp)
    T = tof + h["toffoli"]
    score = float(m["lambda_eff"]) * T * Q
    print(f"T={T:.1f} Q={Q} score={score:.6f} vs baseline={score - SCORE_BASE:+.3f}")


if __name__ == "__main__":
    main()
