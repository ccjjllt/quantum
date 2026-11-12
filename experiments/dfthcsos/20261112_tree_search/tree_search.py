"""Search Givens trees for a cheaper ANGLE loader on the current (8,143,44) table.

Static proxy: decode the current 8-bit words to unit vectors, re-encode them on a
candidate tree with the official unsigned Givens encoding, form the 15 batch XOR
deltas (J=5), and sum tensorqrom.per_output cost.  The current tree is the
reference (per_output 5120, official loader 4097 after tensorqrom.shared).
The best candidates are evaluated with the official chemistry metrics; a full
78,080-shot PASS is only claimed if actually run.
"""
from __future__ import annotations
import math, sys, json, time
from pathlib import Path
import numpy as np

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0, str(ROOT/'data/competition/verifiers'))
sys.path.insert(0, str(ROOT/'artifacts/20261112_chem_pipeline/dfthc_refit'))
import tensorqrom as tq
import encode
from dfthcsos.verify import load_inputs, evaluate_words
from dfthcsos.scoreinfra.dfthc_math import reconstruct_u_vectors

BROT=8; J=5; N=76
P = ROOT/'artifacts/20261112_public_25367/dfthcsos/submission.npz'

def words_from_vectors(u, edges):
    return encode.to_words(encode.tree_angles(u, edges), BROT)

def deltas(words, J=5):
    K=math.ceil(words.shape[1]/J); out=[]; prev=None
    for k in range(K):
        b=words[:,k*J:(k+1)*J]
        if b.shape[1]<J: b=np.pad(b,((0,0),(0,J-b.shape[1])))
        out.append(b if prev is None else b^prev); prev=b
    return out

def proxy(words):
    tot=0
    for delta in deltas(words):
        C=tq.anf_tensor(delta,BROT,4)
        tot += tq.cost(tq.per_output(C), 1<<4, C.shape[1])
    return tot

def path_tree():
    return np.array([[i,i+1] for i in range(N-1)], dtype=np.int64)

def star_tree():
    return np.array([[0,i] for i in range(1,N)], dtype=np.int64)

def heap_tree():
    return np.array([[(i-1)//2,i] for i in range(1,N)], dtype=np.int64)

def random_tree(rng):
    order=list(range(N)); rng.shuffle(order)
    order.remove(0); order=[0]+order
    return np.array([[order[int(rng.integers(0,i))], order[i]] for i in range(1,N)], dtype=np.int64)

def main():
    with np.load(P,allow_pickle=False) as d:
        words=d['angle_words']; tree=d['tree_edges']
    inp=load_inputs(P)
    u=reconstruct_u_vectors(words/(1<<(BROT-1)), tree)
    candidates=[('current',tree),('path',path_tree()),('star',star_tree()),('heap',heap_tree())]
    rng=np.random.default_rng(20261112)
    for i in range(24):
        candidates.append((f'random{i}', random_tree(rng)))
    rows=[]
    for name,edges in candidates:
        t0=time.time()
        w=words_from_vectors(u,edges)
        pr=proxy(w)
        rows.append((pr,name,edges.copy(),w,round(time.time()-t0,1)))
        print(pr,name,rows[-1][-1],flush=True)
    rows.sort(key=lambda x:x[0])
    best=rows[0]
    print('BEST',best[0],best[1],flush=True)
    m=evaluate_words(inp,best[3],best[2],BROT)
    print('BEST METRICS',{k:float(m[k]) for k in ('error_1','error_2','Lambda','E_gap','lambda_eff')},flush=True)
    out=ROOT/'.worktree/dfthcsos/artifacts/20261112_tree_search'
    out.mkdir(parents=True,exist_ok=True)
    np.savez(out/'best_tree.npz',tree_edges=best[2],angle_words=best[3])
    (out/'results.json').write_text(json.dumps([{'proxy':int(r[0]),'name':r[1],'seconds':r[4]} for r in rows],indent=2)+'\n')
    print('WROTE',out,flush=True)
if __name__=='__main__': main()
