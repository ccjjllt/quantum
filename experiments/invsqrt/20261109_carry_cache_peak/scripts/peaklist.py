import kickmix as km, io
c=km.Circuit.from_file('artifacts/20261108_public_frontier/release/invsqrt.kmb')
buf=io.StringIO(); c.to_file(buf, format='kmx')
ops=[l for l in buf.getvalue().splitlines() if l and not l.startswith(('APPEND','REGISTER'))]
live=set(f'q{i}' for i in range(22))
lv=[0]*len(ops)
for idx in range(len(ops)-1,-1,-1):
    l=ops[idx]
    if l.startswith(('PUSH_CONDITION','POP_CONDITION')):
        lv[idx]=len(live); continue
    p=l.split(); op=p[0]
    cond=(' if ' in l)
    if op in ('HMR','R'):
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
    lv[idx]=len(live)
print('global max:',max(lv))
# intervals with lv==62
ints=[]; s=None
for i,v in enumerate(lv):
    if v==62 and s is None: s=i
    if v<62 and s is not None: ints.append((s,i-1)); s=None
if s is not None: ints.append((s,len(ops)-1))
print('n 62-peak intervals:',len(ints))
tot=sum(b-a+1 for a,b in ints)
print('total ops at 62-live:',tot)
for a,b in ints[:40]: print('  ',a,b,ops[a],'|||',ops[b])
