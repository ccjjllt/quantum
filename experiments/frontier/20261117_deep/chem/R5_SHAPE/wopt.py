import numpy as np, sys, time
from scipy.optimize import minimize
sys.path.insert(0,'.')
import fitlib as F, infra as I
from lamopt import LamProblem

class WOpt:
    def __init__(self,U,w):
        LP=LamProblem(U,w)
        self.LP=LP; self.X=LP.X; self.a=LP.a; self.s=LP.s; self.base=LP.base
        self.R,self.C=LP.R,LP.C; self.Cg0=LP.Cg0
        self.floor=I.E_GAP_FLOOR
    def stats(self,W,grad=True):
        R,C=self.R,self.C; W=W.reshape(R,C)
        h1p=self.base-np.einsum('rc,rcpq->pq',W,self.X,optimize=True)
        ev,V=np.linalg.eigh(h1p)
        lam_h1=np.abs(ev).sum(); tr=ev.sum()
        wB=W+self.s; a=self.a
        lam_h2=0.25*np.sum((a+np.abs(wB))**2)
        Lam=lam_h1+lam_h2
        nneg=-ev[ev<0].sum()
        Eg=self.Cg0+2*nneg+0.5*np.sum(W**2)
        le=np.sqrt(Eg*(2*Lam-Eg)) if 0<Eg<2*Lam else np.nan
        out=dict(Lambda=float(Lam),E_gap=float(Eg),lambda_eff=float(le),lam_h1=float(lam_h1),lam_h2=float(lam_h2),sumW2=float(np.sum(W**2)),nneg=float(nneg))
        if grad:
            # T[i,rc] = v_i^T X_rc v_i
            T=np.einsum('rcpq,ip,iq->irc',self.X,V,V,optimize=True)
            sgn=np.sign(ev)
            dLam=-np.einsum('i,irc->rc',sgn,T,optimize=True)
            dLam=dLam+0.5*(a+np.abs(wB))*np.sign(wB)
            dEg=2*np.einsum('i,irc->rc',(ev<0).astype(float),T,optimize=True)+W
            out['gLambda']=dLam; out['gEgap']=dEg
        return out

def optimize(U,w,pen=100.0,init='neg_s',iters=2000,verbose=True,target_eps=2e-5):
    WO=WOpt(U,w); R,C=WO.R,WO.C
    def fg(x):
        st=WO.stats(x)
        dEg=st['E_gap']-WO.floor-target_eps
        pen_term=pen*max(0.0,-dEg)**2
        f=st['Lambda']+pen_term
        g=st['gLambda'].ravel()-2*pen*max(0.0,-dEg)*st['gEgap'].ravel()
        return f,g
    inits={}
    inits['neg_s']=-WO.s.copy()
    # scan best from wscan
    from wscan import scan
    try:
        b=scan(WO.LP,tag='wopt_init')
        if b is not None:
            sign=-np.sign(WO.s.ravel()+1e-300)
            inits['scan']=((sign*(b['c']*WO.a.ravel())).reshape(R,C)-WO.s)
    except Exception as e: print('scan failed',e)
    rng=np.random.default_rng(0)
    inits['rand']=rng.standard_normal((R,C))*0.5
    best=None
    for name,x0 in inits.items():
        t=time.time(); r=minimize(fg,x0.ravel(),jac=True,method='L-BFGS-B',options=dict(maxiter=iters,maxcor=30,ftol=1e-18,gtol=1e-14))
        st=WO.stats(r.x,grad=False); st['name']=name; st['nit']=r.nit; st['time']=time.time()-t
        if verbose: print(f'{name}: Lambda {st["Lambda"]:.4f} E_gap {st["E_gap"]:.9f} le {st["lambda_eff"]:.6f} sumW2 {st["sumW2"]:.2f} nit {r.nit} [{st["time"]:.0f}s]',flush=True)
        if np.isfinite(st['lambda_eff']) and st['E_gap']>WO.floor and st['Lambda']>I.LAMBDA_FLOOR:
            if best is None or st['lambda_eff']<best[0]: best=(st['lambda_eff'],r.x.copy(),st)
    return best

if __name__=='__main__':
    z=np.load(I.ROOT/'experiments/frontier/20261117_deep/chem/data/dfthcsos/submission.npz')
    U=z['U']; w=z['W']; Wt=z['H2_I']-w.sum(axis=1)
    WO=WOpt(U,w); st=WO.stats(Wt.ravel(),grad=False)
    print('shipped',st)
    best=optimize(U,w,pen=100.0,iters=1000)
    if best: print('BEST',best[2])
