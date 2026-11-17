# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Recover an independent matroid-parity basis from an alternating inverse.

Only GF(2^8) arithmetic is used for the randomized witness. Chosen product
columns are separately certified independent over GF(2), so the witness
cannot turn a dependent product plan into an accepted one.
"""
import argparse,json,random,time
from pathlib import Path
import numpy as np
from parity_recover import candidates,basis,MUL,INV,alternating_field,NDIM
BASE=Path(__file__).resolve().parent

def inverse(A):
    n=len(A);A=np.concatenate([A.copy(),np.eye(n,dtype=np.uint8)],axis=1)
    for c in range(n):
        hit=np.flatnonzero(A[c:,c])
        if not len(hit):return None
        p=c+int(hit[0]);A[[c,p]]=A[[p,c]]
        A[c]=MUL[INV[A[c,c]],A[c]]
        coeff=A[:,c].copy();coeff[c]=0
        A^=MUL[coeff[:,None],A[c,None,:]]
    return A[:,n:]

def bitinds(x):
    out=[]
    while x:
        b=x&-x;x^=b;out.append(b.bit_length()-1)
    return out

def project(x,piv):
    return sum(((x>>p)&1)<<j for j,p in enumerate(piv))

def removebit(x,p):return (x&((1<<p)-1))|((x>>(p+1))<<p)

def matching(s,seed=773):
    pairs,hist=candidates(s)
    dim=NDIM-sum(map(len,s['cuts']))
    colbasis=basis([v for p in pairs for v in p[:2]])
    assert len(colbasis)==dim and dim%2==0
    piv=sorted(colbasis)
    coords=[(project(p[0],piv),project(p[1],piv),*p[2:]) for p in pairs]
    rng=random.Random(seed)
    inv=None
    for trial in range(20):
        inv=inverse(alternating_field(coords,rng,dimension=dim))
        if inv is not None:break
    if inv is None:raise RuntimeError('No nonsingular randomized certificate')
    current=[[a,b] for a,b,*_ in coords];chosen=[]
    n=dim
    while n:
        found=None
        for i,(a,b) in enumerate(current):
            if not a or not b or a==b:continue
            av,bv=bitinds(a),bitinds(b)
            val=int(np.bitwise_xor.reduce(inv[np.ix_(av,bv)].ravel()))
            if val:found=i;break
        if found is None:raise RuntimeError('Lost independent pair despite nonsingular witness')
        chosen.append(found)
        # Binary change of coordinate rows sends the pair to two unit vectors.
        p=(current[found][0]&-current[found][0]).bit_length()-1
        def eliminate(mask,pivot):
            nonlocal inv,current
            ix=bitinds(mask)
            if ix:
                inv[pivot,:]^=np.bitwise_xor.reduce(inv[ix,:],axis=0)
                inv[:,pivot]^=np.bitwise_xor.reduce(inv[:,ix],axis=1)
                for ab in current:
                    if (ab[0]>>pivot)&1:ab[0]^=mask
                    if (ab[1]>>pivot)&1:ab[1]^=mask
        eliminate(current[found][0]^(1<<p),p)
        qmask=current[found][1]&~(1<<p)
        q=(qmask&-qmask).bit_length()-1
        eliminate(current[found][1]^(1<<q),q)
        assert current[found]==[1<<p,1<<q]
        t=int(inv[p,q]);assert t
        keep=[i for i in range(n) if i not in (p,q)]
        vp=inv[keep,p].copy();vq=inv[keep,q].copy()
        correction=MUL[INV[t],MUL[vp[:,None],vq[None,:]]^MUL[vq[:,None],vp[None,:]]]
        inv=inv[np.ix_(keep,keep)]^correction
        for ab in current:
            for r in sorted((p,q),reverse=True):
                ab[0]=removebit(ab[0],r);ab[1]=removebit(ab[1],r)
        n-=2
    selected=[pairs[i] for i in chosen]
    assert len(chosen)*2==dim and len(set(chosen))==len(chosen)
    assert len(basis([v for p in selected for v in p[:2]]))==dim
    return selected,{'independent_columns':dim,'products':len(selected),'randomized_trials':trial+1,'seed':seed,'candidate_pairs':len(pairs)}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('state',type=Path);args=ap.parse_args()
    s=json.loads(args.state.read_text());t=time.time();ps,cert=matching(s)
    out=args.state.with_name('matching.json');out.write_text(json.dumps({'pairs':ps,'certificate':cert},indent=2)+'\n')
    print(json.dumps(cert),'seconds',time.time()-t,flush=True)
