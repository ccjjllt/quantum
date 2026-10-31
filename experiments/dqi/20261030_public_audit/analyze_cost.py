"""Read-only DQI cost sensitivity; imports helpers, never runs verification.

The optional --circuit argument measures static counts only, once per invocation.
Upstream runtime T and failure-rate estimates are explicitly labelled.
"""
import argparse
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'data/competition/verifiers'))
from dqi.verify_submission_dqi import (
    clopper_pearson_upper_bound, repetition_overhead, optimal_dqi_weights,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--circuit', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    q, t, n = 889, 433785.0, 102400
    r0 = repetition_overhead(clopper_pearson_upper_bound(0, n))
    rows = []
    for k in [0, 1, 2, 3, 5, 10, 20, 100, 1000]:
        upper = clopper_pearson_upper_bound(k, n)
        rep = repetition_overhead(upper)
        rows.append({'errors': k, 'epsilon_plus': upper, 'R': rep,
                     'cost_at_upstream_T': rep * q*q*t,
                     'DQI_cost_factor_vs_zero_errors': rep/r0,
                     'GM_factor_vs_zero_errors': (r0/rep)**(1/3),
                     'Toffoli_reduction_to_offset': t*(1-r0/rep)})
    weights = optimal_dqi_weights(4095, 35, 12, 2016)**2
    widths = []
    for smaller in [888, 883, 877, 864, 840]:
        widths.append({'Q': smaller, 'DQI_improvement_at_fixed_T_R': (q/smaller)**2,
                       'GM_factor_at_fixed_T_R': (q/smaller)**(2/3),
                       'extra_Toffolis_break_even': t*((q/smaller)**2-1)})
    expected_R = 0.0
    lam = 0.32  # Upstream handoff estimate; not independently measured here.
    for k in range(30):
        p = math.exp(-lam) * lam**k / math.factorial(k)
        expected_R += p * repetition_overhead(clopper_pearson_upper_bound(k,n))
    out = {
        'scope': 'Exact official cost helper calculations plus optional static circuit counts; no simulation or correctness verification',
        'assumed_mean_Toffoli_source': 'hengck23 v1 handoff and Heliosli v26 saved log, rounded to 433785',
        'Q':q, 'input_qubits_lower_bound':70*12, 'scratch_count':q-70*12,
        'default_shots':n, 'failure_sensitivity':rows, 'width_sensitivity':widths,
        'weight_probabilities':weights.tolist(),
        'weight_prefix_probabilities':{str(k):float(sum(weights[:k+1])) for k in [16,18,20,22,24,26,28,30,32,34]},
        'upstream_Poisson_lambda_model':{'lambda':lam,'probability_zero':math.exp(-lam),'expected_R':expected_R,
          'extra_Toffolis_budget_for_eliminating_all_failures':t*(expected_R/r0-1)},
        'score_gap':{'upstream_local_GM_displayed':23.0355,'our_public_LB':23.00037,
          'inferred_DQI_cost_factor_if_other_costs_unchanged':(23.0355/23.00037)**3,
          'predicted_GM_for_0_to_1_failure_at_fixed_T':23.0355*rows[1]['GM_factor_vs_zero_errors'],
          'caveat':'Only a total score is known; numerical agreement does not establish which task changed.'},
        'scan_arithmetic':{'remaining_positions':4095-70,'per_position_Toffoli':11,'product':(4095-70)*11},
    }
    if args.circuit:
        import kickmix as km
        circuit = km.Circuit.from_file(args.circuit,format='kmb')
        stats = circuit.operation_statistics()
        out['static']={'num_qubits':circuit.num_qubits,'num_bits':circuit.num_bits,
                       'num_registers':circuit.num_registers,'num_ops':len(circuit),
                       'toffoli_like':stats.num_toffoli_like,'operations':dict(stats)}
        svg = circuit.flame_chart_svg()
        args.output.parent.mkdir(parents=True,exist_ok=True)
        (args.output.parent/'static_flame_chart.svg').write_text(svg)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))


if __name__ == '__main__':
    main()
