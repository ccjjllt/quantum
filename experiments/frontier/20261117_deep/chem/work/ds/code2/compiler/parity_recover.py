# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Reconstruct block-cut spaces and independently test linear matroid parity.

Uses the alternating-matrix rank certificate over GF(2). Rank/2 is a
constructive lower bound on the maximum independent product pairing; a low
rank for sampled matrices is NOT a rigorous impossibility proof.
"""
import json,itertools,random,time,argparse
from pathlib import Path
import numpy as np
BASE=Path(__file__).resolve().parent
NOUT=35;NDIM=15*NOUT

def basis(xs):
    d={}
    for x in xs:
        while x:
            j=x.bit_length()-1
            if j in d:x^=d[j]
            else:d[j]=x;break
    return d

def nullspace(xs,n):
    d=basis(xs);out=[]
    for f in range(n):
        if f in d:continue
        x=1<<f
        for p in sorted(d):
            if (d[p]&x).bit_count()&1:x^=1<<p
        out.append(x)
    return out

def reduce(x,d):
    for p in sorted(d,reverse=True):
        if x&(1<<p):x^=d[p]
    return x

def unpack_out(v):
    out=0
    for j in range(5):out|=((v>>(8*j))&127)<<(7*j)
    return out

def outer(l,v):
    out=0
    while l:
        b=l&-l;l^=b;out^=v<<(NOUT*(b.bit_length()-1))
    return out

def state(k):
    raw=json.loads((BASE/f'products_{k}.json').read_text())['products']
    ps=[dict(p,out=unpack_out(p['out'])) for p in raw if p['l1'] or p['l2']]
    par=list(range(15))
    def find(i):
        while par[i]!=i:i=par[i]
        return i
    for p in ps:
        for name in ('l1','l2'):
            bs=[i for i in range(15) if (p[name]>>i)&1]
            for b in bs[1:]:par[find(b)]=find(bs[0])
    parts=[]
    for i in range(15):
        if find(i)==i:parts.append([j for j in range(15) if find(j)==i])
    parts.sort(key=min)
    cols=[outer(p[l],p['out']) for p in ps for l in ['l1','l2']]
    target=[]
    for h in range(77):
        x=0
        for p in ps:
            l=(((p['h2']>>h)&1)*p['l1'])^(((p['h1']>>h)&1)*p['l2'])
            x^=outer(l,p['out'])
        target.append(x)
    cuts=[];full=[];extra=[]
    for part in parts:
        def local(x):
            return sum(((x>>(NOUT*i))&((1<<NOUT)-1))<<(NOUT*j) for j,i in enumerate(part))
        cb=nullspace([local(c) for c in cols],len(part)*NOUT)
        cf=nullspace([local(c) for c in target],len(part)*NOUT)
        b=basis(cb);ext=[]
        for c in cf:
            r=reduce(c,b)
            if r:ext.append(c);b=basis([*b.values(),c])
        cuts.append(cb);full.append(cf);extra.append(ext)
    return {'k':k,'parts':parts,'cuts':cuts,'full_cuts':full,'extra':extra,'target':target,'products':ps}

def form_constraints(cuts,l):
    out=[]
    for c in cuts:
        v=0
        for j in range(3):
            if (l>>j)&1:v^=(c>>(NOUT*j))&((1<<NOUT)-1)
        if v:out.append(v)
    return list(basis(out).values())

def candidates(s,cuts=None):
    if cuts is None:cuts=s['cuts']
    dirs=[]
    for part,cs in zip(s['parts'],cuts):
        assert len(part)==3
        for l in range(1,8):
            ll=sum(1<<part[j] for j in range(3) if (l>>j)&1)
            dirs.append((ll,form_constraints(cs,l)))
    pairs=[];hist={}
    for (l1,c1),(l2,c2) in itertools.combinations(dirs,2):
        if 'windows' in s and not any(((l1|l2)&~w)==0 for w in s['windows']):
            continue
        vs=nullspace(c1+c2,NOUT)
        hist[len(vs)]=hist.get(len(vs),0)+1
        # Pairwise sums span all v-v quadratic matrices needed by Lovasz's
        # alternating rank construction, even if the full subspace is large.
        vv=vs+[a^b for a,b in itertools.combinations(vs,2)]
        for v in vv:pairs.append((outer(l1,v),outer(l2,v),l1,l2,v))
    return pairs,hist

def alternating(pairs,rng,dimension=NDIM):
    rows=[0]*dimension
    for a,b,*_ in pairs:
        if not rng.getrandbits(1):continue
        x=a
        while x:
            z=x&-x;x^=z;rows[z.bit_length()-1]^=b
        x=b
        while x:
            z=x&-x;x^=z;rows[z.bit_length()-1]^=a
    return rows

def multiplication_table():
    aa=np.arange(256,dtype=np.uint16)[:,None]
    bb=np.arange(256,dtype=np.uint16)[None,:]
    out=np.zeros((256,256),dtype=np.uint16)
    a=np.broadcast_to(aa,(256,256)).copy();b=np.broadcast_to(bb,(256,256)).copy()
    for _ in range(8):
        out^=np.where(b&1,a,np.uint16(0));a<<=1;a^=np.where(a&256,np.uint16(0x11b),np.uint16(0));b>>=1
    return out.astype(np.uint8)

MUL=multiplication_table()
INV=np.zeros(256,dtype=np.uint8)
for _i in range(1,256):INV[_i]=np.nonzero(MUL[_i]==1)[0][0]

def gf_rank(A):
    A=A.copy();nr,nc=A.shape;r=0
    for col in range(nc):
        piv=np.nonzero(A[r:,col])[0]
        if not len(piv):continue
        i=r+int(piv[0]);A[[r,i]]=A[[i,r]]
        A[r,col:]=MUL[INV[A[r,col]],A[r,col:]]
        if r+1<nr:
            A[r+1:,col:]^=MUL[A[r+1:,col,None],A[r,None,col:]]
        r+=1
        if r==nr:break
    return r

def alternating_field(pairs,rng,dimension=NDIM):
    rows=np.zeros((dimension,dimension),dtype=np.uint8)
    for a,b,*_ in pairs:
        av=[];bv=[]
        while a:
            x=a&-a;a^=x;av.append(x.bit_length()-1)
        while b:
            x=b&-b;b^=x;bv.append(x.bit_length()-1)
        v=rng.randrange(1,256)
        rows[np.ix_(av,bv)]^=v;rows[np.ix_(bv,av)]^=v
    return rows

def probe(s,cuts=None,repeats=4,seed=773):
    start=time.time();pairs,hist=candidates(s,cuts);rng=random.Random(seed)
    ranks=[gf_rank(alternating_field(pairs,rng)) for _ in range(repeats)]
    dim=NDIM-sum(len(c) for c in (s['cuts'] if cuts is None else cuts))
    return {'dim':dim,'ranks':ranks,'parity_lower_bound':max(ranks)//2,'product_upper_bound':dim-max(ranks)//2,
            'num_candidate_pairs':len(pairs),'intersection_dims':hist,'seconds':time.time()-start}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--k',type=int,default=4);ap.add_argument('--repeats',type=int,default=8);args=ap.parse_args()
    s=state(args.k);(BASE/f'cut_state_{args.k}.json').write_text(json.dumps(s,indent=2)+'\n')
    print('state',args.k,s['parts'],'cuts',list(map(len,s['cuts'])),'full',list(map(len,s['full_cuts'])),'extra',list(map(len,s['extra'])),flush=True)
    print('probe',json.dumps(probe(s,repeats=args.repeats)),flush=True)
