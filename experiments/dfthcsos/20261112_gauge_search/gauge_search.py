"""Gauge search for a cheaper tensor-QROM loader on the current chemistry table.

Decode the current words to unit vectors, re-encode canonically, then flip row
signs (chemistry metrics are invariant) and measure the tensorqrom per_output
Toffoli proxy. A lower proxy is a candidate for a full loader build.
"""
from __future__ import annotations
import sys, math, json, time
from pathlib import Path
import numpy as np
ROOT=Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0,str(ROOT/'data/competition/verifiers'))
sys.path.insert(0,str(ROOT/'artifacts/20261112_chem_pipeline/dfthc_refit'))
import tensorqrom as tq
import encode
from dfthcsos.verify import load_inputs, evaluate_words
from dfthcsos.scoreinfra.dfthc_math import reconstruct_u_vectors

P=ROOT/'artifacts/20261112_public_25367/dfthcsos/submission.npz'
BROT=8; J=5
def deltas(words,J=5):
    K=math.ceil(words.shape[1]/J); out=[]; prev=None
    for k in range(K):
        b=words[:,k*J:(k+1)*J]
        if b.shape[1]<J: b=np.pad(b,((0,0),(0,J-b.shape[1])))
        out.append(b if prev is None else b^prev); prev=b
    return out
def proxy(words):
    return sum(tq.cost(tq.per_output(tq.anf_tensor(d,BROT,4)),1<<4,tq.anf_tensor(d,BROT,4).shape[1]) for d in deltas(words))
def main():
    with np.load(P,allow_pickle=False) as z:
        words=z['angle_words']; tree=z['tree_edges']
    inp=load_inputs(P)
    u=reconstruct_u_vectors(words/128,tree); u/=np.linalg.norm(u,axis=1,keepdims=True)
    w0=encode.to_words(encode.tree_angles(u,tree),BROT)
    m0=evaluate_words(inp,w0,tree,BROT)
    p0=proxy(w0)
    print('canonical metrics',{k:float(m0[k]) for k in ('error_1','error_2','lambda_eff')},'proxy',p0,flush=True)
    # test one row flip changes only that row
    r=0; u2=u.copy(); u2[r]=-u2[r]
    w2=encode.to_words(encode.tree_angles(u2,tree),BROT)
    print('one-flip word diff total',np.count_nonzero(w2!=w0),'row0 diff',np.count_nonzero(w2[r]!=w0[r]),flush=True)
    # greedy flips on a random subset, multiple sweeps
    rng=np.random.default_rng(20261112)
    order=rng.permutation(len(u))
    cur=w0.copy(); curp=p0
    best=(curp,cur.copy(),[])
    flips=[]
    t0=time.time()
    for sweep in range(2):
        improved=0
        for r in order:
            u2=u.copy()
            if r in flips: u2[r]=-u2[r]  # current sign
            u2[r]=-u2[r]                 # try flip
            w2=encode.to_words(encode.tree_angles(u2,tree),BROT)
            p2=proxy(w2)
            if p2 < curp:
                cur=w2; curp=p2
                if r in flips: flips.remove(r)
                else: flips.append(r)
                improved+=1
        print('sweep',sweep,'proxy',curp,'flips',len(flips),'improved',improved,'sec',round(time.time()-t0,1),flush=True)
        if improved==0: break
    m=evaluate_words(inp,cur,tree,BROT)
    print('best',curp,'flips',len(flips),'metrics',{k:float(m[k]) for k in ('error_1','error_2','lambda_eff')},flush=True)
    out=ROOT/'.worktree/dfthcsos/artifacts/20261112_gauge_search'; out.mkdir(parents=True,exist_ok=True)
    np.savez(out/'best_gauge.npz',angle_words=cur,tree_edges=tree,flips=np.array(flips,dtype=np.int64))
    (out/'result.json').write_text(json.dumps({'proxy0':p0,'proxy_best':curp,'flips':flips,'seconds':round(time.time()-t0,1)})+'\n')
    print('WROTE',out,flush=True)
if __name__=='__main__': main()
