import kickmix as km, io, pickle
import numpy as np
c=km.Circuit.from_file('artifacts/20261108_public_frontier/release/invsqrt.kmb')
buf=io.StringIO(); c.to_file(buf, format='kmx')
ops=[l for l in buf.getvalue().splitlines() if l and not l.startswith(('APPEND','REGISTER'))]
n_inputs=3133452; n_words=(n_inputs+63)//64
xs=np.arange(1,n_inputs+1,dtype=np.uint64)
pad=n_words*64-n_inputs
xs_pad=np.concatenate([xs,np.ones(pad,dtype=np.uint64)]) if pad else xs
shifts=np.arange(64,dtype=np.uint64)
q=[np.zeros(n_words,dtype=np.uint64) for _ in range(62)]
for bit in range(22):
    bval=((xs_pad>>bit)&1).astype(np.uint64)
    q[bit]=np.bitwise_or.reduce(bval.reshape(-1,64)<<shifts,axis=1)
last_mask=(np.uint64(1)<<np.uint64(n_inputs%64))-np.uint64(1)
ones=np.full(n_words,np.uint64(0xFFFFFFFFFFFFFFFF)); ones[-1]=last_mask
snaps={}
targets={25512,25641,27995,28198,25323,25615,25629,27998,28157,28001,28160,28035,28129,28031,28126,25699,28074,25704,28079,25670,28028}
depth=0
for idx,l in enumerate(ops):
    if idx in targets:
        snaps[idx]=[a.copy() for a in q]
    if l.startswith('PUSH_CONDITION'): depth+=1; continue
    if l.startswith('POP_CONDITION'): depth-=1; continue
    if depth>0 or (' if ' in l): continue
    p=l.split(); op=p[0]
    if op in ('HMR','R'): q[int(p[1][1:])].fill(0)
    elif op=='X':
        w=int(p[1][1:]); q[w]=q[w]^ones
    elif op=='CX':
        a,b=int(p[1][1:]),int(p[2][1:]); q[b]=q[b]^q[a]
    elif op=='SWAP':
        a,b=int(p[1][1:]),int(p[2][1:]); q[a],q[b]=q[b].copy(),q[a].copy()
    elif op=='CCX':
        a,b,t=int(p[1][1:]),int(p[2][1:]),int(p[3][1:]); q[t]=q[t]^(q[a]&q[b])
    elif op=='CSWAP':
        cc,a,b=int(p[1][1:]),int(p[2][1:]),int(p[3][1:])
        d=q[a]^q[b]; pr=q[cc]&d; q[a]=q[a]^pr; q[b]=q[b]^pr
pickle.dump({k:[a.tobytes() for a in v] for k,v in snaps.items()},open('/tmp/snaps.pkl','wb'))
print('saved',sorted(snaps.keys()))
