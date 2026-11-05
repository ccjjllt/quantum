"""Small numerical rejection probes on Maoxin V2 words; no new circuits."""
import json
from pathlib import Path
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data/competition/verifiers"))
from dfthcsos.verify import SubmissionInputs, native_inputs, evaluate_words, passes_accuracy
from dfthcsos.scoreinfra.reference import load_reference, PACKAGED_FCIDUMP, PACKAGED_FIXED_SHIFTS, UPPER_ENERGY

BASE = ROOT / "artifacts/20261105_maoxin_v2/release/dfthcsos"
OUT = ROOT / "artifacts/20261105_maoxin_v2/dfthcsos"


def main():
    start = time.monotonic()
    with np.load(BASE / "submission.npz", allow_pickle=False) as z:
        params = {k: np.array(z[k]) for k in z.files}
    with np.load(PACKAGED_FIXED_SHIFTS, allow_pickle=False) as z:
        params.update({k: np.array(z[k]) for k in ("H1_I", "Hsym_lower")})
    words = np.load(OUT / "recovered_words.npy")
    ref = load_reference(PACKAGED_FCIDUMP)
    w, W, S, beta = native_inputs(params)
    rows = []
    for scale in (1 - 1e-7, 1 - 1e-8, 1.0, 1 + 1e-8, 1 + 1e-7):
        inp = SubmissionInputs(None, params, ref, w * scale, W * scale, S, beta, UPPER_ENERGY)
        m = evaluate_words(inp, words, params["tree_edges"], 8)
        rows.append({"kind": "joint_native_weight_scale", "scale": scale,
                     "metrics": m, "math_accuracy_pass": bool(passes_accuracy(m))})
    inp = SubmissionInputs(None, params, ref, w, W, S, beta, UPPER_ENERGY)
    for mode, reduced in (("floor", words // 2), ("nearest_even", np.rint(words / 2).astype(np.int64) % 128)):
        m = evaluate_words(inp, reduced, params["tree_edges"], 7)
        rows.append({"kind": "naive_7bit_words", "rounding": mode,
                     "metrics": m, "math_accuracy_pass": bool(passes_accuracy(m))})
    result = {"scope": "Numerical function evaluations only, using prior one-shot recovered words; no loader construction or official complete validation",
              "hash_matching_performed": False, "rows": rows, "seconds": time.monotonic() - start}
    (OUT / "parameter_probes.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
