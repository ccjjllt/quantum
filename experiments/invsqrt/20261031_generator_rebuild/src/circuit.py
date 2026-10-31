# SPDX-License-Identifier: Apache-2.0
"""Explicit invsqrt circuit for the Marsyas signed-digit quadratic.

This is the readable form of the Dmitrii dataset v39 `marsyas` builder plus the
`round10` parity ladder, virtual low bit, and derivative-row cleanup. The
upstream notebooks built the same function by rewriting their own source at
runtime. Those rewrites are not used here: every allocation, window, clear,
and phase correction below is an ordinary function of the parameters and the
integer tables.

The construction does not load a KMB, a compressed payload, or an instruction
listing, and it does not call the official verifier.

Integer and phase conventions live in `model.py` and are restated by the
generation entry.
"""
from fractions import Fraction

import kickmix as km

import build as Bd
from hsplit import mdel, measure


def unary_lookup(b, address, target, table, *, last=False):
    """Direct-leaf unary table load. `last` picks the pivot bit of each leaf."""
    address = list(address)
    target = list(target)

    def xor_word(value, control):
        for i, q in enumerate(target):
            if value >> i & 1:
                if control is None:
                    b.x(q)
                else:
                    b.cx(control, q)

    def product_mask(parent, bit, value):
        selected = [q for i, q in enumerate(target) if value >> i & 1]
        if not selected:
            return
        pivot = selected[-1] if last else selected[0]
        others = [q for q in selected if q != pivot]
        for q in others:
            b.cx(pivot, q)
        b.ccx(parent, bit, pivot)
        for q in reversed(others):
            b.cx(pivot, q)

    def walk(bits, rows, parent):
        if len(set(rows)) == 1:
            xor_word(rows[0], parent)
            return
        if len(bits) == 1:
            xor_word(rows[0], parent)
            if parent is None:
                xor_word(rows[0] ^ rows[1], bits[0])
            else:
                product_mask(parent, bits[0], rows[0] ^ rows[1])
            return
        bit = bits[-1]
        half = len(rows) // 2
        if parent is None:
            b.x(bit)
            walk(bits[:-1], rows[:half], bit)
            b.x(bit)
            walk(bits[:-1], rows[half:], bit)
        else:
            temp = b.alloc_qubits(1)[0]
            b.x(bit)
            b.init_and(parent, bit, temp)
            b.x(bit)
            walk(bits[:-1], rows[:half], temp)
            b.cx(parent, temp)
            walk(bits[:-1], rows[half:], temp)
            b.cx(parent, temp)
            b.x(bit)
            b.del_and(parent, bit, temp)
            b.x(bit)
            b.free(km.array([temp]))

    walk(address, [int(v) for v in table], None)

def parity_indices(prm,width):
    parity=set()
    for i in prm.rowsA:
        e=prm.eA(i)+1
        if e<0:continue
        if e<width:parity.symmetric_difference_update({e})
        if 0<=e-1<width:parity.symmetric_difference_update({e-1})
    return sorted(parity)

def virtual_inner(bb,x,prm,op,acc,W,guard,fwd):
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



def win_step(bb,x,prm,op,L,wins,cbits,fwd,store,kbig=0,qcap=None):
 assert prm.rowsB==tuple(range(14)) and [prm.eB(i)+1 for i in prm.rowsB]==list(range(13,-1,-1))
 assert kbig==0 and qcap is None
 b=bb.b
 winrows={i for _,rows in wins for i in rows};big=[i for i in prm.rowsB if i not in winrows]
 order=big+[i for _,rows in wins for i in rows]
 parities={};active=set()
 for i in order:
  parities[i]=sorted(active)
  e=prm.eB(i)+1
  active.symmetric_difference_update({e})
  if e:active.symmetric_difference_update({e-1})
 def row(i,win):
  e=prm.eB(i)+1;bit=op[e] if op[e] is not None else False;prior=op[e-1] if e else None;ctl=x[i]
  if not fwd:b.x(ctl)
  for q in win:b.cx(ctl,q)
  if not fwd:b.x(ctl)
  carry=b.alloc_qubits(1)[0]
  # J = P XOR control XOR B; D = C XOR B.
  js=set(parities[i]);js.symmetric_difference_update({e})
  for k in sorted(js):
    if op[k] is not None:b.cx(op[k],ctl)
  if prior is not None:b.cx(bit,prior);d=prior
  else:d=bit
  b.init_and(ctl,d,carry)
  if prior is not None:b.cx(bit,prior)
  for k in reversed(sorted(js)):
    if op[k] is not None:b.cx(op[k],ctl)
  b.cx(bit,carry)
  srcs=[op[p+e+1] if p+e+1<len(op) else None for p in range(len(win))]
  assert len(op)-e-1<=len(win)
  bb.add(srcs,win,cin=carry)
  b.cx(bit,carry)
  for k in sorted(js):
    if op[k] is not None:b.cx(op[k],ctl)
  if prior is not None:b.cx(bit,prior)
  b.del_and(ctl,d,carry)
  if prior is not None:b.cx(bit,prior)
  for k in reversed(sorted(js)):
    if op[k] is not None:b.cx(op[k],ctl)
  b.free(km.array([carry]))
  if not fwd:b.x(ctl)
  for q in win:b.cx(ctl,q)
  if not fwd:b.x(ctl)
 winrows={i for _,rows in wins for i in rows};big=[i for i in prm.rowsB if i not in winrows]
 def fold(idx,sub):
  k=wins[idx][0]-1;cq=store[idx]
  tgt=list(L[k:wins[idx-1][0]-1])+list(store[idx-1]) if idx else list(L[k:])
  src=list(cq)+[cq[-1]]*(len(tgt)-len(cq));bb.add(src[:len(tgt)],tgt,subtract=sub)
 if fwd:
  for i in big:row(i,list(L))
  for idx,(k,rows) in enumerate(wins):
   cq=list(b.alloc_qubits(cbits[idx]));store.append(cq)
   for i in rows:row(i,list(L[:k-1])+cq)
  for idx in reversed(range(len(wins))):fold(idx,False)
 else:
  for idx in range(len(wins)):fold(idx,True)
  for idx in reversed(range(len(wins))):
   k,rows=wins[idx]
   for i in reversed(rows):row(i,list(L[:k-1])+store[idx])
   b.free(km.array(store[idx]))
  store.clear()
  for i in reversed(big):row(i,list(L))


def generalized_win_step(bb, x, prm, op, L, wins, cbits, fwd, store, kbig=0, qcap=None):
    """Same windowed output Horner when the rounded bits are not exactly 13..0.

    The recipe schedule stays on win_step. This path is the explicit form of the
    upstream generalized outer step: missing operand bits are zeros, not a
    different algorithm.
    """
    b = bb.b
    assert kbig == 0 and qcap is None
    winrows = {i for _, rows in wins for i in rows}
    big = [i for i in prm.rowsB if i not in winrows]
    order = big + [i for _, rows in wins for i in rows]
    prior = {}
    active = set()
    for i in order:
        prior[i] = sorted(active)
        e = prm.eB(i) + 1
        if e < 0:
            continue
        if e < len(op):
            active.symmetric_difference_update({e})
        if 0 <= e - 1 < len(op):
            active.symmetric_difference_update({e - 1})

    def row(i, win):
        e = prm.eB(i) + 1
        ctl = x[i]
        if not fwd:
            b.x(ctl)
        for q in win:
            b.cx(ctl, q)
        if not fwd:
            b.x(ctl)
        bit = op[e] if 0 <= e < len(op) else None
        previous = op[e - 1] if 0 <= e - 1 < len(op) else None
        src = [op[p + e + 1] if 0 <= p + e + 1 < len(op) else None for p in range(len(win))]
        carry = None
        if bit is not None or previous is not None:
            carry = b.alloc_qubits(1)[0]
            js = set(prior[i])
            if bit is not None:
                js.symmetric_difference_update({e})

            def prepare():
                for k in sorted(js):
                    if 0 <= k < len(op) and op[k] is not None:
                        b.cx(op[k], ctl)
                if bit is not None and previous is not None:
                    b.cx(bit, previous)

            def undo():
                if bit is not None and previous is not None:
                    b.cx(bit, previous)
                for k in reversed(sorted(js)):
                    if 0 <= k < len(op) and op[k] is not None:
                        b.cx(op[k], ctl)

            prepare()
            b.init_and(ctl, previous if previous is not None else bit, carry)
            undo()
            if bit is not None:
                b.cx(bit, carry)
        bb.add(src, win, cin=carry)
        if carry is not None:
            if bit is not None:
                b.cx(bit, carry)
            prepare()
            b.del_and(ctl, previous if previous is not None else bit, carry)
            undo()
            b.free(km.array([carry]))
        if not fwd:
            b.x(ctl)
        for q in win:
            b.cx(ctl, q)
        if not fwd:
            b.x(ctl)

    def fold(idx, subtract):
        k = wins[idx][0] - 1
        cq = store[idx]
        target = list(L[k:wins[idx - 1][0] - 1]) + list(store[idx - 1]) if idx else list(L[k:])
        source = list(cq) + [cq[-1]] * (len(target) - len(cq))
        bb.add(source[:len(target)], target, subtract=subtract)

    if fwd:
        for i in big:
            row(i, list(L))
        for j, (k, rows) in enumerate(wins):
            reg = list(b.alloc_qubits(cbits[j]))
            store.append(reg)
            for i in rows:
                row(i, list(L[:k - 1]) + reg)
        for j in reversed(range(len(wins))):
            fold(j, False)
    else:
        for j in range(len(wins)):
            fold(j, True)
        for j in reversed(range(len(wins))):
            _k, rows = wins[j]
            for i in reversed(rows):
                row(i, list(L[:wins[j][0] - 1]) + store[j])
            b.free(km.array(store[j]))
        store.clear()
        for i in reversed(big):
            row(i, list(L))


def xor_output_lsb(b, prm, Tr, dest):
    """XOR (Y' - C0) & 1 onto dest.

    Each signed rounded row flips the accumulator LSB exactly when that
    rounded value is odd, and the sign is irrelevant mod 2. T's bit 0 is the
    virtual even bit, so it is not a wire. u is even, so this parity is L's LSB.
    """
    width = len(Tr) + 1

    def bit(k):
        if k <= 0 or k >= width:
            return None
        return Tr[k - 1]

    for i in prm.rowsB:
        shift = prm.eB(i) + 1
        if shift <= 0:
            continue
        hi = bit(shift)
        lo = bit(shift - 1)
        if hi is not None:
            b.cx(hi, dest)
        if lo is not None:
            b.cx(lo, dest)


def output_horner(bb, x, prm, op, L, wins, cbits, fwd, store, kbig=0, qcap=None):
    schedule = [prm.eB(i) + 1 for i in prm.rowsB]
    if prm.rowsB == tuple(range(14)) and schedule == list(range(13, -1, -1)):
        win_step(bb, x, prm, op, L, wins, cbits, fwd, store, kbig, qcap)
    else:
        generalized_win_step(bb, x, prm, op, L, wins, cbits, fwd, store, kbig, qcap)


def build_ladder(tables, prm, o, lay, angs):
    """sd-mode circuit with the H/L output split (px21 + fused phasing always on)."""
    bb = Bd.B()
    bb.cap = o.cap
    bb.prefix = int(getattr(o, "prefix", 0) or 0)
    b = bb.b
    x = b.create_quantum_register(22, name='x')
    f2, f4, f8, f16 = list(b.alloc_qubits(4))
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
    address = km.array(list(x[14:21]) + [x[21]])

    nT, n2, LB, nH = prm.nT, prm.F2 - 1, lay.LB, lay.nH
    Lr = b.alloc_qubits(LB-1); Hr = b.alloc_qubits(nH); Tr = b.alloc_qubits(nT-1); C2r = b.alloc_qubits(n2)
    target = km.array(list(Lr) + list(Hr) + list(Tr) + list(C2r))
    packed = [int(lay.u[a] >> 1) | (int(lay.H[a]) << (LB-1)) | (int(tables[a, 1] >> 1) << (LB-1 + nH)) | (int(tables[a, 2]) << (LB-1 + nH + nT-1))
              for a in range(256)]
    if getattr(o, "initial_lookup", False):
        unary_lookup(b, address, target, packed, last=bool(getattr(o, "last", False)))
    else:
        b.init_lookup(table=packed, address=address, target=target)
    bb.note(' lookup')
    flags4 = (f2, f4, f8, f16)

    def angfn(ang, off):
        def g(j):
            a = int(ang[off + j]) % (1 << 64) if off + j < len(ang) else 0
            return None if a == 0 else Fraction(2 * a, 1 << 64)
        return g

    # --- phase H (+ the constant 1/2 bit) right away, then free H by measurement-unlookup
    pad = b.alloc_qubits(lay.nHf - nH) if lay.nHf > nH else []
    cq = b.alloc_qubits(1)[0]; b.x(cq)
    ext = b.alloc_qubits(3)
    RH = list(Hr) + list(pad) + [cq] + list(ext)
    bb.label = 'Hphase'
    Bd.fused_phase(bb, RH, lay.nHf, angfn(angs[0], lay.S - prm.G0), flags4)
    b.free(ext); b.x(cq); b.free(km.array([cq]))
    if len(pad):
        b.free(pad)
    Htab = [int(lay.H[a]) for a in range(256)]
    if o.mdel:
        mH = measure(b, Hr)
        b.free(Hr)
    else:
        zpad = b.alloc_qubits(max(0, 12 - nH)) if nH < 12 else []
        b.del_lookup(table=Htab, address=address, target=km.array(list(Hr) + list(zpad)))
        b.free(Hr)
        if len(zpad):
            b.free(zpad)

    # --- Horner
    WA = o.WA if o.WA is not None else nT
    gA = b.alloc_qubits(o.gA) if WA < nT else []
    bb.label = 'A'
    virtual_inner(bb, x, prm, C2r, Tr, WA, gA, True)
    retire = int(getattr(o, "retire", 0) or 0)
    curvature_state = None
    if retire:
        # Measure the high curvature bits after the forward derivative step and
        # return those qubits before the output Horner. The reverse step reloads
        # the same table word; the measurement record is cleared with the lookup.
        curvature_keep = n2 - retire
        curvature_table = [int(tables[a, 2]) >> curvature_keep for a in range(len(tables))]
        curvature_mask = measure(b, C2r[curvature_keep:])
        curvature_low = list(C2r[:curvature_keep])
        b.free(C2r[curvature_keep:])
        curvature_state = (curvature_table, curvature_mask, curvature_low)
    bb.label = 'B'
    if o.wins:
        wstore = []
        output_horner(bb, x, prm, [None]+list(Tr), Lr, o.wins, o.wcb, True, wstore, o.kbig, o.qcap)
    else:
        Bd.sd_step(bb, x, prm.rowsB, Tr, Lr, prm.eB, LB, [], True, False)
    # --- phase L
    # Lr holds L >> 1. u is even, so it does not carry into bit 1, and L's LSB
    # is (Y' - C0) & 1. G0>=1 drops that bit. G0=0 phases it.
    ext = b.alloc_qubits(3)
    low_lsb = None
    if prm.G0 == 0:
        low_lsb = b.alloc_qubits(1)[0]
        xor_output_lsb(b, prm, Tr, low_lsb)
        data = [low_lsb] + list(Lr)
    else:
        data = list(Lr[prm.G0 - 1:])
    RL = data + list(ext)
    bb.label = 'Lphase'
    Bd.fused_phase(bb, RL, LB - prm.G0 - 1, angfn(angs[1], 0), flags4)
    b.free(ext)
    if low_lsb is not None:
        xor_output_lsb(b, prm, Tr, low_lsb)
        b.free(km.array([low_lsb]))
    if o.wins:
        output_horner(bb, x, prm, [None]+list(Tr), Lr, o.wins, o.wcb, False, wstore, o.kbig, o.qcap)
    else:
        Bd.sd_step(bb, x, prm.rowsB, Tr, Lr, prm.eB, LB, [], False, False)
    if curvature_state is not None:
        curvature_table, curvature_mask, curvature_low = curvature_state
        curvature_high = b.alloc_qubits(retire)
        unary_lookup(b, address, curvature_high, curvature_table, last=bool(getattr(o, "last", False)))
        C2r = km.array(list(curvature_low) + list(curvature_high))
    virtual_inner(bb, x, prm, C2r, Tr, WA, gA, False)
    if gA:
        b.free(gA)
    utab = [int(lay.u[a] >> 1) | (int(tables[a, 1] >> 1) << (LB-1)) | (int(tables[a, 2]) << (LB-1 + nT-1)) for a in range(256)]
    tgt2 = km.array(list(Lr) + list(Tr) + list(C2r))
    if o.mdel:
        mR = measure(b, tgt2)
        b.free(tgt2)
        groups = [(mH, Htab), (mR, utab)]
        if curvature_state is not None:
            groups.append((curvature_mask, curvature_table))
        mdel(b, address, groups)
    else:
        b.del_lookup(table=utab, address=address, target=tgt2)
        b.free(tgt2)
    b.cx(x[21],x[0])
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
    Bd.LAST_PEAK = bb.peak
    return b.finish_circuit()
