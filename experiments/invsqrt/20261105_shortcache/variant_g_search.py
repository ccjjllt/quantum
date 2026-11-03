"""Structurally different control probe: vary the shared control g.

v2 fixed g = q23^q21 per plan. This probe sweeps g over 8 control variants
(incl. q18^q27, single wires, other XORs) x 32 u each (seed 8122, 256 exprs total,
same budget class), same cache-live Q, same 29 union sources, same g*u columns.
Reports min residual rank per g. A low rank for any g would reopen the direction.
"""
from __future__ import annotations
import sys
sys.set_int_max_str_digits(0)
sys.path.insert(0, "experiments/invsqrt/20261105_shortcache")
sys.path.insert(0, "experiments/invsqrt/20261103_one_ccx")
import argparse, hashlib, io, json, random
from pathlib import Path
import kickmix as km
import shared_search_v2 as S2
import audit_phase_cache as AP

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT/"artifacts/20261105_shortcache/invsqrt"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--u-per-g",type=int,default=32)
    ap.add_argument("--seed",type=int,default=8122)
    ap.add_argument("--output",type=Path,default=ART/"variant_g_search.json")
    args=ap.parse_args()
    hdr,ops=S2.load()
    def find(pat):
        r=[i for i,l in enumerate(ops) if l==pat]
        assert len(r)==1,(pat,r); return r[0]
    g1p,_=S2.bitrun(ops,find('BIT_STORE0 b24128'))
    g2p,_=S2.bitrun(ops,find('BIT_STORE0 b24192'))
    g3p,_=S2.bitrun(ops,find('BIT_STORE0 b24256'))
    g4p,g4e=S2.bitrun(ops,find('BIT_STORE0 b24320')); g4e=g4p+132
    xs=S2.inputs()
    snaps,N=S2.trace(ops,xs,113,{g1p:0,g2p:0,g3p:0,g4p:0,26635:0,27207:0,27777:0})
    Q1,Q2,Q3,Q4=snaps[g1p],snaps[g2p],snaps[g3p],snaps[g4p]
    Qc=snaps[26635]
    assert Qc[41]==(Qc[18]&Qc[27]) and Qc[50]==(Qc[18]&Qc[27]&Qc[23])
    forms={}
    for g,p in [("G1",g1p),("G2",g2p),("G3",g3p),("G4",g4p)]:
        _,e=S2.bitrun(ops,p)
        if g=="G4": e=g4p+132
        assert e-p>100, (g,p,e)
        forms[g]=AP.affine_classical(ops[p:e])
    CCZs={"G1":[int(l.split()[3][1:]) for l in ops[26635:26635+700] if l.split()[0]=="CCZ"][:19],
          "G2":[int(l.split()[3][1:]) for l in ops[27207:27207+700] if l.split()[0]=="CCZ"][:19],
          "G3":S2.WORDS,"G4":S2.WORDS}
    bases={"G1":24128,"G2":24192,"G3":24256,"G4":24320}
    groups={"G1":(Q1,18,23),"G2":(Q2,27,23),"G3":(Q3,18,21),"G4":(Q4,27,21)}
    S=set()
    for g in groups:
        for i in range(19):
            S|=forms[g].get(f'b{bases[g]+i}',{f'b{bases[g]+i}'})
    S.discard('ONE'); S=sorted(S,key=lambda b:(int(b[1:]) if b[1:].isdigit() else 9**9,b))
    T={s:0 for s in S}; T_ONE=0
    for g,(Q,ga,gb) in groups.items():
        for i in range(19):
            coef=forms[g].get(f'b{bases[g]+i}',{f'b{bases[g]+i}'})
            pat=Q[ga]&Q[gb]&Q[CCZs[g][i]]
            if 'ONE' in coef: T_ONE^=pat
            for s in coef:
                if s=='ONE': continue
                T[s]^=pat
    assert T_ONE==0
    one=(1<<N)-1
    GDEFS={"q23^q21":Qc[23]^Qc[21],"q18^q27":Qc[18]^Qc[27],"q18":Qc[18],"q27":Qc[27],
           "q23":Qc[23],"q21":Qc[21],"q18^q23":Qc[18]^Qc[23],"q27^q23":Qc[27]^Qc[23]}
    out={"n_inputs":N,"n_sources":len(S),"per_g":{}}
    for gname,gcol in GDEFS.items():
        rng=random.Random(args.seed)
        best=None
        for trial in range(args.u_per_g):
            sel=rng.getrandbits(62)&~((1<<28)|(1<<40))
            u=0; wires=[j for j in range(62) if sel>>j&1]
            for j in wires: u^=Qc[j]
            m=gcol&u
            cols=[one]+Qc+[u&t for t in Qc]+[m&t for t in Qc]
            basis=S2.make_basis(cols)
            res=[S2.partial(v,basis)[1] for v in T.values()]
            res=[r for r in res if r]
            r=S2.gfrank(res)
            if best is None or r<best[0]: best=(r,len(res),trial,wires)
        out["per_g"][gname]={"min_residual_rank":best[0],"n_residuals_at_best":best[1],
                             "best_trial":best[2],"best_u_pop":len(best[3])}
        print(gname,best[0],best[1],flush=True)
    out["verdict"]="REVIEW" if min(v["min_residual_rank"] for v in out["per_g"].values())<=7 else "NEGATIVE-GVARIANTS"
    out["status"]="8 control variants x %d u (seed %d); same budget class; stop after this round"%(
        args.u_per_g,args.seed)
    args.output.write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps({"verdict":out["verdict"],"per_g":{k:v["min_residual_rank"] for k,v in out["per_g"].items()},
                      "output":str(args.output)},indent=2))

if __name__=="__main__":main()
