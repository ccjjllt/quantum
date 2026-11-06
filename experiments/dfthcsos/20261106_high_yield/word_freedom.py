"""Manual exact-zero branch freedom census; numerical metrics only, no circuits.

For a rooted Givens tree, an angle whose parent has zero amplitude acts on two
zero entries and can be changed arbitrarily. Keep coded bit0 and gauge bits6/7
to expose safe bit1..5 freedom in the current public representation.
"""
from pathlib import Path
import json
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiments/dfthcsos/20261106_syed_v9"))
from analyze import read_params, inputs
from dfthcsos.verify import evaluate_words, passes_accuracy
from dfthcsos.scoreinfra.reference import load_reference, PACKAGED_FCIDUMP
from dfthcsos.scoreinfra.dfthc_math import reconstruct_u_vectors


def main():
    start = time.monotonic()
    out = ROOT / "artifacts/20261106_high_yield/word_freedom"
    out.mkdir(parents=True, exist_ok=True)
    p = read_params()
    words = np.load(ROOT / "artifacts/20261106_syed_v9/dfthcsos/recovered_words.npy")
    alive = np.zeros((len(words), 76), dtype=bool)
    alive[:, 0] = True
    free = np.zeros_like(words, dtype=bool)
    for j, (parent, child) in enumerate(p["tree_edges"]):
        parent, child = int(parent), int(child)
        if alive[:, child].any():
            raise ValueError("not a rooted parent-before-child tree")
        before = alive[:, parent].copy()
        free[:, j] = ~before
        alive[:, parent] = before & (words[:, j] % 128 != 64)
        alive[:, child] = before & (words[:, j] % 128 != 0)
    modified = words.copy()
    modified[free] &= ~62
    ref = load_reference(PACKAGED_FCIDUMP)
    inp = inputs(p, ref)
    baseline = evaluate_words(inp, words, p["tree_edges"], 8)
    metrics = evaluate_words(inp, modified, p["tree_edges"], 8)
    u = reconstruct_u_vectors(words / 128.0, p["tree_edges"])
    v = reconstruct_u_vectors(modified / 128.0, p["tree_edges"])
    np.save(out / "inactive_angle_mask.npy", free)
    np.save(out / "zeroed_words.npy", modified)
    result = {
        "scope": "Exact-zero support census and a physical word-table probe. No synthesized loader, cost reduction, phase verification or full official validation.",
        "inactive_angles": int(free.sum()),
        "total_angles": int(free.size),
        "bit1_to_bit5_free_coordinates": int(5 * free.sum()),
        "inactive_angles_by_batch": [int(free[:, 5*k:5*k+5].sum()) for k in range(15)],
        "inactive_angles_one_body": int(free[:76].sum()),
        "inactive_angles_two_body": int(free[76:].sum()),
        "changed_words_when_zeroing_bits1_to5": int((words != modified).sum()),
        "max_abs_decoded_vector_difference": float(np.max(np.abs(u-v))),
        "coded_bit0_unchanged": bool(np.array_equal(words & 1, modified & 1)),
        "gauge_bits_unchanged": bool(np.array_equal(words & 192, modified & 192)),
        "baseline": baseline,
        "zeroing_probe_metrics": metrics,
        "zeroing_probe_math_accuracy_pass": bool(passes_accuracy(metrics)),
        "next_action": "Use the exact mask as don't-care variables in smaller-W or low-rank word-table synthesis. Zeroing is an invariance demonstration, not an optimization result.",
        "elapsed_s": time.monotonic() - start,
    }
    (out / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
