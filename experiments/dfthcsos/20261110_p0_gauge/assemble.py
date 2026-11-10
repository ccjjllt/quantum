"""P0 step3: assemble candidate (b9 weights + flipped words/U + loaders) and pre-verify metrology.

Loader provenance: the new word table is bit-identical to gengsr's published
table, so gengsr's published loaders (main-repo release dir, read-only) are the
correct loaders for these exact words. A direct tensorqrom rebuild is not
possible on this table (signed-gauge assertion; see README §3), and naive
signed re-encoding breaks the refined error cancellation (e2 318 mHa). This
script copies the identical-table loaders, assembles submission.npz, and checks
words_match + static costs + predicted T/Q/score. Official 78k-shot validation
is run separately via scripts/manual_verify.py (once).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np

WORKTREE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WORKTREE / "data" / "competition" / "verifiers"))

from dfthcsos.scoreinfra.circuits import (  # noqa: E402
    circuit_costs,
    load_circuits,
    recover_words_from_circuits,
    register_layout,
)
from dfthcsos.verify import heuristic_costs, load_inputs  # noqa: E402

MAIN_REPO = Path("/Users/zhaohuaxiang/ccjjllt/quantum")
GENGSR_DIR = MAIN_REPO / "artifacts/20261110_gengsr_252268/release/dfthcsos"
B9 = WORKTREE / "artifacts/20261108_public_frontier/dfthcsos_refit/submission.npz"
OUT = WORKTREE / "artifacts/20261110_p0_gauge"
CAND = OUT / "candidate"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def main() -> None:
    CAND.mkdir(parents=True, exist_ok=True)
    new_words = np.load(OUT / "new_angle_words.npy")
    new_U = np.load(OUT / "new_U.npy")
    b9 = np.load(B9)

    # 1. Copy the 15 loaders for the identical word table (read-only source).
    loader_shas = {}
    for k in range(15):
        src = GENGSR_DIR / f"angle_k_{k}.kmb"
        dst = CAND / f"angle_k_{k}.kmb"
        shutil.copyfile(src, dst)
        loader_shas[f"angle_k_{k}.kmb"] = sha256_file(dst)

    # 2. Assemble submission.npz: b9 weights, flipped U/words, same tree/shifts.
    sub = {
        "U": np.asarray(new_U),
        "W": np.asarray(b9["W"]),
        "H2_I": np.asarray(b9["H2_I"]),
        "H1_I": np.asarray(b9["H1_I"]),
        "Hsym_lower": np.asarray(b9["Hsym_lower"]),
        "tree_edges": np.asarray(b9["tree_edges"]),
        "angle_words": np.asarray(new_words),
    }
    np.savez(CAND / "submission.npz", **sub)
    npz_sha = sha256_file(CAND / "submission.npz")

    # 3. Metrology on the copied loaders: words_match + static + T/Q prediction.
    fam = load_circuits(CAND)
    lay = register_layout(fam)
    w, _, tof = recover_words_from_circuits(
        fam, num_vectors=len(new_words), num_angles=75,
        shots_per_address=2, seed=20261110)
    ok = bool(np.array_equal(w, new_words))
    cc = circuit_costs(fam)
    static = int(sum(c["max_magic"] for c in cc))
    qmax = int(max(c["num_qubits"] for c in cc))
    sel = len(lay.selection)
    hc = heuristic_costs(76, 8, 143, 44, 8)
    heur = int(hc["toffoli"])
    T = float(tof) + heur
    temp = qmax - sel - 5 * 8
    Q = int(hc["persistent_qubits"]) + 5 * 8 + max(int(hc["temporary_qubits"]), temp)
    inp = load_inputs(str(CAND / "submission.npz"))
    from dfthcsos.verify import evaluate_words
    m = evaluate_words(inp, new_words, np.asarray(sub["tree_edges"]), 8)
    lam = float(m["lambda_eff"])
    pred_score = lam * T * Q
    print(f"words_match={ok} sim_toffoli={tof} static={static} qubits_max={qmax} sel={sel}")
    print(f"T={T} Q={Q} lambda_eff={lam:.15f} pred_score={pred_score:.4f}")
    print(f"metrics e1={float(m['error_1']):.17f} e2={float(m['error_2']):.17f} "
          f"E_gap={float(m['E_gap']):.12f} Lambda={float(m['Lambda']):.11f}")

    manifest = {
        "provenance": {
            "weights_W_H2": "b9eced3e (worktree artifacts/20261108_public_frontier/dfthcsos_refit/submission.npz)",
            "words_U": "gengsr 252268 release table (bit-identical to b9 words + 303 flips + 382 don't-care variants)",
            "loaders": "copied bytes from main-repo artifacts/20261110_gengsr_252268/release/dfthcsos/angle_k_*.kmb",
            "loader_origin": "gengsr lb-25-2268-shifter-46-own-chemistry-loaders v1 "
                             "(references/public-baseline.json); planner unknown externally",
        },
        "candidate_npz_sha256": npz_sha,
        "loader_sha256": loader_shas,
        "metrology_shots_per_address": 2,
        "words_match": ok,
        "sim_toffoli_fwd_rev": float(tof),
        "static_sum": static,
        "qubits_max": qmax,
        "T_total": float(T),
        "Q_total": int(Q),
        "lambda_eff": lam,
        "predicted_score": float(pred_score),
        "metrics": {k: (float(m[k]) if isinstance(m[k], float) else m[k])
                    for k in ("error_1", "error_2", "Lambda", "E_SOS", "E_gap",
                              "lambda_eff", "gap_in_domain")},
    }
    (OUT / "candidate_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("wrote", CAND / "submission.npz", npz_sha[:16])


if __name__ == "__main__":
    main()
