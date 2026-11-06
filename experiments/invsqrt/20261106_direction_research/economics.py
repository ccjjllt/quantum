"""Manual cost sensitivity calculation from the saved official candidate result.

No circuit edits, simulator, or verifier calls. Scenarios are budgets, not gains.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'artifacts/20261106_direction_research/economics.json'


def main():
    result = json.loads((ROOT / 'artifacts/20261106_syed_v9/invsqrt/official_run.json').read_text())['official_result']
    q, c = result['num_qubits'], result['toffoli_equivalent']
    r, score = result['rotation_count'], result['score']
    direct_t = result['t_count'] / 4
    rot_c = c - result['toffoli_count'] - direct_t
    margin = result['rotation_eps'] * r / math.pi
    # Exact official integer tolerance at the largest input; conversion only
    # after computing its integer value. Every admissible phase has margin <= it.
    tol_min_units = math.isqrt((1 << 130) // 3133452) >> 25
    ideal_margin = tol_min_units / 2**64

    def rot_cost(n, m):
        return n * (0.56 * math.log2(n / (math.pi * m)) + 5.3) / 4

    def scenario(q_new, c_new):
        new_score = q_new * c_new
        return dict(Q=q_new, C=c_new, cost=new_score, cost_saving=score-new_score,
                    invsqrt_percent_saving=100*(1-new_score/score),
                    total_GM_percent_gain=100*((score/new_score)**(1/3)-1))

    doc = dict(scope='Analytical sensitivity and break-even budgets only; no new circuit or validation',
               baseline=result,
               components_C=dict(toffoli_like=result['toffoli_count'], direct_T=direct_t, rotations=rot_c),
               components_percent=dict(toffoli_like=100*result['toffoli_count']/c,
                                       direct_T=100*direct_t/c, rotations=100*rot_c/c),
               min_margin_turns=margin, min_tolerance_units=tol_min_units,
               min_tolerance_turns=ideal_margin, fixed_R_max_margin_factor=ideal_margin/margin,
               fixed_R_ideal_phase_upper_saving_C=rot_c-rot_cost(r,ideal_margin),
               fixed_R_ideal_phase_scenario=scenario(q,c-rot_c+rot_cost(r,ideal_margin)),
               qubit_reduction_budgets=[dict(Q=qn, max_extra_C_for_strict_improvement=score/qn-c,
                                            zero_extra_C=scenario(qn,c)) for qn in (61,60,59,58,56,52,48)],
               qubit_increase_budgets=[dict(Q=qn,min_C_reduction_for_strict_improvement=c-score/qn)
                                       for qn in (63,64,66,70,80)],
               rotations_scenarios=[dict(R=rn,saving_C_at_same_margin=rot_c-rot_cost(rn,margin),
                                        optimistic_saving_C_at_ideal_margin=rot_c-rot_cost(rn,ideal_margin))
                                    for rn in (40,36,32,28,24,22)],
               gate_scenarios=[dict(saved_C=s,**scenario(q,c-s)) for s in (.75,1,10,20,50,100)],
               desired_saving_budgets=[dict(invsqrt_percent_saving=p,required_net_C_reduction=c*p/100)
                                       for p in (1,2,5,10)],
               warning='All cost differences use expected C. New arithmetic, lookup, correction, width and synthesis costs must be included. R=22 is a scenario, not a proven lower bound.')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2)+'\n')
    print(json.dumps({k:doc[k] for k in ('components_percent','fixed_R_max_margin_factor','fixed_R_ideal_phase_upper_saving_C','fixed_R_ideal_phase_scenario')},indent=2))


if __name__ == '__main__':
    main()
