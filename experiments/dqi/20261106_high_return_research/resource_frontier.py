"""Manual cost scenarios using official formulas; no circuit verification."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'data/competition/verifiers'))
from dqi.verify_submission_dqi import (
    optimal_dqi_weights, clopper_pearson_upper_bound, repetition_overhead,
)


def main():
    source = ROOT / 'artifacts/20261106_syed_v9/dqi/paired_baseline_probe.json'
    probe = json.loads(source.read_text())
    t = next(r['results']['syed']['mean_T'] for r in probe['rows']
             if r['distribution'] == 'ordinary')
    q, n = 892, 102400
    r0 = repetition_overhead(clopper_pearson_upper_bound(0, n))
    weights = optimal_dqi_weights(4095, 35, 12, 2016) ** 2
    widths = []
    for new_q in (840, 864, 880, 891, 892, 893, 900, 904, 916, 940, 1000, 1837):
        ratio = (new_q / q) ** 2
        widths.append({'Q': new_q, 'max_meanT_at_equal_cost_and_R': t / ratio,
                       'extra_meanT_budget': t / ratio - t,
                       'cost_change_at_fixed_T_R': ratio - 1,
                       'GM_change_at_fixed_T_R': ratio ** (-1/3) - 1})
    errors = []
    for k in (0, 1, 2, 5, 10, 20, 100):
        r = repetition_overhead(clopper_pearson_upper_bound(k, n))
        errors.append({'failed_shots': k, 'R': r,
                       'required_T_reduction_vs_zero_fail_at_same_Q': 1-r0/r,
                       'required_saved_T': t*(1-r0/r)})
    # Deterministic count scenarios, not predicted or expected failure penalties.
    tails = [{'max_weight': bound, 'prob_mass': float(weights[:bound+1].sum()),
              'expected_failed_shots_if_all_in_tail_fail': float(n*weights[:bound+1].sum())}
             for bound in (5, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25)]
    result = {
        'scope': 'Analytical scenarios only; T from one 256-shot ordinary batch. No new candidate or official verification. R held fixed except explicit failed-shot scenarios.',
        'base': {'Q': q, 'meanT': t, 'N': n, 'R_zero_fail': r0},
        'width_frontier': widths, 'failure_frontier': errors,
        'official_weight_probabilities': weights.tolist(), 'weight_tail_scenarios': tails,
        'target_savings': [{'DQI_cost_reduction': d, 'saved_T_same_Q_R': t*d,
                            'overall_GM_increase': (1-d)**(-1/3)-1}
                           for d in (0.01, 0.03, 0.05, 0.10)],
        'published_BM_442397_1837Q': {
            'source': 'https://github.com/andigu/uncompute/blob/64b5a13aa249f1360846657392e6c66817b26d0f/tasks/dqi-reed-solomon/results.jsonl',
            'cost_ratio_same_R': 442397*1837**2/(t*q**2)},
    }
    out = ROOT / 'artifacts/20261106_high_return_research/resource_frontier.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
