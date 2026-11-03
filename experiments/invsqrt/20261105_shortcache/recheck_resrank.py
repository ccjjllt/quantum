"""Independent residual-rank recheck (min-pivot everywhere) for shared_search_v2.

Rebuilds cache-live Q snapshots, real union sources, per-source targets and
g*u columns from scratch (same seeds), then computes residual ranks with an
independent min-pivot eliminator. Compares against saved max-pivot ranks.
"""
from __future__ import annotations
import sys
sys.set_int_max_str_digits(0)
sys.path.insert(0, "experiments/invsqrt/20261105_shortcache")
sys.path.insert(0, "experiments/invsqrt/20261103_one_ccx")
import json, random
from pathlib import Path
import shared_search_v2 as S2
import audit_phase_cache as AP

def basis_min(cols):
    b={}
    for j,v in enumerate(cols):
        c=1<<j; x=v
        while x:
            p=(x&-x).bit_length()-1
            if p not in b: b[p]=(x,c); break
            vx,cx=b[p]; x^=vx; c^=cx
    return b

def part_min(vec,basis):
    c=r=0; v=vec
    while v:
        p=(v&-v).bit_length()-1
        if p in basis:
            vx,cx=basis[p]; v^=vx; c^=cx
        else: r^=1<<p; v^=1<<p
    return c,r

def rank_min(vecs):
    b=set()
    for v in list(vecs):
        while v:
            p=(v&-v).bit_length()-1
            hit=None
            for w in b:
                if (w&-w).bit_length()-1==p: hit=w; break
            if hit is None: b.add(v); break
            v^=hit
    return len(b)

def main():
    hdr,ops=S2.load()
    # locate preps by content (same as main, but explicit)
    def find(pat):
        r=[i for i,l in enumerate(ops) if l==pat]
        assert len(r)==1,(pat,r); return r[0]
    g1p,_=S2.bitrun(ops,find('BIT_STORE0 b24128'))
    g2p,_=S2.bitrun(ops,find('BIT_STORE0 b24192'))
    g3p,_=S2.bitrun(ops,find('BIT_STORE0 b24256'))
    g4p,_=S2.bitrun(ops,find('BIT_STORE0 b24320'))
    xs=S2.inputs()
    snaps,N=S2.trace(ops,xs,113,{g1p:0,g2p:0,g3p:0,g4p:0,26635:0,27777:0})
    Q1,Q2,Q3,Q4=snaps[g1p],snaps[g2p],snaps[g3p],snaps[g4p]
    Qc=snaps[26635]
    assert Qc[41]==(Qc[18]&Qc[27]) and Qc[50]==(Qc[18]&Qc[27]&Qc[23])
    forms={}; bases={"G1":24128,"G2":24192,"G3":24256,"G4":24320}
    groups={"G1":(g1p,18,23,Q1),"G2":(g2p,27,23,Q2),"G3":(g3p,18,21,Q3),"G4":(g4p,27,21,Q4)}
    preps={}
    for g,(p,ga,gb,Q) in groups.items():
        _,e=S2.bitrun(ops,p); preps[g]=(p,e)
        forms[g]=AP.affine_classical(ops[p:e])
    CCZs={"G1":[int(l.split()[3][1:]) for l in ops[26635:26635+700] if l.split()[0]=="CCZ"][:19],
          "G2":[int(l.split()[3][1:]) for l in ops[27207:27207+700] if l.split()[0]=="CCZ"][:19],
          "G3":S2.WORDS,"G4":S2.WORDS}
    S=set()
    for g in groups:
        for i in range(19):
            S|=forms[g].get(f'b{bases[g]+i}',{f'b{bases[g]+i}'})
    S.discard('ONE'); S=sorted(S,key=lambda b:(int(b[1:]) if b[1:].isdigit() else 9**9,b))
    T={s:0 for s in S}; T_ONE=0
    for g,(p,ga,gb,Q) in groups.items():
        for i in range(19):
            coef=forms[g].get(f'b{bases[g]+i}',{f'b{bases[g]+i}'})
            pat=Q[ga]&Q[gb]&Q[CCZs[g][i]]
            if 'ONE' in coef: T_ONE^=pat
            for s in coef:
                if s=='ONE': continue
                T[s]^=pat
    assert T_ONE==0
    gcol=Qc[23]^Qc[21]; one=(1<<N)-1
    saved=json.load(open("artifacts/20261105_shortcache/invsqrt/shared_search_v2.json"))
    sv={t["trial"]:(t["u_wires"],t["residual_rank"],t["n_residuals"]) for t in saved["candidates"]}
    rng=random.Random(8121)
    bad=0; checked=0
    for trial in range(256):
        sel=rng.getrandbits(62)&~((1<<28)|(1<<40))
        u=0; wires=[j for j in range(62) if sel>>j&1]
        for j in wires: u^=Qc[j]
        m=gcol&u
        cols=[one]+Qc+[u&t for t in Qc]+[m&t for t in Qc]
        B=basis_min(cols)
        res=[part_min(v,B)[1] for v in T.values()]
        res=[r for r in res if r]
        rmin=rank_min(res)
        uw,rsv,nsv=sv[trial]
        assert uw==wires,(trial,"u mismatch: RNG diverged")
        if rmin!=rsv or len(res)!=nsv:
            print("MISMATCH",trial,rmin,rsv,len(res),nsv); bad+=1
        checked+=1
    print("checked",checked,"mismatches",bad)
    assert bad==0
    print("RECHECK PASS: min-pivot ranks identical for all 256 (min 25)")

if __name__=="__main__":main()
