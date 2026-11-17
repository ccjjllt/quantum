"""Build a full dfthcsos submission.npz from a fitted (U,w) shape + shipped tree."""
import numpy as np, sys, time, json
sys.path.insert(0,'.')
import fitlib as F, infra as I
from lamopt import LamProblem
pb=F.Problem(); N=F.N
SHIP=I.ROOT/'experiments/frontier/20261117_deep/chem/data/dfthcsos/submission.npz'
zship=np.load(SHIP); tree=zship['tree_edges']; H1_I=zship['H1_I']; Hsym=zship['Hsym_lower']
ref,S,b1=I.reference()
# shipped target h1_prime
LP0=LamProblem(zship['U'],zship['W']); Wt0=zship['H2_I']-zship['W'].sum(axis=1)
h1p_target=LP0.base-np.einsum('rc,rcpq->pq',Wt0,LP0.X,optimize=True)

def encode_vector(v,edges,brot=8):
    u=np.array(v,dtype=float,copy=True)
    imax=int(np.argmax(np.abs(u)))
    if u[imax]<0: u=-u
    words=np.zeros(len(edges),dtype=np.int64)
    for t in range(len(edges)-1,-1,-1):
        p,c=edges[t]
        th=np.arctan2(u[c],u[p])
        if th<0: th+=2*np.pi
        words[t]=int(np.round(th/np.pi*(1<<(brot-1))))&((1<<brot)-1)
        u[p]=np.hypot(u[p],u[c]); u[c]=0.0
    return words

def decode_words(words,edges,brot=8):
    v=np.zeros(len(edges)+1); v[0]=1.0
    for t,(p,c) in enumerate(edges):
        th=np.pi*float(words[t])/(1<<(brot-1)); a,bb=v[p],v[c]
        v[p]=np.cos(th)*a-np.sin(th)*bb; v[c]=np.sin(th)*a+np.cos(th)*bb
    return v

def encode_rows(U,edges,brot=8):
    rows=U.reshape(-1,N); out=np.zeros((rows.shape[0],len(edges)),dtype=np.int64)
    for k,v in enumerate(rows): out[k]=encode_vector(v,edges,brot)
    return out

def solve_W(U,w,lams=(1e-3,3e-3,1e-2,3e-2,1e-1,1.0)):
    LP=LamProblem(U,w); A=LP.X.reshape(LP.R*LP.C,N*N).T; b=(LP.base-h1p_target).ravel()
    AtA=A.T@A; Atb=A.T@b; best=None
    for lam in lams:
        W=np.linalg.solve(AtA+lam*np.eye(LP.R*LP.C),Atb).reshape(LP.R,LP.C)
        st=LP.stats(W); st['lam']=lam; st['res']=float(np.linalg.norm(A@W.ravel()-b))
        if np.isfinite(st['lambda_eff']) and st['E_gap']>I.E_GAP_FLOOR and st['Lambda']>I.LAMBDA_FLOOR:
            if best is None or st['lambda_eff']<best[0]: best=(st['lambda_eff'],W,st)
    if best is None: raise RuntimeError('no feasible W')
    return best[1],best[2],LP

def main(path,out):
    zz=np.load(path); x=zz['x']; R,B,C=int(zz['R']),int(zz['B']),int(zz['C'])
    w=x[:R*B*C].reshape(R,B,C); U=x[R*B*C:].reshape(R,B,N); U/=np.linalg.norm(U,axis=2,keepdims=True)
    e2cont=pb.e2_reduced(x,R,B,C); print('fit',(R,B,C),'continuous e2',e2cont)
    W,st,LP=solve_W(U,w)
    print('W ridge',st['lam'],'res',st['res'],'Lambda',st['Lambda'],'E_gap',st['E_gap'],'le',st['lambda_eff'])
    # encode two-body, decode, re-solve W on decoded X
    words2=encode_rows(U,tree); Uq=np.stack([decode_words(words2[k],tree) for k in range(words2.shape[0])])
    Uq=Uq.reshape(R,B,N)
    rownorm=np.linalg.norm(Uq,axis=2,keepdims=True); Uq=Uq/np.maximum(rownorm,1e-300)
    W,st,LP=solve_W(Uq,w)
    print('W q ridge',st['lam'],'res',st['res'],'Lambda',st['Lambda'],'E_gap',st['E_gap'],'le',st['lambda_eff'])
    # one-body eigenvectors of h1p for the quantized X
    X=LP.X; h1p=LP.base-np.einsum('rc,rcpq->pq',W,X,optimize=True)
    ev,V=np.linalg.eigh(h1p)
    one=encode_rows(V.T,tree)
    allw=np.vstack([one,words2])
    m=I.metrics_from_words(allw,w,W,tree,ref,S,b1,8)
    print('OFFICIAL metrics:')
    for k in ('error_1','error_2','Lambda','E_gap','lambda_eff','gap_in_domain'):
        print(' ',k,m[k])
    # per-row norms / roundtrip
    rows=np.vstack([V.T,Uq.reshape(-1,N)])
    dec=np.stack([decode_words(allw[k],tree) for k in range(allw.shape[0])])
    ov=np.abs(np.sum(dec*rows,axis=1))
    print('row norms min/max',np.linalg.norm(dec,axis=1).min(),np.linalg.norm(dec,axis=1).max(),'overlap min/mean',ov.min(),ov.mean())
    # save npz
    H2_I=W+w.sum(axis=1)
    np.savez_compressed(out,U=Uq,W=w,H2_I=H2_I,H1_I=np.float32(H1_I),Hsym_lower=np.asarray(Hsym,np.float32),tree_edges=tree,angle_words=allw)
    print('saved',out, 'angle_words',allw.shape)
if __name__=='__main__': main(sys.argv[1],sys.argv[2])
