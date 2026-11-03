"""Independent audit of actual adaptive joint-selector KMB bytes.

Does not import phase_cache or consume its proposed matrices as proof. Parses
the emitted branch structure, derives phase polynomials and coefficient masks,
and independently reconstructs/proves the 63-row input contract. No official
verification or submission is invoked.
"""
from __future__ import annotations
import argparse
import collections
import importlib.metadata
import io
import json
import platform
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import kickmix as km
import z3

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_phase_cache as AP  # independent audit interpreter, not generator

ROOT = HERE.parents[2]
ART = ROOT / "artifacts/20261103_one_ccx/invsqrt"
BASE = ROOT / "artifacts/20261102_hw06_opt/invsqrt/baseline_hw06.kmb"
CAND = ART / "phase_joint_selector.kmb"
SHA = "7e2e2843bae6bc0b44063a9d2c4bedee63b4aca8031d78ce626606b91824057e"
LO, MID, PREP2, LO2, HI = 27775, 28213, 28213, 28345, 28783


def mul(a,b):
    out=set()
    for x in a:
        for y in b:
            z=x|y
            if z in out:out.remove(z)
            else:out.add(z)
    return out


def branch_anf(lines):
    """All data variables free except the two proven clean scratch wires.

    Source classical bits occur only as phase coefficients. New HMR outcomes
    get separate coefficient names. Exact ANF cancellation therefore proves
    every outcome's phase correction and all output wires without sampling.
    """
    entry=[{1<<q} if q not in (28,40) else set() for q in range(62)]
    q=[set(v) for v in entry];phase={};measurements=[];ccx=0
    for line in lines:
        p=line.split();k=p[0];qs=[int(t[1:]) for t in p[1:] if t.startswith('q')]
        if k in ('X','CX','CCX','HMR'):
            assert 'if' not in p, ('conditional data inside successful branch',line)
        if k=='CX':q[qs[1]] ^= q[qs[0]]
        elif k=='CCX':q[qs[2]] ^= mul(q[qs[0]],q[qs[1]]);ccx+=1
        elif k=='HMR':
            key='NEW_OUT_'+p[2];measurements.append(p[2]);phase[key]=phase.get(key,set()) ^ q[qs[0]]
            q[qs[0]]=set()
        elif k in ('Z','CZ'):
            assert 'if' in p
            bit=p[-1];key='NEW_OUT_'+bit if bit in measurements else bit
            poly={0}
            for wire in qs:poly=mul(poly,q[wire])
            phase[key]=phase.get(key,set()) ^ poly
        else:raise ValueError(('unexpected success-branch operation',line))
    assert q==entry,'successful branch failed exact output restoration'
    assert len(measurements)==1 and ccx==1
    assert all(not poly for key,poly in phase.items() if key.startswith('NEW_OUT_')),'HMR phase not cancelled'
    phase={k:v for k,v in phase.items() if v and not k.startswith('NEW_OUT_')}
    assert all(m & (1<<21) for poly in phase.values() for m in poly),'phase may remain when q21=0'
    return phase,{'all_62_output_ANFs_identical':True,'new_HMR_phase_coefficients_zero':True,
                  'all_phase_monomials_contain_q21':True,'executed_Toffoli_like_if_selected':1,
                  'new_measurement_bits':measurements,'phase_monomials_per_source':{k:len(v) for k,v in phase.items()}}


def parse_candidate(new,base):
    first_push=next(i for i,l in enumerate(new) if l.startswith('PUSH_CONDITION'))
    classical=new[:first_push]
    assert classical[:LO2-PREP2]==base[PREP2:LO2]
    assert all(l.startswith('BIT_') for l in classical)
    branches=[];pos=first_push
    for j in range(3):
        assert new[pos]==f'PUSH_CONDITION if b{42010+j}'
        end=next(i for i in range(pos+1,len(new)) if new[i]=='POP_CONDITION')
        body=new[pos+1:end]
        assert not any(l.startswith('PUSH_CONDITION') for l in body)
        branches.append(body)
        assert new[end+1]==f'PUSH_CONDITION if b{42000+j}'
        pos=end+2
    assert new[pos:-3]==base[LO:MID]+base[LO2:HI]
    assert new[-3:]==['POP_CONDITION']*3
    return classical,branches


def truth_snapshot(header,base):
    prefix=km.Circuit.from_file(io.StringIO('\n'.join(header+base[:LO])+'\n'),format='kmx')
    sim=km.Simulator(batch_size=63,seed=314159);sim.use_same_registers_as(prefix)
    for i in range(63):sim.write_within_shot('x',i,i+1)
    sim.do(prefix)
    columns=[sum(int(v)<<i for i,v in enumerate(sim.read_across_shots(km.q(q)))) for q in range(62)]
    assert columns[21]==(1<<63)-1 and columns[28]==columns[40]==0
    return columns


def eval_poly(poly,columns):
    ans=0
    for monomial in poly:
        term=(1<<63)-1
        while monomial:
            bit=monomial & -monomial;term &= columns[bit.bit_length()-1];monomial ^= bit
        ans ^= term
    return ans


def local_audit(base,new,columns):
    classical,branches=parse_candidate(new,base)
    prep1=AP.affine_classical(base[27643:LO])
    forms=AP.affine_classical(classical,prep1)
    coeffs=[[f'b{24256+i}' for i in range(19)],[f'b{24320+i}' for i in range(19)]]
    word_groups=[[int(l.split()[3][1:]) for l in base[a:b] if l.startswith('CCZ ')] for a,b in ((LO,MID),(LO2,HI))]
    assert all(len(w)==19 for w in word_groups)
    sources=set().union(*(forms[c] for group in coeffs for c in group))
    assert 'ONE' not in sources
    guards=[columns[18]&columns[21],columns[27]&columns[21]]
    target={s:0 for s in sources}
    for group,words,guard in zip(coeffs,word_groups,guards):
        for c,w in zip(group,words):
            for s in forms[c]:target[s] ^= guard & columns[w]
    branch_records=[];failure_forms=[]
    for j,body in enumerate(branches):
        failure=forms[f'b{42000+j}'];complement=forms[f'b{42010+j}']
        assert failure<=sources and complement==failure ^ {'ONE'}
        failure_forms.append(failure)
        phase,proof=branch_anf(body)
        assert set(phase)<=sources
        residual=None
        for source in sorted(sources):
            difference=eval_poly(phase.get(source,set()),columns)^target[source]
            if source not in failure:
                assert difference==0,(j,source,'unexpected phase residual')
            elif residual is None:residual=difference
            else:assert difference==residual,(j,source,'inconsistent phase residual')
        assert residual is not None
        proof.update({'branch':j,'failure_parity_sources':sorted(failure),
                      'residual_input_pattern':residual,'residual_x':[i+1 for i in range(63) if residual>>i&1],
                      'all_source_direction_identities_exact':True,
                      'phase_difference_formula':'common residual(x) AND failure_parity; vanishes when selected'})
        branch_records.append(proof)
    assert AP.gf2_rank(failure_forms)==3
    # Both original selectors are checked as generic data/phase procedures,
    # independent of finite-domain data or source coefficient correlations.
    selector_records=[]
    for j,(start,stop,cstart,guardwire) in enumerate(((LO,MID,24256,18),(LO2,HI,24320,27))):
        qs=[z3.Bool(f'generic{j}_q{k}') for k in range(62)]
        cbits={f'b{cstart+i}':z3.Bool(f'generic{j}_coef{i}') for i in range(19)}
        cbits.update({f'b{cstart+19+i}':z3.Not(cbits[f'b{cstart+i}']) for i in range(19)})
        cbits[f'b{cstart+38}']=z3.BoolVal(False)
        q,bits,stack,phase,cost,_=AP.execute(base[start:stop],qs,cbits)
        assert not stack
        wanted=z3.BoolVal(False)
        for i,w in enumerate(word_groups[j]):wanted=z3.Xor(wanted,z3.And(cbits[f'b{cstart+i}'],qs[w]))
        wanted=z3.And(qs[guardwire],qs[21],wanted)
        fail=z3.Or([a!=b for a,b in zip(q,qs)]+[phase!=wanted,cost!=z3.If(z3.Or([cbits[f'b{cstart+i}'] for i in range(19)]),1,0)])
        solver=z3.Solver();solver.set(timeout=60000)
        selector_records.append(AP.check(solver,fail,f'original selector {j}: all data restored, generic dot-product phase and nonzero-coefficient cost'))
    return {'branch_structure':'three ordered mutually exclusive success branches; all-failed fallback is verbatim original selectors',
            'all_old_classical_writes':'only original second preparation moved before first selector; selectors perform no BIT writes',
            'branches':branch_records,'failure_rank':3,'source_bits':sorted(sources),'selector_semantics':selector_records,
            'fallback_probability_given_independent_sources':'1/8',
            'expected_new_cost_upper_bound':1.125,'expected_saving_lower_bound':2-2**(-18)-1.125,
            'status':'PASS' if all(r['result']=='unsat' for r in selector_records) else 'NOT_PROVEN'}


def prefix_audit(base,columns):
    solver=z3.Solver();solver.set(timeout=60000)
    x=z3.BitVec('independent_joint_input_x',22)
    solver.add(z3.UGE(x,1),z3.ULE(x,3133452))
    q0=[z3.Extract(i,i,x)==1 for i in range(22)]+[z3.BoolVal(False)]*40
    count=0
    def define(e):
        nonlocal count
        e=z3.simplify(e)
        if z3.is_true(e) or z3.is_false(e):return e
        b=z3.Bool(f'joint_ssa_{count}');count+=1;solver.add(b==e);return b
    q,bits,stack,_,_,events=AP.execute(base[:LO],q0,definition=define,prefix=True)
    assert not stack
    claims=[AP.check(solver,z3.And(q[21],z3.UGE(x,64)),'independent full prefix: q21 implies x<=63',x),
            AP.check(solver,z3.Or(q[28],q[40]),'independent full prefix: q28 and q40 zero for all legal x',x)]
    for value in range(1,64):
        mismatch=z3.Or([q[w]!=z3.BoolVal(bool(columns[w]>>(value-1)&1)) for w in range(62)])
        claims.append(AP.check(solver,z3.And(x==value,mismatch),f'independent prefix x={value}: all 62 values, all measurement outcomes',x))
    return {'ssa_nodes':count,'measurement_variables':events,'claims':claims,
            'status':'PASS' if all(r['result']=='unsat' for r in claims) else 'NOT_PROVEN'}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--prove',action='store_true',required=True);args=ap.parse_args()
    started=time.monotonic()
    bc,bh,base,bsha=AP.read(BASE);cc,ch,cand,csha=AP.read(CAND)
    assert bsha==AP.BASE_SHA and csha==SHA and bc.num_qubits==cc.num_qubits==62 and bh==ch
    cut=len(cand)-(len(base)-HI)
    assert base[:LO]==cand[:LO] and base[HI:]==cand[cut:]
    assert [l for l in base if l.startswith('Z_POW ')]==[l for l in cand if l.startswith('Z_POW ')]
    new=cand[LO:cut]
    old_bits={t for l in base for t in l.split() if t.startswith('b') and t[1:].isdigit()}
    new_bits={t for l in cand for t in l.split() if t.startswith('b') and t[1:].isdigit()}
    expected_fresh={f'b{b}' for b in (42000,42001,42002,42010,42011,42012,42020,42021,42022)}
    assert new_bits-old_bits==expected_fresh
    assert all(l.split()[0] not in ('BIT_STORE0','BIT_STORE1','BIT_INVERT','HMR','R') for l in base[LO:MID]+base[LO2:HI])
    columns=truth_snapshot(bh,base)
    local=local_audit(base,new,columns)
    out=ART/'audit_joint_selector.json'
    result={'status':'LOCAL_PASS_PREFIX_PENDING' if local['status']=='PASS' else 'NOT_PROVEN',
            'baseline_sha256':bsha,'candidate_sha256':csha,'qubits':62,'extra_qubits':0,
            'baseline_window':[LO,HI],'candidate_window':[LO,cut],
            'unchanged_prefix_and_suffix':True,'all_Z_POW_instructions_identical':True,
            'fresh_classical_bits':sorted(expected_fresh),'independent_truth_63_columns':columns,
            'local_audit':local,'official_verifier_shots':0,
            'source_independence_audit':'covered separately by review_discrete; local identities allow arbitrary source assignments',
            'metadata':{'command':'uv run --offline --with z3-solver python experiments/invsqrt/20261103_one_ccx/audit_joint_selector.py --prove',
                        'python':platform.python_version(),'kickmix':importlib.metadata.version('kickmix'),'z3':z3.get_version_string(),
                        'cwd':str(ROOT),'argv':sys.argv,'timestamp':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
                        'script_sha256':AP.sha(Path(__file__).read_bytes()),
                        'helper_audit_phase_cache_sha256':AP.sha(Path(AP.__file__).read_bytes())}}
    out.write_text(json.dumps(result,indent=2)+'\n')
    print('LOCAL_RESULT '+json.dumps({'status':result['status'],'path':str(out)}),flush=True)
    result['prefix_audit']=prefix_audit(base,columns)
    result['status']='PASS' if local['status']==result['prefix_audit']['status']=='PASS' else 'NOT_PROVEN'
    result['metadata']['seconds']=time.monotonic()-started
    out.write_text(json.dumps(result,indent=2)+'\n')
    print('FINAL_RESULT '+json.dumps({'status':result['status'],'path':str(out)}),flush=True)
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
