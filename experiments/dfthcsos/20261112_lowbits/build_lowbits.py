"""Build a signed-gauge Lera table with tensorqrom at lowbits 3/4/5 and measure T/Q."""
from __future__ import annotations
import sys, time
from pathlib import Path
import numpy as np
ROOT=Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0,str(ROOT/'data/competition/verifiers'))
sys.path.insert(0,str(ROOT/'artifacts/20261112_chem_pipeline/dfthc_refit'))
import tensorqrom as tq
from dfthcsos.scoreinfra.circuits import circuit_costs
from dfthcsos.verify import heuristic_costs, load_inputs, evaluate_words

P=ROOT/'artifacts/20261112_chem_pipeline/refined_845.npz'
def main():
    with np.load(P,allow_pickle=False) as z:
        words=np.asarray(z['angle_words'],np.int64)
        tree=np.asarray(z['tree_edges'],np.int64)
        coded=[int(x) for x in z['coded']] if 'coded' in z.files else []
        brot=int(z['brot']) if 'brot' in z.files else 8
    inp=load_inputs(P)
    R,B,C=inp.w.shape
    m=evaluate_words(inp,words,tree,brot)
    print('metrics',{k:float(m[k]) for k in ('error_1','error_2','Lambda','E_gap','lambda_eff')},flush=True)
    hc=heuristic_costs(76,R,B,C,brot)
    print('heuristic',hc['toffoli'],hc['persistent_qubits'],hc['temporary_qubits'],flush=True)
    for lb in (3,4,5):
        t0=time.time()
        try:
            fam=tq.build_family(words,brot=brot,j=5,lowbits=lb,trials=6,jobs=1,coded=coded)
            cc=circuit_costs(fam)
            T=sum(c['max_magic'] for c in cc); Qmax=max(c['num_qubits'] for c in cc)
            sel=11
            temp=Qmax-sel-5*brot
            Q=hc['persistent_qubits']+5*brot+max(hc['temporary_qubits'],temp)
            Ttot=T+hc['toffoli']
            score=float(m['lambda_eff'])*Ttot*Q
            print('lowbits',lb,'anglesT',T,'anglesT/pass',T/2,'Qmax',Qmax,'temp',temp,'Q',Q,'Ttot',Ttot,'score',score,'sec',round(time.time()-t0,1),flush=True)
            out=ROOT/'.worktree/dfthcsos/artifacts/20261112_lowbits'/f'lb{lb}'
            out.mkdir(parents=True,exist_ok=True)
            for k,c in enumerate(fam): c.to_file(str(out/f'angle_k_{k}.kmb'),format='kmb')
            np.savez(out/'submission.npz',**{k:np.asarray(inp.params[k]) for k in ('U','W','H2_I','H1_I','Hsym_lower')},tree_edges=tree,angle_words=words)
            print('WROTE',out,flush=True)
        except Exception as e:
            print('lowbits',lb,'ERR',repr(e),flush=True)
if __name__=='__main__': main()
