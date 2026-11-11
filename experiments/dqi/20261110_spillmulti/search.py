import json
SKIP=('APPEND','REGISTER','INFO_TAG','SEMANTIC','ANNOTATION')
KMX='/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_e9diff/e9.kmx'
cfg={
 'A':{'L':6633495,'b':6633494,'k':6634847,'v':'q852'},
 'B':{'L':52022399,'b':52022399,'k':52023752,'v':'q861'},
 'C':{'L':52028980,'b':52028979,'k':52030332,'v':'q881'},
 'D':{'L':52227905,'b':52227904,'k':52228189,'v':'q863'},
 'E':{'L':41187182,'b':41187181,'k':41187187,'v':'q878'},
}
N_Q=892
def writers(op,qs):
    # qubits whose computational value may change (conservative; cond ignored)
    if op=='X': return [qs[0]]
    if op=='CX': return [qs[1]]
    if op in ('CCX','CCX_CARRY'): return [qs[2]]
    if op in ('SWAP','CSWAP'): return list(qs)
    if op in ('R','HMR'): return [qs[0]]
    return []
last_aff_op=['']*N_Q; last_aff_idx=[-1]*N_Q
snap={}
inw={k:set() for k in cfg}
vwinlen={k:0 for k in cfg}
Bs=sorted(set(v['b'] for v in cfg.values()))
maxk=max(v['k'] for v in cfg.values())
op_idx=-1
with open(KMX,errors='replace') as f:
    for raw in f:
        l=raw.rstrip('\n')
        if not l or l.startswith(SKIP): continue
        op_idx+=1
        if op_idx in Bs:
            for k,v in cfg.items():
                if v['b']==op_idx:
                    snap[k]=(list(last_aff_op),list(last_aff_idx))
        if op_idx>maxk: break
        p=l.split(); op=p[0]
        if op in ('BIT_STORE0','BIT_STORE1','BIT_INVERT','NEG','PUSH_CONDITION','POP_CONDITION'):
            continue
        toks=[t for t in p[1:] if t.startswith('q')]
        qs=[]
        for t in toks:
            try: q=int(t[1:])
            except: continue
            if 0<=q<N_Q: qs.append(q)
        if not qs: continue
        for k,v in cfg.items():
            if v['b']<=op_idx<=v['k']:
                inw[k].update(qs)
                if v['v'] in toks: vwinlen[k]+=1
        if op in ('X','R','HMR','CX','CCX','CCX_CARRY','SWAP','CSWAP'):
            for q in writers(op,['q%d'%q for q in qs]):
                qi=int(q[1:]); last_aff_op[qi]=op; last_aff_idx[qi]=op_idx
        else:
            # unknown q-op: conservative all-write
            if op not in ('CZ','Z','CCZ'):
                for q in qs: last_aff_op[q]=op; last_aff_idx[q]=op_idx
out={}
for k,v in cfg.items():
    la,li=snap[k]
    cands=[]
    for q in range(N_Q):
        if q in inw[k]: continue
        if la[q] in ('R','HMR'):
            cands.append(['q%d'%q,la[q],li[q],v['b']-li[q]])
    cands.sort(key=lambda r:r[3])
    out[k]={'b':v['b'],'k':v['k'],'L':v['L'],'v':v['v'],
            'n_untouched':892-len(inw[k]),'n_borrow':len(cands),
            'borrows':cands[:40],'vwinlen':vwinlen[k]}
    print('====',k,'victim',v['v'],'untouched',892-len(inw[k]),'borrow-cands',len(cands),'vwinlen',vwinlen[k])
    for c in cands[:12]: print('   ',c)
json.dump(out, open("artifacts/20261110_spillmulti/search.json", "w"))
