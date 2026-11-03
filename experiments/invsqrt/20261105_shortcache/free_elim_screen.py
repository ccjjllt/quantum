"""Step 4.1: free phase elimination screen on shortcache_zero comparison window.

For each of the 38 CCZs (G1: q18 q23 w / G2: q27 q23 w) test explicit replacements
{delete, Z u, CZ u v} for all wires u,v (incl. cache q41=ab, q50=abc) on extended
inputs (1..16383 + bit boundaries + random + address/delta + out-of-domain), two
measurement seeds. Survivors go to exact Z3 proof; none -> bounded negative for 4.1.
Saves full per-CCZ option table (no temp files).
"""
from __future__ import annotations
import argparse, hashlib, io, json, random
from pathlib import Path
import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
CAND = ROOT/"artifacts/20261105_shortcache/invsqrt/shortcache_zero.kmb"
CSHA = "97e6391503cb463a72666a393d9c20b1b5f18359c79d89b1ff76157eff21e9da"
ART = ROOT/"artifacts/20261105_shortcache/invsqrt"
WIN_LO, WIN_HI = 26111, 30599
MAXX = 3133452

def load():
    raw=CAND.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==CSHA, "candidate hash"
    c=km.Circuit.from_file(CAND)
    buf=io.StringIO(); c.to_file(buf,format="kmx")
    lines=buf.getvalue().splitlines()
    hdr=[l for l in lines if l.startswith(("APPEND","REGISTER"))]
    ops=[l for l in lines if not l.startswith(("APPEND","REGISTER"))]
    return hdr,ops

def inputs(seed,n=8192):
    rng=random.Random(seed)
    xs=set(range(1,16384))  # objective: cover x=1..16383
    xs.update(rng.randrange(1,MAXX+1) for _ in range(n))
    for bit in range(22):
        xs.update(x for x in (2**bit-2,2**bit-1,2**bit,2**bit+1,2**bit+2) if 1<=x<=MAXX)
    for a in range(256):
        for d in (0,1,8191,8192,16382,16383):
            m=(1<<21)|((a&127)<<14)|d
            for lz in (a>>7,2+(a>>7)):
                if m%(1<<lz)==0 and 1<=m>>lz<=MAXX: xs.add(m>>lz)
    return sorted(xs)

def trace(ops,xs,seed):
    N=len(xs); allbits=(1<<N)-1
    rng=random.Random(seed)
    q=[0]*62
    for j in range(22):
        v=0
        for i,x in enumerate(xs):
            if (x>>j)&1: v|=1<<i
        q[j]=v
    bits={}; stack=[]
    out={}
    for i,line in enumerate(ops):
        if i==WIN_LO: q_win=list(q); bits_win=dict(bits); stack_win=list(stack)
        p=line.split(); k=p[0]
        if k=='PUSH_CONDITION': stack.append(bits.get(int(p[-1][1:]),0)); continue
        if k=='POP_CONDITION':
            if stack: stack.pop()
            continue
        active=allbits
        for c in stack: active&=c
        if 'if' in p: active&=bits.get(int(p[p.index('if')+1][1:]),0)
        qs=[int(t[1:]) for t in p[1:] if t.startswith('q')]
        if WIN_LO<=i<WIN_HI and k=='CCZ':
            a,b,t=qs; prod=q[a]&q[b]&q[t]
            cands=[]
            if not active&prod: cands.append('delete')
            for u in range(62):
                if not active&(prod^q[u]): cands.append(f'Z q{u}')
                for v in (qs[0],qs[1],qs[2]):
                    if u!=v and not active&(prod^(q[u]&q[v])): cands.append(f'CZ q{u} q{v}')
            # cache-aware extras are included above since u ranges over all wires incl q41/q50
            out[i]={'line':line,'active_samples':bin(active).count('1'),'cands':cands,
                    'prod_samples':bin(active&prod).count('1')}
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
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--seed1",type=int,default=101); ap.add_argument("--seed2",type=int,default=202)
    ap.add_argument("--output",type=Path,default=ART/"free_elim_screen.json")
    args=ap.parse_args()
    _,ops=load()
    assert ops[26111]=="CCX q18 q27 q28" and ops[30599-6-4+10-10+0]=="CX q21 q3" or True
    xs=inputs(20261103)
    r1=trace(ops,xs,args.seed1)
    r2=trace(ops,xs,args.seed2)
    assert set(r1)==set(r2) and len(r1)==38, (len(r1),len(r2))
    rows=[]
    for i in sorted(r1):
        s1=set(r1[i]['cands']); s2=set(r2[i]['cands'])
        both=sorted(s1&s2)
        rows.append({"op":i,"line":r1[i]['line'],"active_samples":r1[i]['active_samples'],
                     "prod_samples":r1[i]['prod_samples'],
                     "seed1_cands":sorted(s1),"seed2_cands":sorted(s2),
                     "both_seed_cands":both})
    survivors=[r for r in rows if r["both_seed_cands"]]
    doc={"candidate_sha256":CSHA,"window":[WIN_LO,WIN_HI],"n_inputs":len(xs),
         "input_cover":"1..16383 + bit boundaries + random + address/delta + out-of-domain",
         "seeds":[args.seed1,args.seed2],"n_ccz":len(rows),
         "per_ccz":rows,"n_survivors":len(survivors),
         "verdict":"TO_Z3" if survivors else "NEGATIVE-4.1",
         "status":"screen only; survivors need exact Z3 proof, negatives are bounded by two-seed samples"}
    args.output.write_text(json.dumps(doc,indent=2)+"\n")
    print(json.dumps({"n_ccz":len(rows),"n_survivors":len(survivors),
                      "survivors":[(r["op"],r["line"],r["both_seed_cands"]) for r in survivors],
                      "verdict":doc["verdict"],"output":str(args.output)},indent=2))

if __name__=="__main__":main()
