"""Estimate tensorqrom T on a B=135-like selection (135 bases per rho) of the baseline table."""
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
from dfthcsos.scoreinfra.circuits import circuit_costs  # noqa: E402


def main() -> None:
    base = np.load(WT.parents[1] / "artifacts/20261111_grimoire33/candidate/dfthcsos/submission.npz")
    words = np.asarray(base["angle_words"])
    tree = np.asarray(base["tree_edges"], np.int64)
    W = np.asarray(base["W"], np.float64)
    imp = np.linalg.norm(W, axis=2)
    keep = np.argsort(-imp, axis=1)[:, :135]
    rows = [np.arange(76)]
    for r in range(8):
        rows.append(76 + r * 143 + keep[r])
    idx = np.concatenate(rows)
    tab = signed_gauge(words[idx], tree, 8)
    print("table", tab.shape, "signed", np.array_equal((tab >> 7) & 1, (tab >> 6) & 1), flush=True)
    t0 = time.time()
    fam = build_family(tab, 8, j=5, lowbits=4, trials=2, jobs=2)
    print("build_s", round(time.time() - t0, 1), flush=True)
    cc = circuit_costs(fam)
    static = sum(c["max_magic"] for c in cc)
    print("static/pass", static, "fwd_rev", 2 * static,
          "per", [c["max_magic"] for c in cc], flush=True)


if __name__ == "__main__":
    main()
