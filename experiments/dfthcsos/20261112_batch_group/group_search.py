"""Search batch composition/order for the 75 ANGLE columns under the tensorqrom proxy.

The verifier applies the 15 J=5 batches in order; the final words are the XOR of
the deltas, independent of grouping.  Grouping and batch order are therefore
free variables.  Current groups are consecutive columns.
"""
from __future__ import annotations
import sys, math, json, time
from pathlib import Path
import numpy as np
ROOT=Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0,str(ROOT/'data/competition/verifiers'))
sys.path.insert(0,str(ROOT/'artifacts/20261112_chem_pipeline/dfthc_refit'))
import tensorqrom as tq
from dfthcsos.verify import load_inputs, evaluate_words
P=ROOT/'artifacts/20261112_public_25367/dfthcsos/submission.npz'
BROT=8; J=5; W=75
def proxy_batches(words, groups):
    prev=None; tot=0
    for g in groups:
        b=words[:,g]
        d=b if prev is None else b^prev
        prev=b
        C=tq.anf_tensor(d,BROT,4); tot+=tq.cost(tq.per_output(C),1<<4,C.shape[1])
    return tot
def current_groups():
    return [list(range(i*J,(i+1)*J)) for i in range(W//J)]
def random_groups(rng):
    perm=rng.permutation(W); return [list(perm[i*J:(i+1)*J]) for i in range(W//J)]
def corr_groups(words):
    # columns as 1220-bit signatures; greedy farthest-first grouping by Hamming correlation
    X=(words>127).astype(np.int32)  # high-bit signature
    # similarity: negative Hamming distance; cluster columns by greedy
    C=X.T  # 75 x 1220
    D=(C[:,None,:]!=C[None,:,:]).sum(-1)
    used=set(); groups=[]
    for _ in range(W//J):
        # pick the unused column with largest average distance to used (diverse seed)
        if not used:
            seed=0
        else:
            seed=max((i for i in range(W) if i not in used), key=lambda i: D[i,list(used)].mean() if used else 0)
        g=[seed]; used.add(seed)
        for _ in range(J-1):
            cand=[i for i in range(W) if i not in used]
            # pick the column most similar (small Hamming distance) to the current group
            score=[D[i,g].sum() for i in cand]
            j=cand[int(np.argmin(score))]
            g.append(j); used.add(j)
        groups.append(g)
    return groups
def order_groups(words, groups):
    # order batches to minimize XOR distance between consecutive groups (weighted by size)
    sig=[]
    for g in groups:
        b=words[:,g].reshape(len(words),-1)
        sig.append(b)
    n=len(groups); D=np.zeros((n,n))
    for i in range(n):
        for j in range(n):
            D[i,j]=np.count_nonzero(sig[i]!=sig[j])
    used=[0]; rem=set(range(1,n))
    while rem:
        i=used[-1]; j=min(rem,key=lambda k:D[i,k]); used.append(j); rem.remove(j)
    return [groups[i] for i in used]
def main():
    with np.load(P,allow_pickle=False) as z: words=z['angle_words']; tree=z['tree_edges']
    inp=load_inputs(P)
    cg=current_groups(); p0=proxy_batches(words,cg)
    print('current proxy',p0,flush=True)
    rng=np.random.default_rng(20261112)
    best=(p0,cg,'current')
    for i in range(200):
        g=random_groups(rng); p=proxy_batches(words,g)
        if p<best[0]: best=(p,g,f'random{i}')
    print('best random',best[0],best[2],flush=True)
    c=corr_groups(words); pc=proxy_batches(words,c)
    print('corr groups',pc,flush=True)
    co=order_groups(words,c); pco=proxy_batches(words,co)
    print('corr+order',pco,flush=True)
    for name,g,p in [('corr',c,pc),('corr_order',co,pco)]:
        if p<best[0]: best=(p,g,name)
    print('BEST',best[0],best[2],flush=True)
    # evaluate metrics of the final words (grouping does not change words; sanity)
    m=evaluate_words(inp,words,tree,BROT)
    out=ROOT/'.worktree/dfthcsos/artifacts/20261112_batch_group'; out.mkdir(parents=True,exist_ok=True)
    (out/'result.json').write_text(json.dumps({'proxy_current':p0,'best_proxy':best[0],'best_name':best[2],'best_groups':best[1],'lambda_eff':float(m['lambda_eff'])},indent=2)+'\n')
    print('WROTE',out,flush=True)
if __name__=='__main__': main()
