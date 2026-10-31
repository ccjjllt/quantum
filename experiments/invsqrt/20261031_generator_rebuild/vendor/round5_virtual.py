# SPDX-License-Identifier: Apache-2.0
"""Virtual bit for Marsyas signed rounded rows; Zongao Bian low-bit idea.

For an even anchor, omitted parity is the XOR of each preceding rounded
row parity T[e] XOR T[e-1], independent of the sign. For P equal to that
parity, carry = B XOR ((P XOR x[i] XOR B) AND (C XOR B)), with
B=T[e], C=T[e-1] (T[-1]=0). The same carry serves the inverse row. All original counters,
phase schedule, high split, source tables and model validation remain.
"""
import inspect

def install(H):
 import kickmix as km
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
   e=prm.eB(i)+1;bit=op[e];prior=op[e-1] if e else None;ctl=x[i]
   if not fwd:b.x(ctl)
   for q in win:b.cx(ctl,q)
   if not fwd:b.x(ctl)
   carry=b.alloc_qubits(1)[0]
   # J = P XOR control XOR B; D = C XOR B.
   js=set(parities[i]);js.symmetric_difference_update({e})
   for k in sorted(js):b.cx(op[k],ctl)
   if prior is not None:b.cx(bit,prior);d=prior
   else:d=bit
   b.init_and(ctl,d,carry)
   if prior is not None:b.cx(bit,prior)
   for k in reversed(sorted(js)):b.cx(op[k],ctl)
   b.cx(bit,carry)
   srcs=[op[p+e+1] if p+e+1<len(op) else None for p in range(len(win))]
   assert len(op)-e-1<=len(win)
   bb.add(srcs,win,cin=carry)
   b.cx(bit,carry)
   for k in sorted(js):b.cx(op[k],ctl)
   if prior is not None:b.cx(bit,prior)
   b.del_and(ctl,d,carry)
   if prior is not None:b.cx(bit,prior)
   for k in reversed(sorted(js)):b.cx(op[k],ctl)
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
 H.win_step=win_step
 source=inspect.getsource(H.build_hsplit)
 patches={
  'Lr = b.alloc_qubits(LB);':'Lr = b.alloc_qubits(LB-1);',
  'packed = [int(lay.u[a]) | (int(lay.H[a]) << LB) | (int(tables[a, 1]) << (LB + nH)) | (int(tables[a, 2]) << (LB + nH + nT))':'packed = [int(lay.u[a] >> 1) | (int(lay.H[a]) << (LB-1)) | (int(tables[a, 1]) << (LB-1 + nH)) | (int(tables[a, 2]) << (LB-1 + nH + nT))',
  'RL = list(Lr[prm.G0:]) + list(ext)':'RL = list(Lr[prm.G0-1:]) + list(ext)',
  'utab = [int(lay.u[a]) | (int(tables[a, 1]) << LB) | (int(tables[a, 2]) << (LB + nT))':'utab = [int(lay.u[a] >> 1) | (int(tables[a, 1]) << (LB-1)) | (int(tables[a, 2]) << (LB-1 + nT))',
 }
 for old,new in patches.items():
  assert source.count(old)==1,old
  source=source.replace(old,new)
 source=source.replace('    bb = Bd.B()','    assert prm.G0 == 1 and all(int(v)%2==0 for v in lay.u) and o.wins\n    bb = Bd.B()',1)
 exec(compile(source,'<marsyas-virtual-bit>','exec'),H.__dict__)
