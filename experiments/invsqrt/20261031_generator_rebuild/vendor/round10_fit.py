# SPDX-License-Identifier: Apache-2.0
"""Bounded own coefficient refits; no public circuit data or external optimizer."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import argparse,dataclasses,json,sys,time,gc
import round10_verify as D
import round10_inv as I

def layout_choices(tables,prm):
    import numpy as np,model as M,fit as F
    if F._D is None:F._D=F.domains()
    a,p,xn,bounds=F._D;b=xn&16383
    c0,c1,c2=[tables[a,j] for j in range(3)]
    delta=M.eval_Y(c0,M.eval_T(c1,c2,b,prm),b,prm)-c0
    lo=np.minimum.reduceat(delta,bounds[:-1]);hi=np.maximum.reduceat(delta,bounds[:-1]);rows=[]
    for LB in range(18,23):
        for S in range(LB,9,-1):
            step=1<<S;base=tables[:,0]%step
            u=base+np.maximum(0,(-lo-base+step-1)//step)*step
            if np.any(u+hi>=(1<<LB)) or np.any(tables[:,0]-u<0):continue
            nH=int(((tables[:,0]-u)>>S).max()).bit_length()
            peak=max(24+2*LB+prm.nT+prm.F2-1,26+LB-1+nH+prm.nT+prm.F2-1+4)
            rows.append(dict(LB=LB,S=S,nH=nH,peak_estimate=peak));break
    return rows

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--variant',default='all');ap.add_argument('--verify',action='store_true');a=ap.parse_args()
    I.setup(D.COMP);D.start_audit()
    import numpy as np,fit as F,model as M,run,hsplit as H
    M.CACHE=str(D.OUT/'reference.npz');F._D=F.domains()
    # The omitted accumulator bit requires even anchors during fitting.
    original=F.best_C0_g
    def even_C0(R,ytgt,w,G0,top):
        center=int(round(float(np.median(ytgt-R))));limit=int(top-1-R.max());center=min(center,limit-limit%2);best=None
        for c in range(center-16,center+17):
            if c%2 or c>limit:continue
            score=float(np.max(np.abs((((c+R)>>G0)<<G0)-ytgt)*w))
            if best is None or score<best[0]:best=(score,c)
        return best
    F.best_C0_g=even_C0
    original_fit_source=__import__('inspect').getsource(F.fit_segment)
    variants=[('base',[28,19,8,1],[5]),('f2_7',[28,19,7,1],[4]),('f2_6',[28,19,6,1],[3]),('f27_t18_f7',[27,18,7,1],[5]),('f27_t18_f6',[27,18,6,1],[4]),('derivative',[28,19,8,1],[5]),('deriv_f2_7',[28,19,7,1],[4]),('deriv_f27',[27,18,7,1],[5])]
    if a.variant=='all':variants=variants[:5]
    elif a.variant=='derivatives':variants=[v for v in variants if v[0].startswith('deriv')]
    else:variants=[v for v in variants if v[0]==a.variant]
    rows=[]
    for name,params,drops in variants:
        folder=D.OUT/name;folder.mkdir(exist_ok=True);D.progress('fit_coefficients',candidate=name,params=params)
        prm,_=run.parse([*map(str,params),'sd=1','dropA='+','.join(map(str,drops))])
        if name.startswith('deriv'):
            import inspect
            from round10_virtual import parity_indices
            code=original_fit_source
            code=code.replace('        key = (C1, C2)','        if C1%2 != sum(C2>>k&1 for k in virtual_parity)%2:return (np.inf,0)\n        key = (C1, C2)')
            F.virtual_parity=parity_indices(prm,prm.F2-1)
            exec(compile(code,'<own-derivative-parity-fit>','exec'),F.__dict__)
        if name=='base':tables=np.array(json.loads((I.BASE/'round5_marsyas_tables.json').read_text()),dtype=np.int64);tables[:,0]+=tables[:,0]&1;approx=None
        else:tables,approx=F.fit_all(prm,rad1=6,rad2=3,workers=int(os.environ.get('QCC_JOBS','4')))
        recipe=dict(params=params,dropA=drops,tables=tables.tolist(),derivative=name.startswith('deriv'));(folder/'coefficients.json').write_text(json.dumps(recipe))
        layouts=layout_choices(tables,prm);row=dict(name=name,params=params,drops=drops,approx_worst=approx,layouts=layouts)
        D.record(name+'_fit.json',row);D.progress('coefficient_fit_done',**row)
        if name.startswith('deriv'):layouts=[dict(LB=21 if params[0]==28 else 20,S=20 if params[0]==28 else 19)]
        for choice in layouts[:2]:
            recipe.update(LB=choice['LB'],S=choice['S']);label=name+f"-L{choice['LB']}-S{choice['S']}";build=folder/label
            try:
                model=I.build_model(build/'model',recipe=recipe)
                (build/'recipe.json').write_text(json.dumps(recipe))
                plan=';'.join(f'{prm.nT-1-2*j}:'+','.join(map(str,(i,i-1))) for j,i in enumerate([11,9,7,5,3,1]))
                c,rep=I.build_variant(build,model,plan=plan);del c;gc.collect()
                p=I.optimize(build)
                import kickmix as km,check as C
                c=km.Circuit.from_file(str(p),format='kmb');sample=C.report(c,model[0],model[1],{'pass':True,'min_margin':model[4]['margin']},nbatch=4);del c
                item=dict(label=label,recipe=recipe,fit=model[4],raw=rep,sample=sample,path=str(p.relative_to(D.OUT)))
                D.record(label+'_result.json',item);D.progress('model_built',candidate=label,sample=sample)
                if a.verify and sample['cost']<145000:D.measure('invsqrt',p,label)
            except Exception as exc:D.record(label+'_error.json',dict(error=repr(exc)));D.progress('model_error',candidate=label,error=repr(exc))
            gc.collect()
        rows.append(row);D.record('fits.json',rows)
    D.finish_audit();D.progress('done')
if __name__=='__main__':main()
