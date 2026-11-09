import kickmix as km, io
from collections import defaultdict
c=km.Circuit.from_file('artifacts/20261108_public_frontier/release/invsqrt.kmb')
buf=io.StringIO(); c.to_file(buf, format='kmx')
ops=[l for l in buf.getvalue().splitlines() if l and not l.startswith(('APPEND','REGISTER'))]
# duplicate CZ in w36305: CZ is self-inverse; pair cancels iff between them no op touching either qubit non-diagonally
# diagonal ops (Z, CZ, NEG, Z_POW, cond CZ/Z) commute. CX/SWAP/CCX/CCZ/HMR/R/X/CSWAP don't.
DIAG={'Z','CZ','NEG','Z_POW'}
pos=defaultdict(list)
for i,l in enumerate(ops[36305:49360]):
    p=l.split()
    if p[0]=='CZ' and ' if ' not in l and len(p)==3:
        a,b=p[1],p[2]
        key=(a,b) if a<b else (b,a)
        pos[key].append(36305+i)
dups={k:v for k,v in pos.items() if len(v)>=2}
print('distinct uncond CZ:',len(pos),'with >=2 occurrences:',len(dups))
shown=0
for k,v in sorted(dups.items(), key=lambda x:-len(x[1]))[:15]:
    print(k,'n=',len(v),v[:6])
