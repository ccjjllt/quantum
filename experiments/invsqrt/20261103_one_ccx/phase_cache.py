"""Manual finite-domain compression of the last Lphase CCZ selector.

Pinned bce baseline. The q27*q21 guard is true only for x=1,2,3.
We prove that fact with the full data prefix, then prove the nineteen word
bits at each of those inputs for all measurement outcomes. Their 3-row
truth table has a constant plus two nonconstant basis directions. Classical
XOR aggregation reduces the selector from nineteen coefficients to two.
No official verifier or submission is invoked.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import time
from pathlib import Path
import numpy as np
import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "artifacts/20261102_hw06_opt/invsqrt/baseline_hw06.kmb"
ART = ROOT / "artifacts/20261103_one_ccx/invsqrt"
SHA = "bce2948ff24e20fe59666d131f7fc4316a905103937272c52fdd39d494b6fe47"
LO, HI = 28345, 28783
WORDS = [14,16,17,19,20,22,29,30,31,25,26,45,46,47,48,52,55,56,58]


def load():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == SHA
    c = km.Circuit.from_file(BASE); buf = io.StringIO(); c.to_file(buf,format="kmx")
    lines=buf.getvalue().splitlines()
    header=[l for l in lines if l.startswith(("APPEND","REGISTER"))]
    ops=[l for l in lines if not l.startswith(("APPEND","REGISTER"))]
    return c,header,ops


def discover(c,header,ops):
    import sys
    sys.path.insert(0,str(ROOT/"data/competition/verifiers"))
    from invsqrt import verify_submission_invsqrt as official
    xs=np.array([1,2,3],dtype=np.uint64)
    xr,_=official.validate_registers(c,official.ProblemSpecInvSqrt.for_n_p(10))
    prefix=km.Circuit.from_file(io.StringIO("\n".join(header+ops[:LO])+"\n"),format="kmx")
    sim=km.Simulator(batch_size=3,seed=113)
    sim.write_across_shots(xr,official.to_bits(xs,22)); sim.do(prefix)
    m=np.asarray(sim.read_across_shots(km.array([km.q(q) for q in WORDS])))
    truth={q:sum(int(b)<<i for i,b in enumerate(row)) for q,row in zip(WORDS,m)}
    basis=[7]; basis_w=[]
    for q in WORDS:
        if truth[q] not in {0,*basis,*[a^b for a in basis for b in basis]}:
            basis.append(truth[q]);basis_w.append(q)
        if len(basis)==3:break
    if len(basis)!=3:raise ValueError(("unexpected rank",basis))
    reps={}
    for q in WORDS:
        for mask in range(8):
            val=0
            for j in range(3):
                if mask>>j&1:val^=basis[j]
            if val==truth[q]:reps[q]=mask;break
        else:raise ValueError((q,truth[q],basis))
    return truth,basis_w,reps


def prefix_ssa(ops,stop=LO):
    import z3
    solver=z3.Solver();solver.set(timeout=60000)
    q=[z3.Bool(f"x{j}") for j in range(22)]+[z3.BoolVal(False)]*40
    xv=z3.Sum([z3.If(q[j],1<<j,0) for j in range(22)])
    solver.add(xv>=1,xv<=3133452)
    bits={};stack=[];serial=0;events=0
    def fresh(e):
        nonlocal serial
        e=z3.simplify(e)
        if z3.is_true(e) or z3.is_false(e):return e
        r=z3.Bool(f"v{serial}");serial+=1;solver.add(r==e);return r
    for i,line in enumerate(ops[:stop]):
        p=line.split();k=p[0]
        if k=="PUSH_CONDITION":stack.append(bits.get(int(p[-1][1:]),z3.BoolVal(False)));continue
        if k=="POP_CONDITION":stack.pop();continue
        active=z3.And(*stack) if stack else z3.BoolVal(True)
        if "if" in p:active=z3.And(active,bits.get(int(p[p.index("if")+1][1:]),z3.BoolVal(False)))
        qs=[int(t[1:]) for t in p[1:] if t.startswith("q")]
        if k=="X":q[qs[0]]=fresh(z3.Xor(q[qs[0]],active))
        elif k=="CX":q[qs[1]]=fresh(z3.Xor(q[qs[1]],z3.And(active,q[qs[0]])))
        elif k=="CCX":q[qs[2]]=fresh(z3.Xor(q[qs[2]],z3.And(active,q[qs[0]],q[qs[1]])))
        elif k in ("SWAP","CSWAP"):
            a,b=qs[-2:];control=active if k=="SWAP" else z3.And(active,q[qs[0]])
            aa,bb=q[a],q[b];q[a]=fresh(z3.If(control,bb,aa));q[b]=fresh(z3.If(control,aa,bb))
        elif k in ("R","HMR"):
            q[qs[0]]=fresh(z3.And(q[qs[0]],z3.Not(active)))
            if k=="HMR":
                bit=int(p[2][1:]);r=z3.Bool(f"measurement_{events}");events+=1
                bits[bit]=fresh(z3.If(active,r,bits.get(bit,z3.BoolVal(False))))
        elif k.startswith("BIT_"):
            bit=int(p[1][1:]);old=bits.get(bit,z3.BoolVal(False))
            v=z3.Not(old) if k=="BIT_INVERT" else z3.BoolVal(k=="BIT_STORE1")
            bits[bit]=fresh(z3.If(active,v,old))
    assert not stack
    return solver,q,xv,bits,{"ssa_nodes":serial,"measurement_variables":events}


def joint_discover(c,header,ops):
    import sys,random
    sys.path.insert(0,str(ROOT/"data/competition/verifiers"))
    from invsqrt import verify_submission_invsqrt as official
    xs=np.arange(1,64,dtype=np.uint64)
    xr,_=official.validate_registers(c,official.ProblemSpecInvSqrt.for_n_p(10))
    prefix=km.Circuit.from_file(io.StringIO("\n".join(header+ops[:27775])+"\n"),format="kmx")
    sim=km.Simulator(batch_size=63,seed=113)
    sim.write_across_shots(xr,official.to_bits(xs,22));sim.do(prefix)
    mat=np.asarray(sim.read_across_shots(km.array([km.q(i) for i in range(62)])))
    truth=[sum(int(b)<<i for i,b in enumerate(row)) for row in mat]
    one=(1<<63)-1
    leaves={};forms={}
    for lo,hi in [(27643,27775),(28213,28345)]:
        for line in ops[lo:hi]:
            p=line.split();target=int(p[1][1:]);kind=p[0]
            if kind=="BIT_STORE0":forms[target]=0
            elif kind=="BIT_STORE1":forms[target]=1<<128
            elif kind=="BIT_INVERT":
                source=int(p[-1][1:])
                if source in forms:value=forms[source]
                else:
                    if source not in leaves:leaves[source]=1<<len(leaves)
                    value=leaves[source]
                forms[target]^=value
    targets=[]
    for source,bit in leaves.items():
        val=0
        for start,ctrl in [(24256,18),(24320,27)]:
            for j,w in enumerate(WORDS):
                if forms[start+j]&bit:val^=truth[ctrl]&truth[w]
        targets.append(val)
    def make_basis(columns):
        basis={}
        for j,vec in enumerate(columns):
            comb=1<<j
            while vec:
                pivot=vec.bit_length()-1
                if pivot not in basis:basis[pivot]=(vec,comb);break
                vv,cc=basis[pivot];vec^=vv;comb^=cc
        return basis
    def partial(vec,basis):
        comb=rem=0
        while vec:
            pivot=vec.bit_length()-1
            if pivot in basis:
                vv,cc=basis[pivot];vec^=vv;comb^=cc
            else:rem^=1<<pivot;vec^=1<<pivot
        return comb,rem
    rng=random.Random(8121);branches=[];failure_basis={}
    for trial in range(100):
        sel=rng.getrandbits(62)&~((1<<28)|(1<<40))
        u=0
        for j in range(62):
            if sel>>j&1:u^=truth[j]
        columns=[one]+truth+[u&t for t in truth]
        basis=make_basis(columns)
        if len(basis)!=62:continue
        solutions=[partial(t,basis) for t in targets]
        residuals={r for _,r in solutions if r}
        assert len(residuals)==1
        failure=sum(bool(r)<<j for j,(_,r) in enumerate(solutions))
        _,unseen=partial(failure,failure_basis)
        if not unseen:continue
        old=[v for v,_ in failure_basis.values()]
        failure_basis=make_basis(old+[failure])
        # Check every claimed decomposition on all 63 discovery rows exactly.
        for target,(comb,rem) in zip(targets,solutions):
            val=rem
            for j,col in enumerate(columns):
                if comb>>j&1:val^=col
            assert target==val
            assert all(not(comb>>(1+q)&1) and not(comb>>(63+q)&1) for q in (28,40))
        branches.append({"trial":trial,"u_wires":[j for j in range(62) if sel>>j&1],
                         "span_rank":len(basis),"failure_mask":failure,
                         "residual_vector":next(iter(residuals)),
                         "solutions":[{"source_bit":b,"column_mask":comb,"residual":bool(rem)}
                                      for b,(comb,rem) in zip(leaves,solutions)]})
        if len(branches)==3:break
    assert len(branches)==3 and len(failure_basis)==3
    return {"truth_63x62":truth,"source_bits":list(leaves),"branches":branches,
            "failure_rank":3,"original_masks":[[forms[s+i] for i in range(19)] for s in (24256,24320)]}


def joint_replacement(ops,doc):
    # Move the fourth group's classical-only preparation earlier. The third
    # group's classical masks are already available at 27775.
    out=list(ops[28213:28345])
    for j,br in enumerate(doc["branches"]):
        out.append(f"BIT_STORE0 b{42000+j}")
        for k,b in enumerate(doc["source_bits"]):
            if br["failure_mask"]>>k&1:out.append(f"BIT_INVERT b{42000+j} if b{b}")
        out += [f"BIT_STORE1 b{42010+j}",f"BIT_INVERT b{42010+j} if b{42000+j}"]
    for j,br in enumerate(doc["branches"]):
        out.append(f"PUSH_CONDITION if b{42010+j}")
        computes=[f"CX q{w} q28" for w in br["u_wires"]]
        out+=computes+["CCX q21 q28 q40"]
        for row in br["solutions"]:
            mask=row["column_mask"];b=row["source_bit"]
            if mask&1:out.append(f"Z q21 if b{b}")
            for q in range(62):
                if mask>>(q+1)&1:
                    out.append(("Z q21" if q==21 else f"CZ q21 q{q}")+f" if b{b}")
                if mask>>(q+63)&1:
                    out.append(f"CZ q40 q{q} if b{b}")
        out += [f"HMR q40 b{42020+j}",f"CZ q21 q28 if b{42020+j}"]+computes[::-1]
        out.append("POP_CONDITION")
        out.append(f"PUSH_CONDITION if b{42000+j}")
    # All three failed: original selectors, with unchanged coefficient bits.
    out+=ops[27775:28213]+ops[28345:28783]
    out += ["POP_CONDITION"]*3
    return out


def joint_prefix_prove(ops,truth):
    import z3
    s,q,xv,_,stats=prefix_ssa(ops,27775)
    rows=[]
    def claim(label,formula):
        start=time.monotonic();s.push();s.add(formula);r=s.check()
        rec={"label":label,"result":str(r),"seconds":time.monotonic()-start}
        if r==z3.sat:rec["counterexample_x"]=s.model().eval(xv).as_long()
        if r==z3.unknown:rec["reason"]=s.reason_unknown()
        s.pop();rows.append(rec);print("JOINT_CLAIM",rec,flush=True)
        return r==z3.unsat
    if not claim("q21 implies x<=63",z3.And(q[21],xv>=64)):
        return {**stats,"claims":rows,"pass":False}
    if not claim("q28 and q40 clean",z3.Or(q[28],q[40])):
        return {**stats,"claims":rows,"pass":False}
    for x in range(1,64):
        if not claim(f"all 62 snapshot wires at x={x}, all measurements",
                     z3.And(xv==x,z3.Or([q[j]!=z3.BoolVal(bool(truth[j]>>(x-1)&1)) for j in range(62)]))):
            break
    return {**stats,"claims":rows,"pass":len(rows)==65 and all(r["result"]=="unsat" for r in rows)}


def joint_main(args):
    c,header,ops=load();doc=joint_discover(c,header,ops);repl=joint_replacement(ops,doc)
    assert all(not any(f"q{q}" in line.split() for q in (28,40)) for line in ops[27775:28783])
    nc=km.Circuit.from_file(io.StringIO("\n".join(header+ops[:27775]+repl+ops[28783:])+"\n"),format="kmx")
    ART.mkdir(parents=True,exist_ok=True);p=ART/"phase_joint_selector.kmb";nc.to_file(p,format="kmb")
    doc.update(baseline_sha256=SHA,window=[27775,28783],replacement=repl,
               candidate_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),qubits=nc.num_qubits,
               status="candidate built; discovery matrix identities exact on sampled 63 input snapshots; prefix proof pending",
               official_validation="not run",expected_saving_lower_bound=2-2**-18-1.125)
    report=ART/"phase_joint_selector.json";report.write_text(json.dumps(doc,indent=2)+"\n")
    print("JOINT_BUILT",doc["candidate_sha256"],"Q",nc.num_qubits,"ops",len(repl),flush=True)
    if args.prove:
        doc["prefix_proof"]=joint_prefix_prove(ops,doc["truth_63x62"])
        doc["status"]="prefix proof complete; emission/phase/cost independent audit pending" if doc["prefix_proof"]["pass"] else "prefix proof incomplete"
        report.write_text(json.dumps(doc,indent=2)+"\n")


def joint_certify_existing():
    """Attach proof composition and provenance; never rewrite candidate bytes."""
    import z3,sys,importlib.metadata,datetime,zoneinfo
    c,header,ops=load()
    report=ART/"phase_joint_selector.json";doc=json.loads(report.read_text())
    candidate=ART/"phase_joint_selector.kmb"
    before=hashlib.sha256(candidate.read_bytes()).hexdigest()
    assert before==doc["candidate_sha256"]
    rebuilt=km.Circuit.from_file(io.StringIO("\n".join(header+ops[:27775]+joint_replacement(ops,doc)+ops[28783:])+"\n"),format="kmx")
    raw=io.BytesIO();rebuilt.to_file(raw,format="kmb")
    assert raw.getvalue()==candidate.read_bytes()
    truth=doc["truth_63x62"];one=(1<<63)-1;vectors=0
    for br in doc["branches"]:
        u=0
        for q in br["u_wires"]:
            assert q not in (28,40);u^=truth[q]
        columns=[one]+truth+[u&t for t in truth]
        for j,row in enumerate(br["solutions"]):
            target=0
            for group,ctrl in enumerate((18,27)):
                for i,w in enumerate(WORDS):
                    if doc["original_masks"][group][i]>>j&1:target^=truth[ctrl]&truth[w]
            represented=br["residual_vector"] if row["residual"] else 0
            for col,value in enumerate(columns):
                if row["column_mask"]>>col&1:represented^=value
            assert represented==target
            assert bool(br["failure_mask"]>>j&1)==row["residual"]
            vectors+=1
    # Generic cache, including its event-dependent phase, for any selection
    # condition A and any input u,d. This is not a sampled-measurement check.
    active,u,d,event=z3.Bools("selected u d new_measurement")
    uq=z3.And(active,u);product=z3.And(active,d,uq)
    reset_product=z3.And(product,z3.Not(active))
    uncomputed_u=z3.Xor(uq,z3.And(active,u))
    hmr_phase=z3.And(active,product,event)
    fixup_phase=z3.And(active,d,uq,event)
    s=z3.Solver();s.add(z3.Or(reset_product,uncomputed_u,hmr_phase!=fixup_phase))
    gadget=str(s.check());assert gadget=="unsat"
    coverage=[]
    for mask in range(8):
        f=[bool(mask>>j&1) for j in range(3)]
        selected=[not f[0],f[0] and not f[1],f[0] and f[1] and not f[2],all(f)]
        assert sum(selected)==1;coverage.append(selected.index(True))
    audit_path=ART/"audit_joint_selector.json"
    audit=json.loads(audit_path.read_text())
    assert audit["candidate_sha256"]==before and audit["local_audit"]["status"]=="PASS"
    assert audit["unchanged_prefix_and_suffix"] and audit["all_Z_POW_instructions_identical"]
    assert doc["prefix_proof"]["pass"]
    doc["generation_composition_proof"]={
        "status":"PASS",
        "candidate_bytes_reproduced_in_memory":True,
        "matrix_source_vectors_checked":vectors,
        "exact_input_rows_per_vector":63,
        "generic_cache_data_reset_and_HMR_phase_cancellation":gadget,
        "priority_case_for_each_failure_mask_0_to_7":coverage,
        "proof_chain":[
            "Full original prefix: q21 implies x<=63; all 62 wires fixed on each x=1..63 for every original measurement outcome; q28/q40 globally zero.",
            "Each candidate branch phase is q21 times the exact linear/quadratic column representation; its sole residual is common_R times its failure parity, which is zero whenever that branch is selected.",
            "Cache computation uses q28/q40 only, new HMR phase cancels under the original unchanged u frame, and both helpers return to zero.",
            "Three priority branches and original-selector fallback partition every assignment of the three failure parities; outside q21 all candidate and original phases vanish.",
            "Independent actual-byte ANF audit verifies all 62 outputs and new measurement phase cancellation for each emitted branch; generic original-selector Z3 proofs establish their dot-product phases and restored data."
        ],
        "independent_actual_byte_local_audit":str(audit_path.relative_to(ROOT)),
        "independent_local_audit_status":audit["local_audit"]["status"],
        "official_verification":"not run by this generator"
    }
    doc["provenance"]={
        "generation_and_prefix_command":"uv run --offline --with z3-solver python -B experiments/invsqrt/20261103_one_ccx/phase_cache.py --joint --prove",
        "composition_and_metadata_command":"uv run --offline --with z3-solver python -B experiments/invsqrt/20261103_one_ccx/phase_cache.py --joint-certify",
        "python":sys.version,"kickmix":importlib.metadata.version("kickmix"),
        "z3_solver":importlib.metadata.version("z3-solver"),"numpy":importlib.metadata.version("numpy"),
        "platform_kickmix_module":km.__file__,
        "recorded_at_shanghai":datetime.datetime.now(zoneinfo.ZoneInfo("Asia/Shanghai")).isoformat(),
        "script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "baseline_sha256":SHA,"candidate_sha256":before,
        "solver_timeout_ms_per_claim":60000
    }
    doc["status"]="generation proof composition PASS; full-prefix and all-branch local data/phase obligations discharged; official validation managed separately"
    report.write_text(json.dumps(doc,indent=2)+"\n")
    assert hashlib.sha256(candidate.read_bytes()).hexdigest()==before
    print("JOINT_COMPOSITION_PASS",before,"matrix_vectors",vectors,"candidate_bytes_unchanged",flush=True)


def prove(ops,truth):
    import z3
    t=time.monotonic();s,q,xv,bits,stats=prefix_ssa(ops)
    rec={"build_seconds":time.monotonic()-t,**stats,"claims":[]}
    def claim(label,formula):
        started=time.monotonic();s.push();s.add(formula);r=s.check()
        row={"label":label,"result":str(r),"seconds":time.monotonic()-started}
        if r==z3.sat:row["counterexample_x"]=s.model().eval(xv).as_long()
        if r==z3.unknown:row["reason"]=s.reason_unknown()
        s.pop();rec["claims"].append(row);print("CLAIM",row,flush=True)
    claim("q27*q21 implies x in {1,2,3}",z3.And(q[27],q[21],xv>=4))
    for x in (1,2,3):
        claim(f"all nineteen words exact for x={x}, all measurement outcomes",
              z3.And(xv==x,z3.Or([q[w]!=z3.BoolVal(bool(truth[w]>>(x-1)&1)) for w in WORDS])))
    rec["pass"]=all(r["result"]=="unsat" for r in rec["claims"])
    return rec


def replacement(basis_w,reps):
    out=[]
    for j in range(3):
        out.append(f"BIT_STORE0 b{41000+j}")
        for i,w in enumerate(WORDS):
            if reps[w]>>j&1:out.append(f"BIT_INVERT b{41000+j} if b{24320+i}")
    u,v=basis_w
    out += ["CZ q27 q21 if b41000","PUSH_CONDITION if b41001",
            f"CX q{v} q{u} if b41002",f"CCZ q27 q21 q{u}",
            f"CX q{v} q{u} if b41002","POP_CONDITION",
            "BIT_STORE1 b41003","BIT_INVERT b41003 if b41001",
            "PUSH_CONDITION if b41003",f"CCZ q27 q21 q{v} if b41002","POP_CONDITION"]
    return out


def selector_algebra(ops,repl,basis_w,reps):
    """Prove whole selector data identity and phase equality under its contract."""
    import z3
    initial=[z3.Bool(f"entry_q{i}") for i in range(62)]
    coeff={24320+i:z3.Bool(f"coeff_{i}") for i in range(19)}
    coeff[24358]=z3.BoolVal(False)
    # Original cached complements are computed immediately before the window.
    for i in range(19):coeff[24339+i]=z3.Not(coeff[24320+i])
    def run(lines):
        q=list(initial);bb=dict(coeff);stack=[];phase=z3.BoolVal(False);cost=[]
        for line in lines:
            p=line.split();k=p[0]
            if k=="PUSH_CONDITION":stack.append(bb[int(p[-1][1:])]);continue
            if k=="POP_CONDITION":stack.pop();continue
            active=z3.And(*stack) if stack else z3.BoolVal(True)
            if "if" in p:active=z3.And(active,bb[int(p[p.index("if")+1][1:])])
            qs=[int(t[1:]) for t in p[1:] if t.startswith("q")]
            if k=="CX":q[qs[1]]=z3.Xor(q[qs[1]],z3.And(active,q[qs[0]]))
            elif k in ("CZ","CCZ"):
                phase=z3.Xor(phase,z3.And(active,*[q[j] for j in qs]))
                if k=="CCZ":cost.append(z3.If(active,1,0))
            elif k.startswith("BIT_"):
                bit=int(p[1][1:]);old=bb.get(bit,z3.BoolVal(False))
                val=z3.Not(old) if k=="BIT_INVERT" else z3.BoolVal(k=="BIT_STORE1")
                bb[bit]=z3.If(active,val,old)
            else:raise ValueError(line)
        assert not stack
        return q,phase,z3.Sum(cost),bb
    oq,op,oc,_=run(ops[LO:HI]);nq,np,nc,nb=run(repl)
    guard=z3.And(initial[27],initial[21]);relations=[]
    for w in WORDS:
        mask=reps[w];val=z3.BoolVal(bool(mask&1))
        for j,bw in enumerate(basis_w,1):
            if mask>>j&1:val=z3.Xor(val,initial[bw])
        relations.append(z3.Implies(guard,initial[w]==val))
    solver=z3.Solver();solver.set(timeout=60000);solver.add(*relations)
    solver.add(z3.Or([a!=b for a,b in zip(oq,nq)]+[op!=np]))
    equiv=solver.check()
    solver=z3.Solver();solver.set(timeout=60000)
    expected_old=z3.If(z3.Or(*[coeff[24320+i] for i in range(19)]),1,0)
    expected_new=z3.If(z3.Or(nb[41001],nb[41002]),1,0)
    solver.add(z3.Or(oc!=expected_old,nc!=expected_new));cost=solver.check()
    # Each original coefficient is an affine GF(2) function of unconditional
    # HMR outputs. Recover those masks from the adjacent preparation block.
    forms={};leaves={}
    for line in ops[28213:LO]:
        p=line.split();kind=p[0]
        if not kind.startswith("BIT_"):continue
        target=int(p[1][1:])
        if kind=="BIT_STORE0":forms[target]=0
        elif kind=="BIT_STORE1":forms[target]=1<<128
        else:
            source=int(p[-1][1:])
            if source in forms:value=forms[source]
            else:
                if source not in leaves:leaves[source]=1<<len(leaves)
                value=leaves[source]
            forms[target]^=value
    rows=[forms[24320+i] for i in range(19)]
    new_rows=[0,0,0]
    for i,w in enumerate(WORDS):
        for j in range(3):
            if reps[w]>>j&1:new_rows[j]^=rows[i]
    def rank(vectors):
        basis={}
        for vec in vectors:
            while vec:
                pivot=vec.bit_length()
                if pivot not in basis:basis[pivot]=vec;break
                vec^=basis[pivot]
        return len(basis)
    old_rank,new_rank=rank(rows),rank(new_rows[1:])
    # Check source measurement declarations are unconditional and independent.
    stack=[];declarations={};writes={}
    for i,line in enumerate(ops[:28213]):
        p=line.split();kind=p[0]
        if kind=="PUSH_CONDITION":stack.append(p[-1])
        elif kind=="POP_CONDITION":stack.pop()
        elif kind=="HMR":
            bit=int(p[2][1:]);writes[bit]=(i,kind)
            if bit in leaves:declarations[bit]={"op":i,"unconditional":not stack and "if" not in p}
        elif kind.startswith("BIT_"):writes[int(p[1][1:])]=(i,kind)
    assert all(declarations[b]["unconditional"] and writes[b]==(declarations[b]["op"],"HMR") for b in leaves)
    return {"equivalence_under_finite_domain_contract":str(equiv),"cost_formula":str(cost),
            "old_mask_rank":old_rank,"new_mask_rank":new_rank,
            "expected_old_ccz":1-2**(-old_rank),"expected_new_ccz":1-2**(-new_rank),
            "expected_equivalent_saving":2**(-new_rank)-2**(-old_rank),
            "independent_measurement_sources":declarations,
            "pass":equiv==z3.unsat and cost==z3.unsat}


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--prove",action="store_true");ap.add_argument("--joint",action="store_true");ap.add_argument("--joint-certify",action="store_true");args=ap.parse_args()
    if args.joint_certify:return joint_certify_existing()
    if args.joint:return joint_main(args)
    c,header,ops=load();truth,basis,reps=discover(c,header,ops)
    rec={"baseline_sha256":SHA,"window":[LO,HI],"truth":truth,"basis_wires":basis,"representations":reps,
         "status":"discovery only", "official_validation":"not run"}
    print("DISCOVERY",json.dumps(rec),flush=True)
    if args.prove:
        rec["proof"]=prove(ops,truth)
        if rec["proof"]["pass"]:
            repl=replacement(basis,reps);rec["replacement"]=repl
            rec["selector_algebra"]=selector_algebra(ops,repl,basis,reps)
            assert rec["selector_algebra"]["pass"]
            nc=km.Circuit.from_file(io.StringIO("\n".join(header+ops[:LO]+repl+ops[HI:])+"\n"),format="kmx")
            ART.mkdir(parents=True,exist_ok=True);p=ART/"phase_last_selector.kmb";nc.to_file(p,format="kmb")
            rec.update(status="finite-domain data, all-branch phase/data composition and executed-cost formula proved; independent audit and official validation pending",
                       candidate_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),qubits=nc.num_qubits)
    ART.mkdir(parents=True,exist_ok=True)
    (ART/"phase_last_selector.json").write_text(json.dumps(rec,indent=2)+"\n")


if __name__=="__main__":main()
