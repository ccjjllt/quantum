"""Corrected shared search: cache-live snapshot + real joint sources + g*u columns.

Baseline: shortcache_zero.kmb (cache q41=ab, q50=abc live). Targets: G1/G2/G3/G4
actual phases against the UNION of real measurement sources (forms from prep BITs,
guards q18/q23, q27/q23, q18/q21, q27/q21; no word-proxy). Columns per candidate u
(seed 8121, first 256, temps q28/q40 excluded, cache wires allowed):
[1] + Q(62) + [u&t] + [(g&u)&t], g = q23^q21. Per-candidate: column rank, residuals,
GF(2) residual RANK (conditions needed, not distinct-count), coverage estimate.
Saves script inputs, Q matrix snapshot, per-candidate table. Stops after 256.
"""
from __future__ import annotations
import argparse, hashlib, io, json, random, sys
sys.set_int_max_str_digits(0)
from pathlib import Path
import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/"experiments/invsqrt/20261103_one_ccx"))
import audit_phase_cache as AP
CAND = ROOT/"artifacts/20261105_shortcache/invsqrt/shortcache_zero.kmb"
CSHA = "97e6391503cb463a72666a393d9c20b1b5f18359c79d89b1ff76157eff21e9da"
ART = ROOT/"artifacts/20261105_shortcache/invsqrt"
WORDS=[14,16,17,19,20,22,29,30,31,25,26,45,46,47,48,52,55,56,58]

def load():
    raw=CAND.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==CSHA
    c=km.Circuit.from_file(CAND)
    buf=io.StringIO(); c.to_file(buf,format="kmx")
    lines=buf.getvalue().splitlines()
    hdr=[l for l in lines if l.startswith(("APPEND","REGISTER"))]
    return hdr,[l for l in lines if not l.startswith(("APPEND","REGISTER"))]

def bitrun(ops,start):
    i=start
    while i<len(ops) and ops[i].split()[0].startswith("BIT_"): i+=1
    return start,i

def inputs(seed=20261103,n=8192):
    import random as R
    rng=R.Random(seed); MAXX=3133452
    xs=set(range(1,16384))
    xs.update(rng.randrange(1,MAXX+1) for _ in range(n))
    for bit in range(22):
        xs.update(x for x in (2**bit-2,2**bit-1,2**bit,2**bit+1,2**bit+2) if 1<=x<=MAXX)
    for a in range(256):
        for dd in (0,1,8191,8192,16382,16383):
            m=(1<<21)|((a&127)<<14)|dd
            for lz in (a>>7,2+(a>>7)):
                if m%(1<<lz)==0 and 1<=m>>lz<=MAXX: xs.add(m>>lz)
    return sorted(xs)

def trace(ops,xs,seed,want):
    N=len(xs); mask=(1<<N)-1
    rng=random.Random(seed)
    q=[0]*62
    for j in range(22):
        v=0
        for i,x in enumerate(xs):
            if (x>>j)&1: v|=1<<i
        q[j]=v
    bits={}; stack=[]; snaps={}
    wantset=dict(want)
    for i,line in enumerate(ops):
        if i in wantset: snaps[i]=list(q)
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
        elif k in ('HMR','R'):
            oc=rng.getrandbits(N)
            if k=='HMR': bits[int(p[2][1:])]=(bits.get(int(p[2][1:]),0)&~active)|(oc&active)
            q[qs[0]]&=~active
        elif k.startswith('BIT_'):
            b=int(p[1][1:]); old=bits.get(b,0)
            bits[b]=old^active if k=='BIT_INVERT' else ((old&~active) if k=='BIT_STORE0' else old|active)
    assert not stack
    return snaps,N

def make_basis(columns):
    basis={}
    for j,vec in enumerate(columns):
        comb=1<<j
        v=vec
        while v:
            piv=v.bit_length()-1
            if piv not in basis: basis[piv]=(v,comb); break
            vv,cc=basis[piv]; v^=vv; comb^=cc
    return basis

def partial(vec,basis):
    comb=rem=0; v=vec
    while v:
        piv=v.bit_length()-1
        if piv in basis:
            vv,cc=basis[piv]; v^=vv; comb^=cc
        else: rem^=1<<piv; v^=1<<piv
    return comb,rem

def gfrank(vecs):
    basis=set()
    for v in vecs:
        while v:
            piv=v.bit_length()-1
            hit=None
            for b in basis:
                if b.bit_length()-1==piv: hit=b; break
            if hit is None: basis.add(v); break
            v^=hit
    return len(basis)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--n-expr",type=int,default=256); ap.add_argument("--seed",type=int,default=8121)
    ap.add_argument("--output",type=Path,default=ART/"shared_search_v2.json")
    args=ap.parse_args()
    _,ops=load()
    # locate prep runs by content
    def find(pat):
        r=[i for i,l in enumerate(ops) if l==pat]
        assert len(r)==1, (pat,r); return r[0]
    g1p,_=bitrun(ops,find('BIT_STORE0 b24128'))
    g2p,_=bitrun(ops,find('BIT_STORE0 b24192'))
    g3p,_=bitrun(ops,find('BIT_STORE0 b24256'))
    g4p,g4e=bitrun(ops,find('BIT_STORE0 b24320'))
    assert ops[g4p:g4p+132]==ops[g4p:g4e][:132] and len(ops[g4p:g4p+132])==132
    # First 132 ops are the moved G4 prep; the rest are branch-classical BITs.
    g4e=g4p+132
    groups={"G1":(g1p,26635,18,23),"G2":(g2p,27207,27,23),"G3":(g3p,27777,18,21),"G4":(g4p,27777,27,21)}
    # emission word order from actual CCZs (G1/G2); G3/G4 use WORDS order (original form)
    CCZs={}
    for g,(p,e,ga,gb) in groups.items():
        if g in ("G1","G2"):
            rows=[]
            for line in ops[e:e+700]:
                q=line.split()
                if q[0]=="CCZ": rows.append(int(q[3][1:]))
                if len(rows)==19: break
            assert len(rows)==19,(g,len(rows))
            CCZs[g]=rows
        else: CCZs[g]=list(WORDS)
    xs=inputs()
    snaps,N=trace(ops,xs,113,{g1p:0,g2p:0,g3p:0,g4p:0,26635:0,27777:0})
    Q1,Q2,Q3,Q4=snaps[g1p],snaps[g2p],snaps[g3p],snaps[g4p]
    QJ=snaps[27777]
    assert QJ[21]==sum(1<<i for i,x in enumerate(xs) if x<=63), "q21 domain"
    # cache live check on the wide snapshot
    Qc=snaps[26635]
    assert Qc[41]==(Qc[18]&Qc[27]), "ab live"
    assert Qc[50]==(Qc[18]&Qc[27]&Qc[23]), "abc live"
    # forms per group (string keys via AP)
    forms={}
    for g,(p,e,ga,gb) in groups.items():
        f=AP.affine_classical(ops[p:bitrun(ops,p)[1]])
        forms[g]=f
    # union sources over the four groups' 19+19+19+19 coefficient bits
    bases={"G1":24128,"G2":24192,"G3":24256,"G4":24320}
    S=set()
    for g,(p,e,ga,gb) in groups.items():
        for i in range(19):
            S|=forms[g].get(f'b{bases[g]+i}',{f'b{bases[g]+i}'})
    S.discard('ONE')
    S=sorted(S,key=lambda b:(int(b[1:]) if b[1:].isdigit() else 10**9,b))
    # per-source targets (data patterns); const ONE part must vanish or be listed
    T={}
    for s in S: T[s]=0
    T_ONE=0
    for g,(p,e,ga,gb) in groups.items():
        Q= { "G1":Q1,"G2":Q2,"G3":Q3,"G4":Q4}[g]
        for i in range(19):
            coef=forms[g].get(f'b{bases[g]+i}',{f'b{bases[g]+i}'})
            pat=Q[ga]&Q[gb]&Q[CCZs[g][i]]
            if 'ONE' in coef: T_ONE^=pat
            for s in coef:
                if s=='ONE': continue
                T[s]^=pat
    assert T_ONE==0, "const part nonzero: original phases have no constant term on samples"
    # columns per u
    Qall=Qc
    gcol=Qall[23]^Qall[21]
    one=(1<<N)-1
    rng=random.Random(args.seed)
    cands=[]
    for trial in range(args.n_expr):
        sel=rng.getrandbits(62)&~((1<<28)|(1<<40))
        u=0; wires=[j for j in range(62) if sel>>j&1]
        for j in wires: u^=Qall[j]
        m=gcol&u
        cols=[one]+Qall+[u&t for t in Qall]+[m&t for t in Qall]
        basis=make_basis(cols)
        sols={s:partial(v,basis) for s,v in T.items()}
        res={s:r for s,(c,r) in sols.items() if r}
        rrank=gfrank(list(res.values()))
        cands.append({"trial":trial,"u_wires":wires,"u_pop":len(wires),
                      "col_rank":len(basis),"n_sources":len(S),"n_residuals":len(res),
                      "residual_rank":rrank,
                      "residual_pops":sorted([(s,bin(r).count('1'),r&(2**64-1)) for s,r in res.items()],key=lambda z:z[1])[:12]})
    best=min(cands,key=lambda c:(c["residual_rank"],c["n_residuals"]))
    out={"candidate_sha256":CSHA,"n_inputs":N,"seed":args.seed,"n_expr":args.n_expr,
         "columns":"[1]+Q(62,cache-live)+[u&t]+[(g&u)&t]=187","g":"q23^q21",
         "sources":S,"n_sources":len(S),
         "cache_live":{"ab":True,"abc":True},
         "groups":{g:{"prep":[p,bitrun(ops,p)[1]],"guard":[ga,gb],"words":CCZs[g]} for g,(p,e,ga,gb) in groups.items()},
         "Q_snapshot":[("G1",Q1),("G2",Q2),("G3",Q3),("G4",Q4),("cols",Qall)],
         "candidates":cands,
         "best":{"trial":best["trial"],"residual_rank":best["residual_rank"],"n_residuals":best["n_residuals"]},
         "verdict":"REVIEW" if best["residual_rank"]<=7 else "NEGATIVE-V2",
         "status":"corrected template (cache-live, real union sources, g*u); 256/256 then stop"}
    args.output.write_text(json.dumps(out,indent=2,default=str)+"\n")
    print(json.dumps({"n_expr":args.n_expr,"n_inputs":N,"n_sources":len(S),
                      "best":out["best"],"verdict":out["verdict"],"output":str(args.output)},indent=2))

if __name__=="__main__":main()
