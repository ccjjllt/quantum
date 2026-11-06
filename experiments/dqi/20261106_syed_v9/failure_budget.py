"""Manual probability/cost scenarios; no circuit simulation or candidate change."""
import json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'artifacts/20261106_syed_v9/dqi'
sys.path.insert(0,str(ROOT/'data/competition/verifiers'))
from dqi.verify_submission_dqi import optimal_dqi_weights,clopper_pearson_upper_bound,repetition_overhead

def main():
    probe=json.loads((OUT/'paired_baseline_probe.json').read_text())
    t=next(r['results']['syed']['mean_T'] for r in probe['rows'] if r['distribution']=='ordinary')
    q=892;n=102400;w=optimal_dqi_weights(4095,35,12,2016)**2
    r0=repetition_overhead(clopper_pearson_upper_bound(0,n));rows=[]
    for bound in (5,16,17):
        lam=float(w[:bound+1].sum()*n)
        er=sum(math.exp(-lam)*lam**k/math.factorial(k)*repetition_overhead(clopper_pearson_upper_bound(k,n)) for k in range(12))
        rows.append({'max_weight':bound,'prob_mass':float(w[:bound+1].sum()),'Poisson_lambda_if_all_fail':lam,'repair_extra_meanT_break_even_if_only_this_failure_mass_exists':t*(er/r0-1)})
    result={'scope':'Illustrative Poisson pricing scenario; assume all weights <= bound fail and no others. Not measured failure attribution or exact universal repair budget.',
            'Q':q,'meanT_source':'one ordinary256shot probe','meanT':t,'failure_mass_scenarios':rows,
            'zero_mask_scan_expected_saving_already_present':44275/4096,
            'all_masks_zero_probability_log2':-4095*12,'GM_plus_0_1pct_requires_savedT':t*(1-1/1.001**3)}
    (OUT/'failure_budget.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
