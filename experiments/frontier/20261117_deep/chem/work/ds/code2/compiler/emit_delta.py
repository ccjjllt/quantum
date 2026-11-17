# Copyright 2026 Syed Asad Ali (base emitter, Apache-2.0) + frontier delta-helper fork.
"""*** INVALID CIRCUITS — DO NOT USE FOR BUILDS (see RESULT5.md). ***

This fork emits `CX q{z} q{z}` (control == target) for every nonzero X word:
each X low part is a single degree-2 monomial whose representation mask is the
singleton {own b7 qubit} (measured in delta_cost.py §2/3). kickmix rejects
control==target, and no valid replacement exists at zero cost: the needed
monomial is held by no correct-valued qubit (cache lacks it, hi-cache is
high-only), a fresh AND costs +1T per word, reset breaks reversibility, and a
spare-copy leaves the workspace dirty. Correct emission needs prefix+post
addr-only ANDs (delta_cost.py §5): k9 +2T, k10 +3T, k12 +4T, k14 +4T — all
losses. Kept only as a record of the failed CX-only attempt.

Base logic is byte-for-byte emit_plan.emit except for the helper handling:

* the low/high caches are synthesized from the batch-0 helper table S0 (exactly
  as the base emitter), so cache Toffoli counts are unchanged (69 high + 6 low);
* the loader's own prev/cur helper tables (Hp, Hc) may differ from S0.  Two
  CNOT-only adjustments bridge the gap (zero new ANDs, zero new qubits):
      X_pre  = Hp ^ slow   applied right after the high-cache computation,
      X_post = slow ^ Hc   applied right after the last product,
  where slow[t] is the live low-helper value.  For standard loaders
  (Hp == Hc == S0) X_pre/X_post reduce to the base emitter's high_helper_ops
  (same multiset of CXs), up to ordering.
* the base emitter's prev/cur-vs-batch-0 assertions are replaced by
  separability checks (inside separate_helpers) on Hp and Hc.

Why this is correct: after the entry CX q{17+8j}->q{18+8j} the b7 qubit holds
Hp(a).  X_pre maps it to slow[t], the value the synthesized low cache assumes.
Products and the ah/al polarisation correction only touch b0..b6 targets and
read live cache/helper qubits, so they are unaffected.  X_post maps b7 to
Hc(a); the exit CX then restores bit7(cur) exactly.  The base emitter is the
special case Hp == Hc == S0 with X split into apply/uncompute of the same CXs.
"""
import argparse,json,sys
from pathlib import Path
import numpy as np
from parity_recover import outer,NOUT,basis
from transport_cuts import coordinate_basis,coordinates
from gauge_plan_fit import cross_tensor
from extract_matching import matching,bitinds
from low_helper_cache import synthesize as synthesize_low_cache
from helper_coordinates import separate as separate_helpers
from padding_completion import apply_padding_completion
BASE=Path(__file__).resolve().parent

def mobius(a):
    a=a.copy()
    for b in range((len(a)-1).bit_length()):
        for m in range(len(a)):
            if m&(1<<b):a[m]^=a[m^(1<<b)]
    return a
import argparse,json,sys
from pathlib import Path
import numpy as np
from parity_recover import outer,NOUT,basis
from transport_cuts import coordinate_basis,coordinates
from gauge_plan_fit import cross_tensor
from extract_matching import matching,bitinds
from low_helper_cache import synthesize as synthesize_low_cache
from helper_coordinates import separate as separate_helpers
from padding_completion import apply_padding_completion
BASE=Path(__file__).resolve().parent

def mobius(a):
    a=a.copy()
    for b in range((len(a)-1).bit_length()):
        for m in range(len(a)):
            if m&(1<<b):a[m]^=a[m^(1<<b)]
    return a

def emit(s,words,out_path):
    if 'high_cache_plan' in s:
        # This branch verifies the complete cache algebra and correction;
        # the ordinary full-cache path remains byte-for-byte unchanged.
        from high_subspace_emitter import emit as emit_high_subspace
        return emit_high_subspace(s,words,s['high_cache_plan'],out_path)
    words=apply_padding_completion(s,words)
    k=s['k'];assert k>=1,'ANGLE_0 needs a separately scheduled low-cache window'
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
    target=cross_tensor(words,k);hs=[0]*len(D)
    for h in range(1,77):
        x=coordinates(target[h],co)
        for i in bitinds(x):hs[i]|=1<<h
    ps=[];position=0
    for p in spec:
        h2=hs[position];position+=1
        h1=hs[position] if p['l2'] else 0
        if p['l2']:position+=1
        if h1 or h2:ps.append(dict(p,h1=h1,h2=h2))
    helper_table=((words[:,:5]>>7)^(words[:,:5]>>6))&1
    helper,_=separate_helpers(helper_table)
    prev=words[:,5*k-5:5*k];cur=words[:,5*k:5*k+5]
    # Per-batch helpers (replaces the base emitter's prev/cur-vs-batch-0 asserts).
    # separate_helpers asserts each is a sum of a low-only and a high-only function.
    Hp=((prev>>7)^(prev>>6))&1
    Hc=((cur>>7)^(cur>>6))&1
    lowP,highP=separate_helpers(Hp)
    lowC,highC=separate_helpers(Hc)
    slow=helper  # live low-helper values (16x5); high_S0[0] == 0 by construction
    lines=[]
    for q in range(11):lines.append(f'APPEND_TO_REGISTER q{q} r0')
    lines.append('REGISTER r0 "selection"')
    for j in range(5):
        for b in range(8):lines.append(f'APPEND_TO_REGISTER q{11+8*j+b} r{j+1}')
        lines.append(f'REGISTER r{j+1} "word_{j}"')
    for j in range(5):lines.append(f'CX q{17+8*j} q{18+8*j}')
    hi={1<<b:4+b for b in range(7)};lo={1<<b:b for b in range(4)}
    pure_helpers=True
    for j in range(5):
        ms=[m for m in range(1,16) if np.array_equal(helper[:,j],((np.arange(16)&m)==m).astype(int))]
        if len(ms)!=1:pure_helpers=False
        else:lo[ms[0]]=18+8*j
    nextq=51;computes=[]
    for h in range(1,77):
        if h in hi:continue
        bit=1<<(h.bit_length()-1);x=hi[h^bit];y=hi[bit];z=nextq;nextq+=1;hi[h]=z
        lines += [f'R q{z}',f'CCX q{x} q{y} q{z}'];computes.append((x,y,z))
    if pure_helpers:
        for l in range(1,16):
            if l in lo:continue
            bit=1<<(l.bit_length()-1);x=lo[l^bit];y=lo[bit];z=nextq;nextq+=1;lo[l]=z
            lines += [f'R q{z}',f'CCX q{x} q{y} q{z}'];computes.append((x,y,z))
        low_representations={m:(1<<q,0) for m,q in lo.items()}
    else:
        low_computes,low_representations,nextq=synthesize_low_cache(helper,nextq)
        for x,y,z in low_computes:
            lines += [f'R q{z}',f'CCX q{x} q{y} q{z}'];computes.append((x,y,z))
    assert nextq<=128
    def apply_X(low16,high77):
        """XOR a separable (low,high) 5-bit function into the five b7 qubits.
        CX/X only.  Must run while the high/low caches are live."""
        nCX=0
        for j in range(5):
            z=18+8*j
            t=np.asarray(low16[:,j],dtype=np.uint8)
            if t.any():
                anf=mobius(t)
                if anf[0]:lines.append(f'X q{z}');nCX+=1
                for l in range(1,16):
                    if anf[l]:
                        mask,constant=low_representations[l]
                        if constant:lines.append(f'X q{z}');nCX+=1
                        for q in bitinds(mask):lines.append(f'CX q{q} q{z}');nCX+=1
            for h in range(1,77):
                if high77[h,j]:lines.append(f'CX q{hi[h]} q{z}');nCX+=1
        return nCX
    # X_pre: b7 holds Hp(a); map it to the live low-helper value slow[t].
    n_pre=apply_X(lowP^slow,highP)
    def fanout(mask):return [11+8*(i//7)+i%7 for i in bitinds(mask)]
    def physical(l,h):
        mask=0;constant=0
        for i in bitinds(l):
            low_mask,low_constant=low_representations[i+1];mask^=low_mask;constant^=low_constant
        for i in bitinds(h):mask^=1<<hi[i]
        return mask,constant
    for p in ps:
        a,ac=physical(p['l1'],p['h1']);b,bc=physical(p['l2'],p['h2'])
        ap=(a&-a).bit_length()-1
        ops1=[f'CX q{i} q{ap}' for i in bitinds(a^(1<<ap))]
        if ac:ops1.append(f'X q{ap}')
        # Express b in the temporary basis after a replaced its pivot.
        if (b>>ap)&1:b^=a^(1<<ap);bc^=ac
        bp=((b&~(1<<ap))&-(b&~(1<<ap))).bit_length()-1
        assert bp>=0
        ops2=[f'CX q{i} q{bp}' for i in bitinds(b^(1<<bp))]
        if bc:ops2.append(f'X q{bp}')
        outputs=fanout(p['out']);z=outputs[0]
        fan=[f'CX q{z} q{i}' for i in outputs[1:]]
        lines+=ops1+ops2+fan+[f'CCX q{ap} q{bp} q{z}']+list(reversed(fan))+list(reversed(ops2))+list(reversed(ops1))
    # X_post: b7 holds slow[t]; map it to Hc(a) so the exit CX restores bit7(cur).
    n_post=apply_X(slow^lowC,highC)
    # Reconstruct the polarisation correction independently on all1232rows.
    addr=np.arange(1232);low=addr%16;high=addr//16
    delta=prev^cur
    corr=np.zeros(1232,dtype=np.uint64)
    for j in range(5):corr|=(delta[:,j].astype(np.uint64)&127)<<(7*j)
    for p in ps:
        a=np.zeros(1232,dtype=np.uint8);b=a.copy()
        for i in bitinds(p['l1']):a^=((low&(i+1))==i+1)
        for i in bitinds(p['l2']):b^=((low&(i+1))==i+1)
        for i in bitinds(p['h1']):a^=((high&i)==i)
        for i in bitinds(p['h2']):b^=((high&i)==i)
        corr^=(a&b).astype(np.uint64)*np.uint64(p['out'])
    c=corr.reshape(77,16);ch=c[:,0];cl=c[0]^c[0,0]
    assert np.array_equal(c,ch[:,None]^cl[None,:]),'Product tensor mismatch'
    ah=mobius(ch);al=mobius(cl)
    for z in fanout(int(ah[0])):lines.append(f'X q{z}')
    for h in range(1,77):
        for z in fanout(int(ah[h])):lines.append(f'CX q{hi[h]} q{z}')
    for l in range(1,16):
        mask,constant=low_representations[l]
        for z in fanout(int(al[l])):
            if constant:lines.append(f'X q{z}')
            for q in bitinds(mask):lines.append(f'CX q{q} q{z}')
    for x,y,z in reversed(computes[69:]):lines += [f'HMR q{z} b0',f'CZ q{x} q{y} if b0']
    for x,y,z in reversed(computes[:69]):lines += [f'HMR q{z} b0',f'CZ q{x} q{y} if b0']
    for j in range(5):lines.append(f'CX q{17+8*j} q{18+8*j}')
    out_path.parent.mkdir(parents=True,exist_ok=True)
    out_path.write_text('\n'.join(lines)+'\n')
    report={'k':k,'product_count':len(ps),'high_cache':69,'low_computes':len(computes)-69,'toffoli_count':len(ps)+len(computes),'num_qubits':nextq,'instructions':len(lines),'matching_certificate':cert,'status':'Algebraic table check passed; simulator pending.',
            'delta_helper_entries':int(np.not_equal(Hp,Hc).sum()),
            'x_pre_cx':n_pre,'x_post_cx':n_post}
    out_path.with_suffix('.plan.json').write_text(json.dumps({'report':report,'products':ps},indent=2)+'\n')
    return report

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('state',type=Path);ap.add_argument('--words',type=Path,default=BASE/'all_helpers/completed_words.npy');ap.add_argument('--output',type=Path);args=ap.parse_args()
    s=json.loads(args.state.read_text());out=args.output or BASE/f'all_helpers/circuits/angle_k_{s["k"]}.kmx'
    print(json.dumps(emit(s,np.load(args.words),out)),flush=True)
