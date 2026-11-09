import kickmix as km, io
c=km.Circuit.from_file('artifacts/20261108_public_frontier/release/invsqrt.kmb')
buf=io.StringIO(); c.to_file(buf, format='kmx')
ops=[l for l in buf.getvalue().splitlines() if l and not l.startswith(('APPEND','REGISTER'))]
targets={'q24':10205,'q26':12380,'q28':12768,'q29':11983,'q30':13154,'q31':11591,'q36':13909,'q37':9088,'q39':9471,'q43':14269,'q46':10582,'q47':13545,'q48':11216,'q49':9843,'q50':10864}
for t,last in sorted(targets.items(), key=lambda x:x[1]):
    nccx=0; ccxs=[]
    # scan forward from last to next HMR/R of t
    for j in range(last+1, len(ops)):
        l=ops[j]
        if l.startswith(('PUSH','POP')): continue
        p=l.split()
        if t not in p[1:]: continue
        op=p[0]
        if op in ('HMR','R'):
            print(t,'last_write',last,'-> erased',j,l,'fwd_ccx_into_t:',nccx, ccxs[:6])
            break
        if op=='CCX' and p[3]==t:
            nccx+=1; ccxs.append((j,l))
    else:
        print(t,'NO ERASE FOUND')
