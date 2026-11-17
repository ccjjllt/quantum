# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
import json,numpy as np
from pathlib import Path
from parity_recover import *
from gauge_plan_fit import cross_tensor
BASE=Path(__file__).resolve().parent

def coordinate_basis(xs):
    d={}
    for i,x in enumerate(xs):
        co=1<<i
        while x:
            p=x.bit_length()-1
            if p in d:x^=d[p][0];co^=d[p][1]
            else:d[p]=(x,co);break
    return d

def coordinates(x,d):
    co=0
    while x:
        p=x.bit_length()-1
        if p not in d:raise ValueError('outside basis')
        x^=d[p][0];co^=d[p][1]
    return co

def local(x,part):
    return sum(((x>>(NOUT*i))&((1<<NOUT)-1))<<(NOUT*j) for j,i in enumerate(part))

def forced(part,coded):
    if not coded:return []
    return [1<<(NOUT*j+7*z) for j,m in enumerate(part) if (m+1)&m for z in range(5)]

def complete_forced(full,F):
    b=basis(F);out=[]
    for v in full:
        r=reduce(v,b)
        if r:out.append(v);b=basis([*b.values(),v])
    return out

def rref(rows,n):
    d=basis(rows)
    for p in sorted(d):
        for q in sorted(d):
            if q>p and d[q]&(1<<p):d[q]^=d[p]
    return [d[p] for p in sorted(d,reverse=True)]

def materialize(F,Q,R):
    out=list(F)
    for r in R:
        v=0
        for j,q in enumerate(Q):
            if (r>>j)&1:v^=q
        out.append(v)
    return out

def transport(k,words=None):
    s=state(k)
    if words is None:words=np.load(BASE/'all_helpers/completed_words.npy')
    target=cross_tensor(words,k)
    blocks=[]
    for i,part in enumerate(s['parts']):
        F=forced(part,k>=4)
        oldQ=complete_forced(s['full_cuts'][i],F)
        co=coordinate_basis(F+oldQ)
        R=rref([coordinates(c,co)>>len(F) for c in s['cuts'][i]],len(oldQ))
        fullnew=nullspace([local(x,part) for x in target[1:]],len(part)*NOUT)
        Q=complete_forced(fullnew,F)
        if len(Q)!=len(oldQ):
            print('DIMENSION_CHANGE',k,i,len(oldQ),len(Q))
            R=rref([r&((1<<len(Q))-1) for r in R],len(Q))
        blocks.append({'F':F,'Q':Q,'R':R,'n':len(Q),'old_n':len(oldQ)})
    new=dict(s,words_source='all_helpers/completed_words.npy',target=target,blocks=blocks)
    new['cuts']=[materialize(b['F'],b['Q'],b['R']) for b in blocks]
    new['full_cuts']=[b['F']+b['Q'] for b in blocks]
    return new

if __name__=='__main__':
    for k in range(15):
        s=transport(k);pairs,hist=candidates(s);rank=len(basis([x for p in pairs for x in p[:2]]))
        print(k,'cuts',list(map(len,s['cuts'])),'spanrank',rank,'dim',NDIM-sum(map(len,s['cuts'])),'pairs',len(pairs),flush=True)
        (BASE/f'all_helpers/initial_state_{k}.json').write_text(json.dumps(s,indent=2)+'\n')
