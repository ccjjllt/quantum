# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Isolated exact emitter using a synthesized high-address function space.

The target, every product factor, every helper normalization and the complete
polarization correction must lie in the supplied space. Missing corrections
are rejected; no implicit extra AND is hidden in the advertised cache count.
"""
import argparse,json
from pathlib import Path
import numpy as np
from parity_recover import basis,outer
from transport_cuts import coordinate_basis,coordinates
from extract_matching import matching,bitinds
from gauge_plan_fit import cross_tensor
from helper_coordinates import separate as separate_helpers
from low_helper_cache import synthesize as synthesize_low_cache
from padding_completion import apply_padding_completion
from emit_plan import mobius


def xor_values(mask,values):
    out=0
    for i in bitinds(mask):out^=values[i]
    return out


def form_truth(anf):
    return sum(sum(int((h&m)==m)for m in bitinds(anf))%2<<h for h in range(77))


def joint_controls(a,b):
    """Return a reversible CNOT preparation of two independent XOR forms."""
    assert a and b and a!=b
    pivot=(a&-a).bit_length()-1
    op1=[f'CX q{i} q{pivot}'for i in bitinds(a^(1<<pivot))]
    if b>>pivot&1:b^=a^(1<<pivot)
    avail=b&~(1<<pivot);second=(avail&-avail).bit_length()-1
    assert second>=0
    op2=[f'CX q{i} q{second}'for i in bitinds(b^(1<<second))]
    return pivot,second,op1+op2


def emit(state,words,cache,out_path):
    words=apply_padding_completion(state,words);k=state['k'];assert k>=1
    if 'explicit_products'in state:
        specs=state['explicit_products'];cert=state['explicit_certificate'];columns=[]
        for p in specs:
            columns.append(outer(p['l1'],p['out']))
            if p['l2']:columns.append(outer(p['l2'],p['out']))
    else:
        pairs,cert=matching(state);specs=[{'l1':p[2],'l2':p[3],'out':p[4]}for p in pairs]
        columns=[c for p in pairs for c in p[:2]]
    column_rank=len(basis(columns));target=cross_tensor(words,k)
    if 'explicit_high_coefficients'in state:
        # Dependent product columns are permitted only with literal checked
        # coefficients. This path is isolated from the ordinary matroid
        # emitter, which continues to require independent columns.
        high_coefficients=list(map(int,state['explicit_high_coefficients']))
        assert len(high_coefficients)==len(columns)
        assert all(0<=h<(1<<77)for h in high_coefficients)
        for h in range(1,77):
            reconstructed=0
            for c,f in zip(columns,high_coefficients):
                if f>>h&1:reconstructed^=c
            assert reconstructed==target[h],('Explicit dependent cross coefficients mismatch',h)
    else:
        assert column_rank==len(columns)
        co=coordinate_basis(columns);high_coefficients=[0]*len(columns)
        for h in range(1,77):
            for ci in bitinds(coordinates(target[h],co)):high_coefficients[ci]|=1<<h
    products=[];position=0
    for p in specs:
        h2=high_coefficients[position];position+=1
        h1=high_coefficients[position]if p['l2']else 0
        if p['l2']:position+=1
        if h1 or h2:products.append(dict(p,h1=h1,h2=h2))
    constant=(1<<77)-1
    functions=[sum(((h>>j)&1)<<h for h in range(77))for j in range(7)]
    high_qubits=list(range(4,11));nextq=51;high_operations=[]
    for operation in cache['operations']:
        left,right=operation['left_form'],operation['right_form']
        assert left<(1<<len(functions))and right<(1<<len(functions))
        truth=xor_values(left,functions)&xor_values(right,functions)
        assert truth==operation['truth']
        assert len(basis([constant,*functions,truth]))==len(functions)+2
        a=sum(1<<high_qubits[i]for i in bitinds(left));b=sum(1<<high_qubits[i]for i in bitinds(right))
        x,y,ops=joint_controls(a,b);high_operations.append((x,y,nextq,ops))
        high_qubits.append(nextq);functions.append(truth);nextq+=1
    assert len(high_operations)==cache['AND_count']
    high_co=coordinate_basis([constant,*functions])
    assert len(high_co)==cache['rank']
    def high_physical_truth(truth):
        try:coord=coordinates(int(truth),high_co)
        except ValueError:raise ValueError('Required high function lies outside the explicitly synthesized cache.')
        return sum(1<<high_qubits[i-1]for i in bitinds(coord)if i),coord&1
    def high_physical(anf):return high_physical_truth(form_truth(anf))
    helper_table=((words[:,:5]>>7)^(words[:,:5]>>6))&1
    helper,high_helper=separate_helpers(helper_table)
    prev=words[:,5*k-5:5*k];cur=words[:,5*k:5*k+5]
    for j in range(5):
        assert np.array_equal(((prev[:,j]>>7)^(prev[:,j]>>6))&1,helper_table[:,j])
        assert np.array_equal(((cur[:,j]>>7)^(cur[:,j]>>6))&1,helper_table[:,j])
    lines=[f'APPEND_TO_REGISTER q{q} r0'for q in range(11)]+['REGISTER r0 "selection"']
    for j in range(5):
        lines += [f'APPEND_TO_REGISTER q{11+8*j+b} r{j+1}'for b in range(8)]
        lines.append(f'REGISTER r{j+1} "word_{j}"')
    lines += [f'CX q{17+8*j} q{18+8*j}'for j in range(5)]
    for x,y,z,ops in high_operations:lines += ops+[f'R q{z}',f'CCX q{x} q{y} q{z}']+list(reversed(ops))
    high_helper_ops=[]
    for j in range(5):
        mask,offset=high_physical(sum(int(high_helper[h,j])<<h for h in range(len(high_helper))))
        if offset:high_helper_ops.append(f'X q{18+8*j}')
        high_helper_ops.extend(f'CX q{q} q{18+8*j}'for q in bitinds(mask))
    lines+=high_helper_ops
    low_computes,low_representations,nextq=synthesize_low_cache(helper,nextq)
    for x,y,z in low_computes:lines += [f'R q{z}',f'CCX q{x} q{y} q{z}']
    assert nextq<=128
    def fanout(mask):return [11+8*(i//7)+i%7 for i in bitinds(mask)]
    def physical(low,high):
        mask,offset=high_physical(high)
        for i in bitinds(low):
            m,c=low_representations[i+1];mask^=m;offset^=c
        return mask,offset
    for p in products:
        a,ac=physical(p['l1'],p['h1']);b,bc=physical(p['l2'],p['h2'])
        ap=(a&-a).bit_length()-1
        op1=[f'CX q{i} q{ap}'for i in bitinds(a^(1<<ap))]
        if ac:op1.append(f'X q{ap}')
        if b>>ap&1:b^=a^(1<<ap);bc^=ac
        avail=b&~(1<<ap);bp=(avail&-avail).bit_length()-1;assert bp>=0
        op2=[f'CX q{i} q{bp}'for i in bitinds(b^(1<<bp))]
        if bc:op2.append(f'X q{bp}')
        outputs=fanout(p['out']);z=outputs[0];fan=[f'CX q{z} q{i}'for i in outputs[1:]]
        lines += op1+op2+fan+[f'CCX q{ap} q{bp} q{z}']+list(reversed(fan))+list(reversed(op2))+list(reversed(op1))
    address=np.arange(1232);low=address%16;high=address//16;delta=prev^cur
    corr=sum((delta[:,j].astype(np.uint64)&127)<<(7*j)for j in range(5))
    for p in products:
        a=np.zeros(1232,dtype=np.uint8);b=a.copy()
        for i in bitinds(p['l1']):a^=((low&(i+1))==i+1)
        for i in bitinds(p['l2']):b^=((low&(i+1))==i+1)
        for i in bitinds(p['h1']):a^=((high&i)==i)
        for i in bitinds(p['h2']):b^=((high&i)==i)
        corr^=(a&b).astype(np.uint64)*np.uint64(p['out'])
    c=corr.reshape(77,16);ch=c[:,0];cl=c[0]^c[0,0]
    assert np.array_equal(c,ch[:,None]^cl[None,:]),'Cross product mismatch'
    obstruction=[]
    for bit in range(35):
        truth=sum(int((ch[h]>>np.uint64(bit))&np.uint64(1))<<h for h in range(77))
        try:mask,offset=high_physical_truth(truth)
        except ValueError:obstruction.append(bit);continue
        z=11+8*(bit//7)+bit%7
        if offset:lines.append(f'X q{z}')
        lines.extend(f'CX q{q} q{z}'for q in bitinds(mask))
    if obstruction:
        raise ValueError('Combined pure-high polarization correction lies outside H at payload bits '+str(obstruction))
    al=mobius(cl)
    for lowmon in range(1,16):
        mask,offset=low_representations[lowmon]
        for z in fanout(int(al[lowmon])):
            if offset:lines.append(f'X q{z}')
            lines.extend(f'CX q{q} q{z}'for q in bitinds(mask))
    for x,y,z in reversed(low_computes):lines += [f'HMR q{z} b0',f'CZ q{x} q{y} if b0']
    lines+=list(reversed(high_helper_ops))
    for x,y,z,ops in reversed(high_operations):lines += ops+[f'HMR q{z} b0',f'CZ q{x} q{y} if b0']+list(reversed(ops))
    lines += [f'CX q{17+8*j} q{18+8*j}'for j in range(5)]
    report={'k':k,'product_count':len(products),'high_cache':len(high_operations),'low_computes':len(low_computes),
        'toffoli_count':len(products)+len(high_operations)+len(low_computes),'num_qubits':nextq,
        'instructions':len(lines),'all_high_functions_and_combined_correction_in_cache':True,
        'cache_rank':len(high_co),'product_columns':len(columns),'product_column_rank':column_rank,
        'literal_cross_coefficients_verified':True,'matching_certificate':cert,'status':'Exact algebraic check; endpoint simulation pending.'}
    out_path.parent.mkdir(parents=True,exist_ok=True);out_path.write_text('\n'.join(lines)+'\n')
    out_path.with_suffix('.plan.json').write_text(json.dumps({'report':report,'products':products},indent=2)+'\n')
    return report


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('state',type=Path);ap.add_argument('--words',type=Path,required=True)
    ap.add_argument('--cache',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();print(json.dumps(emit(json.loads(args.state.read_text()),np.load(args.words),json.loads(args.cache.read_text()),args.output)),flush=True)
