"""Independent resource audit for stage1 nofallback (actual bytes)."""
from __future__ import annotations
import hashlib, io, json, sys
from fractions import Fraction
from pathlib import Path
import kickmix as km
ROOT = Path(__file__).resolve().parents[3]
OLD_BASE = ROOT/"artifacts/20261102_hw06_opt/invsqrt/baseline_hw06.kmb"
CAND = ROOT/"artifacts/20261104_stage1_nofallback/invsqrt/stage1_nofallback.kmb"
ART = ROOT/"artifacts/20261104_stage1_nofallback/invsqrt"
OLD_SHA="bce2948ff24e20fe59666d131f7fc4316a905103937272c52fdd39d494b6fe47"
LO,HI=27775,28783
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(path):
    c=km.Circuit.from_file(path); buf=io.StringIO(); c.to_file(buf,format="kmx")
    lines=buf.getvalue().splitlines()
    return c,[l for l in lines if l.startswith(("APPEND","REGISTER"))],[l for l in lines if not l.startswith(("APPEND","REGISTER"))]
def affine_rank(rows):
    basis={}
    for mask,rhs in rows:
        while mask:
            pivot=mask.bit_length()-1
            if pivot not in basis:basis[pivot]=(mask,rhs);break
            other,value=basis[pivot];mask^=other;rhs^=value
        if not mask and rhs:return None
    return len(basis)
def probability(rows):
    r=affine_rank(rows); return Fraction(0) if r is None else Fraction(1,2**r)
def classical_cost(lines, initial, nvars):
    bits,stack,charges=dict(initial),[],[]
    for i,line in enumerate(lines):
        p=line.split();kind=p[0]
        cond=bits[int(p[-1][1:])] if "if" in p else (0,1)
        if kind=="PUSH_CONDITION":stack.append(cond)
        elif kind=="POP_CONDITION":stack.pop()
        elif kind.startswith("BIT_"):
            assert not stack,(i,line,stack)
            target=int(p[1][1:])
            if kind=="BIT_INVERT":
                old=bits.get(target,(0,0));bits[target]=(old[0]^cond[0],old[1]^cond[1])
            else:
                assert "if" not in p;bits[target]=(0,int(kind=="BIT_STORE1"))
        elif kind=="HMR":
            target=int(p[2][1:]);assert target not in bits;bits[target]=(1<<nvars,0);nvars+=1
        elif kind in ("CCX","CCZ"):
            forms=stack+([cond] if "if" in p else [])
            rows=[(mask,1^const) for mask,const in forms]
            prob=probability(rows)
            charges.append({"offset":i,"instruction":line,"rank":affine_rank(rows),"probability":str(prob)})
        else:assert kind in ("CX","CZ","X","Z"),(i,line)
    assert not stack
    return bits,charges,sum((Fraction(c["probability"]) for c in charges),Fraction(0))
def find_subseq(hay,needle,start=0):
    n=len(needle)
    for i in range(start,len(hay)-n+1):
        if hay[i:i+n]==needle:return i
    return -1
def main():
    assert sha(OLD_BASE)==OLD_SHA
    _,hdr,ops=load(OLD_BASE); _,nhdr,nops=load(CAND)
    assert hdr==nhdr
    anchor=ops[HI:HI+10]
    joint_end=find_subseq(nops,anchor,LO)
    assert joint_end>LO
    joint_new=nops[LO:joint_end]
    assert nops[:LO]==ops[:LO]
    # source bits: need doc? derive from prep: use same source list as stage1 json? Load stage1 doc for source order?
    # Instead derive initial from known 29 source bits order from previous run: read audit file?
    # We recompute source bits via affine analysis of classical prefix? Simpler: load stage1_nofallback.json? No, that's generator output.
    # Independent: find HMR writers in prefix that feed joint classical? Reuse method: source bits are those read by joint classical BIT_INVERTs.
    # Collect BIT_INVERT sources in classical part.
    first_push=next(i for i,l in enumerate(joint_new) if l.startswith("PUSH_CONDITION"))
    classical=joint_new[:first_push]
    # second prep block is ops[28213:28345] length 132
    assert joint_new[:132]==ops[28213:28345]
    # failure masks are BIT_INVERT sources for b42000+j
    # parse them
    fail_src=[[] for _ in range(3)]
    for line in classical[132:]:
        p=line.split()
        if p[0]=="BIT_INVERT" and p[1] in ("b42000","b42001","b42002"):
            j=int(p[1][1:])-42000
            fail_src[j].append(int(p[-1][1:]))
    # initial mapping: need order; use sorted unique? But masks must be in terms of bit positions for rank.
    # Use mapping bit->index by sorted order for rank computation (rank invariant under perm).
    all_src=sorted({b for lst in fail_src for b in lst})
    KNOWN_29=[350,351,358,359,363,364,371,372,366,367,374,375,610,368,365,373,353,354,361,362,355,357,369,356,360,370,352,611,612]
    assert set(all_src)<=set(KNOWN_29), f"unexpected {set(all_src)-set(KNOWN_29)}"
    all_src=KNOWN_29
    initial={b:(1<<j,0) for j,b in enumerate(all_src)}
    # Need to propagate through prefix 27643:27775 + second prep? Actually initial for joint window should include prep1 (27643:27775) applied.
    # Reuse classical_cost to propagate prefix.
    tmp,_ ,_=classical_cost(ops[27643:LO],initial,len(all_src))
    # But second prep is part of joint_new[:132]; classical_cost on joint_new will handle it.
    # For old cost, same initial.
    _,old_charges,old_cost=classical_cost(ops[LO:HI],dict(tmp),len(all_src))
    _,new_charges,new_cost=classical_cost(joint_new,dict(tmp),len(all_src))
    print(f"OLD_COST {old_cost} NEW_COST {new_cost} SAVING {old_cost-new_cost}")
    # verify failures
    bits,_,_=classical_cost(joint_new,dict(tmp),len(all_src))
    # Actually bits contains failure entries; extract masks
    # classical_cost returns bits dict mapping bit->(mask,const). Need to capture.
    # Re-run to get bits
    bmap,_,_=classical_cost(classical,dict(tmp),len(all_src))
    failures=[bmap[42000+j][0] for j in range(3)]
    print("FAIL_MASKS",[hex(m) for m in failures])
    rank=affine_rank([(m,0) for m in failures])
    print("RANK",rank)
    assert old_cost==2-Fraction(1,2**18), old_cost
    assert new_cost==Fraction(1,1), new_cost
    assert rank==2
    # triple failure impossible?
    # check old/new charge counts? new should have 3 CCX charges each prob 1/4? Actually each branch CCX has prob 1/4? Sum =3/4? Wait plus? Let's see: each branch's CCX is under PUSH success (prob 1/2?) Hmm original new_cost 9/8 =1.125 came from 3 branches each with prob? For nofallback, new_cost should be 1.0. Our classical_cost counts only CCX/CCZ in joint_new. Each branch has 1 CCX with activation prob? For branch0, PUSH success prob 1/2? Actually success = NOT failure, failure is parity of ~12-14 sources => prob 1/2. So each CCX prob? Branch0 CCX under success (prob 1/2). Branch1 CCX under failure0 (1/2) + success1 (1/2) => 1/4. Branch2 under failure0 & failure1 (1/4) + success2? Since f2 = f0 xor f1, when f0=1,f1=1, f2=0 always, so branch2 executes with prob 1/4. Sum =1/2+1/4+1/4=1. Good.
    report={"old_cost":str(old_cost),"new_cost":str(new_cost),"saving":str(old_cost-new_cost),
            "saving_decimal":float(old_cost-new_cost),"with_tail3":str(old_cost-new_cost+Fraction(3,16)),
            "rank":rank,"fail_masks":[hex(m) for m in failures],
            "old_charges":old_charges,"new_charges":new_charges,
            "candidate_sha256":sha(CAND),"baseline_sha256":OLD_SHA}
    (ART/"audit_stage1_resources.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k not in ("old_charges","new_charges")},indent=2))
if __name__=="__main__":main()
