"""Cost-only audit of the submitted v45_oz chemistry; no verifier simulation."""

import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data/competition/verifiers"))
from dfthcsos.verify import heuristic_costs
from dfthcsos.scoreinfra.circuits import load_circuits, circuit_costs

ART = ROOT / "artifacts/20261030_public_audit/dfthcsos"
BASE = ROOT / "artifacts/20261030_public_best"
data = json.loads((BASE / "local_dfthcsos.json").read_text())
metrics, resource = data["metrics"], data["resources"]
with np.load(BASE / "candidate/dfthcsos/submission.npz", allow_pickle=False) as npz:
    shapes = {key: {"shape": list(npz[key].shape), "dtype": str(npz[key].dtype)} for key in npz.files}
    R, B, C = npz["W"].shape
    N = npz["U"].shape[-1]
family = load_circuits(BASE / "candidate/dfthcsos")
static = circuit_costs(family)
for row, circuit in zip(static, family):
    row["operation_counts"] = dict(circuit.operation_statistics())

def cost_row(r, b, c, beta, j):
    h = heuristic_costs(N, r, b, c, beta)
    q = h["qubits"] + j * beta  # conditional on new loader workspace <= heuristic maximum
    t = h["toffoli"] + resource["angles_toffoli"]
    product = t * q
    return {"R": r, "B": b, "C": c, "brot": beta, "J": j,
            "num_loaders": math.ceil((N - 1) / j), "heuristic": h,
            "hypothetical_Q": q, "hypothetical_T": t,
            "cost_ratio_if_lambda_and_loader_T_unchanged": product / (430 * 16266),
            "overall_score_factor_under_same_assumptions": ((430 * 16266) / product) ** (1 / 3),
            "break_even_angles_T_if_lambda_unchanged": (430 * 16266) / q - h["toffoli"]}

result = {
    "scope": "Original official cost functions; hypothetical resource scenarios only. No new factorization, loader, accuracy or complete candidate verified.",
    "npz_entries": shapes,
    "constraints": {"error_1_margin_Ha": 0.020 - metrics["error_1"],
                    "error_2_margin_Ha": 0.020 - metrics["error_2"],
                    "E_gap_floor_margin_Ha": metrics["E_gap"] - 3.914898,
                    "ANGLE_qubit_headroom": 128 - resource["angles_qubits"]},
    "toffoli_fractions": {k: resource[k] / resource["toffoli"] for k in
                         ("angles_toffoli", "outer_state_prep_toffoli", "inner_state_prep_toffoli", "givens_rotations_toffoli")},
    "static_loaders": static,
    "J_sweep": [cost_row(R, B, C, 8, j) for j in range(1, 11)],
    "brot_sweep": [cost_row(R, B, C, beta, 5) for beta in range(4, 13)],
    "B_sweep": [cost_row(R, b, C, 8, 5) for b in (111, 112, 119, 127, 128, 135, 143, 144, 159, 160)],
    "C_sweep": [cost_row(R, B, c, 8, 5) for c in (44, 48, 52, 56, 59, 60, 61, 64)],
    "loader_T_scenarios": [{"angle_T_reduction_fraction": f,
                             "chemistry_cost_ratio": (16266 - 8336 * f) / 16266,
                             "overall_score_factor": (16266 / (16266 - 8336 * f)) ** (1 / 3)}
                            for f in (0.01, 0.05, 0.10, 0.20)],
}
padding = {}
for axis, values in (("C", range(60, 513)), ("B", range(143, 1025)), ("R", range(8, 65))):
    rows = []
    for value in values:
        shape = {"R": R, "B": B, "C": C}
        shape[axis] = value
        row = cost_row(shape["R"], shape["B"], shape["C"], 8, 5)
        rows.append({"value": value, "Q": row["hypothetical_Q"], "T": row["hypothetical_T"],
                     "ratio": row["cost_ratio_if_lambda_and_loader_T_unchanged"]})
    padding[axis] = {"min": min(rows, key=lambda x: x["ratio"]),
                     "any_better": [x for x in rows if x["ratio"] < 1.0],
                     "bounds": [min(values), max(values)]}
ART.mkdir(parents=True, exist_ok=True)
(ART / "resource_sensitivity.json").write_text(json.dumps(result, indent=2) + "\n")
(ART / "padding_cost_audit.json").write_text(json.dumps({
    "scope": "One-axis zero-padding. C padding preserves loaded angle rows and circuits; B/R padding requires additional/rerouted address support. Loader T held constant, so B/R costs are optimistic. No candidate constructed.",
    "results": padding}, indent=2) + "\n")
print(json.dumps({"constraints": result["constraints"], "toffoli_fractions": result["toffoli_fractions"],
                  "brot": [{k: x[k] for k in ("brot", "hypothetical_Q", "hypothetical_T", "cost_ratio_if_lambda_and_loader_T_unchanged")} for x in result["brot_sweep"]],
                  "J": [{k: x[k] for k in ("J", "hypothetical_Q", "break_even_angles_T_if_lambda_unchanged")} for x in result["J_sweep"]]}, indent=2))
