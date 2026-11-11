"""Re-quantize the 8-bit ANGLE words to 7 bits and evaluate the official metrics.

No circuit is built: this probes only whether the 7-bit word table can meet the
20 mHa gates.  ``evaluate_words`` uses the same official arithmetic as the
verifier, with ``brot=7`` and the same Givens tree.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "data/competition/verifiers"))

from dfthcsos.verify import evaluate_words, load_inputs  # noqa: E402

DEFAULT = WT.parents[1] / "artifacts/20261111_grimoire33/candidate/dfthcsos"


def report(name, words7, inputs, tree):
    m = evaluate_words(inputs, words7, tree, 7)
    print(
        f"{name:8s} e1={m['error_1']:.6f} Ha ({1000 * m['error_1']:.3f} mHa) "
        f"e2={m['error_2']:.6f} Ha ({1000 * m['error_2']:.3f} mHa) "
        f"Lambda={m['Lambda']:.6f} E_gap={m['E_gap']:.9f} "
        f"lambda_eff={m['lambda_eff']:.6f}"
    )
    return m


def main() -> None:
    directory = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    sub = np.load(directory / "submission.npz")
    words = np.asarray(sub["angle_words"])
    tree = np.asarray(sub["tree_edges"])
    inputs = load_inputs(directory / "submission.npz")
    print(f"8-bit words {words.shape}, range {words.min()}..{words.max()}, "
          f"{len(np.unique(words))} levels")
    m8 = evaluate_words(inputs, words, tree, 8)
    print(f"8bit     e1={m8['error_1']:.9f} Ha e2={m8['error_2']:.9f} Ha "
          f"lambda_eff={m8['lambda_eff']:.9f}")
    for name, w7 in (
        ("nearest", np.clip((words + 1) // 2, 0, 127)),
        ("floor", np.clip(words // 2, 0, 127)),
    ):
        report(name, w7, inputs, tree)
    # T estimate: the 215 load CCX are the 40 data bits of a loader; 75
    # prefix/setup CCX are width-independent.  beta=7 also drops Givens T.
    print("T estimate: loads 215 -> 215*35/40 = 188 (-27/loader); "
          "15*2*(-27) = -810 T; Givens 2250 -> 1950 (-300 T); "
          "T 14908 -> 13798 (-7.45%)")


if __name__ == "__main__":
    main()
