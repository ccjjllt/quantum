"""Manual resource-budget study of the official model; no circuit verification.

All changed shapes, precisions and batch sizes below are hypothetical budgets.
The script never edits competition inputs or emits a candidate submission.
"""
from pathlib import Path
import csv
import json
import math
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'data/competition/verifiers'))
from dfthcsos.verify import heuristic_costs
from dfthcsos.scoreinfra.costs_prepare import SpinFreeData_V1, QR

OUT = ROOT / 'artifacts/20261106_high_yield/resources'
BASE = json.loads((ROOT / 'artifacts/20261106_syed_v9/dfthcsos/analysis.json').read_text())
Q0 = BASE['resources']['qubits']
T0 = BASE['resources']['toffoli']
A0 = BASE['resources']['angles_toffoli']
L0 = BASE['metrics']['lambda_eff']


def shape(r=8, b=143, c=44, beta=8, j=5):
    h = heuristic_costs(76, r, b, c, beta)
    model = SpinFreeData_V1(r, b, c, 76, 10, beta)
    selection = math.ceil(math.log2(76 + r * b))
    scratch_cap = 128 - selection - beta * j
    b2 = math.ceil(math.log2(b)) + 11
    k_raw = QR(r * b * c, b2)[0]
    k = model.find_qroam_size_to_minimize_global_temp_ancilla(b2)
    q = h['qubits'] + beta * j
    # All scanned cases have heuristic workspace dominating any legal loader.
    if scratch_cap >= 0 and h['temporary_qubits'] < scratch_cap:
        raise ValueError('ANGLE workspace can dominate; use actual circuit width')
    ratio = q * (h['toffoli'] + A0) / (Q0 * T0)
    return {
        'R': r, 'B': b, 'C': c, 'brot': beta, 'J': j,
        'RB': r*b, 'RC': r*c, 'vectors': 76+r*b,
        'selection_qubits': selection, 'angle_scratch_cap': scratch_cap,
        'num_loaders': math.ceil(75/j), 'b2': b2,
        'inner_qroam_k_unconstrained': k_raw, 'inner_qroam_k': k,
        'inner_temporary': h['inner_state_prep_temporary_qubits'],
        'outer_temporary': h['outer_state_prep_temporary_qubits'],
        'Q': q, 'T_fixed': h['toffoli'],
        'T_with_baseline_angle': h['toffoli']+A0,
        'resource_ratio_fixed_lambda_angle': ratio,
        'chemistry_reduction_fixed_lambda_angle': 1-ratio,
        'gm_increase_fixed_lambda_angle': ratio**(-1/3)-1,
        'lambda_increase_break_even_fixed_angle': 1/ratio-1,
        'angle_break_even_fixed_lambda': Q0*T0/q-h['toffoli'],
        'angle_for_5pct_chemistry_reduction': .95*Q0*T0/q-h['toffoli'],
        'angle_for_10pct_chemistry_reduction': .90*Q0*T0/q-h['toffoli'],
    }


def main():
    start = time.monotonic()
    OUT.mkdir(parents=True, exist_ok=True)
    bounds = json.loads((ROOT / 'artifacts/20261106_high_yield/numerical/bounds.json').read_text())
    rank_min = bounds['psd_rank_bound']['minimum_relaxed_psd_rank_at_20mHa']
    if (Q0, T0, A0) != (427, 14966, 8304):
        raise ValueError('Unexpected baseline; review numerical assumptions')
    selected = [
        shape(), shape(b=128), shape(b=129), shape(b=144),
        shape(beta=7), shape(beta=9), shape(c=37), shape(c=42), shape(c=43),
        shape(r=7,b=135,c=50), shape(r=6,b=143,c=59),
        shape(r=7,b=135,c=42), shape(r=8,b=118,c=44),
        shape(r=5,b=189,c=70), shape(r=4,b=237,c=88),
    ]
    budgets = []
    for reduction in (.01, .05, .10):
        need = T0*reduction
        gap = BASE['metrics']['E_gap']
        target_lambda_raw = ((L0*(1-reduction))**2/gap+gap)/2
        budgets.append({'chemistry_reduction': reduction,
                        'toffoli_saving_required_same_lambda_Q': need,
                        'angle_remaining': A0-need,
                        'angle_fraction_saved': need/A0,
                        'lambda_reduction_required_same_T_Q': reduction,
                        'raw_Lambda_target_at_current_gap': target_lambda_raw,
                        'raw_Lambda_fraction_saved_at_current_gap': 1-target_lambda_raw/BASE['metrics']['Lambda'],
                        'GM_increase': (1-reduction)**(-1/3)-1,
                        'product_reduction_each_of_11_coded_batches': need/22,
                        'integer_product_reduction_each_of_11_coded_batches': math.ceil(need/22)})
    rows = []
    # Broad budgets constrained only by a necessary PSD rank bound and
    # comparable vector/rank totals. No claim of valid DFTHC decompositions.
    for r in range(4, 13):
        for b in range(96, 256):
            if not 750 <= r*b <= 1250:
                continue
            for c in range(24, 97):
                if not rank_min <= r*c <= 384:
                    continue
                rows.append(shape(r,b,c))
    with (OUT/'shape_scan.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
    comparable = [x for x in rows if 344 <= x['RC'] <= 360 and x['selection_qubits'] == 10]
    comparable.sort(key=lambda x: (x['resource_ratio_fixed_lambda_angle'], -x['RB']))
    # Retain the best budget for each R among rank-preserving ten-address-bit shapes.
    ten_bit = [next(x for x in comparable if x['R']==r) for r in sorted({x['R'] for x in comparable})]
    baseline_k5_bound = math.ceil(math.log2(8*44*math.ceil(143/32))) + 31*19
    # Read from Lera V7 tensorqrom.py:327; no external source execution.
    def monomial_cache(size):
        return size-1-(size-1).bit_length()
    base_cache=monomial_cache(16)+monomial_cache(math.ceil(1220/16))
    cache_budgets=[]
    for r,b,c in ((7,135,50),(6,143,59),(7,135,42)):
        item=shape(r,b,c)
        cache=monomial_cache(16)+monomial_cache(math.ceil(item['vectors']/16))
        saving=2*15*(base_cache-cache)
        angle=A0-saving
        total=item['T_fixed']+angle
        cache_budgets.append({'R':r,'B':b,'C':c,'vectors':item['vectors'],
            'full_cache_per_pass_slot':cache,
            'angle_saving_if_products_helpers_unchanged':saving,
            'angle_if_products_helpers_unchanged':angle,
            'chemistry_reduction_if_lambda_products_helpers_unchanged':1-total*item['Q']/(T0*Q0),
            'additional_angle_saving_for_5pct':angle-item['angle_for_5pct_chemistry_reduction'],
            'scope':'Conditional budget only: same 15 slots, 4 low address bits, product counts and helper reuse; none is established after retraining.'})
    out = {
        'scope': 'Official arithmetic-only resource scan, no changed decomposition/circuit or official full validation; all changed-shape gains are conditional budgets.',
        'baseline': {'lambda_eff': L0, 'Q': Q0, 'T': T0, 'ANGLE': A0, 'cost': BASE['cost']},
        'necessary_psd_rank_floor': rank_min,
        'rank_bound_source': 'artifacts/20261106_high_yield/numerical/bounds.json',
        'baseline_k5_workspace_criterion': {'left_side': baseline_k5_bound, 'strict_upper_bound': 8*75, 'selected_k':4},
        'selected_shapes': selected,
        'C_sweep': [shape(c=c) for c in range(25,49)],
        'B_sweep': [shape(b=b) for b in (63,64,65,95,96,111,112,118,127,128,129,135,142,143,144,151,159,160,175,191)],
        'J_sweep': [shape(j=j) for j in range(1,15)],
        'precision_sweep': [shape(beta=b) for b in (6,7,8,9,10)],
        'high_yield_budgets': budgets,
        'conditional_cache_budgets':cache_budgets,
        'scan_count': len(rows),
        'ten_bit_near_baseline_rank_best_budget_per_R': ten_bit,
        'elapsed_seconds': time.monotonic()-start,
    }
    (OUT/'summary.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'baseline':out['baseline'],'scan_count':len(rows),'seconds':out['elapsed_seconds'],'selected_shapes':selected,'high_yield_budgets':budgets,'ten_bit_best_by_R':ten_bit},indent=2))


if __name__ == '__main__':
    main()
