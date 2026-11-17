# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
import numpy as np,json
from pathlib import Path
from parity_recover import state,basis,reduce,outer,NOUT
BASE=Path(__file__).resolve().parent

def cross_tensor(words,k):
    delta=words[:,5*k:5*k+5].copy()
    if k:delta^=words[:,5*k-5:5*k]
    packed=np.zeros(1232,dtype=np.uint64)
    for j in range(5):packed[:len(delta)]|=(delta[:,j].astype(np.uint64)&127)<<(7*j)
    f=packed.reshape(77,16).copy()
    for b in range(4):
        for lo in range(16):
            if lo&(1<<b):f[:,lo]^=f[:,lo^(1<<b)]
    for b in range(7):
        for hi in range(77):
            if hi&(1<<b):f[hi]^=f[hi^(1<<b)]
    return [sum(int(f[h,l])<<((l-1)*NOUT) for l in range(1,16)) for h in range(77)]

if __name__=='__main__':
    old=np.load(BASE.parent/'input/chem_pack/v14/submission.npz')['angle_words']
    new=np.load(BASE/'all_helpers/submission.npz')['angle_words']
    results=[]
    for k in range(15):
        s=state(k);D=basis([outer(p[l],p['out']) for p in s['products'] for l in ['l1','l2']])
        t0=cross_tensor(old,k);t1=cross_tensor(new,k)
        assert all(reduce(x,D)==0 for x in t0[1:76])
        miss=[h for h in range(1,76) if reduce(t1[h],D)]
        d={'k':k,'changed_words':int(np.count_nonzero(old[:,k*5:k*5+5]!=new[:,k*5:k*5+5])),
           'new_tensor_uncovered_high_columns':len(miss),'old_plan_reusable':not miss}
        results.append(d);print(json.dumps(d),flush=True)
    (BASE/'all_helpers/old_plan_fit.json').write_text(json.dumps(results,indent=2)+'\n')
