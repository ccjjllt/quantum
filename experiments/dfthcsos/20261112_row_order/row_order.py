"""Row-order search for a cheaper chemistry ANGLE loader.

The verifier's chemistry metrics are invariant under permutations of the 76
one-body rows and of the B rows within each rho (with w/U/W/H2_I permuted).
The tensor-QROM loader cost depends on the row order through the batch XOR
deltas.  This script compares current / lexical / nearest-neighbour orders on
the canonical word table.
"""
from __future__ import annotations
import sys, math, json, time, dataclasses
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
BROT=8; J=5; N=76
def deltas(words,J=5):
    K=math.ceil(words.shape[1]/J); out=[]; prev=None
    for k in range(K):
        b=words[:,k*J:(k+1)*J]
        if b.shape[1]<J: b=np.pad(b,((0,0),(0,J-b.shape[1])))
        out.append(b if prev is None else b^prev); prev=b
    return out
def proxy(words):
    tot=0
    for d in deltas(words):
        C=tq.anf_tensor(d,BROT,4); tot+=tq.cost(tq.per_output(C),1<<4,C.shape[1])
    return tot
def nn_order(rows, words):
    """Greedy nearest-neighbour Hamming order of the given row indices."""
    rows=list(rows); n=len(rows)
    if n<=1: return rows
    X=words[np.array(rows)]
    D=np.zeros((n,n),dtype=np.int32)
    for i in range(n):
        D[i]=np.count_nonzero(X[i]!=X,axis=1)
    used=np.zeros(n,dtype=bool); order=[0]; used[0]=True
    for _ in range(n-1):
        i=order[-1]
        cand=np.where(~used)[0]
        j=int(cand[np.argmin(D[i,cand])])
        order.append(j); used[j]=True
    return [rows[k] for k in order]
def main():
    with np.load(P,allow_pickle=False) as z:
        words=z['angle_words']; tree=z['tree_edges']
    inp=load_inputs(P)
    R,B,C=inp.w.shape
    u=reconstruct_u_vectors(words/128,tree); u/=np.linalg.norm(u,axis=1,keepdims=True)
    w0=encode.to_words(encode.tree_angles(u,tree),BROT)
    one=np.arange(N); two=np.arange(N,N+R*B)
    groups=[two[r*B:(r+1)*B] for r in range(R)]
    # orders
    orders={}
    orders['canonical']=list(range(N+R*B))
    orders['lex']=sorted(range(N+R*B), key=lambda i: tuple(w0[i]))
    one_nn=nn_order(one,w0); groups_nn=[nn_order(g,w0) for g in groups]
    orders['nn']=one_nn+[int(x) for g in groups_nn for x in g]
    # nearest-neighbour rho order: order groups by first-row distance
    rg=nn_order(list(range(R)), np.array([w0[g[0]] for g in groups]))
    orders['nn_rho']=one_nn+[int(x) for r in rg for x in groups_nn[r]]
    out=[]
    for name,perm in orders.items():
        perm=np.array(perm,dtype=np.int64)
        wp=w0[perm]
        # two-body permutation within the first N rows only; perm[N:] is a permutation of N..N+RB-1
        tb=perm[N:]-N
        w_arr=inp.w.reshape(R*B,C)[tb].reshape(R,B,C)
        U_arr=np.asarray(inp.params['U']).reshape(R*B,N)[tb].reshape(R,B,N)
        # rho permutation: recover which old rho each new rho group's first row came from
        # perm[N:] is laid out group by group in rg order for nn_rho; for other orders use canonical rho
        if name=='nn_rho':
            rho_perm=np.array(rg,dtype=np.int64)
        else:
            rho_perm=np.arange(R)
        W_arr=inp.W[rho_perm]
        H2_arr=np.asarray(inp.params['H2_I'])[rho_perm]
        inp2=dataclasses.replace(inp,w=w_arr,W=W_arr)
        m=evaluate_words(inp2,wp,tree,BROT)
        p=proxy(wp)
        out.append({'name':name,'proxy':p,'error_1':float(m['error_1']),'error_2':float(m['error_2']),'lambda_eff':float(m['lambda_eff'])})
        print(out[-1],flush=True)
    outpath=ROOT/'.worktree/dfthcsos/artifacts/20261112_row_order'; outpath.mkdir(parents=True,exist_ok=True)
    (outpath/'result.json').write_text(json.dumps(out,indent=2)+'\n')
    best=min(out,key=lambda x:x['proxy'])
    print('BEST',best,flush=True)
if __name__=='__main__': main()
