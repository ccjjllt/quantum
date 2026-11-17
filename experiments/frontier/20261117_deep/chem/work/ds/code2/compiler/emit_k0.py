# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""ANGLE_0 emitter retaining the proven eight-live-low-cache schedule."""
import argparse,json
from pathlib import Path
import numpy as np
from emit_plan import mobius
from extract_matching import matching,bitinds
from transport_cuts import coordinate_basis,coordinates
from gauge_plan_fit import cross_tensor
from helper_coordinates import separate as separate_helpers
from parity_recover import outer,basis
from padding_completion import apply_padding_completion
BASE=Path(__file__).resolve().parent

def emit(s,words,out):
    words=apply_padding_completion(s,words)
    assert s['k']==0 and 'windows' in s
    if 'explicit_products' in s:
        spec=s['explicit_products'];D=[]
        for p in spec:
            D.append(outer(p['l1'],p['out']))
            if p['l2']:D.append(outer(p['l2'],p['out']))
        assert len(basis(D))==len(D),'Explicit product columns are dependent'
        cert=s['explicit_certificate']
    else:
        pairs,cert=matching(s)
        spec=[{'l1':p[2],'l2':p[3],'out':p[4]} for p in pairs]
        D=[x for p in pairs for x in p[:2]]
    co=coordinate_basis(D)
    T=cross_tensor(words,0);hs=[0]*len(D)
    for h in range(1,77):
        for i in bitinds(coordinates(T[h],co)):hs[i]|=1<<h
    ps=[];position=0
    for p in spec:
        h2=hs[position];position+=1
        h1=hs[position] if p['l2'] else 0
        if p['l2']:position+=1
        if h1 or h2:ps.append(dict(p,h1=h1,h2=h2))
    for p in ps:
        p['window']=next(i for i,w in enumerate(s['windows']) if ((p['l1']|p['l2'])&~w)==0)
    addr=np.arange(1232);low=addr%16;high=addr//16;cur=words[:,:5]
    corr=np.zeros(1232,dtype=np.uint64)
    for j in range(5):corr|=(cur[:,j].astype(np.uint64)&127)<<(7*j)
    for p in ps:
        a=np.zeros(1232,dtype=np.uint8);b=a.copy()
        for i in bitinds(p['l1']):a^=((low&(i+1))==i+1)
        for i in bitinds(p['l2']):b^=((low&(i+1))==i+1)
        for i in bitinds(p['h1']):a^=((high&i)==i)
        for i in bitinds(p['h2']):b^=((high&i)==i)
        corr^=(a&b).astype(np.uint64)*np.uint64(p['out'])
    c=corr.reshape(77,16);ch=c[:,0];cl=c[0]^c[0,0]
    assert np.array_equal(c,ch[:,None]^cl[None,:])
    ah=mobius(ch);al=mobius(cl)
    helper,high_helper=separate_helpers(((cur>>7)^(cur>>6))&1);hm=mobius(helper)
    def targets(mask):return [11+8*(i//7)+i%7 for i in bitinds(mask)]
    lines=[]
    for q in range(11):lines.append(f'APPEND_TO_REGISTER q{q} r0')
    lines.append('REGISTER r0 "selection"')
    for j in range(5):
        for b in range(8):lines.append(f'APPEND_TO_REGISTER q{11+8*j+b} r{j+1}')
        lines.append(f'REGISTER r{j+1} "word_{j}"')
    for j in range(5):lines.append(f'CX q{17+8*j} q{18+8*j}')
    hi={1<<b:4+b for b in range(7)};lo={1<<b:b for b in range(4)};nextq=51;hcomp=[]
    for h in range(1,77):
        if h in hi:continue
        bit=1<<(h.bit_length()-1);x,y,z=hi[h^bit],hi[bit],nextq;hi[h]=z;nextq+=1
        lines += [f'R q{z}',f'CCX q{x} q{y} q{z}'];hcomp.append((x,y,z))
    assert nextq==120
    for z in targets(int(ah[0])):lines.append(f'X q{z}')
    for j in range(5):
        if hm[0,j]:lines.append(f'X q{18+8*j}')
    for h in range(1,77):
        for z in targets(int(ah[h])):lines.append(f'CX q{hi[h]} q{z}')
    for h in range(1,len(high_helper)):
        for j in range(5):
            if high_helper[h,j]:lines.append(f'CX q{hi[h]} q{18+8*j}')
    def low_correction(m):
        for z in targets(int(al[m])):lines.append(f'CX q{lo[m]} q{z}')
        for j in range(5):
            if hm[m,j]:lines.append(f'CX q{lo[m]} q{18+8*j}')
    for m in [1,2,4,8]:low_correction(m)
    def physical(l,h):
        a=0
        for i in bitinds(l):a^=1<<lo[i+1]
        for i in bitinds(h):a^=1<<hi[i]
        return a
    def product(p):
        a=physical(p['l1'],p['h1']);b=physical(p['l2'],p['h2']);ap=(a&-a).bit_length()-1
        ops1=[f'CX q{i} q{ap}' for i in bitinds(a^(1<<ap))]
        if (b>>ap)&1:b^=a^(1<<ap)
        rest=b&~(1<<ap);bp=(rest&-rest).bit_length()-1;assert bp>=0
        ops2=[f'CX q{i} q{bp}' for i in bitinds(b^(1<<bp))]
        zz=targets(p['out']);z=zz[0];fan=[f'CX q{z} q{i}' for i in zz[1:]]
        lines.extend(ops1+ops2+fan+[f'CCX q{ap} q{bp} q{z}']+list(reversed(fan))+list(reversed(ops2))+list(reversed(ops1)))
    emitted=set();events=json.loads((BASE/'k0_windows.json').read_text())
    for e in events:
        m,q=e['m'],e['qubit']
        if e['action']=='compute':
            x,y=e['controls'];lines.extend([f'R q{q}',f'CCX q{x} q{y} q{q}']);lo[m]=q;low_correction(m)
            active=sum(1<<(mm-1) for mm in lo)
            for wi,win in enumerate(s['windows']):
                if wi not in emitted and (win&~active)==0:
                    for p in ps:
                        if p['window']==wi:product(p)
                    emitted.add(wi)
        else:
            x,y=e['phase_controls'];lines.extend([f'HMR q{q} b0',f'CZ q{x} q{y} if b0']);lo.pop(m)
    assert len(emitted)==len(s['windows'])
    for x,y,z in reversed(hcomp):lines.extend([f'HMR q{z} b0',f'CZ q{x} q{y} if b0'])
    for j in range(5):lines.append(f'CX q{17+8*j} q{18+8*j}')
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text('\n'.join(lines)+'\n')
    report={'k':0,'product_count':len(ps),'high_cache':69,'low_computes':11,'toffoli_count':len(ps)+80,'num_qubits':128,'low_cache_peak':8,'matching_certificate':cert,'instructions':len(lines)}
    out.with_suffix('.plan.json').write_text(json.dumps({'report':report,'products':ps},indent=2)+'\n');return report

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('state',type=Path);ap.add_argument('--words',type=Path,default=BASE/'commuting/completed_words.npy');ap.add_argument('--output',type=Path,default=BASE/'commuting/circuits/angle_k_0.kmx');args=ap.parse_args()
    print(json.dumps(emit(json.loads(args.state.read_text()),np.load(args.words),args.output)),flush=True)
