"""Tower-norm reciprocal with measured erasure of bilinear intermediates."""
from functools import cache, reduce
from operator import xor
import kickmix as km
from .euclid import indices, mul, power


def table(basis):
    return [reduce(xor,(basis[j] for j in indices(i)),0) for i in range(1<<len(basis))]


@cache
def fields():
    z3 = next(x for x in range(2,4096) if power(x,3)^x^1==0)
    bases={3:[1,z3,mul(z3,z3)]}
    norm_const={}
    for k in (3,6):
        z = next(x for x in range(2,4096) if power(x,1<<k)==x^1)
        norm_const[k] = mul(z,z)^z
        bases[2*k]=bases[k]+[mul(z,b) for b in bases[k]]
    tabs={m:table(b) for m,b in bases.items()}
    coord={m:{v:i for i,v in enumerate(t)} for m,t in tabs.items()}
    return bases,tabs,coord,norm_const


@cache
def rank_terms(m):
    bases,tabs,coords,cs=fields()
    if m==3:
        def product(i,j):
            return coords[3][mul(bases[3][i],bases[3][j])]
        # x_i*y_i occurs in its own diagonal term and both incident polar terms.
        return [(1<<i,reduce(xor,(product(i,j) for j in range(3)))) for i in range(3)]+[
            ((1<<i)|(1<<j),product(i,j)) for i in range(3) for j in range(i+1,3)]
    k=m//2
    out=[]
    for mask,z in rank_terms(k):
        out.append((mask,z|(z<<k)))
        out.append((mask<<k,coords[k][mul(cs[k],tabs[k][z])]))
        out.append((mask|(mask<<k),z<<k))
    return out


def norm_stages(m):
    """Arrays contain ordinary polynomial-basis bits at m=12 and tower bits below."""
    bases,tabs,coords,cs=fields()
    inp = [1<<i for i in range(12)] if m==12 else bases[m]
    if m==3:
        value=[coords[3][power(x,6)] for x in tabs[3]]
        lin=[(1<<i,0,value[1<<i]) for i in range(3)]
        quad=[(1<<i,1<<j,value[(1<<i)|(1<<j)]^value[1<<i]^value[1<<j])
              for i in range(3) for j in range(i+1,3)]
        for k in range(8):
            got=reduce(xor,(z for a,b,z in lin+quad if a&k and (not b or b&k)),0)
            assert got==value[k]
        return lin+quad,[]
    k=m//2
    coord_cols=[coords[m][v] for v in inp]
    def lift(mask):
        return sum(((mask&v).bit_count()%2)<<i for i,v in enumerate(coord_cols))
    def out_enc(v):
        return tabs[m][v] if m==12 else v
    norm=[]
    for i in range(m):
        u,v=coord_cols[i]&((1<<k)-1),coord_cols[i]>>k
        lin=mul(tabs[k][u],tabs[k][u])^mul(cs[k],mul(tabs[k][v],tabs[k][v]))
        norm.append((1<<i,0,coords[k][lin]))
    result=[]
    for mask,z in rank_terms(k):
        u,v=lift(mask),lift(mask<<k)
        norm.append((u,v,z))
        result.extend([(u^v,mask<<m,out_enc(z)),(v,mask<<m,out_enc(z<<k))])
    return norm,result


def emit(b,src,tgt,terms,erase=False):
    p=b.alloc_qubits(2)
    if erase:
        meas=b.alloc_bits(len(tgt))
        b.hmr(tgt,meas)
    for a,g,c in terms:
        if c==0:
            continue
        source=[src[i] for i in indices(a)]+[src[i] for i in indices(g)]
        pats=[p[0]]*a.bit_count()+[p[1]]*g.bit_count()
        b.cx(km.array(source),km.array(pats))
        dest=list(indices(c))
        if erase:
            for j in dest:
                b.push_condition(meas[j])
                if g:
                    b.cz(p[0],p[1])
                else:
                    b.z(p[0])
                b.pop_condition()
        elif g:
            pivot=tgt[dest[0]]
            if len(dest)>1:
                b.cx(pivot,km.array([tgt[i] for i in dest[1:]]))
            b.ccx(p[0],p[1],pivot)
            if len(dest)>1:
                b.cx(pivot,km.array([tgt[i] for i in dest[1:]]))
        else:
            b.cx(p[0],km.array([tgt[i] for i in dest]))
        b.cx(km.array(source[::-1]),km.array(pats[::-1]))
    b.free(p)
    if erase:
        b.free(meas)


def inverse(b,x):
    m=len(x)
    norm,finish=norm_stages(m)
    target=b.alloc_qubits(m)
    if m==3:
        emit(b,x,target,norm)
        return target,lambda: erase_leaf(b,x,target,norm)
    n=b.alloc_qubits(m//2)
    emit(b,x,n,norm)
    ni,free_ni=inverse(b,n)
    src=list(x)+list(ni)
    emit(b,src,target,finish)
    def erase():
        emit(b,src,target,finish,True)
        b.free(target)
        free_ni()
        emit(b,x,n,norm,True)
        b.free(n)
    return target,erase


def erase_leaf(b,x,tgt,terms):
    emit(b,x,tgt,terms,True)
    b.free(tgt)
