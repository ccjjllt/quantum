"""Manually reproduce scalar DQI failure-budget scenarios, without simulation.

Imports only weighting/penalty helpers from the unmodified official module.
The finite binomial sum is a scenario, not measured candidate performance or
an exact expectation that assigns a cost to every possible rejected run.
"""

import json
import math
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data/competition/verifiers"))
from dqi.verify_submission_dqi import (
    clopper_pearson_upper_bound,
    optimal_dqi_weights,
    repetition_overhead,
)


def main():
    weights = optimal_dqi_weights(4095, 35, 12, 2016) ** 2
    # Frozen ordinary-distribution 256-shot measurement from the prior study.
    t = 395395.47265625
    n = 102400
    r0 = repetition_overhead(clopper_pearson_upper_bound(0, n))
    penalties = [
        repetition_overhead(clopper_pearson_upper_bound(k, n))
        for k in range(300)
    ]

    def finite_mean_penalty(probability):
        pk = math.exp(n * math.log1p(-probability))
        total = pk * penalties[0]
        mass = pk
        k = 0
        while mass < 1 - 2e-14 and k < 299:
            pk *= ((n - k) / (k + 1)) * (probability / (1 - probability))
            k += 1
            total += pk * penalties[k]
            mass += pk
        return total, mass, k

    base_probability = float(weights[:18].sum())
    base_penalty = finite_mean_penalty(base_probability)[0]
    rows = []
    for bound in (5, 16, 17, 18, 19, 20, 21):
        probability = float(weights[:bound + 1].sum())
        penalty, mass, k = finite_mean_penalty(probability)
        rows.append({
            "weight_max": bound,
            "probability": probability,
            "expected_failures_at_N": n * probability,
            "scenario_mean_R": penalty,
            "summed_binomial_mass": mass,
            "summation_max_k": k,
            "repair_allowance_T_vs_zero_failure": t * (penalty / r0 - 1),
            "extra_pruning_required_saving_T_vs_le17_scenario":
                t * (1 - base_penalty / penalty),
        })
    result = {
        "date": "2026-11-06",
        "scope": "Analytic scenarios only; import official scalar weighting and penalty helpers; no circuit simulation and no official verify call. Binomial K under assumed all weight<=bound fail, no other failures; finite sum residual shown. Costs use 256-shot local meanT as approximation. Not empirical candidate results.",
        "N": n,
        "Q": 892,
        "T": t,
        "R0": r0,
        "weights": [float(x) for x in weights],
        "rows": rows,
        "bm_comparison": {
            "source": "https://raw.githubusercontent.com/andigu/uncompute/64b5a13aa249f1360846657392e6c66817b26d0f/tasks/dqi-reed-solomon/results.jsonl",
            "T": 442397,
            "Q": 1837,
            "same_R_cost_ratio": 1837 ** 2 * 442397 / (892 ** 2 * t),
            "scope": "Resource-only comparison across different contracts, not a converted verified Kaggle candidate",
        },
        "Q_floor": 840,
        "max_width_only_cost_fraction_saved_at_fixed_T_R": 1 - (840 / 892) ** 2,
        "restoration_static_T": 62558 + 40452 + 96903,
        "restoration_fraction_of_static_T": (62558 + 40452 + 96903) / 395679,
        "top_weight_truncation_failure_mass": {
            "max34": float(weights[35]),
            "max33": float(weights[34:].sum()),
        },
    }
    output = ROOT / "artifacts/20261106_high_return_research/algorithms/budgets.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"output": str(output), "rows": rows}, indent=2))


if __name__ == "__main__":
    main()
