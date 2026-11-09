import kickmix as km, io, pickle
from collections import defaultdict
import numpy as np
c=km.Circuit.from_file('artifacts/20261108_public_frontier/release/invsqrt.kmb')
buf=io.StringIO(); c.to_file(buf, format='kmx')
ops=[l for l in buf.getvalue().splitlines() if l and not l.startswith(('APPEND','REGISTER'))]
# duplicates inside w8860
pos=defaultdict(list)
for i,l in enumerate(ops[8860:15800]):
    if l.startswith('CCX'): pos[l].append(8860+i)
print('--- w8860 repeated triples ---')
for k,v in sorted(pos.items()):
    if len(v)>1: print(k,v)
# global: for each CCX in w8860, all occurrences in full circuit
print('--- global occurrences of w8860 CCX triples (first 12 distinct) ---')
gpos=defaultdict(list)
for i,l in enumerate(ops):
    if l.startswith('CCX'): gpos[l].append(i)
seen=0
for k in pos:
    if seen>=12: break
    print(k, gpos[k][:8])
    seen+=1
# check [36305:49360]: any non-diagonal non-CX op?
from collections import Counter
print('--- w36305 full count ---')
print(Counter(l.split()[0] for l in ops[36305:49360]))
print('--- w36305 the 59 CX + 1 HMR ---')
for i,l in enumerate(ops[36305:49360]):
    if l.split()[0] in ('CX','HMR','X','CCX','CCZ','CSWAP','SWAP'):
        print(36305+i,l)
