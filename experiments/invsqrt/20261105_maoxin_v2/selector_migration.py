"""Manually build and audit the old nofallback method on Maoxin V2.

No hashes and no full official verification. Reuses locally authored algebra
helpers, not downloaded notebook code. New-prefix SSA and native sampling are
explicit parts of this command. The submitted ZIP is never changed.
"""
from __future__ import annotations
import importlib.util
import io
import json
import platform
import sys
import time
from fractions import Fraction
from pathlib import Path

import kickmix as km
import numpy as np
import z3

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "artifacts/20261105_maoxin_v2/invsqrt"
BASE = ROOT / "artifacts/20261105_maoxin_v2/release/invsqrt.kmb"
OLD = ROOT / "artifacts/20261104_public_refresh/kirill_v5_invsqrt.kmb"
LO, MID, LO2, HI = 27911, 28349, 28481, 28919
PRE1, PRE2 = (27779, 27911), (28349, 28481)


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


M = module("maoxin_migration_support", "experiments/invsqrt/20261104_public62_optimization/migrate_public62_nofallback.py")
A = module("maoxin_algebra_support", "experiments/invsqrt/20261104_public62_optimization/audit_migrated.py")
S = module("maoxin_sampling_support", "experiments/invsqrt/20261104_public62_optimization/sample_migrated.py")


def load(path):
    c = km.Circuit.from_file(path)
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    return c, [l for l in lines if l.startswith(("APPEND", "REGISTER"))], [l for l in lines if not l.startswith(("APPEND", "REGISTER"))]


def main():
    t0 = time.monotonic()
    c, hdr, base = load(BASE)
    _, _, old = load(OLD)
    assert c.num_qubits == 62 and len(base) == 48261
    assert base[LO:HI] == old[27745:28753]
    assert base[PRE1[0]:LO] == old[27613:27745]
    assert base[PRE2[0]:PRE2[1]] == old[28183:28315]
    assert c.num_bits == 42006
    M.LO, M.PRE1, M.PRE2 = LO, PRE1, PRE2
    doc = M.discover(hdr, base, c)
    replacement = M.joint_replacement(base, doc)
    full = base[:LO] + replacement + base[HI:]
    candidate = km.Circuit.from_file(io.StringIO("\n".join(hdr + full) + "\n"), format="kmx")
    assert candidate.num_qubits == 62
    assert [l for l in base if l.startswith("Z_POW")] == [l for l in full if l.startswith("Z_POW")]
    ART.mkdir(parents=True, exist_ok=True)
    outpath = ART / "maoxin_v2_nofallback.kmb"
    candidate.to_file(outpath, format="kmb")
    first = next(i for i,l in enumerate(replacement) if l.startswith("PUSH_CONDITION"))
    classical = replacement[:first]
    branches, pos = [], first
    for j in range(3):
        assert replacement[pos] == f"PUSH_CONDITION if b{42009+j}"
        end = next(i for i in range(pos+1,len(replacement)) if replacement[i] == "POP_CONDITION")
        branches.append(replacement[pos+1:end])
        assert replacement[end+1] == f"PUSH_CONDITION if b{42006+j}"
        pos = end+2
    assert replacement[pos:] == ["POP_CONDITION"]*3
    columns = doc["truth_63x62"]
    prep = A.AP.affine_classical(base[PRE1[0]:LO])
    forms = A.AP.affine_classical(classical, prep)
    coeffs = [[f"b{start+i}" for i in range(19)] for start in (24256,24320)]
    words = [[int(l.split()[3][1:]) for l in base[a:b] if l.startswith("CCZ ")] for a,b in ((LO,MID),(LO2,HI))]
    assert all(len(w)==19 for w in words)
    sources = set().union(*(forms[k] for group in coeffs for k in group))
    target = {s:0 for s in sources}
    for group, ws, guard in zip(coeffs,words,(columns[18]&columns[21],columns[27]&columns[21])):
        for k,w in zip(group,ws):
            for s in forms[k]: target[s] ^= guard & columns[w]
    failure = [forms[f"b{42006+j}"] for j in range(3)]
    assert not (failure[0]^failure[1]^failure[2]) and A.AP.gf2_rank(failure)==2
    branch_records=[]
    for j,body in enumerate(branches):
        phase, proof=A.branch_anf(body)
        residual=A.check_residuals(phase,failure[j],sources,columns,target)
        proof.update(branch=j,residual_inputs=[i+1 for i in range(63) if residual>>i&1])
        branch_records.append(proof)
    dropped=next(i for i,l in enumerate(branches[0]) if l.startswith("CZ q21"))
    negative=False
    try:
        phase,_=A.branch_anf([l for i,l in enumerate(branches[0]) if i!=dropped])
        A.check_residuals(phase,failure[0],sources,columns,target)
    except (AssertionError, ValueError): negative=True
    assert negative
    selectors=[]
    for j,(start,stop,cstart,guardwire) in enumerate(((LO,MID,24256,18),(LO2,HI,24320,27))):
        entry=[z3.Bool(f"selector{j}_q{k}") for k in range(62)]
        cbits={f"b{cstart+i}":z3.Bool(f"selector{j}_c{i}") for i in range(19)}
        cbits.update({f"b{cstart+19+i}":z3.Not(cbits[f"b{cstart+i}"]) for i in range(19)})
        cbits[f"b{cstart+38}"]=z3.BoolVal(False)
        q,b,st,phase,cost,_=A.AP.execute(base[start:stop],entry,cbits)
        assert not st
        wanted=z3.BoolVal(False)
        for i,w in enumerate(words[j]):wanted=z3.Xor(wanted,z3.And(cbits[f"b{cstart+i}"],entry[w]))
        wanted=z3.And(entry[guardwire],entry[21],wanted)
        fail=z3.Or([a!=b for a,b in zip(q,entry)]+[phase!=wanted,cost!=z3.If(z3.Or([cbits[f"b{cstart+i}"] for i in range(19)]),1,0)])
        sol=z3.Solver();sol.set(timeout=60000)
        selectors.append(A.AP.check(sol,fail,f"original selector {j}"))
    assert all(r["result"]=="unsat" for r in selectors)
    # A fresh SSA prefix checks the new arithmetic before the unchanged window.
    solver=z3.Solver();solver.set(timeout=60000)
    x=z3.BitVec("maoxin_x",22)
    solver.add(z3.UGE(x,1),z3.ULE(x,3133452))
    q0=[z3.Extract(i,i,x)==1 for i in range(22)]+[z3.BoolVal(False)]*40
    serial=0
    def define(e):
        nonlocal serial
        e=z3.simplify(e)
        if z3.is_true(e) or z3.is_false(e):return e
        b=z3.Bool(f"maoxin_ssa_{serial}");serial+=1;solver.add(b==e);return b
    qs,bits,stack,_,_,events=A.AP.execute(base[:LO],q0,definition=define,prefix=True)
    assert not stack
    claims=[A.AP.check(solver,z3.And(qs[21],z3.UGE(x,64)),"q21 implies x<=63",x),
            A.AP.check(solver,z3.Or(qs[28],qs[40]),"q28 and q40 zero",x)]
    for value in range(1,64):
        mismatch=z3.Or([qs[w]!=z3.BoolVal(bool(columns[w]>>(value-1)&1)) for w in range(62)])
        claims.append(A.AP.check(solver,z3.And(x==value,mismatch),f"all wires x={value}",x))
    assert all(r["result"]=="unsat" for r in claims)
    known=["b350","b351","b358","b359","b363","b364","b371","b372","b366","b367","b374","b375","b610","b368","b365","b373","b353","b354","b361","b362","b355","b357","b369","b356","b360","b370","b352","b611","b612"]
    initial={int(b[1:]):(1<<j,0) for j,b in enumerate(known)}
    tmp,_,_=A.classical_cost(base[PRE1[0]:LO],initial,len(known))
    _,oldcharges,oldcost=A.classical_cost(base[LO:HI],dict(tmp),len(known))
    _,newcharges,newcost=A.classical_cost(replacement,dict(tmp),len(known))
    assert oldcost==Fraction(2)-Fraction(1,2**18) and newcost==1
    # Three native diagnostic streams; sampling is not official full validation.
    xs=S.inputs(20261105,16384)
    if len(xs)%256:xs += [S.MAXX]*(256-len(xs)%256)
    target,tol=S.official.reference_values(S.official.ProblemSpecInvSqrt.for_n_p(10),np.asarray(xs,dtype=np.uint64))
    samples=[]
    for seed in (101,202,303):
        rb,pb=S.run(c,xs,seed);rc,pc=S.run(candidate,xs,seed)
        err=[(pc[i]-int(target[i])+(1<<63))%(1<<64)-(1<<63) for i in range(len(xs))]
        ratios=[abs(err[i])/int(tol[i]) for i in range(len(xs))]
        row=dict(seed=seed,inputs=len(xs),baseline=rb,candidate=rc,phase_differences=sum(a!=b for a,b in zip(pb,pc)),tolerance_failures=sum(abs(e)>int(t) for e,t in zip(err,tol)),worst_ratio=max(ratios),worst_x=xs[ratios.index(max(ratios))],mean_toffoli_saved=rb['mean_toffoli_with_padding']-rc['mean_toffoli_with_padding'])
        assert not row['phase_differences'] and not row['tolerance_failures'] and not rb['n_failures'] and not rc['n_failures']
        samples.append(row);print(json.dumps(row),flush=True)
    result=dict(status="LOCAL_PROOF_AND_SAMPLE_PASS",scope="No full official verification; no Kaggle submission; no hash matching",baseline=str(BASE.relative_to(ROOT)),candidate=str(outpath.relative_to(ROOT)),replaced_window=[LO,HI],source_window_length=HI-LO,replacement_length=len(replacement),candidate_ops=len(full),qubits=62,original_selector_semantics=selectors,prefix_claims=claims,prefix_ssa_nodes=serial,prefix_free_measurements=events,branch_records=branch_records,negative_control_rejected=negative,failure_parities_rank=2,triple_failure_impossible=True,billing=dict(scope="Exact expectation over measurement outcomes; per-shot saving varies",old=str(oldcost),new=str(newcost),saving_C=str(oldcost-newcost),saving_cost=float(62*(oldcost-newcost)),old_charge_count=len(oldcharges),new_charge_count=len(newcharges)),samples=samples,seconds=time.monotonic()-t0,python=platform.python_version(),kickmix="1.0.0",z3=z3.get_version_string())
    (ART/"selector_migration.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:result[k] for k in ('status','candidate','candidate_ops','billing','seconds')}),flush=True)


if __name__=="__main__":main()
