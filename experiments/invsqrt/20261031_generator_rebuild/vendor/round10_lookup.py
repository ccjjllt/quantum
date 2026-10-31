# SPDX-License-Identifier: Apache-2.0
"""Pruned unary table with direct output-mask leaves and early curvature erasure.

Adaptive lookup: our round3 implementation; direct leaves and lifetime
schedule reconstructed from algebra. Original QROM/MBU lineage retained.
"""
import kickmix as km

def lookup(b,address,target,table,*,last=False):
    address=list(address);target=list(target);stats={'ands':0,'leaves':0}
    def xor_word(value,control):
        for i,q in enumerate(target):
            if value>>i&1:
                if control is None:b.x(q)
                else:b.cx(control,q)
    def product_mask(parent,bit,value):
        selected=[q for i,q in enumerate(target) if value>>i&1]
        if not selected:return
        pivot=selected[-1] if last else selected[0]
        others=[q for q in selected if q!=pivot]
        for q in others:b.cx(pivot,q)
        b.ccx(parent,bit,pivot)
        for q in reversed(others):b.cx(pivot,q)
        stats['leaves']+=1
    def walk(bits,rows,parent):
        if len(set(rows))==1:xor_word(rows[0],parent);return
        assert bits
        if len(bits)==1:
            xor_word(rows[0],parent)
            if parent is None:xor_word(rows[0]^rows[1],bits[0])
            else:product_mask(parent,bits[0],rows[0]^rows[1])
            return
        bit=bits[-1];half=len(rows)//2
        if parent is None:
            b.x(bit);walk(bits[:-1],rows[:half],bit);b.x(bit);walk(bits[:-1],rows[half:],bit)
        else:
            t=b.alloc_qubits(1)[0];b.x(bit);b.init_and(parent,bit,t);b.x(bit);stats['ands']+=1
            walk(bits[:-1],rows[:half],t);b.cx(parent,t);walk(bits[:-1],rows[half:],t);b.cx(parent,t)
            b.x(bit);b.del_and(parent,bit,t);b.x(bit);b.free(km.array([t]))
    walk(address,list(map(int,table)),None)
    return stats

def bend_curvature(b,x,curvature,*,inverse=False):
    """One-unit curvature change in the lower half of the delta window.

Fitted bases exclude a low-word wrap, so the two high curvature bits are
unchanged. This also preserves the fitted zero derivative parity.
"""
    flag=b.alloc_qubits(1)[0];b.x(x[14]);b.init_and(curvature[-1],x[14],flag);b.x(x[14])
    method=b.isub if inverse else b.iadd
    method(1,target=curvature[:-2],control=flag)
    b.x(x[14]);b.del_and(curvature[-1],x[14],flag);b.x(x[14]);b.free(km.array([flag]))

def patch_source(source,H,*,retire=0,last=False,initial=False,bend=False):
    H.own_lookup=lambda b,address,target,table:lookup(b,address,target,table,last=last)
    if initial:
        anchor='    b.init_lookup(table=packed, address=address, target=target)'
        assert source.count(anchor)==1;source=source.replace(anchor,'    own_lookup(b,address,target,packed)')
    if retire:
        anchor="    bb.label = 'B'"
        insert=f'''    curvature_keep=n2-{retire}
    curvature_table=[int(tables[a,2])>>curvature_keep for a in range(len(tables))]
    curvature_mask=measure(b,C2r[curvature_keep:])
    curvature_low=list(C2r[:curvature_keep]);b.free(C2r[curvature_keep:])
'''
        assert source.count(anchor)==1;source=source.replace(anchor,insert+anchor)
        # Restore the pure table word only after both outer arithmetic passes.
        anchor="    Bd.sd_step(bb, x, prm.rowsA, C2r, Tr, prm.eA, WA, gA, False, False)"
        if anchor not in source:anchor='    virtual_inner(bb, x, prm, C2r, Tr, WA, gA, False)'
        assert source.count(anchor)==1
        source=source.replace(anchor,f'''    curvature_high=b.alloc_qubits({retire})
    own_lookup(b,address,curvature_high,curvature_table)
    C2r=km.array(curvature_low+list(curvature_high))
'''+anchor)
        old='mdel(b, address, [(mH, Htab), (mR, utab)])'
        assert source.count(old)==1;source=source.replace(old,'mdel(b, address, [(mH, Htab), (mR, utab), (curvature_mask, curvature_table)])')
    if bend:
        H.bend_curvature=bend_curvature
        for direction in ['True','False']:
            anchor=f'    virtual_inner(bb, x, prm, C2r, Tr, WA, gA, {direction})'
            assert source.count(anchor)==1
            source=source.replace(anchor,'    bend_curvature(b,x,C2r)\n'+anchor+'\n    bend_curvature(b,x,C2r,inverse=True)')
    return source
