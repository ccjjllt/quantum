"""One manual, bounded diagnostic on Maoxin V2; never calls verify().

Five fixed-weight batches and two batches drawn from the official distribution.
No candidate edits, hash calculation, statistical pass claim, or full score.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import kickmix as km
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'data/competition/verifiers'))
from dqi.verify_submission_dqi import (
    ProblemSpecDQI,FieldTables,sample_shots,to_bits,validate_registers,optimal_dqi_weights,
)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--boundary',action='store_true',help='Follow-up four batches at weights17,18,19,20 after the original w17 failures.')
    args=parser.parse_args()
    c=km.Circuit.from_file(ROOT/'artifacts/20261105_maoxin_v2/release/dqi.kmb',format='kmb')
    spec=ProblemSpecDQI.benchmark_instance()
    s,e,a=validate_registers(c,spec)
    s,e=km.array(s),km.array(e)
    tables=FieldTables(km.GF2Field(spec.degree))
    ordinary=optimal_dqi_weights(spec.m,spec.max_errors,spec.degree,spec.r)**2
    rows=[]
    labels=[17,18,19,20] if args.boundary else [0,16,17,31,35,'ordinary_0','ordinary_1']
    for j,label in enumerate(labels):
        probs=np.zeros(spec.max_errors+1) if isinstance(label,int) else ordinary
        if isinstance(label,int):probs[label]=1
        seed=(2026110700 if args.boundary else 2026110500)+j
        started=time.monotonic()
        values,masks,phases=sample_shots(spec,tables,np.random.default_rng(seed),256,probs)
        sim=km.Simulator(batch_size=256,counting_operations=True,debug_print=False,seed=seed+100)
        sim.use_same_registers_as(c)
        bits=to_bits(values,spec.degree)
        sim.write_across_shots(s,bits)
        sim.write_across_shots(e,to_bits(masks,spec.degree))
        sim.do(c)
        bad_syndrome=(sim.read_across_shots(s)^bits).any(axis=0)
        bad_scratch=sim.read_across_shots(a).any(axis=0)
        bad_value=bad_syndrome|bad_scratch
        bad_phase=(sim.read_phase_flipped_across_shots()^phases)&~bad_value
        row={'sample':label,'shots':256,'input_seed':seed,'measurement_seed':seed+100,
             'value_errors':int(bad_value.sum()),'phase_errors_with_correct_values':int(bad_phase.sum()),
             'syndrome_errors':int(bad_syndrome.sum()),'scratch_errors':int(bad_scratch.sum()),
             'mean_toffoli_like':sim.operation_statistics().num_toffoli_like/256,
             'seconds':time.monotonic()-started}
        rows.append(row);print(json.dumps(row),flush=True)
    scope=('1024-shot fixed-weight boundary diagnostic at17,18,19,20.' if args.boundary else '1792-shot local diagnostic: 1280 fixed-weight + 512 ordinary-distribution shots.')
    out={'scope':scope+' Not full official validation, not a rare-failure estimate, not a leaderboard score.',
         'hash_computed_or_matched':False,'candidate_changed':False,'num_qubits':c.num_qubits,
         'rows':rows,'official_weight_prefix_probabilities':{str(k):float(ordinary[:k+1].sum()) for k in (16,17,20,24,28,31)},
         'mean_weight':float(np.arange(len(ordinary))@ordinary)}
    outpath=ROOT/'artifacts/20261105_maoxin_v2/dqi'/('boundary_probe.json' if args.boundary else 'distribution_probe.json')
    outpath.write_text(json.dumps(out,indent=2)+'\n')


if __name__=='__main__':
    main()
