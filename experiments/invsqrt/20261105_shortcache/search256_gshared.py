"""256-expression shared-AND search on the Stage1 baseline window (saved artifacts).

Scope (bounded): seed 8121, first 256 u expressions; columns [1]+truth(62)+[u&t(62)];
targets = G1+G2 (q23 groups) and G3/G4-equivalent (q21 groups) CCZ phases sampled on
4096 legal inputs with zeroed measurements at the group entries.
Saves: full script, sample matrix, per-candidate residual rank and coverage.
No KMB generation, no official verification in this step.
"""
from __future__ import annotations
import argparse, hashlib, io, json, random
from pathlib import Path
import numpy as np, kickmix as km

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT/"artifacts/20261104_stage1_nofallback/invsqrt/stage1_nofallback.kmb"
BSHA = "80ba3fe75262c6cdb0b6829bfde6e368946d897b6eef2ed7e7626b6355f346a3"
ART = ROOT/"artifacts/20261105_shortcache/invsqrt"
WORDS=[14,16,17,19,20,22,29,30,31,25,26,45,46,47,48,52,55,56,58]

def load():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BSHA
    c=km.Circuit.from_file(BASE)
    buf=io.StringIO(); c.to_file(buf,format="kmx")
    lines=buf.getvalue().splitlines()
    hdr=[l for l in lines if l.startswith(("APPEND","REGISTER"))]
    ops=[l for l in lines if not l.startswith(("APPEND","REGISTER"))]
    return c,hdr,ops

def sample_truth(ops,n=4096,seed=20261103):
    import random as R
    rng=R.Random(seed)
    MAXX=3133452
    xs=set(range(1,4097))
    xs.update(rng.randrange(1,MAXX+1) for _ in range(n))
    for bit in range(22):
        xs.update(x for x in (2**bit-2,2**bit-1,2**bit,2**bit+1,2**bit+2) if 1<=x<=MAXX)
    xs=sorted(x for x in xs if 1<=x<=MAXX)
    N=len(xs); mask=(1<<N)-1
    q=[0]*62; qb=[0]*22
    for j in range(22):
        v=0
        for i,x in enumerate(xs):
            if (x>>j)&1: v|=1<<i
        qb[j]=v
    q=list(qb)+[0]*40
    bits={}; stack=[]
    snaps={}
    # trace with zeroed measurements, record wire values at group entries
    for i,line in enumerate(ops):
        if i in (26633,27205,27775,28345):
            snaps[i]=list(q)
        p=line.split(); k=p[0]
        if k=='PUSH_CONDITION': stack.append(bits.get(int(p[-1][1:]),0)); continue
        if k=='POP_CONDITION':
            if stack: stack.pop()
            continue
        active=mask
        for c in stack: active&=c
        if 'if' in p: active&=bits.get(int(p[p.index('if')+1][1:]),0)
        qs=[int(t[1:]) for t in p[1:] if t.startswith('q')]
        if k=='X': q[qs[0]]^=active
        elif k=='CX': q[qs[1]]^=active&q[qs[0]]
        elif k=='CCX': q[qs[2]]^=active&q[qs[0]]&q[qs[1]]
        elif k in ('SWAP','CSWAP'):
            a,b=qs[-2:]; m=active if k=='SWAP' else active&q[qs[0]]
            d=(q[a]^q[b])&m; q[a]^=d; q[b]^=d
        elif k in ('HMR','R'): q[qs[0]]&=mask^active
        elif k.startswith('BIT_'):
            b=int(p[1][1:]); old=bits.get(b,0)
            bits[b]=old^active if k=='BIT_INVERT' else ((old&~active) if k=='BIT_STORE0' else old|active)
    return xs,snaps,mask

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--n-expr",type=int,default=256)
    ap.add_argument("--seed",type=int,default=8121)
    ap.add_argument("--output",type=Path,default=ART/"search256_gshared.json")
    args=ap.parse_args()
    _,_,ops=load()
    xs,snaps,mask=sample_truth(ops)
    N=len(xs)
    # group entries: G1 prep->[26633], G2 [27205]; q21 groups use stage1 joint entry 27775
    truth={k:v for k,v in snaps.items()}
    # targets: for each group, phase = qa&qb&word over its CCZ span; use word wires from ops
    groups={}
    for name,emit,qa,qb in [("G1_q18q23",26633,18,23),("G2_q27q23",27205,27,23)]:
        rows=[]
        for line in ops[emit:emit+600]:
            p=line.split()
            if p[0]=="CCZ": rows.append(int(p[3][1:]))
            if len(rows)==19: break
        assert len(rows)==19, (name,len(rows))
        t=truth[emit]
        tgt=[t[qa]&t[qb]&t[w] for w in rows]
        groups[name]={"controls":[qa,qb],"words":rows,"targets":tgt}
    # q21 groups in stage1 coords: joint branches implement the same two 19-coeff phases;
    # reuse bce-mapped word lines via stage1 prefix values at 27775 (data identical pre-joint).
    t=truth[27775]
    groups["G34_q21_joint"]={"controls":[21],"words":"stage1-branches","targets":[t[21]&t[w] for w in WORDS],
                             "note":"upper-bound proxy: any single-residual representation of the joint phase"}
    # enumerate
    base_cols=[mask]+[0]*0  # one-vector first
    # build per-sample wire matrix at 26633 entry (widest common prefix for G1/G2; joint shares prefix values)
    Q=snaps[26633]
    one=mask
    rng=random.Random(args.seed)
    cands=[]
    for trial in range(args.n_expr):
        sel=rng.getrandbits(62)&~((1<<28)|(1<<40))
        u=0
        for j in range(62):
            if sel>>j&1: u^=Q[j]
        cols=[one]+Q+[u&v for v in Q]
        # rank
        basis={}
        for j,vec in enumerate(cols):
            comb=1<<j
            v=vec
            while v:
                piv=v.bit_length()-1
                if piv not in basis: basis[piv]=(v,comb); break
                vv,cc=basis[piv]; v^=vv; comb^=cc
        rank=len(basis)
        # single-residual success per group
        def partial(vec):
            comb=rem=0; v=vec
            while v:
                piv=v.bit_length()-1
                if piv in basis:
                    vv,cc=basis[piv]; v^=vv; comb^=cc
                else: rem^=1<<piv; v^=1<<piv
            return comb,rem
        rec={"trial":trial,"u_pop":bin(sel).count("1"),"rank":rank,"groups":{}}
        for gname,g in groups.items():
            if gname=="G34_q21_joint":
                sols=[partial(v) for v in g["targets"]]
            else:
                sols=[partial(v) for v in g["targets"]]
            res={r for _,r in sols if r}
            ok=len(res)==1
            rec["groups"][gname]={"single_residual":ok,"n_residuals":len(res),
                                  "residuals":[hex(r) for r in sorted(res)][:8]}
        rec["any_success"]=any(v["single_residual"] for v in rec["groups"].values())
        cands.append(rec)
    succ=[c for c in cands if c["any_success"]]
    out={"baseline_sha256":BSHA,"samples":N,"seed":args.seed,"n_expr":args.n_expr,
         "columns":"[1]+truth(62)+[u&t(62)]=125","matrix_note":"per-candidate columns rebuilt from saved Q on demand; Q snapshot saved",
         "Q_snapshot":Q,"xs_sha256":hashlib.sha256(json.dumps(xs).encode()).hexdigest(),
         "groups":{k:{"controls":v["controls"],"words":v["words"]} for k,v in groups.items()},
         "candidates":cands,
         "n_success":len(succ),
         "verdict":"STOP-AT-256" if not succ else "REVIEW",
         "status":"bounded search complete; no KMB; no official verification"}
    args.output.write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps({"n_expr":args.n_expr,"samples":N,"n_success":len(succ),"verdict":out["verdict"],
                      "output":str(args.output)},indent=2))

if __name__=="__main__":main()
