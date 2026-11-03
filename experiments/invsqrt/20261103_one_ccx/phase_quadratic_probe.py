"""Manual Clifford replacement hypotheses at two fine-phase CCZ sites.

Fit the complete degree<=2 phase span of live wires, then check the fixed
expression on an independent trajectory sample. This is discovery, not proof.
"""
import argparse,json,random
from affine_probe import load, OUT, SHA, inputs

SITES=(27834,28441)


def snapshots(xs,seed):
    _,ops=load();n=len(xs);allbits=(1<<n)-1;rng=random.Random(seed)
    q=[sum(((x>>j)&1)<<i for i,x in enumerate(xs)) for j in range(22)]+[0]*40
    bits={};stack=[];snap={}
    for i,line in enumerate(ops[:max(SITES)+1]):
        p=line.split();k=p[0]
        if k=='PUSH_CONDITION':stack.append(bits.get(int(p[-1][1:]),0));continue
        if k=='POP_CONDITION':
            if stack:stack.pop()
            continue
        active=allbits
        for c in stack:active &= c
        if 'if' in p:active &= bits.get(int(p[-1][1:]),0)
        qs=[int(t[1:]) for t in p[1:] if t.startswith('q')]
        if i in SITES:snap[i]=(list(q),active,qs)
        if k=='X':q[qs[0]] ^= active
        elif k=='CX':q[qs[1]] ^= q[qs[0]]&active
        elif k=='CCX':q[qs[2]] ^= q[qs[0]]&q[qs[1]]&active
        elif k in ('SWAP','CSWAP'):
            a,b=qs[-2:];m=active if k=='SWAP' else active&q[qs[0]]
            d=(q[a]^q[b])&m;q[a]^=d;q[b]^=d
        elif k in ('R','HMR'):
            outcome=rng.getrandbits(n)
            if k=='HMR':
                b=int(p[2][1:]);bits[b]=(bits.get(b,0)&~active)|(outcome&active)
            q[qs[0]] &= ~active
        elif k.startswith('BIT_'):
            b=int(p[1][1:]);old=bits.get(b,0)
            bits[b]=old^active if k=='BIT_INVERT' else old&~active if k=='BIT_STORE0' else old|active
    return snap


def columns(q,mask):
    yield (),mask
    for i in range(62):yield (i,),q[i]&mask
    for i in range(62):
        for j in range(i+1,62):yield (i,j),q[i]&q[j]&mask


def fit(q,mask,qs):
    basis={};names=[]
    for name,v in columns(q,mask):
        bits=1<<len(names);names.append(name)
        while v:
            p=v.bit_length()-1
            if p not in basis:basis[p]=(v,bits);break
            w,c=basis[p];v^=w;bits^=c
    target=mask
    for w in qs:target &= q[w]
    coeff=0
    while target:
        p=target.bit_length()-1
        if p not in basis:return None,len(basis)
        w,c=basis[p];target^=w;coeff^=c
    return [list(n) for i,n in enumerate(names) if coeff>>i&1],len(basis)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--n',type=int,default=32768);args=ap.parse_args()
    xs=inputs(20261103,args.n)+[x for x in range(1,64) for _ in range(128)]
    ys=inputs(20261104,args.n)+[x for x in range(1,64) for _ in range(128)]
    s=snapshots(xs,883);t=snapshots(ys,884);rows=[]
    for i in SITES:
        q,m,qs=s[i];expr,rank=fit(q,m,qs)
        r={'op':i,'rank':rank,'expression':expr,'sample_count':len(xs),'active':m.bit_count()}
        if expr is not None:
            qq,mm,qss=t[i];pred=0
            for term in expr:
                v=mm
                for j in term:v &= qq[j]
                pred ^= v
            want=mm
            for j in qss:want &= qq[j]
            r['independent_mismatches']=(pred^want).bit_count()
        rows.append(r);print(json.dumps(r),flush=True)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'phase_quadratic_probe.json').write_text(json.dumps({'baseline_sha256':SHA,'scope':'sample hypotheses, not proof','rows':rows},indent=2)+'\n')


if __name__=='__main__':main()
