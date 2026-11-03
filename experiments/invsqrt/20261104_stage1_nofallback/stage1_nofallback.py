"""Stage1: eliminate fallback by using trial40 (seed 8121) as third branch.

Baseline (parent for comparison): joint_tail_combined.kmb SHA 04ea98...
Old bce baseline SHA bce294... used for construction (prefix identical).
Builds candidate with 3 mutually exclusive branches, no fallback.
Expected extra saving 0.125 C vs new baseline.
"""
from __future__ import annotations
import argparse, hashlib, io, json, random, sys, time
from pathlib import Path
import numpy as np, kickmix as km

ROOT = Path(__file__).resolve().parents[3]
OLD_BASE = ROOT/"artifacts/20261102_hw06_opt/invsqrt/baseline_hw06.kmb"
OLD_SHA = "bce2948ff24e20fe59666d131f7fc4316a905103937272c52fdd39d494b6fe47"
NEW_BASE = ROOT/"artifacts/20261103_one_ccx/invsqrt/joint_tail_combined.kmb"
NEW_SHA = "04ea98e71a544f39d417f4414fae1e15551a673c184dc5f3c98dcb6e0?".replace("?","")
# fix SHA (copy exact)
NEW_SHA = "04ea98e71a544f39d417f4414fae1e15551a673c184dc5f3c98dcb6e0a"[:64]
# Actually correct SHA from earlier: 04ea98e71a544f39d417f4414fae1e15551a673c184dc5f3c98dcb6e0a? Let's use file check
# We'll assert below with real value read from known json.
ART = ROOT/"artifacts/20261104_stage1_nofallback/invsqrt"
WORDS=[14,16,17,19,20,22,29,30,31,25,26,45,46,47,48,52,55,56,58]

def load_kmx(path):
    c=km.Circuit.from_file(path); buf=io.StringIO(); c.to_file(buf,format="kmx")
    lines=buf.getvalue().splitlines()
    hdr=[l for l in lines if l.startswith(("APPEND","REGISTER"))]
    ops=[l for l in lines if not l.startswith(("APPEND","REGISTER"))]
    return c,hdr,ops

def discover_branches(header, ops, c):
    sys.path.insert(0,str(ROOT/"data/competition/verifiers"))
    from invsqrt import verify_submission_invsqrt as official
    xs=np.arange(1,64,dtype=np.uint64)
    xr,_=official.validate_registers(c,official.ProblemSpecInvSqrt.for_n_p(10))
    prefix=km.Circuit.from_file(io.StringIO("\n".join(header+ops[:27775])+"\n"),format="kmx")
    sim=km.Simulator(batch_size=63,seed=113)
    sim.write_across_shots(xr,official.to_bits(xs,22)); sim.do(prefix)
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
    rng=random.Random(8121)
    wanted={1,2,40}
    branches={}
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
        if len(residuals)!=1:continue
        failure=sum(bool(r)<<j for j,(_,r) in enumerate(solutions))
        if trial in wanted:
            branches[trial]={"trial":trial,"u_wires":[j for j in range(62) if sel>>j&1],
                             "span_rank":len(basis),"failure_mask":failure,
                             "residual_vector":next(iter(residuals)),
                             "solutions":[{"source_bit":b,"column_mask":comb,"residual":bool(rem)}
                                          for b,(comb,rem) in zip(leaves,solutions)]}
            # verify exact
            for (comb,rem),t in zip([(s["column_mask"],1 if s["residual"] else 0) for s in branches[trial]["solutions"]], targets):
                rep=branches[trial]["residual_vector"] if rem else 0
                for col,value in enumerate(columns):
                    if comb>>col&1:rep^=value
                assert rep==t
        if len(branches)==3:break
    assert set(branches)=={1,2,40}
    assert branches[1]["failure_mask"]==0x1cbc6090
    assert branches[2]["failure_mask"]==0x185ecd3
    assert branches[40]["failure_mask"]==0x1d398c43
    assert (branches[1]["failure_mask"] ^ branches[2]["failure_mask"] ^ branches[40]["failure_mask"])==0
    doc={"truth_63x62":truth,"source_bits":list(leaves),"branches":[branches[1],branches[2],branches[40]],
         "original_masks":[[forms[s+i] for i in range(19)] for s in (24256,24320)],
         "failure_rank_note":"rank 2 (dependent): f2 = f0 xor f1, covering all assignments"}
    return doc

def joint_replacement_nofallback(ops, doc):
    out=list(ops[28213:28345])
    for j,br in enumerate(doc["branches"]):
        out.append(f"BIT_STORE0 b{42000+j}")
        for k,b in enumerate(doc["source_bits"]):
            if br["failure_mask"]>>k&1:out.append(f"BIT_INVERT b{42000+j} if b{b}")
        out+=[f"BIT_STORE1 b{42010+j}",f"BIT_INVERT b{42010+j} if b{42000+j}"]
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
        out+=[f"HMR q40 b{42020+j}",f"CZ q21 q28 if b{42020+j}"]+computes[::-1]
        out.append("POP_CONDITION")
        out.append(f"PUSH_CONDITION if b{42000+j}")
    # No fallback: empty unreachable branch
    out+=["POP_CONDITION"]*3
    return out

def tail_tagged(B, extended=True):
    lo,hi=47113,47186
    tagged=[]
    for i in range(lo,hi):
        if i==47123 and extended:
            tagged+=[(i,'CCX q19 q11 q36'),(None,'CZ q36 q10')]
        elif i==47160 and extended:
            tagged+=[(None,'CX q36 q20 if b320'),(i,'CCX q19 q11 q20 if b90001')]
        elif i==47158:
            tagged+=[(None,'BIT_STORE1 b90001'),(None,'BIT_INVERT b90001 if b320'),
                     (None,'CX q34 q32 if b320'),(i,'CCX q18 q13 q32 if b90001')]
        elif i==47159:
            tagged+=[(None,'CX q35 q19 if b320'),(i,'CCX q32 q12 q19 if b90001')]
        else:tagged.append((i,B[i]))
        if i==47122:tagged+=[(None,'CX q32 q34'),(None,'CX q19 q35')]
    cleanup=['PUSH_CONDITION if b320','X q13','X q12']
    if extended:cleanup+=['X q11','HMR q36 b90004','CZ q35 q11 if b90004','X q11']
    cleanup+=['HMR q35 b90002','CZ q34 q12 if b90002',
              'HMR q34 b90003','CZ q18 q13 if b90003',
              'X q12','X q13','POP_CONDITION']
    tagged+=[(None,l) for l in cleanup]
    return lo,hi,tagged

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--baseline",default=str(NEW_BASE))
    ap.add_argument("--baseline-sha",default=None)
    ap.add_argument("--output",default=None)
    ap.add_argument("--prove",action="store_true")
    args=ap.parse_args()
    # verify SHAs
    assert hashlib.sha256(OLD_BASE.read_bytes()).hexdigest()==OLD_SHA, "old base mismatch"
    new_bytes=Path(args.baseline).read_bytes()
    new_sha=hashlib.sha256(new_bytes).hexdigest()
    # expected new SHA from known record
    exp_new="04ea98e71a544f39d417f4414fae1e15551a673c184dc5f3c98dcb6e0a"
    # The file name in earlier logs: 04ea98e71a544f39d417f4414fae1e15551a673c184dc5f3c98dcb6e0a? Let's check length
    # Actually earlier SHA: 04ea98e71a544f39d417f4414fae1e15551a673c184dc5f3c98dcb6e0a is 63 chars? Count.
    # Use recorded value from joint_tail_combined.json instead of hardcode.
    import json as _json
    rec=_json.loads((ROOT/"artifacts/20261103_one_ccx/invsqrt/joint_tail_combined.json").read_text())
    exp_new=rec["candidate_sha256"]
    assert new_sha==exp_new, f"new base mismatch {new_sha} vs {exp_new}"
    if args.baseline_sha: assert new_sha==args.baseline_sha
    _,old_hdr,old_ops=load_kmx(OLD_BASE)
    c_old,_,_=load_kmx(OLD_BASE)  # c_old is tuple? load returns (c,hdr,ops); fix
    # reload properly
    c_old_obj,hdr,ops = load_kmx(OLD_BASE)
    # discover
    doc=discover_branches(hdr,ops,c_old_obj)
    joint_new=joint_replacement_nofallback(ops,doc)
    lo,hi,tagged=tail_tagged(ops,extended=True)
    tail_body=[l for _,l in tagged]
    full=ops[:27775]+joint_new+ops[28783:lo]+tail_body+ops[hi:]
    # build circuit
    nc=km.Circuit.from_file(io.StringIO("\n".join(hdr+full)+"\n"),format="kmx")
    assert nc.num_qubits==62
    ART.mkdir(parents=True,exist_ok=True)
    out_path=Path(args.output) if args.output else ART/"stage1_nofallback.kmb"
    nc.to_file(out_path,format="kmb")
    cand_sha=hashlib.sha256(out_path.read_bytes()).hexdigest()
    # verify Z_POW unchanged vs old
    import io as _io
    def zpow_list(op_list): return [l for l in op_list if l.startswith("Z_POW")]
    assert zpow_list(full)==zpow_list(ops), "Z_POW changed"
    result={"parent_new_baseline_sha256":new_sha,"parent_new_baseline_path":str(args.baseline),
            "old_bce_sha256":OLD_SHA,"joint_window_old":[27775,28783],"tail_window_old":[lo,hi],
            "candidate_sha256":cand_sha,"qubits":62,"operations":len(full),
            "joint_len":len(joint_new),"tail_len":len(tail_body),
            "branches":[ {"trial":b["trial"],"failure_mask":hex(b["failure_mask"]),"u_pop":len(b["u_wires"])} for b in doc["branches"]],
            "failure_xor_zero":True,
            "expected_extra_saving_vs_new_baseline_C":0.125,
            "expected_extra_cost_saving":7.75,
            "expected_total_saving_vs_bce_C":0.1875+(2-2**-18-1.0),
            "source_bits":doc["source_bits"],"status":"built; proof/sample/official pending"}
    (out_path.with_suffix(".json")).write_text(json.dumps(result,indent=2)+"\n")
    print("STAGE1_BUILT",cand_sha,"Q",nc.num_qubits,"ops",len(full),flush=True)
    print(json.dumps(result,indent=2))

if __name__=="__main__":main()
