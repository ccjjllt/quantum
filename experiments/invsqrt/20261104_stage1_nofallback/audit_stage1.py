"""Independent audit for stage1 nofallback candidate.

Reads ACTUAL OLD bce baseline and stage1 KMB. Does not import stage1 generator.
Verifies joint no-fallback structure, ANF phases, prefix contract, covering, cost,
and tail three_and equivalence. No official verifier invoked here.
"""
from __future__ import annotations
import argparse, collections, hashlib, importlib.metadata, io, json, platform, sys, time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import kickmix as km
import z3

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT/"experiments/invsqrt/20261103_one_ccx"))
import audit_phase_cache as AP
OLD_BASE = ROOT/"artifacts/20261102_hw06_opt/invsqrt/baseline_hw06.kmb"
OLD_SHA = "bce2948ff24e20fe59666d131f7fc4316a905103937272c52fdd39d494b6fe47"
CAND = ROOT/"artifacts/20261104_stage1_nofallback/invsqrt/stage1_nofallback.kmb"
ART = ROOT/"artifacts/20261104_stage1_nofallback/invsqrt"
# Pinned three_and evidence (strengthened tail audit, 2026-11-05)
THREE_AND_KMB = ROOT/"artifacts/20261103_one_ccx/invsqrt/tail_cache_three_and.kmb"
THREE_AND_KMB_SHA = "c2c255036961fcddbbabca84c231d4101ae928cbf34ae9a3da75926b7b665a0f"
THREE_AND_PROOF = ROOT/"artifacts/20261103_one_ccx/invsqrt/tail_cache_three_and_proof.json"
THREE_AND_PROOF_SHA = "9031f7f5a834df380793dc35721de15c01192d434825cf9296adbc86b48ef625"
THREE_AND_AUDIT = ROOT/"artifacts/20261103_one_ccx/invsqrt/audit_tail_cache_three_and.json"
THREE_AND_AUDIT_SHA = "34403ce9f0f75d276f4749dfb320bd09091b364c7899caa2bb2c2d7e760fc373"
TAIL_CONTENT_SHA = "a847244739d2b1e0534f9373a87a7bf67d2e7b0bc591b199bf42e23ce8b5f764"
TAIL_LEN = 95
LO, MID, PREP2, LO2, HI = 27775, 28213, 28213, 28345, 28783
TLO, THI = 47113, 47186

def load(path):
    raw=path.read_bytes()
    c=km.Circuit.from_file(path)
    buf=io.StringIO(); c.to_file(buf,format="kmx")
    hdr,ops=[],[]
    for line in buf.getvalue().splitlines():
        (hdr if line.startswith(("APPEND","REGISTER")) else ops).append(line)
    return c,hdr,ops,hashlib.sha256(raw).hexdigest()

def mul(a,b):
    out=set()
    for x in a:
        for y in b:
            z=x|y
            if z in out:out.remove(z)
            else:out.add(z)
    return out

def branch_anf(lines):
    entry=[{1<<q} if q not in (28,40) else set() for q in range(62)]
    q=[set(v) for v in entry];phase={};measurements=[];ccx=0
    for line in lines:
        p=line.split();k=p[0];qs=[int(t[1:]) for t in p[1:] if t.startswith('q')]
        if k in ('X','CX','CCX','HMR'):
            assert 'if' not in p, ('conditional data in successful branch',line)
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

def find_subseq(hay, needle, start=0):
    n=len(needle)
    for i in range(start, len(hay)-n+1):
        if hay[i:i+n]==needle:
            return i
    return -1

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--prove",action="store_true")
    ap.add_argument("--candidate",type=Path,default=CAND)
    ap.add_argument("--baseline",type=Path,default=OLD_BASE)
    ap.add_argument("--baseline-sha",type=str,default=OLD_SHA)
    args=ap.parse_args()
    started=time.monotonic()
    bc,bh,base,bsha=load(args.baseline)
    cc,ch,cand,csha=load(args.candidate)
    assert bsha==args.baseline_sha, bsha
    assert bc.num_qubits==cc.num_qubits==62 and bh==ch
    assert [l for l in base if l.startswith("Z_POW ")]==[l for l in cand if l.startswith("Z_POW ")]
    # locate joint_end via middle anchor OLD[28783:28793]
    anchor_mid=base[HI:HI+10]
    joint_end=find_subseq(cand, anchor_mid, LO)
    assert joint_end>LO, "joint_end not found"
    joint_new=cand[LO:joint_end]
    # locate tail: anchor OLD[47186:47196] in cand after joint_end
    anchor_tail=base[THI:THI+10]
    tail_end=find_subseq(cand, anchor_tail, joint_end)
    assert tail_end>joint_end, "tail_end not found"
    # middle must match
    mid_len=47113-HI
    assert cand[joint_end:joint_end+mid_len]==base[HI:HI+mid_len], "middle mismatch"
    tail_new=cand[joint_end+mid_len:tail_end]
    assert cand[tail_end:]==base[THI:], "suffix mismatch"
    assert base[:LO]==cand[:LO], "prefix mismatch"
    print(f"JOINT_NEW len {len(joint_new)} TAIL_NEW len {len(tail_new)} joint_end {joint_end} tail_end {tail_end}",flush=True)
    # parse joint_new: must start with second prep block
    assert joint_new[:LO2-PREP2]==base[PREP2:LO2]
    # find first push
    first_push=next(i for i,l in enumerate(joint_new) if l.startswith("PUSH_CONDITION"))
    classical=joint_new[:first_push]
    assert all(l.startswith("BIT_") for l in classical)
    # parse 3 branches, no fallback
    pos=first_push
    branches=[]
    for j in range(3):
        assert joint_new[pos]==f"PUSH_CONDITION if b{42010+j}", (j,joint_new[pos])
        end=next(i for i in range(pos+1,len(joint_new)) if joint_new[i]=="POP_CONDITION")
        body=joint_new[pos+1:end]
        assert not any(l.startswith("PUSH_CONDITION") for l in body)
        branches.append(body)
        assert joint_new[end+1]==f"PUSH_CONDITION if b{42000+j}", (j,joint_new[end+1])
        pos=end+2
    # remainder must be exactly 3 POPs (no fallback)
    assert joint_new[pos:]==["POP_CONDITION"]*3, joint_new[pos:pos+5]
    print("STRUCTURE_OK 3 branches no fallback",flush=True)
    # local audit: same as before but with new branches
    # need columns truth, forms etc.
    prefix=km.Circuit.from_file(io.StringIO("\n".join(bh+base[:LO])+"\n"),format="kmx")
    sim=km.Simulator(batch_size=63,seed=314159);sim.use_same_registers_as(prefix)
    for i in range(63):sim.write_within_shot('x',i,i+1)
    sim.do(prefix)
    columns=[sum(int(v)<<i for i,v in enumerate(sim.read_across_shots(km.q(q)))) for q in range(62)]
    assert columns[21]==(1<<63)-1 and columns[28]==columns[40]==0
    prep1=AP.affine_classical(base[27643:LO])
    forms=AP.affine_classical(classical,prep1)
    WORDS=[14,16,17,19,20,22,29,30,31,25,26,45,46,47,48,52,55,56,58]
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
    # check failure forms XOR zero and covering
    failure_forms=[]
    for j in range(3):
        f=forms[f'b{42000+j}']
        assert f<=sources
        assert forms[f'b{42010+j}']==f ^ {'ONE'}
        failure_forms.append(f)
    # XOR of all three must be empty (f2 = f0 xor f1)
    assert (failure_forms[0] ^ failure_forms[1] ^ failure_forms[2])==set(), f"xor not zero: {[sorted(s) for s in failure_forms]}"
    assert AP.gf2_rank(failure_forms)==2, "expected rank 2 dependent"
    print(f"FAILURE_XOR_ZERO rank 2 masks {[hex(sum(1<<i for i,s in enumerate(sorted(sources)) if s in ff)) for ff in failure_forms]}",flush=True)
    # branch phases
    branch_records=[]
    for j,body in enumerate(branches):
        failure=forms[f'b{42000+j}']
        phase,proof=branch_anf(body)
        assert set(phase)<=sources
        residual=None
        for source in sorted(sources):
            diff=eval_poly(phase.get(source,set()),columns)^target[source]
            if source not in failure:
                assert diff==0,(j,source,'unexpected phase residual')
            elif residual is None:residual=diff
            else:assert diff==residual,(j,source,'inconsistent residual')
        assert residual is not None
        proof.update({'branch':j,'failure_parity_sources':sorted(failure),
                      'residual_x':[i+1 for i in range(63) if residual>>i&1]})
        branch_records.append(proof)
    print("BRANCH_PHASES_OK",flush=True)
    # generic selector semantics (same as before)
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
        selector_records.append(AP.check(solver,fail,f'original selector {j}'))
    # prefix audit
    def prefix_audit():
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
        claims=[AP.check(solver,z3.And(q[21],z3.UGE(x,64)),'q21 implies x<=63',x),
                 AP.check(solver,z3.Or(q[28],q[40]),'q28/q40 zero',x)]
        for value in range(1,64):
            mismatch=z3.Or([q[w]!=z3.BoolVal(bool(columns[w]>>(value-1)&1)) for w in range(62)])
            claims.append(AP.check(solver,z3.And(x==value,mismatch),f'x={value}',x))
        return {'ssa_nodes':count,'measurement_variables':events,'claims':claims,
                'status':'PASS' if all(r['result']=='unsat' for r in claims) else 'NOT_PROVEN'}
    pref=prefix_audit()
    print("PREFIX",pref['status'],flush=True)
    # cost: new expected 1.0 (exactly one branch per shot given covering, but need to prove triple-failure impossible)
    # Prove triple failure impossible via GF2 already (xor zero) + also need to show no assignment gives all three failures=1?
    # With f2=f0 xor f1, (1,1,1) would require 1 xor1 xor1=1 !=0, impossible. Since we proved set xor empty, any assignment's parity xor is 0, so count of 1s even, cannot be 3.
    # Formal Z3 check on failure parities as functions of source bits:
    src_vars={s:z3.Bool(f'src_{s}') for s in sources}
    def parity(form):
        v=z3.BoolVal(False)
        for s in form:v=z3.Xor(v,src_vars[s])
        return v
    s=z3.Solver();s.add(parity(failure_forms[0]),parity(failure_forms[1]),parity(failure_forms[2]))
    triple=s.check()
    assert str(triple)=="unsat", f"triple failure reachable: {triple}"
    print("TRIPLE_FAILURE_UNSAT",flush=True)
    # tail audit (strengthened 2026-11-05): pin three_and KMB/proof/audit, require
    # proof status + subproofs, then compare the actual 95 tail instructions item by item.
    # The old bit-name-only shortcut is deleted.
    assert hashlib.sha256(THREE_AND_KMB.read_bytes()).hexdigest()==THREE_AND_KMB_SHA, "three_and kmb hash"
    assert hashlib.sha256(THREE_AND_PROOF.read_bytes()).hexdigest()==THREE_AND_PROOF_SHA, "three_and proof hash"
    assert hashlib.sha256(THREE_AND_AUDIT.read_bytes()).hexdigest()==THREE_AND_AUDIT_SHA, "three_and audit hash"
    proof_doc=json.loads(THREE_AND_PROOF.read_text())
    assert proof_doc.get("candidate_sha256")==THREE_AND_KMB_SHA, proof_doc.get("candidate_sha256")
    assert proof_doc.get("local_miter")=="unsat", proof_doc.get("local_miter")
    assert all(v=="unsat" for v in proof_doc.get("clean_entry_proofs",{}).values()), proof_doc.get("clean_entry_proofs")
    audit_doc=json.loads(THREE_AND_AUDIT.read_text())
    assert audit_doc.get("status")=="PASS", audit_doc.get("status")
    assert audit_doc.get("candidate_sha256")==THREE_AND_KMB_SHA, audit_doc.get("candidate_sha256")
    # Load the pinned three_and actual tail bytes and compare item by item.
    _t3c,_t3h,_t3ops,_t3sha=load(THREE_AND_KMB)
    assert _t3sha==THREE_AND_KMB_SHA
    pinned_tail=_t3ops[47113:47113+TAIL_LEN]
    assert len(pinned_tail)==TAIL_LEN, len(pinned_tail)
    assert hashlib.sha256(("\n".join(pinned_tail)).encode()).hexdigest()==TAIL_CONTENT_SHA, "pinned tail content"
    assert len(tail_new)==TAIL_LEN, f"candidate tail len {len(tail_new)} != {TAIL_LEN}"
    mismatches=[(i,a,b) for i,(a,b) in enumerate(zip(pinned_tail,tail_new)) if a!=b]
    assert not mismatches, f"tail item mismatches: {mismatches[:5]}"
    assert hashlib.sha256(("\n".join(tail_new)).encode()).hexdigest()==TAIL_CONTENT_SHA, "candidate tail content"
    print(f"TAIL_STRICT_OK len {TAIL_LEN} sha {TAIL_CONTENT_SHA}",flush=True)
    out=ART/"audit_stage1_nofallback.json"
    result={'status':'PASS' if all(r['result']=='unsat' for r in selector_records) and pref['status']=='PASS' else 'NOT_PROVEN',
            'baseline_sha256':OLD_SHA,'candidate_sha256':csha,'qubits':62,
            'joint_new_len':len(joint_new),'tail_new_len':len(tail_new),
            'failure_forms_sizes':[len(f) for f in failure_forms],
            'branch_records':branch_records,'selector_semantics':selector_records,
            'prefix_audit':pref,'triple_failure':str(triple),
            'expected_new_cost':1.0,'expected_extra_saving_vs_new_baseline_C':0.125,
            'metadata':{'seconds':time.monotonic()-started,'python':platform.python_version(),
                        'kickmix':importlib.metadata.version('kickmix'),'z3':z3.get_version_string()}}
    out.write_text(json.dumps(result,indent=2)+"\n")
    print('FINAL_RESULT '+json.dumps({'status':result['status'],'path':str(out)}),flush=True)
    return 0 if result['status']=='PASS' else 1

def eval_poly(poly,columns):
    ans=0
    for monomial in poly:
        term=(1<<63)-1
        while monomial:
            bit=monomial & -monomial;term &= columns[bit.bit_length()-1];monomial ^= bit
        ans ^= term
    return ans

if __name__=="__main__":raise SystemExit(main())
