"""Survey Lera's quantized DF-THC tables with the official metrics and the tensorqrom cost proxy."""
from __future__ import annotations
import sys, math, json, glob
from pathlib import Path
import numpy as np
ROOT=Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0,str(ROOT/'data/competition/verifiers'))
sys.path.insert(0,str(ROOT/'artifacts/20261112_chem_pipeline/dfthc_refit'))
import tensorqrom as tq
from dfthcsos.verify import load_inputs, evaluate_words, heuristic_costs

J=5; BROT=8; N=76
def deltas(words,J=5):
    K=math.ceil(words.shape[1]/J); out=[]; prev=None
    for k in range(K):
        b=words[:,k*J:(k+1)*J]
        if b.shape[1]<J: b=np.pad(b,((0,0),(0,J-b.shape[1])))
        out.append(b if prev is None else b^prev); prev=b
    return out
def proxy(words):
    return sum(tq.cost(tq.per_output(tq.anf_tensor(d,BROT,4)),1<<4,tq.anf_tensor(d,BROT,4).shape[1]) for d in deltas(words))
def survey(path):
    with np.load(path,allow_pickle=False) as z:
        if 'angle_words' not in z.files or 'tree_edges' not in z.files: return None
        words=np.asarray(z['angle_words'],np.int64); tree=np.asarray(z['tree_edges'],np.int64)
        brot=int(z['brot']) if 'brot' in z.files else BROT
        inp=load_inputs(path)
        R,B,C=inp.w.shape
        if words.shape!=(N+R*B,N-1): return {'path':str(path),'err':f'words shape {words.shape} != {(N+R*B,N-1)}'}
        m=evaluate_words(inp,words,tree,brot)
        hc=heuristic_costs(N,R,B,C,brot)
        pt=proxy(words)
        # calibrated tensorqrom shared factor from the current table: 4097/5119
        cal=4097.0/5119.0
        at=pt*cal
        T=at+hc['toffoli']; Q=hc['persistent_qubits']+J*brot+max(hc['temporary_qubits'],77)
        return {'path':Path(path).name,'R':R,'B':B,'C':C,'brot':brot,
                'error_1_mHa':1e3*float(m['error_1']),'error_2_mHa':1e3*float(m['error_2']),
                'Lambda':float(m['Lambda']),'E_gap':float(m['E_gap']),'lambda_eff':float(m['lambda_eff']),
                'A_proxy':pt,'A_cal':at,'heurT':hc['toffoli'],'T':T,'Q':Q,'score':float(m['lambda_eff'])*T*Q}
if __name__=='__main__':
    paths=[ROOT/'artifacts/20261112_public_25367/dfthcsos/submission.npz']
    paths += sorted((ROOT/'artifacts/20261112_chem_pipeline').glob('*.npz'))
    rows=[]
    for p in paths:
        try:
            r=survey(p)
            if r: rows.append(r); print(json.dumps(r),flush=True)
        except Exception as e:
            print(json.dumps({'path':Path(p).name,'err':str(e)}),flush=True)
    rows=[r for r in rows if 'err' not in r]
    rows.sort(key=lambda r:r['score'])
    out=ROOT/'.worktree/dfthcsos/artifacts/20261112_table_survey'
    out.mkdir(parents=True,exist_ok=True)
    (out/'survey.json').write_text(json.dumps(rows,indent=2)+'\n')
    print('BEST',json.dumps(rows[0]) if rows else None,flush=True)
