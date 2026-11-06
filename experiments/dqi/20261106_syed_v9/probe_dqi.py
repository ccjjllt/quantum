"""Manual paired finite-distribution diagnostics on Syed V9 and prior DQI.

Not the default full official verifier. Saves per-shot error masks, fixed input
and measurement seeds, and actual operation counts. No hash calculation.
"""
import argparse
import json
from pathlib import Path
import sys
import time
import kickmix as km
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'data/competition/verifiers'))
from dqi.verify_submission_dqi import (ProblemSpecDQI, FieldTables, sample_shots,
    validate_registers, to_bits, optimal_dqi_weights, clopper_pearson_upper_bound, repetition_overhead)
OUT=ROOT/'artifacts/20261106_syed_v9/dqi'

def run(c,shots,seed):
    spec=ProblemSpecDQI.benchmark_instance()
    s,e,a=validate_registers(c,spec);s=km.array(s);e=km.array(e)
    synd,mb,phase=shots;bits=to_bits(synd,spec.degree)
    sim=km.Simulator(batch_size=len(synd),seed=seed,debug_print=False,counting_operations=True)
    sim.use_same_registers_as(c);sim.write_across_shots(s,bits);sim.write_across_shots(e,to_bits(mb,spec.degree));sim.do(c)
    syndrome_errors=(sim.read_across_shots(s)^bits).any(axis=0)
    scratch=sim.read_across_shots(a).any(axis=0)
    ve=syndrome_errors|scratch;pe=(sim.read_phase_flipped_across_shots()^phase)&~ve
    stat=sim.operation_statistics()
    return {'value_errors':int(ve.sum()),'phase_errors':int(pe.sum()),
            'syndrome_errors':int(syndrome_errors.sum()),'scratch_errors':int(scratch.sum()),
            'value_error_indices':np.flatnonzero(ve).tolist(),'phase_error_indices':np.flatnonzero(pe).tolist(),
            'mean_T':stat.num_toffoli_like/len(synd),'operations':dict(stat)}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--candidate',type=Path);args=parser.parse_args()
    paths={'syed':ROOT/'artifacts/20261106_syed_v9/release/dqi.kmb',
           'old_merged':ROOT/'artifacts/20261106_leo_merge/dqi_merged_b99bf233.kmb'}
    if args.candidate:paths['candidate']=args.candidate
    circuits={k:km.Circuit.from_file(p,format='kmb') for k,p in paths.items()}
    spec=ProblemSpecDQI.benchmark_instance();tables=FieldTables(km.GF2Field(spec.degree))
    rows=[]
    for index,weight in enumerate((0,5,6,16,17,18,31,35,'ordinary','zero_mask')):
        input_seed=2026110600+index;sim_seed=2026111600+index
        probs=None
        if isinstance(weight,int):probs=np.zeros(36);probs[weight]=1
        shots=sample_shots(spec,tables,np.random.default_rng(input_seed),256,probs)
        if weight=='zero_mask':shots=(shots[0],np.zeros_like(shots[1]),np.zeros_like(shots[2]))
        start=time.monotonic();results={k:run(c,shots,sim_seed) for k,c in circuits.items()}
        row={'distribution':weight,'shots':256,'input_seed':input_seed,'measurement_seed':sim_seed,
             'results':results,'seconds':time.monotonic()-start};rows.append(row)
        print(json.dumps(row),flush=True)
    t=rows[-2]['results']['syed']['mean_T'];q=circuits['syed'].num_qubits
    r0=repetition_overhead(clopper_pearson_upper_bound(0,102400))
    weights=optimal_dqi_weights(spec.m,spec.max_errors,spec.degree,spec.r)**2
    summary={'scope':'10 explicitly chosen 256-shot input batches, each circuit on identical logical inputs and simulator seeds; not full official verification or population failure-rate estimate',
             'paths':{k:str(p.relative_to(ROOT)) for k,p in paths.items()},'rows':rows,
             'cost_scenarios_scope':'Illustrative using one ordinary batch mean; R and failure behavior held constant unless stated',
             'width_tradeoffs':[{'Q':w,'extra_meanT_break_even':t*((q/w)**2-1),
                                'GM_gain_at_fixed_T_R':(q/w)**(2/3)-1} for w in (891,890,893,894)],
             'single_additional_error_T_saving_to_offset':t*(1-r0/repetition_overhead(clopper_pearson_upper_bound(1,102400))),
             'T_saving_for_GM_plus_0_1pct':t*(1-1/1.001**3),
             'official_prob_weight_le5':float(weights[:6].sum()),'official_prob_weight17':float(weights[17])}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/('paired_candidate_probe.json' if args.candidate else 'paired_baseline_probe.json')).write_text(json.dumps(summary,indent=2)+'\n')

if __name__=='__main__':main()
