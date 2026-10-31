# SPDX-License-Identifier: Apache-2.0
"""Own-source invsqrt: Marsyas arithmetic, virtual low bit, exact phase reads.

Phuc Thai described the parity-in-top-wire normalization ladder. This
implementation derives it directly, without reading an assembly fixture.
All numerical inputs are small coefficient/phase JSON, never a circuit.
"""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import argparse,inspect,json,sys,time,gc
ROOT=Path(__file__).resolve().parent
BASE=ROOT

def install_ladder(H,*,derivative=False,retire=0,last=False,initial_lookup=False,generalized=False,bend=False):
    source=inspect.getsource(H._own_original)
    start=source.index('    f1, f2, f4, f8, f16 =')
    stop=source.index('    address =',start)
    source=source[:start]+'''    f2, f4, f8, f16 = list(b.alloc_qubits(4))
    # Count pairs of leading zeros. The first two bits cannot both be one
    # on the promised x <= 3133452 domain; [top2=0] is their affine NOR.
    th=b.alloc_qubits(19)
    b.x(x[2:22]);b.x(th[0]);b.cx(x[21],th[0]);b.cx(x[20],th[0])
    for k in range(1,19):b.init_and(th[k-1],x[20-k],th[k])
    for count in range(2,21,2):
        q=th[count-2];b.cx(q,f2)
        if count%4==0:b.cx(q,f4)
        if count%8==0:b.cx(q,f8)
        if count==16:b.cx(q,f16)
    for k in reversed(range(1,19)):b.del_and(th[k-1],x[20-k],th[k])
    b.cx(x[20],th[0]);b.cx(x[21],th[0]);b.x(th[0]);b.x(x[2:22]);b.free(th)
    for d,f in [(16,f16),(8,f8),(4,f4),(2,f2)]:
        for i in range(21-d,-1,-1):b.cswap(f,x[i],x[i+d])
    # The even shift leaves the leading one at 20 or 21. After X, wire21
    # is the odd-normalization bit. Rotate the remaining 21 wires by one;
    # the wrapped leading one is cancelled, so no parity ancilla is needed.
    b.x(x[21])
    for i in range(19,-1,-1):b.cswap(x[21],x[i],x[i+1])
    b.cx(x[21],x[0])
''' + source[stop:]
    start=source.index('    nf1 =')
    stop=source.index('    Bd.LAST_PEAK',start)
    source=source[:start]+'''    b.cx(x[21],x[0])
    for i in range(20):b.cswap(x[21],x[i],x[i+1])
    b.x(x[21])
    for d,f in [(2,f2),(4,f4),(8,f8),(16,f16)]:
        for i in range(22-d):b.cswap(f,x[i],x[i+d])
        top=list(x[22-d:22]);m=b.alloc_bits(1)[0];b.hmr(f,m)
        b.push_condition(m);b.x(km.array(top))
        if d==2:b.cz(top[0],top[1])
        else:
            anc=b.alloc_qubits(d-2)
            b.init_and(top[0],top[1],anc[0])
            for j in range(1,d-2):b.init_and(anc[j-1],top[j+1],anc[j])
            b.cz(anc[d-3],top[d-1])
            for j in reversed(range(1,d-2)):b.del_and(anc[j-1],top[j+1],anc[j])
            b.del_and(top[0],top[1],anc[0]);b.free(anc)
        b.x(km.array(top));b.pop_condition();b.free(km.array([m]))
    b.free(km.array([f2,f4,f8,f16]))
''' + source[stop:]
    # Same virtual-bit register layout as round5_virtual.install. Its row
    # implementation remains installed; transform the pristine build source.
    replacements={
      'Lr = b.alloc_qubits(LB);':'Lr = b.alloc_qubits(LB-1);',
      'packed = [int(lay.u[a]) | (int(lay.H[a]) << LB) | (int(tables[a, 1]) << (LB + nH)) | (int(tables[a, 2]) << (LB + nH + nT))':'packed = [int(lay.u[a] >> 1) | (int(lay.H[a]) << (LB-1)) | (int(tables[a, 1]) << (LB-1 + nH)) | (int(tables[a, 2]) << (LB-1 + nH + nT))',
      'RL = list(Lr[prm.G0:]) + list(ext)':'RL = list(Lr[prm.G0-1:]) + list(ext)',
      'utab = [int(lay.u[a]) | (int(tables[a, 1]) << LB) | (int(tables[a, 2]) << (LB + nT))':'utab = [int(lay.u[a] >> 1) | (int(tables[a, 1]) << (LB-1)) | (int(tables[a, 2]) << (LB-1 + nT))',
    }
    for old,new in replacements.items():assert source.count(old)==1;source=source.replace(old,new)
    if derivative:
        source=source.replace('Tr = b.alloc_qubits(nT);','Tr = b.alloc_qubits(nT-1);')
        source=source.replace('int(tables[a, 1])','int(tables[a, 1] >> 1)')
        source=source.replace('<< (LB-1 + nH + nT)','<< (LB-1 + nH + nT-1)')
        source=source.replace('<< (LB-1 + nT)','<< (LB-1 + nT-1)')
        source=source.replace('win_step(bb, x, prm, Tr, Lr,','win_step(bb, x, prm, [None]+list(Tr), Lr,')
        for direction in ['True','False']:
            old=f'Bd.sd_step(bb, x, prm.rowsA, C2r, Tr, prm.eA, WA, gA, {direction}, False)'
            assert source.count(old)==1,old
            source=source.replace(old,f'virtual_inner(bb, x, prm, C2r, Tr, WA, gA, {direction})')
        from round10_virtual import inner,install_outer
        H.virtual_inner=inner;install_outer(H)
    if generalized:
        from round10_virtual import generalized_outer
        H.win_step=generalized_outer
    if retire or initial_lookup or bend:
        from round10_lookup import patch_source
        source=patch_source(source,H,retire=retire,last=last,initial=initial_lookup,bend=bend)
    exec(compile(source,'<own-normalization-ladder>','exec'),H.__dict__)

def setup(competition):
    sys.path[:0]=[str(BASE),str(BASE/'marsyas'),str(competition/'kickmix'),str(competition/'verifiers')]

def build_model(work,*,fit_file=None,drop=1,recipe=None):
    import numpy as np,model as M,fit as F,run,hsplit as H,build as B
    work=Path(work);work.mkdir(exist_ok=True,parents=True);M.CACHE=str(work/'reference.npz')
    recipe=recipe or {};params=recipe.get('params',[28,19,8,1]);dropA=recipe.get('dropA',[5])
    prm,_=run.parse([*map(str,params),'sd=1','dropA='+','.join(map(str,dropA))])
    if recipe.get('bend'):
        if not hasattr(M,'_own_eval_before_bend'):M._own_eval_before_bend=M.eval_T
        high=prm.F2-2
        M.eval_T=lambda C1,C2,b,p:M._own_eval_before_bend(C1,C2+((b>>14&1)^1)*(C2>>high&1),b,p)
    tables=np.array(recipe.get('tables') or json.loads((BASE/'round5_marsyas_tables.json').read_text()),dtype=np.int64)
    tables[:,0]+=tables[:,0]&1
    lay=H.layout(tables,prm,recipe.get('LB',21),recipe.get('S',20))
    assert lay is not None,'no high/low layout'
    if fit_file:
        fit=json.loads(Path(fit_file).read_text());angs=fit['angles']
        worst,margin,*_=H.check_multi(tables,prm,lay,angs)
    else:
        angs,worst,margin,nrot=H.calibrate_multi(tables,prm,lay,drop=drop,verbose=True)
    assert worst<1 and margin>0,(worst,margin)
    fit=dict(angles=angs,worst=worst,margin=margin,drop=drop,params=params,derivative=recipe.get('derivative',False),generalized=recipe.get('delta_bits',14)!=14,bend=recipe.get('bend',False),tables_sha256=__import__('hashlib').sha256(tables.tobytes()).hexdigest())
    (work/'phase_fit.json').write_text(json.dumps(fit,indent=1))
    F._D=F.domains() if F._D is None else F._D
    a,p,xn,bounds=F._D;W=M.window_ranges1(tables,prm,xn,p)
    M.PHASE_FN=lambda xs:H.phases_multi(H.regs(tables,prm,lay,xs),angs)
    return tables,prm,lay,angs,fit,W

def build_variant(out,model,*,plan,ladder=True,exact_reads=True,prefix=0,retire=0,last=False,initial_lookup=False):
    import build as B,hsplit as H,round5_virtual as V,check as C
    tables,prm,lay,angs,fit,W=model
    if not hasattr(H,'_own_original'):H._own_original=H.build_hsplit
    H.build_hsplit=H._own_original;V.install(H)
    if ladder:install_ladder(H,derivative=fit.get('derivative',False),retire=retire,last=last,initial_lookup=initial_lookup,generalized=fit.get('generalized',False),bend=fit.get('bend',False))
    if not hasattr(B,'_own_phase_original'):B._own_phase_original=B.fused_phase
    B.fused_phase=B._own_phase_original
    if exact_reads:
        from round9_marsyas_phase import fused_phase
        B.fused_phase=lambda *args:fused_phase(*args,low_fuse=True,clifford=True,s_gadget=True)
    if not hasattr(B.B,'_own_add_original'):B.B._own_add_original=B.B.add
    B.B.add=B.B._own_add_original
    if prefix:
        def add(self,src,tgt,subtract=False,stream=False,cin=None,cout=None):
            import kickmix as km
            needed=max(0,self.b.num_allocated_qubits+max(0,len(tgt)-2)+int(cout is not None)-abs(prefix))
            k=min(prefix if prefix>0 else needed+int(needed>0 and cin is None),len(tgt)-2)
            legal=(len(set(src[:k]))==k and not set(src[:k]).intersection(list(src[k:])+[cin]+list(tgt)))
            if k>0 and legal and cout is None and all(isinstance(q,km.q) for q in src[:k]) and len(src)>=k:
                # In-place MAJ prefix restores sources exactly. The recursive
                # tail uses the original adder, avoiding repeated prefixes.
                if subtract:self.b.x(km.array(tgt))
                orig=self.add;self.add=lambda *a,**kw:B.B._own_add_original(self,*a,**kw)
                self.add_ip(src,tgt,cin,k);self.add=orig
                if subtract:self.b.x(km.array(tgt))
            else:B.B._own_add_original(self,src,tgt,subtract,stream,cin,cout)
        B.B.add=add
    o=B.Opts(WA=W['A'],gA=1);o.mdel=True;o.wins=H.parse_plan(plan);o.wcb=H.choose_cbits(tables,prm,lay,o.wins);o.kbig=0;o.qcap=None
    assert o.wcb is not None,plan
    out=Path(out);out.mkdir(exist_ok=True,parents=True)
    c=H.build_hsplit(tables,prm,o,lay,angs)
    rep=C.report(c,tables,prm,{'pass':True,'min_margin':fit['margin']},nbatch=4)
    rep.update(plan=plan,cbits=o.wcb,ladder=ladder,exact_reads=exact_reads,prefix=prefix,retire=retire,last=last,initial_lookup=initial_lookup,peak=B.LAST_PEAK)
    (out/'raw.kmx').write_text(str(c));(out/'build.json').write_text(json.dumps(rep,indent=1))
    return c,rep

def optimize(out):
    import domain_compile as D,round6_hmr as H,kickmix as km
    out=Path(out)
    r=D.compile(out/'raw.kmx',out/'domain.kmx',max_x=3133452,linear=True)
    (out/'domain_proof.json').write_text(json.dumps(r,indent=1))
    r=H.compile(out/'domain.kmx',out/'hmr.kmx')
    (out/'hmr_proof.json').write_text(json.dumps(r,indent=1))
    c=km.Circuit.from_file(str(out/'hmr.kmx'),format='kmx');path=out/'invsqrt.kmb';c.to_file(str(path),format='kmb')
    return path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--fit',type=Path);ap.add_argument('--drop',type=int,default=1);ap.add_argument('--plan');ap.add_argument('--prefix',type=int,default=0);ap.add_argument('--verify',action='store_true');ap.add_argument('--no-ladder',action='store_true');a=ap.parse_args()
    import round10_verify as D
    setup(D.COMP);D.start_audit();D.progress('calibrate')
    model=build_model(D.OUT/'model',fit_file=a.fit,drop=a.drop)
    plans=[a.plan] if a.plan else ['17:11,10;15:9,8;13:7,6;11:5,4;9:3,2;7:1,0','17:11,10,9,8,7,6,5,4,3,2,1,0','16:10,9,8,7,6,5,4,3,2,1,0','15:9,8,7,6,5,4,3,2,1,0','17:11,10,9,8;13:7,6,5,4;9:3,2,1,0']
    rows=[]
    for i,plan in enumerate(plans):
        name=f'INV-FUSED-OWN-{i}-P{a.prefix}';folder=D.OUT/name;D.progress('build',candidate=name,plan=plan)
        try:
            c,row=build_variant(folder,model,plan=plan,ladder=not a.no_ladder,prefix=a.prefix);del c;gc.collect()
            D.progress('optimize',candidate=name,raw=row)
            p=optimize(folder)
            import kickmix as km,check as C
            c=km.Circuit.from_file(str(p),format='kmb');sample=C.report(c,model[0],model[1],{'pass':True,'min_margin':model[4]['margin']},nbatch=4)
            row.update(name=name,optimized=sample,sha256=D.sha(p));del c;gc.collect()
            if a.verify:row['official']=D.measure('invsqrt',p,name)
        except Exception as exc:row=dict(name=name,plan=plan,error=repr(exc));D.progress('variant_error',**row)
        rows.append(row);D.record('sweep.json',rows)
        D.progress('variant_done',**row)
    D.finish_audit();D.progress('done')
if __name__=='__main__':main()
