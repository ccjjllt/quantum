import numpy as np, sys, time
sys.path.insert(0,'.')
import fitlib as F, infra as I
pb=F.Problem(); N=F.N
PA0,PA1=pb.PA[:,0],pb.PA[:,1]; sqw=pb.sqw

def vech(X): return X[PA0,PA1]*sqw
def unvech(v):
    M=np.zeros((N,N)); M[PA0,PA1]=v/sqw
    return np.triu(M)+np.triu(M,1).T

def cpals(Xs, B, C, U0=None, sweeps=200, tol=1e-10, verbose=False):
    """Symmetric CP-ALS for X_c = sum_b W[b,c] u_b u_b^T. Returns U (B,N), W (B,C), colerr."""
    C=len(Xs)
    X=np.stack(Xs,axis=0)  # (C,N,N)
    if U0 is None:
        rng=np.random.default_rng(0); U0=rng.standard_normal((B,N))
    U=U0/np.linalg.norm(U0,axis=1,keepdims=True)
    prev=None
    for sw in range(sweeps):
        # W solve
        Hh=np.einsum('bn,k nm,bm->bk',U,X,U,optimize=True)  # (B,C)
        G=(U@U.T)**2
        W=np.linalg.lstsq(G,Hh,rcond=1e-12)[0]
        # U update: A_b = sum_c W[b,c] X_c ; S = W W^T
        A=np.einsum('bc,cnm->bnm',W,X,optimize=True)  # (B,N,N)
        S=W@W.T
        # precompute UU[b'] = u_b' u_b'^T; residual R_b = A_b - sum_{b'!=b} S[b,b'] UU[b']
        UU=np.einsum('bn,bm->bnm',U,U,optimize=True)
        for b in range(B):
            R=A[b]-(S[b]@UU.reshape(B,N*N)).reshape(N,N)+S[b,b]*UU[b]
            R=0.5*(R+R.T)
            ev,evec=np.linalg.eigh(R)
            u=evec[:,-1]
            if u[np.argmax(np.abs(u))]<0: u=-u
            U[b]=u
            UU[b]=np.outer(u,u)
        colerr=float(np.linalg.norm(np.einsum('bn,bc,bm->cnm',U,W,U,optimize=True)-X))
        if verbose and (sw%20==0 or sw==sweeps-1):
            print(f'  cpals sweep {sw}: colerr {1e3*colerr:.3f} mHa',flush=True)
        if prev is not None and abs(prev-colerr)<tol*max(1,colerr):
            break
        prev=colerr
    return U,W,colerr

if __name__=='__main__':
    z=np.load(I.CACHE/'fit_8_143_88.npz'); x=z['x']; R,B,C=int(z['R']),int(z['B']),int(z['C'])
    w=x[:R*B*C].reshape(R,B,C); U=x[R*B*C:].reshape(R,B,N); U=U/np.linalg.norm(U,axis=2,keepdims=True)
    Ys=[pb.proj(U[r])@w[r] for r in range(R)]
    which=int(sys.argv[1]) if len(sys.argv)>1 else 0
    Y=Ys[which]
    Xs=[unvech(Y[:,c]) for c in range(C)]
    rng=np.random.default_rng(1)
    for tag,U0 in [('true',U[which]),('random',rng.standard_normal((B,N)))]:
        t=time.time(); Un,Wn,ce=cpals(Xs,B,C,U0=U0,sweeps=60,verbose=True)
        Yh=pb.proj(Un)@Wn
        print(f'{tag}: col {1e3*ce:.3f} mHa gram {pb.e2_reduced(np.concatenate([Wn.ravel(),Un.ravel()]),1,B,C):.3f} direct {1e3*np.linalg.norm(Yh-Y):.3f} [{time.time()-t:.0f}s]',flush=True)
