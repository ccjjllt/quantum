"""Manual sampled audit of the unchanged public invsqrt circuit (not full verification)."""

from pathlib import Path
import hashlib
import io
import json
import math
import sys
from fractions import Fraction

import kickmix as km
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data/competition/verifiers"))
from invsqrt import verify_submission_invsqrt as official


def measured_counts(stats):
    gate_counts = dict(stats)
    return np.array([stats.num_toffoli_like, stats.num_t_like,
                     stats.num_z_pow(min_clifford_hierarchy_level=4),
                     *(gate_counts.get(name, 0) for name in ("CCX", "CCZ", "CSWAP", "HMR"))], dtype=float)


def main():
    source = ROOT / "artifacts/20261030_public_best/candidate/invsqrt.kmb"
    output = ROOT / "artifacts/20261030_public_audit/invsqrt"
    output.mkdir(parents=True, exist_ok=True)
    circuit = km.Circuit.from_file(source)
    text = io.StringIO()
    circuit.to_file(text, format="kmx")
    lines = text.getvalue().splitlines()
    header = [line for line in lines if line.startswith(("APPEND_TO_REGISTER", "REGISTER"))]
    ops = [line for line in lines if not line.startswith(("APPEND_TO_REGISTER", "REGISTER"))]
    cuts = [0, 15244, 15583, 25630, 25871, len(ops)]
    labels = ["before first phase", "first phase block", "between phase blocks", "second phase block", "after second phase"]
    stages = [km.Circuit.from_file(io.StringIO("\n".join(header + ops[a:b])), format="kmx") for a,b in zip(cuts,cuts[1:])]
    static = dict(circuit.operation_statistics())
    spec = official.ProblemSpecInvSqrt.for_n_p(10)
    xreg, scratch = official.validate_registers(circuit, spec)
    rng = np.random.default_rng(20261030)
    uniform = rng.integers(1, spec.max_x + 1, 8192, dtype=np.uint64)
    boundary = sorted(set(range(1,1025)) | set(range(spec.max_x-1023,spec.max_x+1)) |
                      {2**k+d for k in range(22) for d in range(-3,4) if 1<=2**k+d<=spec.max_x} |
                      {k*k+d for k in range(1,257) for d in (-1,0,1) if 1<=k*k+d<=spec.max_x})
    boundary=np.array(boundary,dtype=np.uint64)
    boundary=np.resize(boundary, math.ceil(len(boundary)/256)*256)
    records=[]
    profile=[]
    for name,xs in [("uniform",uniform),("boundary",boundary)]:
        targets,tols=official.reference_values(spec,xs)
        for seed in [101,202,303]:
            sim=km.Simulator(batch_size=256, counting_operations=True, seed=seed)
            maxratio=0.; worstx=0; minmargin=1<<64; marginx=0; badx=0; dirty=0; failures=0
            totals=np.zeros((5,7))
            for offset in range(0,len(xs),256):
                batch=xs[offset:offset+256]
                sim.clear_for_shot(); sim.write_across_shots(xreg,official.to_bits(batch,22))
                previous=measured_counts(sim.operation_statistics())
                for j,stage in enumerate(stages):
                    sim.do(stage)
                    stats=sim.operation_statistics()
                    current=measured_counts(stats)
                    totals[j]+=current-previous; previous=current
                badx+=np.count_nonzero(official.from_bits(sim.read_across_shots(xreg))!=batch)
                dirty+=np.count_nonzero(sim.read_across_shots(scratch).any(axis=0))
                theta=np.array([official.half_turns_to_units(sim.read_shot_phase(i)) for i in range(256)],dtype=np.uint64)
                errors=np.abs((theta-targets[offset:offset+256]).view(np.int64)).view(np.uint64)
                allowed=tols[offset:offset+256]
                ratios=errors/allowed
                idx=int(np.argmax(ratios))
                if ratios[idx]>maxratio: maxratio=float(ratios[idx]);worstx=int(batch[idx])
                margins=allowed-errors
                marginidx=int(np.argmin(margins))
                if int(margins[marginidx])<minmargin:
                    minmargin=int(margins[marginidx]); marginx=int(batch[marginidx])
                failures+=np.count_nonzero(errors>allowed)
            records.append({"set":name,"seed":seed,"shots":len(xs),"x_restoration_errors":int(badx),"dirty_scratch_shots":int(dirty),"phase_failures":int(failures),"worst_error_over_tolerance":maxratio,"worst_x":worstx,"sample_min_margin_turns":minmargin/2**64,"sample_min_margin_x":marginx})
            if name=="uniform": profile.append(totals/len(xs))
    means=np.mean(profile,axis=0)
    q=62; upstream_cost=100940.61; upstream_toffoli=1331.48; C=upstream_cost/q
    nrot=41; maxmargin=2**-24/math.sqrt(spec.max_x)
    min_synthesis=nrot*official.rotation_t_count(math.pi*maxmargin/nrot)/4
    sensitivity={
        "input_costs_are_rounded_upstream_values":True,
        "upstream_cost":upstream_cost,"upstream_toffoli_mean":upstream_toffoli,
        "equivalent_cost_per_qubit":C,"synthesis_and_T_equivalent":C-upstream_toffoli,
        "largest_possible_global_margin_turns":maxmargin,
        "minimum_synthesis_equivalent_for_41_rotations":min_synthesis,
        "optimistic_max_reduction_only_improving_margin":(C-upstream_toffoli-min_synthesis)/C,
        "optimistic_max_GM_gain_only_improving_margin":(C/(upstream_toffoli+min_synthesis))**(1/3)-1,
        "remove_one_unconditional_toffoli_GM_gain":(C/(C-1))**(1/3)-1,
        "remove_100_unconditional_toffoli_GM_gain":(C/(C-100))**(1/3)-1,
        "one_fewer_qubit_same_gates_GM_gain":(62/61)**(1/3)-1,
        "one_fewer_qubit_break_even_extra_equivalent_gates":C/61,
        "two_extra_qubits_break_even_gate_saving":C*(1-62/64),
        "two_extra_qubits_saving100_equivalent_GM_gain":(62*C/(64*(C-100)))**(1/3)-1,
        "unpriced_CX_CZ_fraction_of_static_ops":(static["CX"]+static["CZ"])/len(circuit),
    }
    whole=km.Simulator(batch_size=256,seed=101)
    split=km.Simulator(batch_size=256,seed=101)
    for sim in (whole,split):
        sim.clear_for_shot(); sim.write_across_shots(xreg,official.to_bits(uniform[:256],22))
    whole.do(circuit)
    for stage in stages:split.do(stage)
    split_same=all(whole.read_shot_phase(i)==split.read_shot_phase(i) for i in range(256)) and np.array_equal(whole.read_across_shots(km.array([km.q(i) for i in range(62)])),split.read_across_shots(km.array([km.q(i) for i in range(62)])))
    assert split_same
    result={"scope":"Sampled diagnostic only: uniform sample and selected boundary inputs, 3 seeds; NOT full official local verifier PASS", "source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),"num_ops":len(circuit),"num_qubits":circuit.num_qubits,"num_bits":circuit.num_bits,"static_operations":static,"non_clifford_rotation_count":circuit.operation_statistics().num_z_pow(min_clifford_hierarchy_level=4),"split_stage_simulation_matches_unsplit_for_256_shots":split_same,"sample_records":records,"stage_profile":[{"name":name,"start_op":cuts[i],"stop_op_exclusive":cuts[i+1],"mean_executed_toffoli_like":float(means[i,0]),"mean_T_like":float(means[i,1]),"mean_nonclifford_rotations":float(means[i,2]),"mean_CCX":float(means[i,3]),"mean_CCZ":float(means[i,4]),"mean_CSWAP":float(means[i,5]),"mean_HMR":float(means[i,6]),"static_toffoli_like":stages[i].operation_statistics().num_toffoli_like} for i,name in enumerate(labels)],"sensitivity":sensitivity}
    (output/"audit.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
