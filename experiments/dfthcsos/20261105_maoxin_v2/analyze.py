"""Manual Maoxin V2 chemistry audit: reduced-shot words, metrics and cost scenarios.

No full verifier, hash matching, downloaded executable, or candidate mutation.
"""
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data/competition/verifiers"))
from dfthcsos.verify import (SubmissionInputs, native_inputs, evaluate_words,
                            heuristic_costs, resource_costs, passes_accuracy)
from dfthcsos.scoreinfra.reference import load_reference, PACKAGED_FCIDUMP, PACKAGED_FIXED_SHIFTS, UPPER_ENERGY
from dfthcsos.scoreinfra.circuits import load_circuits, circuit_costs, recover_words_from_circuits
from dfthcsos.scoreinfra.dfthc_math import reconstruct_u_vectors

BASE = ROOT / "artifacts/20261105_maoxin_v2/release/dfthcsos"
OUT = ROOT / "artifacts/20261105_maoxin_v2/dfthcsos"
SRC = OUT / "sources/atakan_static/datasets/qcc-pi-gauge-carry-padding-v3"


def rank(rows):
    pivots = {}
    for value in rows:
        value = int(value)
        while value:
            p = value.bit_length() - 1
            if p not in pivots:
                pivots[p] = value
                break
            value ^= pivots[p]
    return len(pivots)


def xor_rows(rows, mask):
    out = 0
    for j, row in enumerate(rows):
        if mask >> j & 1:
            out ^= int(row)
    return out


def block_anf(words):
    batches = words.reshape(1220, 15, 5)
    delta = batches.copy()
    delta[:, 1:] ^= batches[:, :-1]
    bits = ((delta[:1216].reshape(76, 16, 15, 5)[..., None] >> np.arange(8)) & 1).astype(np.uint8)
    for bit in range(4):
        for mask in range(16):
            if mask >> bit & 1:
                bits[:, mask] ^= bits[:, mask ^ (1 << bit)]
    nonlinear = bits[:, [m for m in range(16) if m.bit_count() > 1]].sum(axis=1)
    return [{"k": k, "affine_fraction_per_bit": np.mean(nonlinear[:, k] == 0, axis=(0, 1)).tolist(),
             "nonlinear_coefficients": int(nonlinear[:, k].sum())} for k in range(15)]


def main():
    start = time.monotonic()
    OUT.mkdir(parents=True, exist_ok=True)
    with np.load(BASE / "submission.npz", allow_pickle=False) as data:
        params = {k: np.array(data[k]) for k in data.files}
    circuits = load_circuits(BASE)
    static = circuit_costs(circuits)
    for row, circuit in zip(static, circuits):
        row["operation_counts"] = dict(circuit.operation_statistics())
        row["conditioned_paid_lines"] = sum(
            line.startswith(("CCX ", "CCZ ", "CSWAP ")) and " if " in line
            for line in str(circuit).splitlines())
    before = time.monotonic()
    words, layout, angles_t = recover_words_from_circuits(
        circuits, num_vectors=1220, num_angles=75, shots_per_address=1, seed=20261105)
    recovery = {"scope": "1220 addresses, one shot/address, full forward/reverse loader traversal; not default 64 shots/address",
                "seed": 20261105, "shots_per_address": 1, "total_shots": 1220,
                "npz_words_equal_recovered": bool(np.array_equal(params["angle_words"], words)),
                "angles_double_pass_toffoli": angles_t, "seconds": time.monotonic() - before}
    if not recovery["npz_words_equal_recovered"]:
        raise ValueError("Recovered words differ from NPZ words")
    np.save(OUT / "recovered_words.npy", words)
    print(json.dumps({"recovery": recovery}), flush=True)

    # Read packaged official arrays directly: no check_fcidump/load_fixed_shifts
    # hash wrapper, and no modifications to any official file or function.
    with np.load(PACKAGED_FIXED_SHIFTS, allow_pickle=False) as fixed:
        params.update({k: np.array(fixed[k]) for k in ("H1_I", "Hsym_lower")})
    ref = load_reference(PACKAGED_FCIDUMP)
    w, W, S, beta_1 = native_inputs(params)
    inputs = SubmissionInputs(BASE / "submission.npz", params, ref, w, W, S, beta_1, UPPER_ENERGY)
    metrics = evaluate_words(inputs, words, params["tree_edges"], layout.brot)
    resource = resource_costs(inputs, circuits, layout.brot, angles_t)
    cost = metrics["lambda_eff"] * resource["toffoli"] * resource["qubits"]
    R, B, C = w.shape
    N = inputs.num_orbitals
    margins = {"error_1_microHa": (0.020 - metrics["error_1"]) * 1e6,
               "error_2_microHa": (0.020 - metrics["error_2"]) * 1e6,
               "E_gap_floor_microHa": (metrics["E_gap"] - 3.914898) * 1e6,
               "Lambda_floor": metrics["Lambda"] - 49.0}
    print(json.dumps({"metrics": metrics, "resources": resource, "cost": cost, "margins": margins}), flush=True)

    def scenario(r=R, b=B, c=C, beta=layout.brot, j=layout.batch_size):
        h = heuristic_costs(N, r, b, c, beta)
        # Assumes changed loader workspace stays below the heuristic max.
        q = h["qubits"] + j * beta
        t = h["toffoli"] + angles_t
        ratio = (q * t) / (resource["qubits"] * resource["toffoli"])
        return {"R": r, "B": b, "C": c, "brot": beta, "J": j,
                "Q_if_workspace_fits": q, "T_if_loader_T_unchanged": t,
                "cost_ratio_if_lambda_and_loader_T_unchanged": ratio,
                "break_even_angles_T_if_lambda_unchanged": resource["qubits"] * resource["toffoli"] / q - h["toffoli"],
                "lambda_increase_budget_if_loader_T_unchanged": 1 / ratio - 1}

    design = json.loads((SRC / "design.json").read_text())
    codes = np.array(design["codes"], dtype=np.int64)[design["order"]]
    xs = np.arange(len(words))
    quad_bits = np.stack([((xs & m) == m) for m in (3, 5, 6, 9)], axis=1).astype(np.int64)
    gauge = (quad_bits @ ((codes[:, None] >> np.arange(4)) & 1).T) % 2
    canonical = words ^ (gauge << 7)
    decoded = reconstruct_u_vectors(words / 128.0, params["tree_edges"])
    ungauged = reconstruct_u_vectors(canonical / 128.0, params["tree_edges"])
    signs = np.where(np.sum(decoded * ungauged, axis=1) >= 0, 1, -1)
    gauge_error = float(np.max(np.abs(decoded - signs[:, None] * ungauged)))
    packets = codes.reshape(15, 5).tolist()
    geometry = []
    prev = [0] * 5
    products_total = 0
    for k, current in enumerate(packets):
        same_images = [xor_rows(prev, m) for m in range(32) if xor_rows(prev, m) == xor_rows(current, m)]
        r = rank(same_images)
        d = rank([p ^ q for p, q in zip(prev, current)])
        plan = json.loads((SRC / f"plans/plan_{k}.json").read_text())
        count = len(plan["products"])
        products_total += count
        geometry.append({"k": k, "common_helper_rank": r, "dirty_rank": d,
                         "product_count": count, "predicted_AND": 80 + count - r,
                         "observed_static_AND": static[k]["max_magic"],
                         "predicted_Q": 126 + d, "observed_Q": static[k]["num_qubits"],
                         "padding_completion_present": bool((plan.get("source_report") or {}).get("padding_completion"))})
        prev = current
    paths = {0: 0}
    for j, (a, b) in enumerate(params["tree_edges"]):
        a, b = int(a), int(b)
        if a not in paths or b in paths:
            raise ValueError("Unexpected tree order")
        paths[a] ^= 1 << j
        paths[b] = paths[a]
    constraint_rank = rank([paths[v] ^ paths[0] for v in range(1, 76)])
    helper_sum = sum(x["common_helper_rank"] for x in geometry)
    gauge_report = {
        "scope": "Own GF(2) rank calculations and actual recovered words; source generator not executed",
        "quad_masks": [3, 5, 6, 9],
        "canonical_bit7_equals_bit6": bool(np.all((canonical >> 7) == ((canonical >> 6) & 1))),
        "gauged_bit7_equals_bit6": bool(np.all((words >> 7) == ((words >> 6) & 1))),
        "all_vectors_global_sign_max_abs_error": gauge_error,
        "two_body_global_sign_flips": int(np.sum(signs[76:] == -1)),
        "nominal_U_vs_loaded_abs_max_difference": float(np.max(np.abs(np.abs(params["U"]) - np.abs(decoded[76:].reshape(8, 143, 76))))),
        "physical_pi_gauge_linear_dimension": 75 - constraint_rank,
        "geometry": geometry, "products_per_pass": products_total,
        "common_helpers_per_pass": helper_sum,
        "fixed_four_quad_upper_helpers_per_pass": 14 * 4,
        "fixed_four_quad_remaining_AND_upper_per_pass": 14 * 4 - helper_sum,
        "upper_bound_scope": "Only unchanged 4-helper basis / 15 batches / first zero-input batch. Not a bound for general gauge bases, tensors or full circuits."
    }

    result = {
        "scope": "Manual reduced-shot circuit diagnostic plus exact official numerical/cost functions; not full official verifier or leaderboard measurement",
        "hash_matching_performed": False, "official_files_modified": False,
        "npz_shape": {k: list(v.shape) for k, v in params.items()},
        "recovery": recovery, "metrics_from_recovered_words": metrics,
        "accuracy_math_pass": bool(passes_accuracy(metrics)), "margins": margins,
        "resources": resource, "reconstructed_cost": cost, "static_loaders": static,
        "fractions": {k: resource[k] / resource["toffoli"] for k in
                      ("angles_toffoli", "outer_state_prep_toffoli", "inner_state_prep_toffoli", "givens_rotations_toffoli")},
        "gauge": gauge_report,
        "ANF_recovered_gauged": block_anf(words), "ANF_ungauged": block_anf(canonical),
        "cost_scenarios_scope": "Hypothetical only: no new factorization or loaders; lambda/loader T held fixed and workspace assumed to fit",
        "J_sweep": [scenario(j=j) for j in (3, 4, 5, 6, 8, 10)],
        "brot_sweep": [scenario(beta=b) for b in (6, 7, 8, 9, 10)],
        "C_sweep": [scenario(c=c) for c in (39, 40, 42, 43, 44, 45, 46, 47, 48, 56, 60)],
        "B_sweep": [scenario(b=b) for b in (127, 128, 135, 142, 143, 144, 151, 159, 160)],
        "R_sweep": [scenario(r=r) for r in (7, 8, 9)],
        "loader_reduction_scenarios": [
            {"fraction": f, "chem_cost_reduction": angles_t * f / resource["toffoli"],
             "overall_GM_gain": (resource["toffoli"] / (resource["toffoli"] - angles_t * f)) ** (1 / 3) - 1}
            for f in (0.01, 0.05, 0.10)],
        "wall_seconds": time.monotonic() - start
    }
    (OUT / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"gauge": gauge_report, "seconds": result["wall_seconds"]}), flush=True)


if __name__ == "__main__":
    main()
