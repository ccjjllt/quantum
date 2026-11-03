"""Issue-3 follow-up: full 1891-pair CZ screen + bounded cross-gate pair merges.

Full CZ family per CCZ: {delete, Z u (62), CZ u v (1891 unordered pairs)}, two seeds,
25809 inputs. Plus intra-group same-control CCZ-pair merges: CCZ(a,b,c)+CCZ(a,b,d)
with the same guard stack reduce to one CCZ(a,b,w) iff w == c^d on the union active
domain (sample-necessary; survivors need Z3). Saves explicit per-gate tables.
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
import sys; sys.path.insert(0, str(ROOT/"experiments/invsqrt/20261105_shortcache"))
from free_elim_screen import inputs

def snap_trace(ops,xs,seed):
    N=len(xs); mask=(1<<N)-1
    rng=random.Random(seed)
    q=[0]*62
    for j in range(22):
        v=0
        for k,x in enumerate(xs):
            if (x>>j)&1: v|=1<<k
        q[j]=v
    bits={}; stack=[]; rec={}
    for i,line in enumerate(ops):
        p=line.split(); k=p[0]
        if k=='PUSH_CONDITION': stack.append(bits.get(int(p[-1][1:]),0)); continue
        if k=='POP_CONDITION':
            if stack: stack.pop()
            continue
        active=mask
        for cc in stack: active&=cc
        if 'if' in p: active&=bits.get(int(p[p.index('if')+1][1:]),0)
        qs=[int(t[1:]) for t in p[1:] if t.startswith('q')]
        if WIN_LO<=i<WIN_HI and k=='CCZ':
            rec[i]={"active":active,"q":list(q),"line":line}
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
            bb=int(p[1][1:]); old=bits.get(bb,0)
            bits[bb]=old^active if k=='BIT_INVERT' else ((old&~active) if k=='BIT_STORE0' else old|active)
    assert not stack
    return rec

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,default=ART/"free_elim_fullpairs.json")
    args=ap.parse_args()
    assert hashlib.sha256(CAND.read_bytes()).hexdigest()==CSHA
    c=km.Circuit.from_file(CAND)
    buf=io.StringIO(); c.to_file(buf,format="kmx")
    ops=[l for l in buf.getvalue().splitlines() if not l.startswith(("APPEND","REGISTER"))]
    xs=inputs(20261103)
    R={s:snap_trace(ops,xs,s) for s in (101,202)}
    ids=sorted(R[101])
    assert set(R[202])==set(ids) and len(ids)==38
    pairs=[(u,v) for u in range(62) for v in range(u+1,62)]
    both={}; firing_survivors=0; vacuous=0
    for i in ids:
        line=R[101][i]["line"]
        per_seed=[]
        for s in (101,202):
            a=R[s][i]["active"]; q=R[s][i]["q"]
            p=line.split(); A,B,T=(int(x[1:]) for x in p[1:4])
            prod=q[A]&q[B]&q[T]
            if not a&prod:
                per_seed.append(None); continue  # vacuous on this seed
            good=[]
            if True:  # delete never valid when firing
                pass
            for u in range(62):
                if not a&(prod^q[u]): good.append(["Z",u])
            for u,v in pairs:
                if not a&(prod^(q[u]&q[v])): good.append(["CZ",u,v])
            per_seed.append({json.dumps(g) for g in good})
        if any(h is None for h in per_seed):
            both[i]="vacuous-on-a-seed"; vacuous+=1
        else:
            inter=sorted(per_seed[0]&per_seed[1])
            both[i]=inter
            if inter: firing_survivors+=1
    # pair merges among same-control CCZs (guard stacks must also match: require same line prefix controls AND same active bitset pattern is checked via w==c^d on union domain)
    merges={}
    for a in range(len(ids)):
        for b in range(a+1,len(ids)):
            i,j=ids[a],ids[b]
            pi,pj=R[101][i]["line"].split(),R[101][j]["line"].split()
            if pi[1:3]!=pj[1:3]: continue
            A,B=pi[1],pi[2]; c1,c2=int(pi[3][1:]),int(pj[3][1:])
            rec=[]
            for s in (101,202):
                ai,qi=R[s][i]["active"],R[s][i]["q"]
                aj,qj=R[s][j]["active"],R[s][j]["q"]
                U=ai|aj
                # need w with w == (c^d) on U; c^d differs per snapshot (q evolves) -> use per-snapshot halves:
                # require w == qi[c1]^qj[c2] on U is ill-formed across snapshots; instead require per-gate
                # half-match: too weak. Correct merge test: single w with w==c^d on U in BOTH snapshots.
                cands=[w for w in range(62) if not U&((qi[c1]^qj[c2])^qi[w]) and not U&((qi[c1]^qj[c2])^qj[w])]
                rec.append(cands)
            inter=[w for w in rec[0] if w in rec[1]]
            if inter: merges[f"{i}+{j}"]={"controls":[A,B],"thirds":[c1,c2],"witness_wires":inter}
    doc={"candidate_sha256":CSHA,"window":[WIN_LO,WIN_HI],"n_inputs":len(xs),
         "cz_pairs_tested":1891,"z_tested":62,"n_ccz":len(ids),
         "both_seed":({k:(v if isinstance(v,str) else v[:20]) for k,v in both.items()}),
         "n_both_lists_truncated_to_20":True,
         "firing_with_survivors":firing_survivors,"vacuous_on_a_seed":vacuous,
         "pair_merges_found":merges,
         "status":"full-pair + pair-merge screen; survivors (if any) need Z3"}
    args.output.write_text(json.dumps(doc,indent=2)+"\n")
    print(json.dumps({"n_ccz":len(ids),"firing_with_survivors":firing_survivors,
                      "vacuous":vacuous,"merges":merges,"output":str(args.output)},indent=2))

if __name__=="__main__":main()
