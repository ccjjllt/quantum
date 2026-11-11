import json
SKIP=('APPEND','REGISTER','INFO_TAG','SEMANTIC','ANNOTATION')
KMX='/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_e9diff/e9.kmx'
cands={'q874':52030324,'q845':52030323,'q849':52030322,'q861':52030321,
 'q875':41176959,'q885':41176957,'q880':41176955,'q874e':41176953,'q881':41176951,
 'q859':41176949,'q849e':41176947,'q890':41176945,'q873':41176943,'q841':41176941,'q846':17640990}
Db=52227904; Eb=41187181
op_idx=-1
hits={q:0 for q in cands}
first={q:None for q in cands}
with open(KMX,errors='replace') as f:
    for raw in f:
        l=raw.rstrip('\n')
        if not l or l.startswith(SKIP): continue
        op_idx+=1
        p=l.split(); op=p[0]
        if op in ('BIT_STORE0','BIT_STORE1','BIT_INVERT','NEG','PUSH_CONDITION','POP_CONDITION'): continue
        toks=[t for t in p[1:] if t.startswith('q')]
        for q,birth in cands.items():
            qq=q.rstrip('e') if q.endswith('e') else q
            end=Db if birth>52000000 else Eb
            if birth<op_idx<end and qq in toks:
                hits[q]+=1
                if first[q] is None: first[q]=(op_idx,l[:70])
        if op_idx>Db: break
for q in cands:
    print(q,'birth',cands[q],'touches-in-gap:',hits[q],first[q])
