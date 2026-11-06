"""Read Syed V9 plans using reviewed public dfthc_refit 1.7.0 symbolic reader.

Scope: exact Boolean terms on real addresses; this reader ignores CZ/HMR phase,
so this is not a phase proof, re-emission check, or full official validation.
"""
from pathlib import Path
import hashlib
import json
import sys
import time

import kickmix
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "artifacts/20261106_high_yield/public/dfthc_refit_1.7.0"
sys.path.insert(0, str(SOURCE))
import recover
import gauge


def main():
    start = time.monotonic()
    out = ROOT / "artifacts/20261106_high_yield/recovered_plans"
    out.mkdir(parents=True, exist_ok=True)
    words = np.load(ROOT / "artifacts/20261106_syed_v9/dfthcsos/recovered_words.npy")
    base = ROOT / "artifacts/20261106_syed_v9/release/dfthcsos"
    summary = []
    for k in range(15):
        try:
            gin = gauge.slot_gauge(words, k)[0]
            report, rec, padded, _ = recover.recover_loader(
                kickmix, base / f"angle_k_{k}.kmb", words, k, gauge_in=gin
            )
            report["terms"] = [list(map(int, t)) for t in rec["terms"]]
            (out / f"k{k}.json").write_text(json.dumps(report, indent=2) + "\n")
            np.save(out / f"k{k}_padded_delta.npy", padded)
            st = report["structure"]
            row = {"k": k, "toffolis": report["num_toffoli_like"],
                   "qubits": report["num_qubits"], "products": report["products"],
                   "caches": report["caches"], "low_caches": report["low_caches"],
                   "function_ok": report["recovered_equals_delta_on_rows"],
                   "dimW": st["dimW"], "fixed_feature_space_pair_bound": st["lower_bound_pairs"],
                   "low_partition": st["low_partition"], "pairing": st["pairing"],
                   "output_sharing": st["output_sharing"]}
        except (ValueError, AssertionError, KeyError) as exc:
            row = {"k": k, "error": f"{type(exc).__name__}: {exc}"}
        summary.append(row)
        print(json.dumps(row), flush=True)
    result = {
        "scope": "Symbolic Boolean recovery only. No phase proof, no full verifier, no new circuit or cost gain.",
        "source": "manwithacat/dfthc-refit V5, dfthc_refit 1.7.0, Apache-2.0; upstream credits preserved in public source snapshot.",
        "source_sha256": {f: hashlib.sha256((SOURCE / f).read_bytes()).hexdigest()
                          for f in ("recover.py", "gauge.py", "dfthc_refit.py")},
        "slots": summary,
        "elapsed_s": time.monotonic() - start,
    }
    (out / "summary.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
