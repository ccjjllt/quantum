# SPDX-License-Identifier: Apache-2.0
"""Two virtual low bits, in separate Horner accumulators.

Zongao Bian/Gluzdov low-bit lineage; Phuc Thai derivative-parity refit idea.
The initial derivative parity is the XOR of all rounded row parities, so
the final derivative is even. No omitted quantum wire is reconstructed.
"""
import inspect,textwrap

def parity_indices(prm,width):
    parity=set()
    for i in prm.rowsA:
        e=prm.eA(i)+1
        if e<0:continue
        if e<width:parity.symmetric_difference_update({e})
        if 0<=e-1<width:parity.symmetric_difference_update({e-1})
    return sorted(parity)

def inner(bb,x,prm,op,acc,W,guard,fwd):
    import kickmix as km
    b=bb.b;assert len(guard)==1 and 0<W<len(acc)
    win=list(acc[:W])+list(guard);high=list(acc[W:]);top=acc[W-1];g=guard[0]
    active=set(parity_indices(prm,len(op)));prior={}
    for i in prm.rowsA:
        prior[i]=sorted(active);e=prm.eA(i)+1
        if e<0:continue
        if e<len(op):active.symmetric_difference_update({e})
        if 0<=e-1<len(op):active.symmetric_difference_update({e-1})
    assert not active
    def row(i):
        e=prm.eA(i)+1;src=[op[p+e+1] if 0<=p+e+1<len(op) else None for p in range(len(win))]
        B=op[e] if 0<=e<len(op) else None;C=op[e-1] if 0<=e-1<len(op) else None
        if all(q is None for q in src) and B is None and C is None:return
        ctl=x[i]
        if not fwd:b.x(ctl)
        for q in win:b.cx(ctl,q)
        if not fwd:b.x(ctl)
        carry=None
        if B is not None or C is not None:
            carry=b.alloc_qubits(1)[0];js=set(prior[i])
            if B is not None:js.symmetric_difference_update({e})
            def prepare():
                for k in sorted(js):b.cx(op[k],ctl)
                if B is not None and C is not None:b.cx(B,C)
            def unprepare():
                if B is not None and C is not None:b.cx(B,C)
                for k in reversed(sorted(js)):b.cx(op[k],ctl)
            prepare();b.init_and(ctl,C if C is not None else B,carry);unprepare()
            if B is not None:b.cx(B,carry)
        bb.add(src,win,cin=carry)
        if carry is not None:
            if B is not None:b.cx(B,carry)
            prepare();b.del_and(ctl,C if C is not None else B,carry);unprepare();b.free(km.array([carry]))
        if not fwd:b.x(ctl)
        for q in win:b.cx(ctl,q)
        if not fwd:b.x(ctl)
    if fwd:
        b.x(top);b.cx(top,g)
        for i in prm.rowsA:row(i)
        if high:bb.add([top],high);bb.add([g],high,subtract=True)
        b.x(top)
    else:
        b.x(top)
        if high:bb.add([g],high);bb.add([top],high,subtract=True)
        for i in reversed(prm.rowsA):row(i)
        b.cx(top,g);b.x(top)

def install_outer(H):
    """Extend the existing virtual output adder to an implicit zero Tr[0]."""
    s=textwrap.dedent(inspect.getsource(H.win_step))
    s=s.replace('for k in sorted(js):b.cx(op[k],ctl)','for k in sorted(js):\n    if op[k] is not None:b.cx(op[k],ctl)')
    s=s.replace('for k in reversed(sorted(js)):b.cx(op[k],ctl)','for k in reversed(sorted(js)):\n    if op[k] is not None:b.cx(op[k],ctl)')
    # Only e=0 sees a missing B; then C is also zero, so that carry is zero.
    # Use bool controls for it. CircuitBuilder removes all false products.
    s=s.replace('e=prm.eB(i)+1;bit=op[e];','e=prm.eB(i)+1;bit=op[e] if op[e] is not None else False;')
    exec(compile(s,'<own-virtual-outer-zero>','exec'),H.__dict__)

def generalized_outer(bb,x,prm,op,L,wins,cbits,fwd,store,kbig=0,qcap=None):
    """Virtual output for any nonnegative or left-shifted signed row."""
    import kickmix as km
    b=bb.b;assert kbig==0 and qcap is None
    winrows={i for _,rows in wins for i in rows};big=[i for i in prm.rowsB if i not in winrows]
    order=big+[i for _,rows in wins for i in rows];prior={};active=set()
    for i in order:
        prior[i]=sorted(active);e=prm.eB(i)+1
        if e<0:continue
        if e<len(op):active.symmetric_difference_update({e})
        if 0<=e-1<len(op):active.symmetric_difference_update({e-1})
    def row(i,win):
        e=prm.eB(i)+1;ctl=x[i]
        if not fwd:b.x(ctl)
        for q in win:b.cx(ctl,q)
        if not fwd:b.x(ctl)
        bit=op[e] if 0<=e<len(op) else None;previous=op[e-1] if 0<=e-1<len(op) else None;carry=None
        src=[op[p+e+1] if 0<=p+e+1<len(op) else None for p in range(len(win))]
        if bit is not None or previous is not None:
            carry=b.alloc_qubits(1)[0];js=set(prior[i]);
            if bit is not None:js.symmetric_difference_update({e})
            def prepare():
                for k in sorted(js):
                    if op[k] is not None:b.cx(op[k],ctl)
                if bit is not None and previous is not None:b.cx(bit,previous)
            def undo():
                if bit is not None and previous is not None:b.cx(bit,previous)
                for k in reversed(sorted(js)):
                    if op[k] is not None:b.cx(op[k],ctl)
            prepare();b.init_and(ctl,previous if previous is not None else bit,carry);undo()
            if bit is not None:b.cx(bit,carry)
        bb.add(src,win,cin=carry)
        if carry is not None:
            if bit is not None:b.cx(bit,carry)
            prepare();b.del_and(ctl,previous if previous is not None else bit,carry);undo();b.free(km.array([carry]))
        if not fwd:b.x(ctl)
        for q in win:b.cx(ctl,q)
        if not fwd:b.x(ctl)
    def fold(idx,subtract):
        k=wins[idx][0]-1;cq=store[idx]
        target=list(L[k:wins[idx-1][0]-1])+list(store[idx-1]) if idx else list(L[k:])
        source=list(cq)+[cq[-1]]*(len(target)-len(cq));bb.add(source[:len(target)],target,subtract=subtract)
    if fwd:
        for i in big:row(i,list(L))
        for j,(k,rows) in enumerate(wins):
            reg=list(b.alloc_qubits(cbits[j]));store.append(reg)
            for i in rows:row(i,list(L[:k-1])+reg)
        for j in reversed(range(len(wins))):fold(j,False)
    else:
        for j in range(len(wins)):fold(j,True)
        for j in reversed(range(len(wins))):
            k,rows=wins[j]
            for i in reversed(rows):row(i,list(L[:k-1])+store[j])
            b.free(km.array(store[j]))
        store.clear()
        for i in reversed(big):row(i,list(L))
