"""Measure tensorqrom's loader T on a 1,156-row signed-gauge table (cost estimate only)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "artifacts/20261111_r3_probe/lera_pipeline/dfthc_refit"))
sys.path.insert(0, str(WT / "data/competition/verifiers"))

from tensorqrom import build_family  # noqa: E402
from onebody import signed_gauge  # noqa: E402
from dfthcsos.scoreinfra.circuits import circuit_costs, recover_words_from_circuits  # noqa: E402


def main() -> None:
    base = np.load(WT.parents[1] / "artifacts/20261111_grimoire33/candidate/dfthcsos/submission.npz")
    words = np.asarray(base["angle_words"])[:1156]
    tree = np.asarray(base["tree_edges"], np.int64)
    words = signed_gauge(words, tree, 8)
    print("table", words.shape,
          "signed", np.array_equal((words >> 7) & 1, (words >> 6) & 1), flush=True)
    t0 = time.time()
    fam = build_family(words, 8, j=5, lowbits=4, trials=1, jobs=1)
    print("build_s", round(time.time() - t0, 1), flush=True)
    cc = circuit_costs(fam)
    static = sum(c["max_magic"] for c in cc)
    print("n", len(fam), "static/pass", static, "fwd_rev", 2 * static,
          "qmax", max(c["num_qubits"] for c in cc),
          "per", [c["max_magic"] for c in cc], flush=True)
    w, lay, tof = recover_words_from_circuits(
        fam, num_vectors=1156, num_angles=75, shots_per_address=2, seed=20261111)
    print("words_match", np.array_equal(w, words), "tof", tof, flush=True)


if __name__ == "__main__":
    main()
