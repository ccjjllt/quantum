"""Manual diagnostics: relaxed PSD-rank bound and 7-bit rounding of Syed V9.

No candidate circuits are generated and no full official verifier is run.
The symmetric-pair basis is orthonormal, preserving the full N^4 Frobenius norm.
"""
from pathlib import Path
import json
import sys
import time

import numpy as np
from scipy.linalg import eigvalsh

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiments/dfthcsos/20261106_syed_v9"))
from analyze import read_params, inputs
from dfthcsos.scoreinfra.reference import load_reference, PACKAGED_FCIDUMP
from dfthcsos.scoreinfra.dfthc_math import reconstruct_u_vectors, reconstruct_x, build_h1_prime, lambda_h2
from dfthcsos.verify import evaluate_words, passes_accuracy

OUT = ROOT / "artifacts/20261106_high_yield/numerical"


def main():
    start = time.monotonic()
    OUT.mkdir(parents=True, exist_ok=True)
    p = read_params()
    words = np.load(ROOT / "artifacts/20261106_syed_v9/dfthcsos/recovered_words.npy")
    ref = load_reference(PACKAGED_FCIDUMP)
    inp = inputs(p, ref)
    baseline = evaluate_words(inp, words, p["tree_edges"], 8)
    n = ref["orbitals"]
    row, col = np.tril_indices(n)
    multiplicity = np.where(row == col, 1.0, np.sqrt(2.0))
    s = inp.S[row, col] * multiplicity
    ident = (row == col).astype(float)
    target = ref["tei"][row[:, None], col[:, None], row[None, :], col[None, :]]
    target *= multiplicity[:, None] * multiplicity[None, :]
    target += 0.5 * (np.outer(s, ident) + np.outer(ident, s))
    symmetry_error = float(np.max(np.abs(target - target.T)))
    vectors = reconstruct_u_vectors(words / 128.0, p["tree_edges"])
    x = reconstruct_x(vectors[n:].reshape(8, 143, n), inp.w)
    factors = (x[:, :, row, col] * multiplicity).reshape(352, -1)
    packed_residual = float(np.linalg.norm(factors.T @ factors - target))
    # An independent representation check, not a test file or validation gate.
    representation_difference = abs(packed_residual - baseline["error_2"])
    eigenvalues = eigvalsh(target, check_finite=True, driver="evr")
    np.save(OUT / "shifted_target_eigenvalues.npy", eigenvalues)
    positive = eigenvalues[eigenvalues > 0][::-1]
    negative_squared = float(np.sum(eigenvalues[eigenvalues < 0] ** 2))
    positive_tail_squared = np.r_[np.cumsum((positive**2)[::-1])[::-1], 0.0]
    errors = np.sqrt(negative_squared + positive_tail_squared)
    feasible = np.flatnonzero(errors <= 0.020)
    ranks = [128, 192, 224, 256, 280, 288, 289, 290, 294, 296, 304, 312, 320, 328, 336, 344, 352, 360]
    bounds = {
        "definition": "Minimum Frobenius error over all PSD matrices of rank <= k; a necessary, not sufficient, condition for an R*C=k DFTHC factorization.",
        "matrix_dimension": len(row),
        "symmetry_max_abs": symmetry_error,
        "packed_baseline_error_2": packed_residual,
        "packed_vs_official_error_2_abs_difference": representation_difference,
        "irreducible_negative_spectrum_error": float(np.sqrt(negative_squared)),
        "positive_eigenvalue_count": len(positive),
        "negative_eigenvalue_count": int((eigenvalues < 0).sum()),
        "minimum_relaxed_psd_rank_at_20mHa": int(feasible[0]) if len(feasible) else None,
        "rank_error_bounds_Ha": {str(k): float(errors[min(k, len(positive))]) for k in ranks},
        "scope": "Ignores shared rank-one u_b basis, L1 normalization, SOS gap, one-body error, angle quantization and circuit synthesis; cannot establish feasibility.",
    }
    print(json.dumps({"rank_bound": bounds}), flush=True)
    rounded = {}
    choices = {
        "floor": words // 2,
        "nearest_ties_even": np.rint(words / 2.0).astype(np.int64) % 128,
        "ceil": ((words + 1) // 2) % 128,
    }
    for name, w7 in choices.items():
        metrics = evaluate_words(inp, w7, p["tree_edges"], 7)
        rounded[name] = {"metrics": metrics, "math_accuracy_pass": bool(passes_accuracy(metrics))}
    # Isolate one-body and two-body quantization effects at the same 8-bit layout.
    for name, subset in (("one_body_only", slice(0, n)), ("two_body_only", slice(n, None))):
        w8 = words.copy()
        w8[subset] = 2 * choices["nearest_ties_even"][subset]
        metrics = evaluate_words(inp, w8, p["tree_edges"], 8)
        rounded[name] = {"metrics": metrics, "math_accuracy_pass": bool(passes_accuracy(metrics))}
    h1 = build_h1_prime(ref["h1_thc"], inp.S, inp.beta_1, ref["electrons"], inp.W, x)
    lam1 = float(np.abs(np.linalg.eigvalsh(h1)).sum())
    lam2 = lambda_h2(inp.w, inp.W)
    nuclear = np.abs(np.linalg.eigvalsh(x)).sum(axis=-1)
    coefficient_l1 = np.abs(inp.w).sum(axis=1)
    relaxed_lam2 = float(0.25 * np.sum((np.abs(p["H2_I"]) + nuclear) ** 2))
    gap = baseline["E_gap"]
    relaxed_eff = float(np.sqrt(gap * (2 * (lam1 + relaxed_lam2) - gap)))
    lower_gap_eff = float(np.sqrt(3.914898 * (2 * baseline["Lambda"] - 3.914898)))
    normalization = {
        "lambda_h1": lam1,
        "lambda_h2": lam2,
        "same_X_nuclear_relaxation_lambda_h2": relaxed_lam2,
        "same_X_nuclear_relaxation_lambda_eff": relaxed_eff,
        "relative_lambda_eff_reduction_in_relaxation": 1 - relaxed_eff / baseline["lambda_eff"],
        "coefficient_l1_over_nuclear_min_median_max": [float(v) for v in
            (np.min(coefficient_l1 / nuclear), np.median(coefficient_l1 / nuclear), np.max(coefficient_l1 / nuclear))],
        "max_relative_lambda_eff_gain_from_gap_to_strict_floor_limit": 1 - lower_gap_eff / baseline["lambda_eff"],
        "scope": "Hold each physical X and its native offset W fixed. Nuclear norms relax the requirement that all columns in rho share B rank-one vectors. They measure basis-induced L1 overhead, not an attainable candidate or a bound across different X/offset families. Gap-floor value is only a limiting infimum.",
    }
    out = {
        "scope": "Local numerical research only; no circuit candidate, no full official validation, no leaderboard score.",
        "source": "Fixed Syed V9/run366109544 words and official fixed-shift FeMoCo76o113e tensors.",
        "baseline": baseline,
        "psd_rank_bound": bounds,
        "seven_bit_rounding": rounded,
        "normalization_diagnostics": normalization,
        "fraction_odd_words": float(np.mean(words % 2)),
        "elapsed_s": time.monotonic() - start,
    }
    (OUT / "bounds.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2), flush=True)


if __name__ == "__main__":
    main()
