import numpy as np, sys, time, os
sys.path.insert(0,'.')
import fitlib as F, infra as I
from init_span import init_span
pb=F.Problem(); N=F.N
R,B,C=int(sys.argv[1]),int(sys.argv[2]),int(sys.argv[3])
mode=sys.argv[4] if len(sys.argv)>4 else 'ship'
rounds=int(sys.argv[5]) if len(sys.argv)>5 else 20
itw=int(sys.argv[6]) if len(sys.argv)>6 else 300
itu=int(sys.argv[7]) if len(sys.argv)>7 else 200
suffix=sys.argv[8] if len(sys.argv)>8 else ''
K=R*C
tag=(f'{R}_{B}_{C}_{mode}' if not mode.startswith('load:') else f'{R}_{B}_{C}_load')+suffix
if mode.startswith('load:'):
    z=np.load(mode[5:]); x=z['x']; xR,xB,xC=int(z['R']),int(z['B']),int(z['C'])
    assert (xR,xB,xC)==(R,B,C),(xR,xB,xC)
    F.log(f'{tag}: loaded start {pb.e2_reduced(x,R,B,C):.3f}')
else:
    z=np.load(I.ROOT/'experiments/frontier/20261117_deep/chem/data/dfthcsos/submission.npz')
    Xs0=F.shipped_Xs(z); pool=z['U'].reshape(-1,N)
    if mode=='ship':
        if K<=len(Xs0):
            order=np.argsort([-np.linalg.norm(X) for X in Xs0])[:K]; tg=[Xs0[i] for i in order]
        else:
            tg=F.targets_from_shipped_plus_residual(pb,Xs0,K)
    elif mode=='ref88':
        zz=np.load(I.CACHE/'fit_8_143_88.npz'); xx=zz['x']; R8,B8,C8=int(zz['R']),int(zz['B']),int(zz['C'])
        w8=xx[:R8*B8*C8].reshape(R8,B8,C8); U8=xx[R8*B8*C8:].reshape(R8,B8,N); U8/=np.linalg.norm(U8,axis=2,keepdims=True)
        Y=np.hstack([pb.proj(U8[r])@w8[r] for r in range(R8)])
        Uy,s,Vt=np.linalg.svd(Y,full_matrices=False); Yk=Uy[:,:K]*s[:K]
        tg=[]
        for k in range(K):
            M=np.zeros((N,N)); M[pb.PA[:,0],pb.PA[:,1]]=Yk[:,k]/pb.sqw
            tg.append(np.triu(M)+np.triu(M,1).T)
    else: raise SystemExit(mode)
    F.log(f'{tag}: K {K} rows {N+R*B} floor {pb.floor(K):.3f}; {len(tg)} targets')
    t=time.time(); x=init_span(pb,tg,R,B,C,pool); F.log(f'{tag}: init {pb.e2_reduced(x,R,B,C):.3f} [{time.time()-t:.0f}s]')
    np.savez_compressed(I.CACHE/f'ck_{tag}.npz',x=x,R=R,B=B,C=C)
out=I.CACHE/f'ck_{tag}.npz'
for rd in range(rounds):
    x=F.alt_min(pb,x,R,B,C,rounds=1,itw=itw,itu=itu,tag=tag)
    e=pb.e2_reduced(x,R,B,C)
    np.savez_compressed(out,x=x,R=R,B=B,C=C)
    F.log(f'== {tag} round {rd}: {e:.3f} mHa (floor {pb.floor(K):.3f})')
    if e<15: break
F.log(f'DONE {tag}: {pb.e2_reduced(x,R,B,C):.3f} mHa')
