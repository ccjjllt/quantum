import numpy as np, sys, time
from scipy.linalg import eigh as geigh
sys.path.insert(0,'.')
import fitlib as F, infra as I
pb=F.Problem(); N=F.N; H=pb.H

def block_w(pb, x, R,B,C, sweeps=5, update_u=False, verbose=True):
    nw=R*B*C
    w=x[:nw].reshape(R,B,C).copy(); U=x[nw:].reshape(R,B,N).copy(); U/=np.linalg.norm(U,axis=2,keepdims=True)
    Ps=[pb.proj(U[r]) for r in range(R)]
    Gs=[P.T@P for P in Ps]
    PHPs=[P.T@(pb.H@P) for P in Ps]
    Ys=[Ps[r]@w[r] for r in range(R)]
    def err():
        Y=np.hstack(Ys); return 1e3*np.linalg.norm(Y@Y.T-pb.H)
    if verbose: print('block init',err(),flush=True)
    for sw in range(sweeps):
        t0=time.time()
        for r in range(R):
            P=Ps[r]; G=Gs[r]; M=PHPs[r].copy()
            # subtract other groups' contribution: M -= (P^T Yother)(P^T Yother)^T
            Yother=np.hstack([Ys[s] for s in range(R) if s!=r]) if R>1 else np.zeros((pb.NS,0))
            Bt=P.T@Yother
            M-=Bt@Bt.T
            M=0.5*(M+M.T)
            lam,V=geigh(M,G)
            order=np.argsort(lam)[::-1][:C]
            lam=lam[order]
            if np.any(lam<0):
                # keep positive only
                keep=lam>0; order=order[keep]; lam=lam[keep]
            V=V[:,order]
            w[r]=V*np.sqrt(np.maximum(lam,0))[None,:]
            Ys[r]=P@w[r]
        if verbose: print(f'  block sweep {sw}: {err():.3f} mHa [{time.time()-t0:.0f}s]',flush=True)
    return np.concatenate([w.ravel(),U.ravel()]),err()

if __name__=='__main__':
    name=sys.argv[1]; sweeps=int(sys.argv[2]) if len(sys.argv)>2 else 5
    z=np.load(name if name.endswith('.npz') else I.CACHE/f'{name}.npz')
    R,B,C=int(z['R']),int(z['B']),int(z['C']); x=z['x']
    pb=F.Problem(); print('start',pb.e2_reduced(x,R,B,C),flush=True)
    x2,e=block_w(pb,x,R,B,C,sweeps=sweeps,verbose=True)
    print('final',e,'reduced',pb.e2_reduced(x2,R,B,C),flush=True)
    np.savez_compressed(I.CACHE/f'block_{R}_{B}_{C}.npz',x=x2,R=R,B=B,C=C)
