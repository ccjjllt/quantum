import kickmix as km, io
c=km.Circuit.from_file('artifacts/20261108_public_frontier/release/invsqrt.kmb')
buf=io.StringIO(); c.to_file(buf, format='kmx')
ops=[l for l in buf.getvalue().splitlines() if l and not l.startswith(('APPEND','REGISTER'))]
live=set(f'q{i}' for i in range(22))
maxlive=22; maxidx=-1; maxset=None
in15900=None
for idx in range(len(ops)-1,-1,-1):
    l=ops[idx]
    if l.startswith(('PUSH_CONDITION','POP_CONDITION')): continue
    p=l.split(); op=p[0]
    cond=(' if ' in l)
    if op in ('BIT_STORE0','BIT_STORE1','BIT_STORE','BIT_INVERT','NEG','Z','CZ','Z_POW'):
        pass  # diagonal/classical: reads only (quantum state preserved) -> no liveness change
    elif op=='X':
        w=p[1]
        if not cond and w not in live:
            pass  # dead op
        # X always reads w; unconditional X never kills (read+written, value preserved in liveness sense)
    elif op in ('HMR','R'):
        w=p[1]
        if not cond: live.discard(w)
    elif op=='CX':
        a,b=p[1],p[2]
        if b in live: live.add(a)
        elif not cond:
            pass  # dead op, nothing
        else: live.add(a)  # conditional: reads a even if b dead... (b survives-if-not-fired; a read-if-fired)
        if cond: live.add(b)  # survives if not fired
    elif op=='SWAP':
        pass
    elif op=='CCX':
        a,b,t=p[1],p[2],p[3]
        if t in live or cond: live.add(a); live.add(b)
        if cond: live.add(t)
    elif op=='CSWAP':
        cc,a,b=p[1],p[2],p[3]
        if (a in live or b in live or cond): live.add(cc)
        if cond: live.add(a); live.add(b)
    else:
        pass
    if len(live)>maxlive:
        maxlive=len(live); maxidx=idx; maxset=sorted(live,key=lambda x:int(x[1:]))
print('true maxlive =',maxlive,'at idx',maxidx,':',ops[maxidx])
# max within [15900,16800]
live=set(f'q{i}' for i in range(22))
m2=0; mi2=-1
for idx in range(len(ops)-1,-1,-1):
    l=ops[idx]
    if l.startswith(('PUSH_CONDITION','POP_CONDITION')): continue
    p=l.split(); op=p[0]
    cond=(' if ' in l)
    if op in ('X','Z','CZ','Z_POW','NEG','BIT_STORE0','BIT_STORE1','BIT_INVERT'): pass
    elif op in ('HMR','R'):
        if not cond: live.discard(p[1])
    elif op=='CX':
        a,b=p[1],p[2]
        if b in live or cond: live.add(a)
        if cond: live.add(b)
    elif op=='CCX':
        a,b,t=p[1],p[2],p[3]
        if t in live or cond: live.add(a); live.add(b)
        if cond: live.add(t)
    elif op=='CSWAP':
        cc,a,b=p[1],p[2],p[3]
        if (a in live or b in live or cond): live.add(cc)
        if cond: live.add(a); live.add(b)
    if 15900<=idx<=16800 and len(live)>m2:
        m2=len(live); mi2=idx
print('maxlive in [15900,16800] =',m2,'at idx',mi2,':',ops[mi2] if mi2>=0 else None)
